# Desenvolvimento e distribuição

## Estrutura

`src/tessera_piano` contém modelo musical, importação, interpretação, agendamento, saída Windows, biblioteca, atualizações e interface QML. O player recebe uma agenda pronta; análise musical e importação acontecem fora da thread da interface.

`tests` cobre lógica e compatibilidade. `scripts/verify_ui.py` exercita a interface real com saída de teclado simulada. `packaging` contém o lançador, o instalador e textos de licença.

## Verificações

Na raiz, com as dependências do README instaladas:

```powershell
.venv\Scripts\python -m pytest -q
.venv\Scripts\ruff check src tests scripts packaging
.venv\Scripts\ruff format --check src tests scripts packaging
.venv\Scripts\python scripts\verify_ui.py
```

O teste de interface percorre o assistente inicial, temas, páginas, importação, biblioteca e parada. Capturas ficam em `.local/previews`. Ele usa perfil temporário e não envia teclas ao sistema. Para abrir uma prévia manual isolada:

```powershell
.venv\Scripts\python -m tessera_piano --preview --profile .local\preview-profile
```

O caminho normal, sem `--preview`, envia entradas apenas após o usuário iniciar e selecionar o Roblox. Qualidade sonora, mapeamento e pedal devem ser conferidos no instrumento do jogo; testes simulados não verificam o áudio recebido.

## Compilar

Instale [Inno Setup 6](https://jrsoftware.org/isinfo.php). No Windows:

```powershell
.venv\Scripts\python scripts\build.py
```

Use `--iscc CAMINHO` se o compilador estiver fora do local padrão. O script executa PyInstaller, verifica a inicialização do executável compilado e gera `dist/TesseraPiano-Setup-VERSÃO-x64.exe`. A distribuição usa bibliotecas Qt compartilhadas e inclui suas licenças. O instalador não tem certificado de assinatura de editor do Windows.

## Publicar uma versão

Atualize `src/tessera_piano/__init__.py`, `pyproject.toml` e o changelog. Execute as verificações e crie uma tag `vVERSÃO`. O workflow de release constrói o instalador e o manifesto.

A chave Ed25519 privada fica no secret `TESSERA_SIGNING_KEY` do GitHub Actions; somente a chave pública está no aplicativo. A chave precisa corresponder a `update_trust.py`. Não grave chaves privadas no repositório nem nos artefatos. Se o secret não existir, o workflow falha antes de publicar.

Para uma publicação local autorizada, `scripts/sign_release.py INSTALADOR --key-file CAMINHO` gera `dist/update.json` e o checksum. Publique esses arquivos junto do instalador na release correspondente. O manifesto assina versão, origem, tamanho e hash.

## Atualização e recuperação

O aplicativo consulta releases públicas do canal estável e rejeita versões iguais ou anteriores. Após o download, confere a assinatura e o arquivo novamente antes de iniciar a instalação.

O auxiliar PowerShell espera o aplicativo encerrar, guarda uma cópia da instalação e das preferências, executa o instalador e verifica a nova versão em um perfil temporário. Se instalação ou verificação falharem, restaura os arquivos anteriores e reinicia o aplicativo. Resultado e log ficam em `updates` dentro do perfil. A primeira atualização a partir da versão 3.1 exige executar o novo instalador.

As preferências antigas recebem um backup antes da migração. A configuração de pedal existente é preservada; o assistente permite escolher explicitamente o modo Automático.
