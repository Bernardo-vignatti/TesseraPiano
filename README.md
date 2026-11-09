# Tessera Piano

Biblioteca de músicas e interpretação por teclado para [Visual Pianos](https://www.roblox.com/games/5593470048/Visual-Pianos) e pianos compatíveis no Roblox. Aplicativo para Windows 10/11 de 64 bits, com interface Qt Quick.

![Reprodução no Tessera Piano](docs/images/player.png)

## Instalação

Baixe o instalador na página de [Releases](https://github.com/Bernardo-vignatti/TesseraPiano/releases/latest). Python e as bibliotecas necessárias já acompanham o aplicativo.

Na primeira abertura, configure aparência, alcance do piano, interpretação e bandeja. Você também pode começar com os padrões e voltar ao assistente nas configurações.

## Como tocar

1. Importe um MIDI, `piano.json` ou partitura TXT, ou escolha uma música da coleção.
2. Escolha o alcance de 61 ou 88 teclas. Para 88, ative também **88key** no jogo.
3. Abra o piano no Roblox e feche o chat.
4. Pressione **F6** e selecione o jogo durante a contagem.
5. Use **F8** ou **Esc** para interromper. Mudar de janela durante a execução também interrompe o envio.

O aplicativo verifica se a janela selecionada pertence ao Roblox. Ele envia teclas pelo Windows, sem acessar a memória do jogo.

## Interpretação e pedal

- **Original:** mantém tempos e articulações, com as adaptações necessárias ao teclado físico.
- **Natural:** acrescenta fraseado discreto e pequenas diferenças de ataque.
- **Expressivo:** aumenta a presença dessas variações. A intensidade é ajustável.

O modo de pedal **Automático** usa CC64 quando presente e gera pedalização contextual quando o arquivo não tem esse controle. **Apenas MIDI**, **Ligado**, **Desligado** e **Manual** também estão disponíveis.

No Visual Pianos, **Espaço solto liga a sustentação; Espaço segurado desliga**. Os testes de pedal e alcance nas configurações ajudam a conferir a resposta do instrumento. O teclado comum não transmite velocity; o volume das notas depende da entrada oferecida pelo jogo.

Importações antigas continuam funcionando. Para recuperar faixas, alturas ou pedal que uma versão antiga não guardou, reimporte o MIDI original. Novas importações preservam uma cópia da origem.

## Biblioteca e preferências

Os dados ficam em `%LOCALAPPDATA%\TesseraPiano`. Atualização e desinstalação preservam essa pasta. Favoritos, nomes personalizados e exclusões reversíveis continuam disponíveis após migrar da versão 3.1.

Temas claro, escuro e do sistema, redução de movimento, atalhos, importação por arrastar arquivos e modo bandeja estão nas configurações. **Ctrl+O** importa; **Ctrl+F** busca; **Ctrl+,** abre configurações.

O aplicativo consulta novas releases no GitHub quando essa opção está ativada. Downloads são autenticados com manifesto assinado e SHA-256; a instalação acontece quando você escolher atualizar. Músicas e preferências não são enviadas. Não há telemetria.

## Desenvolvimento

Python 3.12 e um ambiente virtual:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.lock
.venv\Scripts\python -m pip install -e . --no-deps
.venv\Scripts\python -m tessera_piano
```

Consulte [desenvolvimento e distribuição](docs/development.md) para testes, prévia sem envio de teclas, compilação e publicação.

## Licença

O código próprio é [MIT](LICENSE). Músicas e dependências mantêm suas [licenças e atribuições](THIRD_PARTY_NOTICES.md).
