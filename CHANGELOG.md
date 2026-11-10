# Alterações

## 4.2.0-beta.2

- Praticar mantém a tecla esperada e seus modificadores acesos enquanto aguarda o toque. A compensação de atraso fica restrita ao modo Acompanhar.
- A sessão Chroma reaplica a iluminação enquanto aguarda, mesmo quando a tecla esperada continua a mesma.

## 4.2.0-beta.1

- Análise de andamento, frases e harmonia; perfis Contido, Cantabile e Rítmico com interpretação salva por música.
- Motor opcional Pianist Transformer em CPU, executado offline em processo separado. Pacote autenticado, progresso, cancelamento e alternativa explícita por regras.
- Pedal automático considera contexto harmônico, articulação e pausas. Eventos MIDI intencionais continuam preservados no modo Apenas MIDI.
- Modo guiado Razer Chroma: acompanhar o ritmo ou praticar aguardando as teclas e o pedal corretos, sem injetar comandos.
- Calibração de iluminação, modificadores, antecedência, brilho, paletas, compensação de atraso e mapa físico ajustável.
- Verificação de combinações incompatíveis, melodia simplificada e repetição de trechos A/B.
- F8 encerra com uma curta desaceleração e liberação das notas e do pedal. Segundo F8, Esc e perda de foco interrompem imediatamente.
- Canal Beta separado do Estável; a versão 4.1.1 continua disponível para quem usa o canal estável.

O motor é experimental: download adicional de aproximadamente 480 MiB, cerca de 1,6 GiB instalados. A primeira preparação ocorre antes de tocar e pode levar minutos em músicas longas; resultados válidos são reutilizados. O teclado comum não oferece intensidade de ataque nem meio pedal no jogo. A sequência de LEDs foi confirmada em um Cynosa Chroma; outros modelos dependem da compatibilidade com a API e da calibração física.

## 4.1.1

- Nova identidade visual com grafite, marfim, iluminação âmbar e teclado com profundidade, nos temas claro e escuro.
- Painel de interpretação lateral que recolhe em janelas menores; biblioteca e primeiro uso seguem o mesmo padrão.
- Menus, seletores, campos, diálogos e controles padronizados, com transições suaves e redução de movimento.
- Correções de foco e navegação por teclado; seleção de faixas mantém pelo menos uma faixa ativa.
- Menu da bandeja acompanha o tema e habilita reprodução e parada conforme o estado do aplicativo.
- Fontes musicais e recursos de instalação separados do pacote; arte e ícones redundantes removidos. Créditos preservados.
- Verificação de segredos no histórico pelo CI. Atualizações removem recursos obsoletos da instalação anterior.

## 4.1.0

Candidata não distribuída, substituída pela 4.1.1.

## 4.0.1

- O pedal automático reconhece MIDIs com apenas um reset CC64 inicial e gera sustentação para esses arquivos.
- A versão do pacote e do instalador passam a usar a mesma definição do aplicativo.

## 4.0.0

- Interface Qt Quick com temas claro, escuro e do sistema, navegação por teclado e redução de movimento.
- Configuração de primeiro uso, modo bandeja e importação por arrastar arquivos.
- Interpretações Original, Natural e Expressivo, com fraseado, articulação e variação reproduzível.
- Pedal automático para músicas sem CC64 e estados explícitos de sustentação para Visual Pianos.
- Importação MIDI com preservação da origem, faixas, canais e mapa de andamento.
- Importação e preparação em segundo plano; duração total consistente com o fim do arquivo.
- Atualização pelo GitHub com manifesto assinado, verificação de integridade e recuperação da instalação.
- Migração da biblioteca 3.1 preservando favoritos, nomes personalizados e exclusões reversíveis.
- Build Windows, testes e documentação reorganizados.

## 3.1.0

Suporte a 61/88 teclas, pedal CC64, alturas originais, renomeação e exclusão reversível na biblioteca.
