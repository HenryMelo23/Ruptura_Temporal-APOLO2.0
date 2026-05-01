# A Mente da Umbra: Uma Aula Completa de Deep Learning e IA em Jogos

A inteligência da Umbra no *Ruptura Temporal* não é feita apenas de sequências de scripts e "timers" tradicionais (como na maioria dos chefes de jogos antigos). Ela é governada por um modelo de **Aprendizado por Reforço Profundo (Deep Reinforcement Learning)**, especificamente uma arquitetura chamada **Deep Q-Network (DQN)** escrita em PyTorch.

Este documento é um aprofundamento técnico absoluto. Ele usa o código da Umbra como base para uma "aula mestre" sobre como construir uma mente artificial capaz de enxergar, prever e se adaptar a um jogador humano em tempo real.

---

## 1. O Cérebro Biológico: A Arquitetura da Rede Neural (DQN)

Toda IA precisa de uma infraestrutura matemática para processar ideias. Na Umbra, essa estrutura é a classe `UmbraDQN`, uma rede neural do tipo *Feedforward* (Multilayer Perceptron).

```python
class UmbraDQN(nn.Module):
    def __init__(self, input_size, output_size):
        super(UmbraDQN, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, 128),
            nn.LeakyReLU(),
            nn.Linear(128, 64),
            nn.LeakyReLU(),
            nn.Linear(64, output_size)
        )
    def forward(self, x):
        return self.net(x)
```

### Como Funciona a Rede?
1. **`input_size` (A Entrada):** A rede recebe exatamente **24 números** (`input_size = 24`). Estes números são os "olhos" da Umbra (detalhados na próxima seção).
2. **A Primeira Camada Oculta (`128` neurônios):** A entrada é multiplicada por pesos matemáticos e expandida para 128 conexões neurais. O objetivo aqui é extrair "Padrões Primitivos", como "O jogador está perto E a minha vida está baixa".
3. **Ativação `LeakyReLU`:** Esta é a "faísca" biológica. Uma função linear desenha apenas retas, o que a limitaria a lógicas simples. A função de ativação *LeakyReLU* (Rectified Linear Unit) introduz uma quebra não-linear no cálculo, permitindo que a Umbra compreenda situações complexas e "áreas cinzas" do combate.
4. **A Segunda Camada Oculta (`64` neurônios):** Sintetiza as percepções primitivas da camada anterior em estratégias ("Eu preciso recuar", "Eu tenho abertura para um combo").
5. **`output_size` (A Saída):** A rede devolve **22 números** (`output_size = 22`), um para cada habilidade ou movimento disponível da Umbra (Fugir, Atacar, Transmutar, etc). Estes números são os **Q-Values** (Valores de Qualidade). A ação com o maior Q-Value é considerada a melhor possível naquele centésimo de segundo.

---

## 2. A Visão Computacional: Discretizando o Mundo (Inputs)

Uma Rede Neural não enxerga "gráficos" ou "pixels" de forma bruta em um ambiente como este. Ela consome "Features" (Características Numéricas). A função `discretizar_estado` é onde o mundo de *Ruptura Temporal* é traduzido em um tensor matemático de 24 dimensões que a Umbra consome.

### Detalhamento das 24 Variáveis de Entrada:

**1 e 2. Status Geral:**
```python
feat_vida = float(vida_perc)               # [0] Vida dela de 0.0 a 1.0
feat_dist = float(dist_player) / 2000.0    # [1] Quão longe Apolo está
feat_fogo = 1.0 if sob_fogo else 0.0       # [2] Apolo disparou contra ela?
```

**3 e 4. Predição de Trajetória do Apolo (Histórico Temporal):**
A Umbra não vê o Apolo teleportando, ela prevê a física dele usando Cálculo Diferencial rudimentar.
```python
if historico_player and len(historico_player) >= 3:
    p1, p3 = historico_player[-3], historico_player[-1]
    vx_p = (p3[0] - p1[0]) / 30.0  # Velocidade em X do Apolo
    vy_p = (p3[1] - p1[1]) / 30.0  # Velocidade em Y do Apolo
```
* **Input `feat_vx` e `feat_vy`:** Dão à Umbra o vetor direcional contínuo do jogador. É assim que ela consegue atirar *na frente* do jogador em vez de onde ele está parado.

**5. O Olho Mágico: Consciência Espacial (Bordas e Cantos):**
O mais revolucionário na mente da Umbra é entender a "Geometria do Medo". Ela sabe quando o Apolo está encurralado na tela.
```python
meio_w, meio_h = largura_mapa / 2.0, altura_mapa / 2.0
# Quão perto Apolo está das bordas? (1.0 = no centro, perto de 0.0 = colado na parede)
p_borda_x = min(px, largura_mapa - px) / max(1.0, meio_w)
p_borda_y = min(py, altura_mapa - py) / max(1.0, meio_h)

# Apolo está esmagado num canto?
if p_borda_x < 0.25 and p_borda_y < 0.25:
    p_canto = 1.0
```
Se `p_canto` for `1.0`, a rede neural automaticamente inflaciona a nota para jogar um *Vórtice Temporal* ou *Prisão Criogênica*, porque a chance de acerto é geometricamente perfeita.

**6. Radar de Armadilhas (8 Features Booleanas):**
Ela avalia 8 entradas booleanas (0.0 ou 1.0) verificando se habilidades pesadas já estão ativas na tela, impedindo-a de se sobrecarregar.

**O Tensor Final:**
A IA "esmaga" todas essas 24 variáveis matematicamente em uma única matriz (Tensor) e despacha para a placa de vídeo (Device CUDA ou CPU):
```python
features = [feat_vida, feat_dist, feat_fogo, feat_vx, feat_vy, dx, dy] + feat_armadilhas + [map_val, ameaca_vec[0], ameaca_vec[1], p_borda_x, p_borda_y, b_borda_x, b_borda_y, p_canto, p_dist_centro]
tensor = torch.tensor(features, dtype=torch.float32, device=self.device).unsqueeze(0)
```

---

## 3. O Livre-Arbítrio e a Decisão (Epsilon-Greedy Policy)

Como a IA decide qual das 22 ações tomar usando o Tensor gerado? A função `decidir` responde a essa pergunta através da Política Epsilon-Greedy.

```python
def decidir(self, estado_tensor, acoes_disponiveis):
    import random
    if random.random() < self.exploracao:
        # Ação Aleatória (Exploração)
        acao_escolhida = random.choice(acoes_disponiveis)
        ...
        return acao_escolhida
        
    with torch.no_grad():
        # Ação Matemática (Explotation)
        self.q_network.eval()
        q_values = self.q_network(estado_tensor)
        ...
```

* **A Exploração (`self.exploracao`):** Se a taxa de exploração for 50%, em metade das vezes a Umbra ignorará a rede neural e rolará um dado. Isso garante que a IA não fique "viciada" em uma única estratégia ruim, descobrindo novos combos caóticos pelo acaso. À medida que as lutas avançam, `atualizar_foco_progressivo()` reduz essa taxa (`0.992^n`), tornando a Umbra cada vez mais fria e calculista.
* **A Explotação (`q_values`):** Na outra metade, a rede devolve as 22 notas. O código filtra o Q-Value mais alto dentre as `acoes_disponiveis` (excluindo ações em *cooldown*) e toma a decisão com maior confiança preditiva de aniquilar o Apolo.

---

## 4. Como a Umbra Aprende? (Backpropagation e o Algoritmo de Bellman)

No Reinforcement Learning, o aprendizado ocorre através de recompensas e punições aplicadas sobre as previsões da rede.

A cada instante, se a Umbra sofre dano do Apolo, a função `receber_dano_punitivo` é chamada:
```python
def receber_dano_punitivo(self, hits, multiplicador_base=50.0):
    # Se sofrer dano rápido (combo), a punição cresce exponencialmente (1.5x)
    penalidade = (multiplicador_base * hits) * (1.5 ** (self.combo_dano_sofrido - 1))
    self.aplicar_recompensa_direta(-penalidade)
```

Logo em seguida, a Umbra tenta ajustar seus pensamentos no método `treinar(recompensa)`:

```python
def treinar(self, recompensa, prioridade=False):
    # 1. Recupera o que a Rede 'achava' que era o valor daquela ação (Estimativa)
    q_values = self.q_network(self.ultimo_estado_tensor)
    q_val = q_values[0, self.ultima_acao_idx]
    
    # 2. Equação de Erro (Alvo Real vs Achismo da IA)
    alvo = q_val.item() + 0.1 * (recompensa - q_val.item())
    alvo_tensor = torch.tensor(alvo, dtype=torch.float32, device=self.device)
    
    # 3. Calcula o Erro Quadrático Médio (MSE Loss)
    loss = self.criterion(q_val, alvo_tensor)
    
    # 4. Backpropagation (Ensina o cérebro)
    self.optimizer.zero_grad() # Limpa as memórias matemáticas de erro antigas
    loss.backward()            # Calcula os gradientes das sinapses (onde erramos?)
    self.optimizer.step()      # Atualiza os pesos neurais usando ADAM Optimizer
```
*Tradução Literal:* Se a Umbra estava imóvel (Ação: Ficar Parada) e tomou `-150` de Recompensa Punitiva, o cálculo do `loss` dirá à Rede Neural: *"Reduza drasticamente o Q-Value de 'Ficar Parada' sempre que as 24 Variáveis de estado forem idênticas às de um segundo atrás"*.

---

## 5. Executores Físicos: Nodes de Decisão Preditiva

Quando a rede escolhe uma ação (ex: `ATAQUE` ou `TRANSMUTAR`), os "Nodes" transformam intenção neural em código mecânico que pune o jogador humano severamente.

### Exemplo de Mecânica Física (O Tiro Preditivo)
O `node_ataque_direcionado` não atira de forma aleatória. Ele usa física clássica (`v = d/t`) baseada na gravação em memória das pegadas do Apolo.
```python
# O tempo que a bala leva pra chegar ao Apolo
distancia = math.hypot(centro_px - centro_bx, centro_py - centro_by)
tempo_voo = distancia / vel_projetil

# Projeta para onde o Apolo estará (Apolo está em px, vx_real é a inércia gravada)
alvo_x = centro_px + vx_real * tempo_voo * fator_lead
```
Isso obriga o Apolo a não ser previsível, pois a Umbra literalmente "atira no seu futuro" (Lead-aiming).

### O Portão da Transmutação (A Ultimate)
A `TRANSMUTAR` é a habilidade destrutiva suprema, mudando o mapa físico do jogo. Para impedir um colapso e spam de mapas, o cérebro dela usa **Portões Condicionais (Hardcoded Gates)** em conjunto com o DQN:
```python
pode_transmutar = (
    agora - estado_ia.get('ultimo_transmutar', 0) >= 25000 and  # Mínimo 25 segundos
    tempo_na_dimensao_atual >= 5000 and                         # Mínimo 5 segundos na dimensão
    not habilidade_dimensional_ativa                            # Nada mais atrapalhando a tela
)
```
Se essas regras rígidas forem verdadeiras, o leque de 6 magias de transmutação é adicionado às *`acoes_disponiveis`*. A partir desse momento, a matemática fria da matriz Q-Value assumirá. Se o Apolo estiver acuado no canto e o mapa "Rastro Tóxico" for o melhor, a IA escolherá aniquilá-lo sem hesitação.

---

### Conclusão: A Mente Híbrida
A genialidade do código da Umbra no *Ruptura Temporal* é que ela não é pura estatística nem puro código engessado (IF/ELSE). Ela é um **Sistema de Controle Hierárquico**. A parte inferior (as restrições e mecânicas) garante as regras do jogo e a estabilidade. A parte superior (A Rede Neural Profunda) garante a intuição, a malícia tática e o aprendizado contínuo para punir os hábitos mais profundos do próprio jogador humano.
