# Documento de Requisitos: Documentação Técnica da Transição DQN

## Introdução

Este documento define os requisitos para a criação de uma documentação técnica fundacional e extensiva que explica a transição do modelo Q-Learning Tabular para Deep Q-Learning (DQN) no projeto Ruptura Temporal. A documentação deve servir como referência arquitetural para engenheiros de IA, detalhando as diferenças técnicas, fundamentos matemáticos, comportamento de memória e implicações práticas da evolução dos agentes Umbra (Boss) e Apolo (Player).

## Glossário

- **Sistema_Documentacao**: O sistema responsável por gerar e estruturar a documentação técnica
- **Q_Learning_Tabular**: Modelo de aprendizado por reforço baseado em tabelas discretas (dicionários) que mapeia estados para valores Q
- **DQN**: Deep Q-Network - modelo de aprendizado por reforço que utiliza redes neurais para aproximar a função Q
- **Umbra**: Agente de IA que controla o boss do jogo, implementado com UmbraDQN (18 features → 128 → 64 → 22 ações)
- **Apolo**: Agente de IA que controla o jogador, implementado com ApoloDQN (23 features → 128 → 64 → 5 ações)
- **Tensor**: Estrutura de dados multidimensional utilizada pelo PyTorch para representar estados e pesos sinápticos
- **Pesos_Sinapticos**: Parâmetros aprendidos da rede neural armazenados em arquivos .pt
- **Espaco_Estados**: Conjunto de todas as possíveis configurações do ambiente que o agente pode observar
- **Generalizacao**: Capacidade da rede neural de inferir valores Q para estados nunca vistos anteriormente
- **Colapso_Dimensionalidade**: Problema onde o espaço de estados cresce exponencialmente, tornando Q-Learning tabular impraticável
- **Bias_Bayesiano**: Sistema de rastreamento estatístico de padrões de movimento do jogador implementado na Umbra
- **Exploracao**: Taxa de ações aleatórias (epsilon) utilizada para descobrir novas estratégias (20% em ambos agentes)
- **Recompensa**: Sinal numérico que indica o sucesso ou falha de uma ação (positivo para comportamentos desejados, negativo para indesejados)
- **Backpropagation**: Algoritmo de otimização que ajusta os pesos sinápticos da rede neural baseado no erro de predição

## Requisitos

### Requisito 1: Documentação da Arquitetura e Transição Técnica

**User Story:** Como arquiteto de IA, eu quero uma documentação detalhada comparando Q-Learning Tabular e DQN, para que eu possa compreender as diferenças arquiteturais fundamentais e as razões técnicas da transição.

#### Acceptance Criteria

1. THE Sistema_Documentacao SHALL criar uma seção "Transição e Diferenças Essenciais" que contrasta a arquitetura tabular com a arquitetura DQN
2. THE Sistema_Documentacao SHALL explicar o mapeamento de estados discretos (dicionários JSON) versus representação contínua (tensores PyTorch)
3. THE Sistema_Documentacao SHALL documentar a estrutura das redes neurais de ambos agentes (camadas, neurônios, funções de ativação)
4. THE Sistema_Documentacao SHALL detalhar as 23 features de entrada do Apolo e as 18 features de entrada da Umbra
5. THE Sistema_Documentacao SHALL explicar o conceito de generalização matemática abstrata versus lookup direto em tabelas
6. THE Sistema_Documentacao SHALL incluir diagramas ou representações visuais da arquitetura neural (128→64→N neurônios)
7. THE Sistema_Documentacao SHALL contrastar o armazenamento em JSON (Q-tables) versus arquivos .pt (pesos sinápticos)
8. THE Sistema_Documentacao SHALL documentar os hiperparâmetros utilizados (learning rate 0.001, gamma 0.95, epsilon 0.20)

### Requisito 2: Fundamentos Matemáticos e Justificativa Tática

**User Story:** Como engenheiro de IA, eu quero compreender os fundamentos matemáticos e as razões táticas da transição para DQN, para que eu possa avaliar a necessidade e os benefícios dessa evolução no contexto do jogo.

#### Acceptance Criteria

1. THE Sistema_Documentacao SHALL criar uma seção "Fundamentos e Necessidade Tática" explicando o problema do colapso da dimensionalidade
2. THE Sistema_Documentacao SHALL calcular e demonstrar o crescimento exponencial do espaço de estados no Q-Learning tabular
3. THE Sistema_Documentacao SHALL explicar como DQN resolve o problema de escalabilidade através de aproximação funcional
4. THE Sistema_Documentacao SHALL detalhar a equação de Bellman e como ela é implementada em ambos os paradigmas
5. THE Sistema_Documentacao SHALL explicar o conceito de "fluidez tática extrema" em cenários dinâmicos do jogo
6. THE Sistema_Documentacao SHALL documentar como a rede neural interpola valores Q para estados intermediários
7. THE Sistema_Documentacao SHALL justificar a escolha de LeakyReLU como função de ativação
8. THE Sistema_Documentacao SHALL explicar o papel do otimizador Adam e da função de perda MSE no treinamento

### Requisito 3: Comportamento de Memória e Retenção de Conhecimento

**User Story:** Como desenvolvedor de sistemas de IA, eu quero entender como a memória e retenção de conhecimento funcionam no novo sistema DQN, para que eu possa compreender as vantagens sobre o sistema anterior baseado em JSON.

#### Acceptance Criteria

1. THE Sistema_Documentacao SHALL criar uma seção "Comportamento da Memória (Umbra e Apolo)" detalhando os mecanismos de persistência
2. THE Sistema_Documentacao SHALL contrastar arquivos JSON estáticos versus pesos sinápticos em tensores .pt
3. THE Sistema_Documentacao SHALL explicar como os pesos sinápticos codificam conhecimento de forma distribuída
4. THE Sistema_Documentacao SHALL documentar o processo de salvamento e carregamento de pesos (torch.save/torch.load)
5. THE Sistema_Documentacao SHALL detalhar o sistema de Bias Bayesiano da Umbra e como ele rastreia padrões de movimento
6. THE Sistema_Documentacao SHALL explicar a "intuição predatória" da Umbra através da análise de tendências de esquiva
7. THE Sistema_Documentacao SHALL documentar como o Apolo aprende estratégias de evasão através de recompensas baseadas em sobrevivência
8. THE Sistema_Documentacao SHALL explicar o conceito de "retenção letal" - como conhecimento persiste entre sessões de jogo
9. THE Sistema_Documentacao SHALL detalhar as estruturas de dados: tendencias_umbra.json para bias estatístico e .pt para pesos neurais
10. THE Sistema_Documentacao SHALL explicar como a memória distribuída em pesos permite generalização superior ao lookup discreto

### Requisito 4: Horizonte Prático e Comportamento Observável

**User Story:** Como designer de jogos, eu quero compreender as mudanças práticas no comportamento dos agentes na arena, para que eu possa avaliar o impacto da transição DQN na experiência de jogo.

#### Acceptance Criteria

1. THE Sistema_Documentacao SHALL criar uma seção "Horizonte Prático e Novas Percepções" descrevendo comportamentos observáveis
2. THE Sistema_Documentacao SHALL explicar como os agentes processam variáveis geométricas brutas em tempo real
3. THE Sistema_Documentacao SHALL documentar a capacidade de reação a situações 100% inéditas através de generalização
4. THE Sistema_Documentacao SHALL detalhar as 22 ações disponíveis para Umbra (movimento + habilidades especiais)
5. THE Sistema_Documentacao SHALL detalhar as 5 ações disponíveis para Apolo (up, down, left, right, dash)
6. THE Sistema_Documentacao SHALL explicar como features geométricas (posição, distância, velocidade) influenciam decisões
7. THE Sistema_Documentacao SHALL documentar o sistema de recompensas do Apolo (sobrevivência, dano causado/recebido, posicionamento)
8. THE Sistema_Documentacao SHALL documentar o sistema de recompensas da Umbra (acertos, eficiência tática, controle de arena)
9. THE Sistema_Documentacao SHALL explicar o equilíbrio entre exploração (20%) e exploração (80%) no comportamento dos agentes
10. THE Sistema_Documentacao SHALL contrastar comportamento determinístico (Q-table lookup) versus comportamento adaptativo (DQN inference)
11. THE Sistema_Documentacao SHALL documentar exemplos práticos de situações onde DQN supera Q-Learning tabular

### Requisito 5: Estrutura e Formatação do Documento

**User Story:** Como leitor técnico, eu quero que a documentação siga padrões profissionais de formatação e organização, para que eu possa navegar e compreender o conteúdo facilmente.

#### Acceptance Criteria

1. THE Sistema_Documentacao SHALL criar o arquivo "LOGICA_IA_UMBRA_E_APOLO_DQN_FUNDACIONAL.md" no diretório raiz do projeto
2. THE Sistema_Documentacao SHALL escrever todo o conteúdo em português brasileiro
3. THE Sistema_Documentacao SHALL estruturar o documento com hierarquia clara de seções e subseções
4. THE Sistema_Documentacao SHALL utilizar formatação Markdown apropriada (cabeçalhos, listas, blocos de código, tabelas)
5. THE Sistema_Documentacao SHALL incluir blocos de código Python para ilustrar conceitos técnicos quando apropriado
6. THE Sistema_Documentacao SHALL utilizar terminologia técnica precisa e consistente ao longo do documento
7. THE Sistema_Documentacao SHALL incluir equações matemáticas formatadas quando necessário para explicar conceitos
8. THE Sistema_Documentacao SHALL manter tom profissional e técnico apropriado para arquitetos de IA
9. THE Sistema_Documentacao SHALL garantir que o documento seja extenso e meticulosamente detalhado (mínimo 2000 palavras)
10. THE Sistema_Documentacao SHALL incluir uma introdução contextual e uma conclusão sintetizando os pontos principais

### Requisito 6: Detalhamento Técnico de Implementação

**User Story:** Como engenheiro implementando sistemas similares, eu quero detalhes técnicos específicos da implementação, para que eu possa compreender decisões de design e replicar conceitos em outros contextos.

#### Acceptance Criteria

1. THE Sistema_Documentacao SHALL documentar a escolha de PyTorch como framework de deep learning
2. THE Sistema_Documentacao SHALL explicar o uso de CUDA quando disponível (torch.device)
3. THE Sistema_Documentacao SHALL detalhar o processo de normalização de features (divisão por constantes, clamping)
4. THE Sistema_Documentacao SHALL documentar o tratamento de features de armadilhas (8 features binárias para Umbra)
5. THE Sistema_Documentacao SHALL explicar o cálculo de velocidade do jogador através de histórico de posições
6. THE Sistema_Documentacao SHALL documentar o sistema de priorização de treinamento (parâmetro prioridade na função treinar)
7. THE Sistema_Documentacao SHALL explicar a estratégia epsilon-greedy implementada (20% exploração)
8. THE Sistema_Documentacao SHALL detalhar o processo de forward pass e backward pass durante treinamento
9. THE Sistema_Documentacao SHALL documentar o tratamento de casos onde arquivos .pt não existem (inicialização de pesos)
10. THE Sistema_Documentacao SHALL explicar a integração entre o sistema de decisão DQN e o grafo de pesos heurísticos

### Requisito 7: Análise Comparativa de Performance

**User Story:** Como analista de performance, eu quero compreender as diferenças de performance entre Q-Learning tabular e DQN, para que eu possa avaliar trade-offs de tempo de execução versus qualidade de decisão.

#### Acceptance Criteria

1. THE Sistema_Documentacao SHALL criar uma seção comparando complexidade computacional de lookup em tabela versus inferência neural
2. THE Sistema_Documentacao SHALL explicar o custo de memória: JSON discreto versus pesos sinápticos contínuos
3. THE Sistema_Documentacao SHALL documentar o overhead de treinamento em tempo real durante combate
4. THE Sistema_Documentacao SHALL explicar como o tamanho da rede (128→64→N) afeta performance
5. THE Sistema_Documentacao SHALL discutir o trade-off entre exploração (20%) e qualidade de decisão
6. THE Sistema_Documentacao SHALL documentar vantagens de generalização versus precisão de lookup direto
7. THE Sistema_Documentacao SHALL explicar como o treinamento incremental afeta a estabilidade do comportamento

### Requisito 8: Documentação de Casos de Uso e Exemplos

**User Story:** Como desenvolvedor aprendendo sobre DQN, eu quero exemplos concretos e casos de uso, para que eu possa visualizar como os conceitos abstratos se manifestam no jogo.

#### Acceptance Criteria

1. THE Sistema_Documentacao SHALL incluir exemplo de como Umbra decide entre TELEPORTE, VORTICE e INTERCEPTAR
2. THE Sistema_Documentacao SHALL incluir exemplo de como Apolo decide entre DASH e movimento direcional sob ameaça
3. THE Sistema_Documentacao SHALL documentar cenário onde generalização DQN supera Q-Learning (estado nunca visto)
4. THE Sistema_Documentacao SHALL explicar como features geométricas (distância, ângulo) influenciam decisões específicas
5. THE Sistema_Documentacao SHALL incluir exemplo de como Bias Bayesiano da Umbra prediz movimento do jogador
6. THE Sistema_Documentacao SHALL documentar exemplo de recompensa positiva e negativa para cada agente
7. THE Sistema_Documentacao SHALL explicar cenário de treinamento: estado → ação → recompensa → atualização de pesos

