# Interpretação local e prática Chroma

Proposta de implementação para aprovação. Base: 4.1.1, analisada em 10/11/2026. Nenhuma alteração no funcionamento do aplicativo nesta etapa.

## Escopo confirmado

Analisar os MIDI e as partituras já aceitas pelo Tessera, preparar interpretações mais naturais e acrescentar orientação luminosa em teclados Razer Chroma compatíveis. Reconhecimento de áudio e identificação de títulos por uma gravação ficam fora deste trabalho.

O teclado de referência do usuário é o Cynosa Chroma. A integração deve atender outros modelos compatíveis, com iluminação individual e todas as teclas e combinações exigidas pelo mapa escolhido. As 88 notas usam o mapa existente com Shift/Ctrl; não exigem 88 teclas físicas distintas.

## O que existe

- `midi.py` preserva tempo, compasso, intensidade, faixas e eventos CC64. `music.py` separa duração sonora e duração da tecla pressionada.
- `performance.py` aplica regras de fraseado, pequenas variações e pedal harmônico. Não usa aprendizagem de máquina. A referência rítmica atual considera principalmente o primeiro andamento.
- `Controller.prepare()` prepara a música fora da interface. `playback.py` agenda eventos por relógio monotônico e interrompe ao perder o foco do alvo.
- `keyboard_windows.py` envia teclas e representa corretamente o pedal invertido do jogo: Espaço solto liga a sustentação; pressionado desliga. A saída não transmite velocity.
- `prepare_keyboard()` adapta colisões de teclas físicas. Uma adaptação executável por automação não é necessariamente confortável ou possível para uma pessoa.

## Interpretação automática

### Análise e preparação

1. Conservar a fonte intacta e atribuir identidades estáveis às notas. Usar alturas originais e faixas selecionadas antes de adaptar oitavas ao teclado do jogo.
2. Construir uma linha musical por batidas, usando todo o mapa de tempo e compasso. Quando faltarem marcações, estimar a pulsação com confiança explícita, sem quantizar indiscriminadamente gravações expressivas.
3. Estimar acordes e inversões por janelas de contexto, baixo e notas sustentadas; distinguir notas de passagem. Extrair melodia/acompanhamento prováveis, densidade, pausas, frases e mudanças de seção.
4. Sugerir um perfil de execução pela textura: contido, cantabile ou rítmico. Essa classificação inicial será uma análise explicável por características, não uma alegação de reconhecer com certeza gênero, compositor ou título. O usuário pode corrigir a escolha.
5. Gerar a interpretação completa antes de tocar, com progresso e cancelamento. Guardar a análise e a agenda no perfil local, indexadas por conteúdo, faixas, configuração, versão do analisador e do modelo. Selecionar novamente uma música reutiliza o resultado válido.

### Modelo já treinado

O primeiro candidato para a prova técnica é o **Pianist Transformer, checkpoint rendering**. O projeto recebe MIDI, oferece inferência em CPU e possui pesos publicados. O repositório e a ficha dos pesos declaram Apache-2.0. O modelo tem aproximadamente 135 milhões de parâmetros; o autor informa cerca de 270 MB para os pesos. O ambiente de inferência ocupa espaço adicional e o desempenho no Windows do usuário ainda precisa ser medido. [Projeto](https://github.com/yhj137/PianistTransformer), [pesos](https://huggingface.co/yhj137/pianist-transformer-rendering), [exemplo em CPU](https://github.com/yhj137/PianistTransformer/blob/main/src/inference/inference.py).

Usar um processo separado e um pacote opcional de inferência, instalado pelo aplicativo, com origem, versão e integridade verificadas. Não incorporar o ambiente completo de pesquisa, treinamento, telemetria ou outra biblioteca de interface ao app. Depois da instalação do pacote, a análise funciona offline e não envia músicas. Manter o núcleo do Tessera sob MIT e distribuir as licenças e créditos próprios das dependências.

A adoção depende de comprovar: execução em CPU no Windows, memória e tempo aceitáveis, preservação das notas e melhoria audível depois da conversão para o Roblox. Exportação ONNX e quantização serão avaliadas somente se necessárias e viáveis; não são premissas do plano.

O modelo sugere expressão; análise de acordes e seleção dos perfis são etapas separadas. Não pressupor que os pesos já oferecem controle de gêneros. Conferir correspondência com as notas originais e rejeitar resultados que percam notas, acrescentem material indevido ou gerem tempos inválidos. O processamento de referência do modelo mescla instrumentos e trata sobreposições: o adaptador deve conservar a identidade e as escolhas de faixas do Tessera.

Em falha ou ausência do pacote, continuar com o motor por regras, identificando a origem da interpretação. Essa alternativa não será apresentada como resultado de um modelo treinado.

### Fraseado e imperfeições

- Combinar curvas de andamento por frase, respirações, articulação e pequenos desencontros entre vozes. Variações devem ter continuidade musical e limites por contexto, sem somar aleatoriedade independente em cada nota.
- Preservar execução expressiva existente; dosar a transformação para não humanizar duas vezes. Não acrescentar a variação atual integralmente por cima da saída do modelo.
- Presets acompanham o app; a escolha automática e os resultados preparados ficam salvos por música. Um controle de expressão permite ajustes e uma semente conserva uma execução reproduzível. Gerar nova variação é uma ação explícita.
- Erros de nota e omissões ficam desligados por padrão. Uma opção avançada de imperfeições pode admitir ocorrências raras e limitadas, sem alterar a fonte. Naturalidade será avaliada também sem esses erros.

### Pedal

Classificar os eventos de origem: execução utilizável, ausentes, resets iniciais ou sinais suspeitos. No modo MIDI, preservar a intenção explícita de desligar o pedal. No Automático, decidir com contexto e confiança; não transformar todo arquivo sem pedal em sustentação permanente.

Planejar as trocas por harmonia, baixo, articulação, pausas e estilo, incluindo repedalização depois do ataque quando musicalmente apropriada. Reduzir sustentação em passagens densas e separar duração da tecla de duração sonora. Converter a curva prevista em estados binários com histerese e intervalo mínimo entre trocas, evitando oscilações do Espaço. Notas e pedal seguem a mesma transformação temporal, inclusive ao mudar a velocidade ou iniciar de outro ponto.

Calibrar a resposta do instrumento e a latência percebida. No protocolo atual não há meio pedal nem intensidade de ataque variável. O objetivo verificável é uma execução mais convincente nos recursos disponíveis; não prometer realismo de 100% ou equivalência a um piano acústico.

## Modo guiado Razer Chroma

### Compatibilidade e conexão

Usar inicialmente a API REST local oficial, restrita ao dispositivo teclado. Ela oferece efeitos por tecla, sessão e manutenção da conexão. Negociar o efeito suportado, verificar falhas e encerrar a sessão ao sair para devolver o controle da iluminação ao software Razer. Não prometer restaurar uma fotografia exata do perfil anterior. [Sessão](https://assets.razerzone.com/dev_portal/REST/html/index.html), [efeitos](https://assets.razerzone.com/dev_portal/REST/html/md__r_e_s_t_external_03_keyboard.html).

O assistente verifica serviço Razer, iluminação individual, disposição física e teclas exigidas, com uma sequência curta de confirmação visual. Oferecer mapeamento/calibração para ANSI, ISO e ABNT2; o layout do Cynosa do usuário ainda não foi informado. Outros formatos entram por capacidade, sem prender o código a um único modelo. Um retorno de sucesso do SDK, sozinho, não comprova que as luzes físicas funcionaram.

O Cynosa Chroma tem iluminação individual e rollover anunciado de dez teclas. Considerar modificadores e Espaço na avaliação dos acordes; confirmar combinações reais na calibração. [Especificações Razer](https://mysupport.razer.com/app/answers/detail/a_id/3606/~/razer-cynosa-chroma-%7C-rz03-0226x-support-%26-faqs).

### Experiência

- **Acompanhar:** a música avança no ritmo escolhido. Pré-iluminação discreta antecipa o próximo grupo; brilho e pulso indicam o ataque; a luz mantida orienta a sustentação e seu fim indica soltar. Ajustar antecedência, brilho e compensação de atraso.
- **Praticar:** aguardar o grupo correto antes de avançar, com tolerância para acordes. Permitir escolher faixas/mãos quando identificáveis, velocidade reduzida, repetição de trecho e progressão de velocidade opcional.
- Usar poucas cores configuráveis, com intensidade/pulso para reforçar o significado. Dar prioridade ao grupo atual se a mesma tecla reaparecer na antecipação.
- Iluminar também Shift/Ctrl e orientar o Espaço pela ação física: manter pressionado desliga o pedal; soltar religa. Identificar claramente conflitos entre notas que compartilham uma tecla ou exigem estados incompatíveis de modificadores.
- Conferir executabilidade manual e sugerir, com escolha explícita, um arranjo simplificado ou acorde distribuído. Não aplicar silenciosamente os pequenos deslocamentos usados pelo automático nem exigir acordes impossíveis.
- Feedback breve de antecipação/atraso e acerto de teclas, com resumo ao terminar. Ele mede entrada física; não comprova o áudio recebido no Roblox.

Nesse modo, o app não injeta notas nem pedal: a pessoa toca. A primeira versão não terá acompanhamento automático de outra mão ou pedal assistido. Ler pressionamentos e solturas pela entrada Windows separada do SDK de luzes, somente durante a sessão e com o alvo em foco, sem bloquear as teclas que seguem para o jogo ou registrar digitação externa.

Notas, orientação e avaliação compartilham o relógio musical. A saída Chroma trabalha em um trabalhador separado, inicialmente até 30 quadros/s, com atualização do estado mais recente e sem fila crescente de quadros atrasados. A antecedência de leitura e a latência das luzes serão calibradas no teclado físico. Ao trocar de janela, pausar a sessão; desconexão, bloqueio do Windows, reconexão e encerramento devem liberar recursos.

## Integração e interface

Reaproveitar `Song`, importação, biblioteca, agendamento, saída Windows e componentes QML. Criar somente as fronteiras necessárias: análise musical, adaptador do modelo/cache e sessão guiada/adaptador Chroma. Não montar um sistema genérico de plugins ou duplicar o player. A inferência nunca roda na thread da interface nem no agendador de eventos.

Na tela de execução, acrescentar o seletor **Automático / Guiado**. No automático, mostrar perfil sugerido, expressão e pedal; no guiado, conexão, Acompanhar/Praticar e velocidade. Antecedência, calibração e demais ajustes ficam em um painel secundário. Preservar o visual atual e evitar diagnóstico técnico permanente na tela.

## Entregas e critérios

| Etapa | Entrega | Condição de conclusão |
| --- | --- | --- |
| 1. Prova técnica | Modelo local e Chroma em protótipos isolados | Medir CPU/RAM, tempo e tamanho; verificar correspondência de notas; confirmar luzes, modificadores e rollover no Cynosa. Se o modelo falhar nesses critérios, revisar a escolha antes da integração completa. |
| 2. Automático | Análise, cache, perfis e novo pedal | Comparação entre original, 4.1.1 e nova execução no jogo, com faixas de texturas diferentes. Conferir mapa de tempo, pedal e preservação de performances já expressivas. |
| 3. Guiado | Acompanhar, Praticar, calibração e interface | Validar acordes, solturas, trechos, antecipação e perda de foco; nenhuma entrada sintética no modo guiado. Verificar outros modelos quando houver hardware disponível, distinguindo suporte projetado de validação física. |
| 4. Distribuição | Instalador e atualização assinada | Migração preserva músicas/preferências; pacote do modelo verificável; instalação e recuperação passam antes de tornar a release estável. |

Usar versões preliminares 4.2.0-beta.N durante a implementação e propor 4.2.0 estável ao concluir os critérios; sem datas ou ganhos numéricos inventados. Versionar cada etapa em commits revisáveis e manter pesos, caches e relatórios gerados fora do Git. A 4.1.1 permanece estável enquanto o trabalho é avaliado.

Testes direcionados: correspondência musical e determinismo; pedal ausente/reset/intencional, mudanças de andamento e retomada; cache e cancelamento; serviço Chroma simulado com timeouts; mapa físico, modificadores e ausência de SendInput no guiado; navegação dos novos controles; instalador/atualizador e regressões já cobertas. A validação de naturalidade requer escuta no instrumento e a de iluminação requer hardware, além dos testes simulados.
