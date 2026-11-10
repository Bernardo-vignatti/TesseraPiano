"""Saída Razer Chroma local. Um único trabalhador possui a sessão do SDK."""

import json
import threading
import time
from urllib.parse import urlparse
from urllib.request import Request, ProxyHandler, build_opener

KEY_POSITIONS = {}
for row, start, keys in (
    (1, 2, "1234567890"),
    (2, 2, "qwertyuiop"),
    (3, 2, "asdfghjkl"),
    (4, 3, "zxcvbnm"),
):
    KEY_POSITIONS.update({key: (row, start + i) for i, key in enumerate(keys)})
KEY_POSITIONS.update({"shift": (4, 1), "ctrl": (5, 1), "space": (5, 7)})


class Chroma:
    def __init__(self, positions=None, brightness=70):
        self.positions = dict(KEY_POSITIONS, **(positions or {}))
        self.brightness = max(0, min(100, brightness)) / 100
        self.pending = {}
        self.condition = threading.Condition()
        self.closed = False
        self.failure = None
        self.ready = threading.Event()
        self.uri = None
        self.effect = None
        self.opener = build_opener(ProxyHandler({}))

    def request(self, method, url, body=None):
        request = Request(
            url,
            data=json.dumps(body).encode() if body is not None else None,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        with self.opener.open(request, timeout=1) as response:
            data = response.read(65537)
        if len(data) > 65536:
            raise OSError("Resposta Chroma inválida.")
        result = json.loads(data) if data else {}
        if result.get("result", 0) != 0:
            raise OSError(f"Chroma recusou o efeito ({result['result']}).")
        return result

    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True, name="tessera-chroma")
        self.thread.start()
        if not self.ready.wait(5) or self.failure:
            self.close()
            raise OSError(
                "Não foi possível ativar o Chroma. Confira o serviço e a permissão no aplicativo Razer."
            ) from self.failure
        return self

    def frame(self, colors):
        if self.failure:
            raise OSError("A conexão com o Chroma foi interrompida.") from self.failure
        with self.condition:
            self.pending = dict(colors)
            self.condition.notify()

    def parameters(self, colors, effect):
        grid = [[0] * 22 for _ in range(6)]
        for key, rgb in colors.items():
            if key in self.positions:
                row, col = self.positions[key]
                r, g, b = (round(max(0, min(255, c)) * self.brightness) for c in rgb)
                grid[row][col] = r | (g << 8) | (b << 16)
        if effect == "CHROMA_CUSTOM":
            return grid
        return {
            "color": [
                [0] * (24 if effect == "CHROMA_CUSTOM2" else 22)
                for _ in range(8 if effect == "CHROMA_CUSTOM2" else 6)
            ],
            "key": [[c | 0x01000000 for c in row] for row in grid],
        }

    def run(self):
        try:
            result = self.request(
                "POST",
                "http://localhost:54235/razer/chromasdk",
                {
                    "title": "Tessera Piano",
                    "description": "Orientação musical por tecla",
                    "author": {
                        "name": "Tessera Piano",
                        "contact": "https://github.com/Bernardo-vignatti/TesseraPiano",
                    },
                    "device_supported": ["keyboard"],
                    "category": "application",
                },
            )
            uri = result["uri"]
            parsed = urlparse(uri)
            if (
                parsed.scheme != "http"
                or parsed.hostname not in ("localhost", "127.0.0.1", "::1")
                or parsed.username
                or parsed.password
                or not parsed.port
            ):
                raise OSError("O SDK não retornou uma sessão local válida.")
            self.uri = uri.rstrip("/")
            for effect in ("CHROMA_CUSTOM_KEY", "CHROMA_CUSTOM2", "CHROMA_CUSTOM"):
                try:
                    self.request(
                        "PUT",
                        self.uri + "/keyboard",
                        {"effect": effect, "param": self.parameters({}, effect)},
                    )
                    self.effect = effect
                    break
                except OSError:
                    continue
            if not self.effect:
                raise OSError("Iluminação individual indisponível.")
            self.ready.set()
            heartbeat = 0
            sent = None
            while True:
                with self.condition:
                    self.condition.wait(0.033)
                    if self.closed:
                        break
                    colors = self.pending
                refresh = time.monotonic() - heartbeat >= 1
                # No modo Praticar, o mesmo quadro pode ficar ativo até o músico responder.
                if colors != sent or (colors and refresh):
                    self.request(
                        "PUT",
                        self.uri + "/keyboard",
                        {"effect": self.effect, "param": self.parameters(colors, self.effect)},
                    )
                    sent = colors
                if refresh:
                    self.request("PUT", self.uri + "/heartbeat")
                    heartbeat = time.monotonic()
        except Exception as exc:
            self.failure = exc
        finally:
            self.ready.set()
            if self.uri:
                try:
                    self.request("DELETE", self.uri)
                except Exception:
                    pass

    def close(self):
        with self.condition:
            self.closed = True
            self.condition.notify()
        if hasattr(self, "thread"):
            self.thread.join(2)

    def __enter__(self):
        return self.start()

    def __exit__(self, *args):
        self.close()
