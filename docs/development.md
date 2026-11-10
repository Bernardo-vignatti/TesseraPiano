# Desenvolvimento e distribuição

## Estrutura

`src/tessera_piano` contém modelo musical, importação, interpretação, agendamento, saída Windows, biblioteca, atualizações e interface QML. O player recebe uma agenda pronta; análise musical e importação acontecem fora da thread da interface.

`tests` cobre lógica e compatibilidade. `scripts/verify_ui.py` exercita a interface real com saída de teclado simulada. `packaging` contém o lançador, o instalador e textos de licença.

`repertoire` guarda as fontes MIDI/LilyPond e seus créditos, separadas dos recursos usados pelo aplicativo. Matrizes de arte, instaladores e relatórios locais ficam fora do Git. O ícone ICO contém os tamanhos de 16 a 256 px; somente o PNG usado pela interface acompanha o pacote.

O CI verifica o histórico com Gitleaks. A única exceção em `.gitleaksignore` corresponde ao mapa literal de teclas, revisado no commit inicial. Não são ignorados arquivos inteiros nem regras de credenciais. A auditoria anterior à 4.1 não encontrou credenciais ou dados pessoais do perfil no conteúdo público.

## Verificações

Na raiz, com as dependências do README instaladas:

```powershell
.venv\Scripts\python -m pytest -q
.venv\Scripts\ruff check src tests scripts packaging
.venv\Scripts\ruff format --check src tests scripts packaging
.venv\Scripts\python scripts\verify_ui.py
```

O teste de interface percorre o assistente, temas, menus, diálogos, seletores, faixas, bandeja e transporte. Confere foco, teclado, o bloqueio da última faixa e o painel compacto. Capturas ficam em `.local/previews`. Ele usa perfil temporário, renderização de software para resultados estáveis e não envia teclas ao sistema. Para conferir as janelas Windows, execute com `QT_QPA_PLATFORM=windows`; para escalas maiores, use `QT_SCALE_FACTOR`. Para abrir uma prévia manual isolada:

```powershell
.venv\Scripts\python -m tessera_piano --preview --profile .local\preview-profile
```

No CI, `TESSERA_TEST_REDUCED_MOTION=1` exercita os controles com movimento reduzido, evitando depender da sincronização de quadros de um servidor sem tela. A execução local mantém as transições para conferir as animações no desktop.

O caminho normal, sem `--preview`, envia entradas apenas após o usuário iniciar e selecionar o Roblox. Qualidade sonora, mapeamento e pedal devem ser conferidos no instrumento do jogo; testes simulados não verificam o áudio recebido.

No modo Guiado, apenas a entrada física é observada e a iluminação é enviada ao Chroma. `guided.py` não recebe uma saída de automação. Testes usam um leitor sem métodos de envio para verificar essa separação. F8 é uma solicitação separada do cancelamento imediato; Esc e a troca da janela continuam sendo emergências.

## Pacote musical opcional

`analysis.py` e `preparation.py` fazem análise e cache. O modelo é executado por `resources/model_worker.py` em outro processo, com ambiente offline e Python embarcado. O aplicativo principal não depende de PyTorch. O pacote guarda somente fontes e pesos públicos fixados por revisão, bibliotecas CPU e licenças; músicas e perfis não entram nele.

Para compilar o pacote separado no Windows, com Python 3.12 disponível:

```powershell
.venv\Scripts\python scripts\build_model_pack.py --key-file CAMINHO_DA_CHAVE_PRIVADA
```

O script usa `packaging/model-requirements.lock`, cria o runtime em `.local/model-build`, executa uma inferência real com notas conhecidas e gera `.local/model-release/pianist-cpu-1.zip` e `models.json`. A chave deve corresponder à chave pública do app e ficar fora do projeto. O manifesto assina origem, versão, tamanho e hash. Publique ambos como assets da release indicada em `model_pack.py`, junto ao instalador. O download é validado antes de extrair, com bloqueio de caminhos externos e limite de tamanho descompactado.

No ensaio local, um trecho de 120 notas foi preservado pelo modelo em CPU; após o aquecimento do runtime, preparação levou cerca de 15 s, pico de memória de 1,1 GiB e leitura do cache de 7 ms. Esses valores descrevem esse ensaio, não uma garantia para outros computadores ou músicas. A sequência física de números, letras e modificadores do Chroma foi confirmada em um Cynosa Chroma. A naturalidade sonora no jogo requer escuta; outros modelos de teclado precisam de validação física.

## Compilar

Instale [Inno Setup 6](https://jrsoftware.org/isinfo.php). No Windows:

```powershell
.venv\Scripts\python scripts\build.py
```

Use `--iscc CAMINHO` se o compilador estiver fora do local padrão. O script executa PyInstaller, verifica a inicialização do executável compilado e gera `dist/TesseraPiano-Setup-VERSÃO-x64.exe`. A distribuição usa bibliotecas Qt compartilhadas e inclui suas licenças. O instalador não tem certificado de assinatura de editor do Windows.

## Publicar uma versão

Atualize `src/tessera_piano/__init__.py` e o changelog. Execute as verificações e crie uma tag `vVERSÃO`. O pacote e o instalador usam essa definição de versão. O workflow constrói o instalador e o manifesto em uma release de rascunho, que ainda não é oferecida pelo atualizador.

Tags com hífen são publicadas como pré-lançamento após a validação. O canal Estável consulta somente releases estáveis; o canal Beta também admite pré-lançamentos autenticados. O instalador da beta não torna essa versão a mais recente do canal estável.

Baixe os arquivos desse rascunho, confira o manifesto e execute `scripts/verify_installation.py --baseline INSTALADOR_ANTERIOR --installer INSTALADOR_NOVO`. O ensaio usa diretórios temporários e verifica instalação, recuperação, preferências, músicas e remoção de recursos obsoletos. Após passar, publique o rascunho como release mais recente no GitHub. O workflow não publica antes dessa conferência.

A chave Ed25519 privada fica no secret `TESSERA_SIGNING_KEY` do GitHub Actions; somente a chave pública está no aplicativo. A chave precisa corresponder a `update_trust.py`. Não grave chaves privadas no repositório nem nos artefatos. Se o secret não existir, o workflow falha antes de publicar.

Para uma publicação local autorizada, `scripts/sign_release.py INSTALADOR --key-file CAMINHO` gera `dist/update.json` e o checksum. Publique esses arquivos junto do instalador na release correspondente. O manifesto assina versão, origem, tamanho e hash.

## Atualização e recuperação

O aplicativo consulta releases públicas do canal estável e rejeita versões iguais ou anteriores. Após o download, confere a assinatura e o arquivo novamente antes de iniciar a instalação.

O auxiliar PowerShell espera o aplicativo encerrar, guarda uma cópia da instalação e das preferências, executa o instalador e verifica a nova versão em um perfil temporário. Se instalação ou verificação falharem, restaura os arquivos anteriores e reinicia o aplicativo. Resultado e log ficam em `updates` dentro do perfil. A primeira atualização a partir da versão 3.1 exige executar o novo instalador.

As preferências antigas recebem um backup antes da migração. A configuração de pedal existente é preservada; o assistente permite escolher explicitamente o modo Automático.
