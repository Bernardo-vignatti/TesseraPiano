# Verificação das versões 4.0 e 4.0.1

## 4.0.1

- 83 testes de lógica e 27 subtestes passaram, incluindo o caso de MIDI com reset CC64 inicial.
- A compilação e a publicação automatizadas passaram no [GitHub Actions](https://github.com/Bernardo-vignatti/TesseraPiano/actions/runs/42703098153).
- O cliente configurado como versão 4.0.0 encontrou a 4.0.1 pela API pública. Assinatura e SHA-256 dos dois instaladores públicos foram verificados pelo código do atualizador.
- Os instaladores baixados das releases 4.0.0 e 4.0.1 passaram pelo ensaio de atualização e restauração, preservando preferências e o registro da instalação existente.

## 4.0.0

Executada no Windows 10 x64, com Python 3.12 e Qt 6.12.

- 82 testes de lógica passaram, além de 27 subtestes de compatibilidade.
- O teste QML percorreu configuração inicial, quatro páginas, temas claro e escuro, importação, favoritos, renomeação, exclusão reversível, reprodução simulada e parada.
- A interface foi renderizada em escala de 100%, 150% e 200%, incluindo janelas de 1040×720 e 1600×1000.
- O executável empacotado iniciou sem depender de Python externo.
- Instalação, atualização e restauração foram exercitadas em diretório e perfil isolados. Preferências e o registro da instalação existente foram preservados.
- O ensaio usou um build de referência 3.9.0 e o instalador 4.0.0. A versão 3.9.0 foi criada somente para esse teste, sem publicação.
- Uma divergência forçada de versão na verificação acionou a recuperação do executável anterior.

O envio nos testes de interface é simulado. A resposta sonora, o mapeamento e a naturalidade precisam de conferência no piano do Roblox. A entrada distribuída nesta versão é por teclado; ela não transmite velocity MIDI.

Comandos reproduzíveis e o processo de distribuição estão em [development.md](development.md). Capturas e relatórios locais ficam em `.local`; instaladores, em `dist`.
