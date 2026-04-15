# A Mente de Apolo: Como a IA Toma Decisões

## Índice
1. [Visão Geral](#visão-geral)
2. [Arquitetura Neural](#arquitetura-neural)
3. [Sistema de Percepção](#sistema-de-percepção)
4. [Sistema de Recompensas](#sistema-de-recompensas)
5. [Decisão de Orbes de Vida](#decisão-de-orbes-de-vida)
6. [Processo de Decisão](#processo-de-decisão)
7. [Aprendizado e Memória](#aprendizado-e-memória)

---

## Visão Geral

Apolo é um agente de Deep Q-Learning (DQN) que aprende a sobreviver contra a Umbra através de tentativa e erro. Ele não tem regras programadas - apenas um sistema de recompensas que o guia a descobrir estratégias vencedoras.

### Filosofia de Design
```
"Apolo não sabe o que é uma orbe de vida. 
Ele apenas sabe que quando se aproxima de algo verde 
e sua vida está baixa, coisas boas acontecem."
```

---

## Arquitetura Neural

### Estrutura da Rede

```python
class ApoloDQN(nn.Module):
    def __init__(self, input_size, output_size):
        super(ApoloDQN, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, 128),    # 40 features → 128 neurônios
            nn.LeakyReLU(),                # Ativação não-linear
            nn.Linear(128, 64),            # 128 → 64 neurônios
            nn.LeakyReLU(),                # Ativação não-linear
            nn.Linear(64, output_size)     # 64 → 9 ações
        )
```

**Dimensões**:
- **Input**: 40 features (percepção do mundo)
- **Hidden Layer 1**: 128 neurônios
- **Hidden Layer 2**: 64 neurônios
- **Output**: 9 ações possíveis

**Ações Disponíveis**:
```python
0 = Cima
1 = Baixo
2 = Esquerda
3 = Direita
4 = Cima-Esquerda (diagonal)
5 = Cima-Direita (diagonal)
6 = Baixo-Esquerda (diagonal)
7 = Baixo-Direita (diagonal)
8 = Dash
```

---

## Sistema de Percepção

Apolo "vê" o mundo através de 40 features numéricas normalizadas (0-1):

### 1. Posicionamento Básico (4 features)

```python
feat_px = px / max(1, largura_mapa)  # Posição X normalizada
feat_py = py / max(1, altura_mapa)   # Posição Y normalizada
feat_bx = bx / max(1, largura_mapa)  # Posição X da Umbra
feat_by = by / max(1, altura_mapa)   # Posição Y da Umbra
```

**O que Apolo entende**: "Onde estou? Onde está o inimigo?"

### 2. Status de Vida (2 features)

```python
feat_vida_p = vida_apolo / 1000.0  # Vida própria (0-1)
feat_vida_b = vida_boss / 1200.0   # Vida da Umbra (0-1)
```

**O que Apolo entende**: "Quão perto estou da morte? Quão perto está o inimigo?"

### 3. Consciência de Bordas (5 features)

```python
margem_perigo = 100  # Pixels de margem perigosa

feat_dist_borda_esquerda = min(1.0, px / margem_perigo)
feat_dist_borda_direita = min(1.0, (largura_mapa - px) / margem_perigo)
feat_dist_borda_cima = min(1.0, py / margem_perigo)
feat_dist_borda_baixo = min(1.0, (altura_mapa - py) / margem_perigo)

# Detecta cantos (situação crítica)
em_canto = 1.0 if (em_canto_detectado) else 0.0
```

**O que Apolo entende**: "Estou perto de uma parede? Estou encurralado?"

### 4. Projéteis Inimigos (3 features)

```python
# Encontra projétil mais próximo dentro de 250 pixels
for proj in projeteis_boss:
    d = math.hypot(proj_x - px, proj_y - py)
    if d < 250:
        projeteis_proximos.append((proj_x, proj_y, d))

if projeteis_proximos:
    proj_x, proj_y, d = min(projeteis_proximos, key=lambda p: p[2])
    dist_perigo = d / 250.0                    # Distância normalizada
    dx_perigo = (proj_x - px) / max(1.0, d)   # Direção X
    dy_perigo = (proj_y - py) / max(1.0, d)   # Direção Y
```

**O que Apolo entende**: "Há algo perigoso vindo em minha direção? De onde?"

### 5. Orbes de Vida (3 features) ⭐

```python
# Encontra orbe mais próxima
orbes_com_distancia = []
for orbe in esferas_energia:
    ox, oy = orbe.get('x', px), orbe.get('y', py)
    dist_orbe = math.hypot(ox - px, oy - py)
    orbes_com_distancia.append((ox, oy, dist_orbe))

if orbes_com_distancia:
    ox_prox, oy_prox, dist_prox = min(orbes_com_distancia, key=lambda o: o[2])
    
    # Feature 1: Distância à orbe mais próxima
    feat_dist_orbe_proxima = min(1.0, dist_prox / 800.0)  # 0 = muito perto, 1 = longe
    
    # Feature 2 e 3: Direção vetorial para a orbe
    if dist_prox > 0:
        feat_dir_orbe_x = (ox_prox - px) / dist_prox  # -1 a 1
        feat_dir_orbe_y = (oy_prox - py) / dist_prox  # -1 a 1
```

**O que Apolo entende**: 
- "Há algo verde por perto?"
- "Quão longe está?"
- "Em que direção devo ir para alcançá-lo?"

**Importante**: Apolo NÃO sabe que é uma "orbe de vida". Ele apenas percebe:
1. Um objeto em uma posição específica
2. A distância até ele
3. A direção para alcançá-lo

### 6. Laser (9 features)

```python
feat_laser_fase = 0.0           # 0=inativo, 0.5=carregando, 1.0=disparando
feat_laser_rodada = rodada/4.0  # Qual rodada (1-4)
feat_laser_progresso = 0.0      # Progresso da fase atual
feat_laser_num_feixes = num/6.0 # Quantos feixes
feat_laser_sentido_rotacao = sentido  # -1 ou 1
feat_laser_velocidade_angular = vel   # Quão rápido gira
feat_laser_angulo_mais_proximo = ang  # Ângulo do feixe próximo
feat_laser_dist_feixe_proximo = dist  # Distância ao feixe
feat_laser_tempo_ate_atingir = tempo  # Tempo até ser atingido
```

### 7. Ratos (4 features)

```python
feat_qtd_ratos = len(ratos) / 20.0           # Quantos ratos ativos
feat_dist_rato_proximo = dist / 600.0        # Distância ao mais próximo
feat_dir_rato_x = (rx - px) / dist           # Direção X
feat_dir_rato_y = (ry - py) / dist           # Direção Y
```

### 8. Armadilhas (6 features)

```python
feat_armadilhas = [0.0] * 6
keys = ['vortice_ativo', 'prisao_ativa', 'caminho_espinhos', 
        'laser_ativo', 'descarga_eletrica', 'miasma_ativo']
for i, k in enumerate(keys):
    if estado_ia.get(k): 
        feat_armadilhas[i] = 1.0  # Flag binária
```

---

## Sistema de Recompensas

Apolo aprende através de recompensas e penalidades. Cada frame, ele recebe uma pontuação que guia seu aprendizado.

### Recompensas Base

```python
recompensa = 0.5  # Sobrevivência base (+0.5 por frame vivo)

# Mudanças de vida
if delta_vida_apolo < 0:
    recompensa -= 50      # Tomou dano: -50 pontos
if delta_vida_boss < 0:
    recompensa += 30      # Causou dano: +30 pontos
if delta_vida_apolo > 0:
    recompensa += 300     # Curou: +300 pontos (MUITO IMPORTANTE!)
```

### Recompensas de Posicionamento

```python
# Bordas
if dist_borda < 50:
    recompensa -= 25      # Muito perto da borda
elif dist_borda < 100:
    recompensa -= 8       # Perto da borda

# Cantos (pior situação)
if em_canto:
    recompensa -= 40      # Penalidade EXTREMA

# Centro do mapa (zona segura)
if dist_centro < raio_seguro:
    recompensa += 3       # Recompensa por estar seguro

# Distância do boss
if 300 < dist_boss < 600:
    recompensa += 1       # Distância ideal
elif dist_boss < 200:
    recompensa -= 3       # Muito perto (perigoso)
```

---

## Decisão de Orbes de Vida

### Como Apolo Decide Buscar Orbes

Apolo usa um sistema de **Dense Rewards** (Recompensas Densas) - ele é recompensado a cada pixel que se aproxima da orbe, e penalizado a cada pixel que se afasta.

#### Código Completo:

```python
if esferas_energia and len(esferas_energia) > 0:
    # 1. CALCULA VIDA PERCENTUAL
    percentual_vida_atual = vida_jogador / 1000.0  # 0.0 a 1.0
    
    # 2. ENCONTRA ORBE MAIS PRÓXIMA
    dist_min_orbe = float('inf')
    for orbe in esferas_energia:
        ox, oy = orbe.get('x', px), orbe.get('y', py)
        dist = math.hypot(ox - px, oy - py)
        if dist < dist_min_orbe:
            dist_min_orbe = dist
            orbe_mais_proxima = orbe
    
    if orbe_mais_proxima:
        # 3. SISTEMA DE GUIA DE MIGALHAS (Dense Reward)
        if hasattr(self, 'dist_orbe_anterior'):
            # Calcula mudança de distância desde o último frame
            delta_distancia = self.dist_orbe_anterior - dist_min_orbe
            
            # PROTEÇÃO CONTRA TRAUMA NEURAL
            # Se a distância mudar muito (orbe coletada/despawnou), ignora
            if abs(delta_distancia) < 50:
                
                # 4. FATOR DE DESESPERO
                # Quanto menos vida, mais forte a recompensa/penalidade
                fator_necessidade = 1.0
                if percentual_vida_atual < 0.3:      # Vida crítica
                    fator_necessidade = 5.0
                elif percentual_vida_atual < 0.6:    # Vida baixa
                    fator_necessidade = 2.5
                
                # 5. RECOMPENSA PROPORCIONAL
                # Se aproximou: delta_distancia > 0 → ganha pontos
                # Se afastou: delta_distancia < 0 → perde pontos
                recompensa += (delta_distancia * 0.5) * fator_necessidade
                
                # 6. REFORÇO EXTREMO (muito perto + vida baixa)
                if dist_min_orbe < 100 and percentual_vida_atual < 0.5:
                    recompensa += 5  # Bônus extra
        
        # 7. MEMORIZA DISTÂNCIA PARA PRÓXIMO FRAME
        self.dist_orbe_anterior = dist_min_orbe
else:
    # 8. LIMPEZA DE MEMÓRIA
    # Remove memória quando não há orbes (evita fobia)
    if hasattr(self, 'dist_orbe_anterior'):
        delattr(self, 'dist_orbe_anterior')
```

### Análise Detalhada

#### 1. Cálculo de Vida Percentual
```python
percentual_vida_atual = vida_jogador / 1000.0
```
- Vida cheia (1000 HP) = 1.0
- Metade da vida (500 HP) = 0.5
- Vida crítica (300 HP) = 0.3

#### 2. Encontrar Orbe Mais Próxima
```python
dist_min_orbe = float('inf')
for orbe in esferas_energia:
    dist = math.hypot(ox - px, oy - py)  # Distância euclidiana
    if dist < dist_min_orbe:
        dist_min_orbe = dist
```
- Calcula distância para TODAS as orbes
- Escolhe a MAIS PRÓXIMA
- Ignora orbes muito distantes

#### 3. Sistema de Guia de Migalhas (Dense Reward)

**Conceito**: Recompensar cada pequeno passo na direção certa.

```python
delta_distancia = self.dist_orbe_anterior - dist_min_orbe
```

**Exemplos**:

| Frame | Distância | Delta | Significado |
|-------|-----------|-------|-------------|
| 1 | 500px | - | Primeira detecção |
| 2 | 490px | +10px | Aproximou 10px → +5 pontos |
| 3 | 485px | +5px | Aproximou 5px → +2.5 pontos |
| 4 | 495px | -10px | Afastou 10px → -5 pontos |
| 5 | 480px | +15px | Aproximou 15px → +7.5 pontos |

**Fórmula Base**:
```python
recompensa += (delta_distancia * 0.5) * fator_necessidade
```

#### 4. Fator de Desespero

**Quanto menos vida, mais urgente é buscar a orbe**:

```python
if percentual_vida_atual < 0.3:      # <30% vida
    fator_necessidade = 5.0          # Multiplicador 5x
elif percentual_vida_atual < 0.6:    # <60% vida
    fator_necessidade = 2.5          # Multiplicador 2.5x
else:
    fator_necessidade = 1.0          # Multiplicador 1x
```

**Tabela de Recompensas**:

| Vida | Fator | Aproximou 10px | Afastou 10px |
|------|-------|----------------|--------------|
| 90% (900 HP) | 1.0x | +5 pontos | -5 pontos |
| 50% (500 HP) | 2.5x | +12.5 pontos | -12.5 pontos |
| 25% (250 HP) | 5.0x | +25 pontos | -25 pontos |

**Insight**: Com vida crítica, cada pixel conta MUITO mais!

#### 5. Proteção Contra Trauma Neural

```python
if abs(delta_distancia) < 50:
    # Aplica recompensa
```

**Por quê?**
- Orbe coletada: distância pula de 50px para 800px (orbe nova)
- Orbe despawnou: distância pula de 100px para infinito
- Sem proteção: Apolo receberia -400 pontos (trauma!)
- Com proteção: Ignora mudanças bruscas

#### 6. Reforço Extremo

```python
if dist_min_orbe < 100 and percentual_vida_atual < 0.5:
    recompensa += 5
```

**Quando ativa**:
- Orbe a menos de 100 pixels
- Vida abaixo de 50%

**Efeito**: "Você está QUASE lá, continue!"

#### 7. Limpeza de Memória

```python
if hasattr(self, 'dist_orbe_anterior'):
    delattr(self, 'dist_orbe_anterior')
```

**Por quê?**
- Quando não há orbes, remove a memória
- Evita que Apolo desenvolva "fobia" de orbes
- Quando nova orbe aparecer, começa do zero

### Exemplo Completo: Apolo Buscando Orbe

**Situação**: Apolo com 300 HP (30% vida), orbe a 400px

```
Frame 1: Distância = 400px
  - Primeira detecção
  - Memoriza: dist_orbe_anterior = 400
  - Recompensa: 0

Frame 2: Distância = 390px (moveu em direção à orbe)
  - Delta = 400 - 390 = +10px
  - Fator = 5.0 (vida <30%)
  - Recompensa = (10 * 0.5) * 5.0 = +25 pontos
  - Memoriza: dist_orbe_anterior = 390

Frame 3: Distância = 385px (continuou se aproximando)
  - Delta = 390 - 385 = +5px
  - Fator = 5.0
  - Recompensa = (5 * 0.5) * 5.0 = +12.5 pontos
  - Memoriza: dist_orbe_anterior = 385

Frame 4: Distância = 395px (desviou de projétil, afastou)
  - Delta = 385 - 395 = -10px
  - Fator = 5.0
  - Recompensa = (-10 * 0.5) * 5.0 = -25 pontos
  - Memoriza: dist_orbe_anterior = 395
  - Apolo aprende: "Desviar foi necessário, mas custou caro"

Frame 5: Distância = 380px (voltou a se aproximar)
  - Delta = 395 - 380 = +15px
  - Fator = 5.0
  - Recompensa = (15 * 0.5) * 5.0 = +37.5 pontos
  - Memoriza: dist_orbe_anterior = 380

...

Frame 50: Distância = 80px (muito perto!)
  - Delta = 85 - 80 = +5px
  - Fator = 5.0
  - Recompensa base = (5 * 0.5) * 5.0 = +12.5 pontos
  - Reforço extremo = +5 pontos (dist < 100 e vida < 50%)
  - Recompensa total = +17.5 pontos

Frame 51: Coletou orbe! Vida = 400 HP
  - delta_vida_apolo = +100 HP
  - Recompensa = +300 pontos (JACKPOT!)
  - Distância nova orbe = 600px (muito longe)
  - Delta = 80 - 600 = -520px (>50, ignora)
  - Memoriza: dist_orbe_anterior = 600
```

**Total de recompensas**: ~+500 pontos ao longo de 50 frames

**O que Apolo aprende**:
1. "Quando minha vida está baixa, ir em direção a coisas verdes é BOM"
2. "Cada pixel que me aproximo vale pontos"
3. "Às vezes preciso me afastar (desviar), mas devo voltar"
4. "Quando finalmente alcanço, recebo MUITOS pontos"

---

## Processo de Decisão

### Fluxo Completo

```
1. PERCEPÇÃO
   ↓
   [40 features numéricas]
   ↓
2. REDE NEURAL
   ↓
   [40 → 128 → 64 → 9]
   ↓
   [Q-values para cada ação]
   ↓
3. FILTRAGEM
   ↓
   [Remove ações inválidas (bordas)]
   ↓
4. PERSISTÊNCIA
   ↓
   [Mantém ação por 15 frames OU emergência]
   ↓
5. SELEÇÃO
   ↓
   [Exploração (aleatório) OU Exploitação (melhor Q-value)]
   ↓
6. EXECUÇÃO
   ↓
   [Move personagem]
   ↓
7. RECOMPENSA
   ↓
   [Calcula pontuação do resultado]
   ↓
8. APRENDIZADO
   ↓
   [Atualiza pesos da rede neural]
   ↓
   [Volta para 1]
```

### Exploração vs Exploitação

```python
if random.random() < self.taxa_exploracao:
    acao = random.choice(acoes_validas)  # EXPLORAÇÃO
else:
    q_vals = self.q_network(estado_tensor)[0]
    acao = torch.argmax(q_vals_masked).item()  # EXPLOITAÇÃO
```

**Taxa de Exploração**:
```python
self.taxa_exploracao = max(0.01, 0.20 * (0.985 ** geracoes))
```

| Geração | Taxa | Comportamento |
|---------|------|---------------|
| 0 | 50% | Muito aleatório |
| 50 | 20% | Ainda explorando |
| 100 | 8% | Mais confiante |
| 200 | 3% | Quase expert |
| 500 | 1% | Expert (mínimo) |

### Sistema de Persistência

```python
self.frames_minimos_por_acao = 15  # ~250ms a 60fps

if self.frames_acao_atual < self.frames_minimos_por_acao:
    acao = self.acao_atual  # Mantém ação atual
else:
    acao = nova_decisao()   # Escolhe nova ação
```

**Exceções (Emergências)**:
- Laser a menos de 100px
- Rato a menos de 80px
- Projétil a menos de 80px
- Vida crítica (<200 HP)

---

## Aprendizado e Memória

### Algoritmo: Deep Q-Learning

```python
# 1. Predição (Q-value da ação tomada)
q_values = self.q_network(self.ultimo_estado_tensor)
q_val = q_values[0, self.acao_anterior]

# 2. Alvo (Q-value + recompensa)
alvo = q_val.item() + 0.15 * (recompensa - q_val.item())

# 3. Perda (diferença entre predição e alvo)
loss = self.criterion(q_val, alvo_tensor)

# 4. Backpropagation (atualiza pesos)
self.optimizer.zero_grad()
loss.backward()
self.optimizer.step()
```

**Taxa de Aprendizado**: 0.15 (15% da diferença)

### Memória Persistente

```python
def salvar_memoria(self):
    torch.save(self.q_network.state_dict(), "apolo_memoria_dqn.pt")

def carregar_memoria(self):
    if os.path.exists("apolo_memoria_dqn.pt"):
        self.q_network.load_state_dict(torch.load("apolo_memoria_dqn.pt"))
```

**Arquivo**: `apolo_memoria_dqn.pt`
- Contém todos os pesos da rede neural
- ~200 KB de tamanho
- Carregado no início de cada partida
- Salvo ao final de cada partida

---

## Resumo: Como Apolo Decide Buscar Orbes

### Passo a Passo

1. **Percepção**: "Há algo verde a 400px na direção nordeste"
   - `feat_dist_orbe_proxima = 0.5` (400/800)
   - `feat_dir_orbe_x = 0.7` (direção X)
   - `feat_dir_orbe_y = -0.7` (direção Y)

2. **Contexto**: "Minha vida está em 30%"
   - `feat_vida_p = 0.3`
   - Fator de desespero = 5.0x

3. **Rede Neural**: "Baseado em experiências passadas..."
   - Processa 40 features
   - Calcula Q-values para 9 ações
   - Ação 5 (Cima-Direita) tem maior Q-value

4. **Decisão**: "Vou para cima-direita"
   - Move em diagonal na direção da orbe

5. **Resultado**: "Aproximei 10 pixels"
   - Delta = +10px
   - Recompensa = (10 * 0.5) * 5.0 = +25 pontos

6. **Aprendizado**: "Essa foi uma boa decisão!"
   - Atualiza pesos da rede neural
   - Reforça: "Quando vida baixa + orbe próxima → ir em direção à orbe"

7. **Repetição**: Continua se aproximando frame a frame

8. **Coleta**: "Alcancei a orbe!"
   - Vida aumenta +100 HP
   - Recompensa = +300 pontos (JACKPOT!)
   - Aprendizado forte: "Isso foi MUITO bom!"

### O que Apolo NÃO Sabe

- ❌ Que é uma "orbe de vida"
- ❌ Que vai curar exatamente 100 HP
- ❌ Que foi criada pela Umbra
- ❌ Que tem tempo de vida limitado

### O que Apolo SABE

- ✅ Posição do objeto verde
- ✅ Distância até ele
- ✅ Direção para alcançá-lo
- ✅ Sua vida atual
- ✅ Que se aproximar quando vida baixa = bom
- ✅ Que alcançar = MUITO bom

---

## Conclusão

Apolo é um exemplo de **Aprendizado por Reforço Emergente**. Ele não tem regras sobre orbes - apenas um sistema de recompensas que o guia a descobrir que:

1. Quando vida está baixa
2. E há algo verde por perto
3. Ir em direção a isso
4. Resulta em coisas boas

Através de centenas de gerações, Apolo desenvolve uma "intuição" sobre quando e como buscar orbes, sem nunca ter sido explicitamente programado para isso.

**É aprendizado puro através de experiência.**
