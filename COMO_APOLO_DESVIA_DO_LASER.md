# Como Apolo Desvia do Laser: Análise Completa da Percepção e Decisão

## Índice
1. [Visão Geral](#visão-geral)
2. [Sistema de Percepção do Laser](#sistema-de-percepção-do-laser)
3. [Features Neurais do Laser](#features-neurais-do-laser)
4. [Sistema de Recompensas](#sistema-de-recompensas)
5. [Sistema de Emergência](#sistema-de-emergência)
6. [Processo Completo de Decisão](#processo-completo-de-decisão)
7. [Exemplos Práticos](#exemplos-práticos)

---

## Visão Geral

O laser da Umbra é uma das ameaças mais complexas que Apolo enfrenta. Diferente de projéteis simples, o laser:
- Tem múltiplas fases (carregamento → disparo)
- Gira continuamente em diferentes velocidades
- Possui múltiplos feixes simultâneos (1, 2, 4 ou 6)
- Muda de comportamento a cada rodada

**Filosofia de Design**:
```
"Apolo não sabe que é um 'laser'. 
Ele apenas percebe linhas de perigo que giram, 
e aprende que ficar longe delas = bom, 
ficar perto = muito ruim."
```

---

## Sistema de Percepção do Laser

### 1. Detecção de Fase

Apolo identifica em que fase o laser está através de uma feature binária:

```python
feat_laser_fase = 0.0  # 0 = inativo, 0.5 = carregando, 1.0 = disparando

if laser.get('fase') == 'carregando':
    feat_laser_fase = 0.5
    tempo_laser = agora - laser['tempo_inicio']
    feat_laser_progresso = min(1.0, tempo_laser / laser['duracao_carga'])
    
elif laser.get('fase') == 'disparando':
    feat_laser_fase = 1.0
    t_disp = agora - laser['tempo_inicio_disparo']
    feat_laser_progresso = min(1.0, t_disp / laser['duracao_disparo'])
```

**O que Apolo entende**:
- `0.0`: "Não há perigo de laser agora"
- `0.5`: "Algo está carregando, prepare-se"
- `1.0`: "PERIGO ATIVO! Evite agora!"

### 2. Identificação da Rodada

Cada rodada tem comportamento diferente:

```python
rodada = laser.get('rodada', 1)
feat_laser_rodada = rodada / 4.0  # Normalizado 0.25, 0.5, 0.75, 1.0
```

**Configurações por Rodada**:

| Rodada | Feixes | Sentido | Giro Total | Dificuldade |
|--------|--------|---------|------------|-------------|
| 1 | 1 | Horário (+1) | 360° (2π) | Fácil |
| 2 | 2 | Anti-horário (-1) | 360° (2π) | Médio |
| 3 | 4 | Horário (+1) | 144° (0.8π) | Difícil |
| 4 | 6 | Anti-horário (-1) | 144° (0.8π) | Extremo |

```python
if rodada == 1:
    num_feixes = 1
    sentido = 1
    giro_total = math.pi * 2
elif rodada == 2:
    num_feixes = 2
    sentido = -1
    giro_total = math.pi * 2
elif rodada == 3:
    num_feixes = 4
    sentido = 1
    giro_total = math.pi * 0.8
else:  # Rodada 4
    num_feixes = 6
    sentido = -1
    giro_total = math.pi * 0.8
```

---

## Features Neurais do Laser

Apolo percebe o laser através de **9 features numéricas** que alimentam sua rede neural:

### Feature 1: Fase do Laser
```python
feat_laser_fase = 0.0  # 0 = inativo, 0.5 = carregando, 1.0 = disparando
```
**Significado**: Estado atual do laser

### Feature 2: Rodada Atual
```python
feat_laser_rodada = rodada / 4.0  # 0.25, 0.5, 0.75, 1.0
```
**Significado**: Qual padrão de ataque está ativo

### Feature 3: Progresso da Fase
```python
feat_laser_progresso = min(1.0, tempo_decorrido / duracao_fase)
```
**Significado**: Quão perto está de mudar de fase (0 = início, 1 = fim)

### Feature 4: Número de Feixes
```python
feat_laser_num_feixes = num_feixes / 6.0  # 0.16, 0.33, 0.66, 1.0
```
**Significado**: Quantos feixes simultâneos existem

### Feature 5: Sentido de Rotação
```python
feat_laser_sentido_rotacao = sentido  # -1 = anti-horário, 1 = horário
```
**Significado**: Direção do movimento do laser

### Feature 6: Velocidade Angular
```python
duracao_disparo = laser.get('duracao_disparo', 4000)  # ms
velocidade_angular = giro_total / (duracao_disparo / 1000.0)  # rad/s
feat_laser_velocidade_angular = min(1.0, abs(velocidade_angular) / (2 * math.pi))
```
**Significado**: Quão rápido o laser está girando

### Feature 7: Ângulo do Feixe Mais Próximo
```python
feat_laser_angulo_mais_proximo = math.sin(angulo_feixe_proximo)  # -1 a 1
```
**Significado**: Direção angular do feixe mais perigoso

### Feature 8: Distância ao Feixe Mais Próximo ⭐
```python
feat_laser_dist_feixe_proximo = min(1.0, menor_dist / 400.0)
```
**Significado**: Quão perto está do perigo (0 = muito perto, 1 = longe)

### Feature 9: Tempo Até Ser Atingido ⭐⭐
```python
# Calcula ângulo entre posição do player e feixe
angulo_player = math.atan2(py - origem_laser[1], px - origem_laser[0])
diff_angulo = angulo_player - angulo_atual

# Normaliza para -π a π
while diff_angulo > math.pi: diff_angulo -= 2 * math.pi
while diff_angulo < -math.pi: diff_angulo += 2 * math.pi

# Se laser está girando na direção do player
if (sentido > 0 and diff_angulo > 0) or (sentido < 0 and diff_angulo < 0):
    tempo_ate_atingir = abs(diff_angulo) / abs(velocidade_angular)
else:
    tempo_ate_atingir = 999  # Laser se afastando

feat_laser_tempo_ate_atingir = min(1.0, tempo_ate_atingir / 3.0)
```
**Significado**: Quanto tempo até o feixe varrer sua posição (CRÍTICO!)

---

## Cálculo da Distância ao Feixe

### Geometria: Distância Ponto-Linha

Apolo calcula a distância perpendicular entre sua posição e cada feixe do laser:

```python
# Para cada feixe
for i in range(num_feixes):
    angulo_atual = angulo_base + i * ((math.pi * 2) / num_feixes)
    
    # Ponto final do feixe (linha infinita)
    comp_laser = 2500  # Comprimento do laser
    fim_x = origem_laser[0] + math.cos(angulo_atual) * comp_laser
    fim_y = origem_laser[1] + math.sin(angulo_atual) * comp_laser
    
    # Fórmula de distância ponto-linha
    # d = |ax + by + c| / sqrt(a² + b²)
    numerador = abs((fim_y - origem_laser[1])*px - (fim_x - origem_laser[0])*py + 
                  fim_x*origem_laser[1] - fim_y*origem_laser[0])
    denominador = math.hypot(fim_y - origem_laser[1], fim_x - origem_laser[0])
    dist_linha = numerador / denominador if denominador > 0 else 9999
    
    # Verifica se está na frente do laser (não atrás)
    dot_product = (px - origem_laser[0]) * math.cos(angulo_atual) + \
                (py - origem_laser[1]) * math.sin(angulo_atual)
    
    if dot_product > 0:  # Está na frente
        menor_dist = min(menor_dist, dist_linha)
```

**Visualização**:
```
        Umbra (origem)
            *
            |\ 
            | \  <- Feixe (ângulo_atual)
            |  \
            |   \
            |    \
            |     \
            |  d   * <- Apolo (px, py)
            |     /
            |    /
            |   /
            |  /
            | /
            |/

d = distância perpendicular (menor_dist)
```

---

## Sistema de Recompensas

Apolo aprende a evitar o laser através de recompensas e penalidades:

### Durante Carregamento

```python
if laser.get('fase') == 'carregando':
    tempo_laser = agora - laser['tempo_inicio']
    progresso_carga = min(1.0, tempo_laser / laser['duracao_carga'])
    
    # Recompensa por se afastar do centro durante carregamento
    if boss_hitbox:
        dist_centro = math.hypot(boss_hitbox.centerx - px, boss_hitbox.centery - py)
        
        if dist_centro > 400:  # Longe do epicentro
            recompensa += 5
        elif dist_centro < 200:  # Muito perto (perigoso)
            recompensa -= 10
    
    # Alerta crescente conforme laser está prestes a disparar
    if progresso_carga > 0.8:  # 80% carregado
        recompensa += 3  # Recompensa por estar preparado
```

**O que Apolo aprende**:
- "Quando algo está carregando, afaste-se do centro"
- "Quando está quase pronto (80%), é bom estar longe"

### Durante Disparo (CRÍTICO)

```python
elif laser.get('fase') == 'disparando':
    # Calcula distância ao feixe mais próximo
    menor_dist = calcular_menor_distancia_aos_feixes()
    
    # Sistema de recompensas baseado em distância
    if menor_dist < 50:  # ZONA DE PERIGO EXTREMO
        recompensa -= 30
    elif menor_dist < 100:  # Zona de perigo
        recompensa -= 15
    elif menor_dist < 200:  # Zona de alerta
        recompensa -= 5
    elif 200 <= menor_dist < 350:  # Zona segura próxima
        recompensa += 8
    elif menor_dist >= 350:  # Zona muito segura
        recompensa += 15
    
    # Recompensa EXTRA por sobreviver sem dano
    if delta_vida_apolo == 0:
        recompensa += 25  # Grande recompensa por evasão perfeita
    
    # Penalidade SEVERA por ser atingido
    if delta_vida_apolo < 0:
        recompensa -= 200  # Penalidade massiva
```

**Tabela de Zonas**:

| Distância | Zona | Recompensa | Significado |
|-----------|------|------------|-------------|
| < 50px | Perigo Extremo | -30 | "VOCÊ VAI MORRER!" |
| 50-100px | Perigo | -15 | "Muito perto!" |
| 100-200px | Alerta | -5 | "Cuidado..." |
| 200-350px | Segura Próxima | +8 | "Bom, mas pode melhorar" |
| ≥ 350px | Muito Segura | +15 | "Perfeito!" |
| Sem dano | Evasão Perfeita | +25 | "EXCELENTE!" |
| Tomou dano | Falha Crítica | -200 | "NUNCA MAIS FAÇA ISSO!" |

---

## Sistema de Emergência

Quando o laser está muito próximo, Apolo ignora a persistência de ação e toma uma nova decisão imediatamente:

```python
# Condições para forçar nova decisão
forcar_nova_decisao = False

# Emergência 1: Laser ativo e muito próximo
if estado_ia:
    laser = estado_ia.get('laser_ativo')
    if laser and laser.get('fase') == 'disparando':
        if boss_hitbox:
            # Calcula distância ao feixe mais próximo
            menor_dist = calcular_menor_distancia_aos_feixes()
            
            # Se laser muito próximo, força nova decisão
            if menor_dist < 100:
                forcar_nova_decisao = True
```

**Sistema de Persistência Normal**:
- Apolo mantém uma ação por 15 frames (~250ms) para movimento fluido
- Evita "tremor" de decisões muito rápidas

**Sistema de Emergência**:
- Quando laser < 100px: IGNORA persistência
- Toma nova decisão IMEDIATAMENTE
- Prioriza sobrevivência sobre fluidez

---

## Processo Completo de Decisão

### Fluxo Frame-a-Frame

```
FRAME N: Laser Carregando (80% completo)
├─ PERCEPÇÃO
│  ├─ feat_laser_fase = 0.5 (carregando)
│  ├─ feat_laser_progresso = 0.8 (80% carregado)
│  ├─ dist_centro = 250px (perto do epicentro)
│  └─ feat_laser_rodada = 0.75 (rodada 3, 4 feixes)
│
├─ RECOMPENSA
│  ├─ dist_centro < 400: -10 pontos (muito perto)
│  └─ progresso > 0.8: +3 pontos (preparado)
│  └─ TOTAL: -7 pontos
│
├─ REDE NEURAL
│  ├─ Input: 40 features (incluindo 9 do laser)
│  ├─ Processamento: 40 → 128 → 64 → 9
│  └─ Output: Q-values para cada ação
│
├─ DECISÃO
│  ├─ Ação 7 (Baixo-Direita) tem maior Q-value
│  └─ Move para longe do centro
│
└─ APRENDIZADO
   └─ "Quando laser carregando + perto do centro = afastar"

---

FRAME N+15: Laser Disparando (início)
├─ PERCEPÇÃO
│  ├─ feat_laser_fase = 1.0 (DISPARANDO!)
│  ├─ feat_laser_num_feixes = 0.66 (4 feixes)
│  ├─ feat_laser_sentido_rotacao = 1.0 (horário)
│  ├─ feat_laser_velocidade_angular = 0.4
│  ├─ feat_laser_dist_feixe_proximo = 0.5 (200px)
│  └─ feat_laser_tempo_ate_atingir = 0.6 (1.8s)
│
├─ RECOMPENSA
│  ├─ menor_dist = 200px: -5 pontos (zona de alerta)
│  └─ delta_vida = 0: +25 pontos (sem dano)
│  └─ TOTAL: +20 pontos
│
├─ DECISÃO
│  ├─ Ação 3 (Direita) tem maior Q-value
│  └─ Move perpendicular ao feixe
│
└─ APRENDIZADO
   └─ "Quando laser disparando + 200px = mover perpendicular = bom"

---

FRAME N+30: Laser Muito Próximo!
├─ PERCEPÇÃO
│  ├─ feat_laser_fase = 1.0 (disparando)
│  ├─ feat_laser_dist_feixe_proximo = 0.2 (80px)
│  └─ feat_laser_tempo_ate_atingir = 0.1 (0.3s!)
│
├─ EMERGÊNCIA ATIVADA!
│  ├─ menor_dist < 100: forcar_nova_decisao = True
│  └─ IGNORA persistência de ação
│
├─ RECOMPENSA
│  ├─ menor_dist = 80px: -15 pontos (zona de perigo)
│  └─ delta_vida = 0: +25 pontos (ainda sem dano)
│  └─ TOTAL: +10 pontos
│
├─ DECISÃO IMEDIATA
│  ├─ Ação 1 (Baixo) tem maior Q-value
│  └─ Move para longe do feixe AGORA
│
└─ APRENDIZADO
   └─ "Quando laser < 100px = MOVER IMEDIATAMENTE"

---

FRAME N+45: Laser Passou
├─ PERCEPÇÃO
│  ├─ feat_laser_dist_feixe_proximo = 0.9 (360px)
│  └─ feat_laser_tempo_ate_atingir = 0.8 (2.4s)
│
├─ RECOMPENSA
│  ├─ menor_dist = 360px: +15 pontos (zona muito segura)
│  └─ delta_vida = 0: +25 pontos (evasão perfeita)
│  └─ TOTAL: +40 pontos (EXCELENTE!)
│
└─ APRENDIZADO FORTE
   └─ "Sequência de ações levou a evasão perfeita = REPETIR!"
```

---

## Exemplos Práticos

### Exemplo 1: Rodada 1 (1 Feixe, Horário)

**Situação Inicial**:
- Apolo está no centro do mapa (960, 540)
- Umbra ativa laser rodada 1
- 1 feixe girando no sentido horário

**Frame 1: Carregamento Iniciado**
```python
feat_laser_fase = 0.5
feat_laser_rodada = 0.25
feat_laser_progresso = 0.0
dist_centro = 50px  # Muito perto da Umbra

Recompensa: -10 (muito perto do epicentro)
Decisão: Mover para Baixo-Direita (afastar)
```

**Frame 60: Carregamento 80%**
```python
feat_laser_progresso = 0.8
dist_centro = 350px  # Já se afastou

Recompensa: +5 (longe do epicentro) + 3 (preparado) = +8
Decisão: Continuar se afastando
```

**Frame 90: Disparo Iniciado**
```python
feat_laser_fase = 1.0
feat_laser_num_feixes = 0.16  # 1 feixe
feat_laser_sentido_rotacao = 1.0  # Horário
feat_laser_velocidade_angular = 0.5
feat_laser_dist_feixe_proximo = 0.75  # 300px
feat_laser_tempo_ate_atingir = 0.5  # 1.5s

Recompensa: +8 (zona segura próxima)
Decisão: Mover perpendicular ao feixe
```

**Frame 120: Feixe Aproximando**
```python
feat_laser_dist_feixe_proximo = 0.25  # 100px
feat_laser_tempo_ate_atingir = 0.2  # 0.6s

Recompensa: -15 (zona de perigo)
EMERGÊNCIA: forcar_nova_decisao = True
Decisão: Dash perpendicular (ação 8)
```

**Frame 150: Feixe Passou**
```python
feat_laser_dist_feixe_proximo = 0.85  # 340px
delta_vida_apolo = 0  # Sem dano!

Recompensa: +15 (zona muito segura) + 25 (evasão perfeita) = +40
Aprendizado: "Dash perpendicular quando feixe < 100px = ÓTIMO!"
```

### Exemplo 2: Rodada 4 (6 Feixes, Anti-horário)

**Situação Inicial**:
- Apolo está em (800, 400)
- Umbra ativa laser rodada 4
- 6 feixes girando anti-horário (MUITO DIFÍCIL!)

**Frame 1: Carregamento**
```python
feat_laser_rodada = 1.0  # Rodada 4 (máxima dificuldade)
feat_laser_num_feixes = 1.0  # 6 feixes
dist_centro = 200px

Recompensa: -10 (muito perto)
Decisão: Afastar URGENTEMENTE
```

**Frame 90: Disparo com 6 Feixes**
```python
feat_laser_fase = 1.0
feat_laser_num_feixes = 1.0  # 6 feixes
feat_laser_sentido_rotacao = -1.0  # Anti-horário
feat_laser_velocidade_angular = 0.3  # Mais lento (0.8π)

# Calcula distância para CADA feixe
feixes = [0°, 60°, 120°, 180°, 240°, 300°]
distancias = [250px, 180px, 400px, 320px, 150px, 280px]
menor_dist = 150px  # Feixe mais próximo

feat_laser_dist_feixe_proximo = 0.375  # 150px
feat_laser_tempo_ate_atingir = 0.4  # 1.2s

Recompensa: -5 (zona de alerta)
Decisão: Mover para o "gap" entre feixes
```

**Frame 120: Navegando Entre Feixes**
```python
# Apolo está entre dois feixes
distancias = [300px, 250px, 350px, 280px, 200px, 320px]
menor_dist = 200px

feat_laser_dist_feixe_proximo = 0.5  # 200px

Recompensa: +8 (zona segura próxima)
Decisão: Manter movimento circular
```

**Frame 180: Feixe Crítico**
```python
menor_dist = 90px  # MUITO PERTO!
feat_laser_tempo_ate_atingir = 0.15  # 0.45s

Recompensa: -15 (zona de perigo)
EMERGÊNCIA: forcar_nova_decisao = True
Decisão: Dash para o gap mais largo
```

**Frame 240: Sobreviveu!**
```python
menor_dist = 380px
delta_vida_apolo = 0  # SEM DANO!

Recompensa: +15 (zona muito segura) + 25 (evasão perfeita) = +40
Aprendizado: "Navegar entre 6 feixes = possível com movimento circular"
```

---

## Resumo: Como Apolo Aprende a Desviar

### Fase 1: Ignorância (Gerações 0-50)
```
"O que é esse laser? Vou ficar parado."
Resultado: -200 pontos (tomou dano)
```

### Fase 2: Medo (Gerações 50-100)
```
"Quando vejo feat_laser_fase = 1.0, devo me mover!"
Resultado: -15 pontos (ainda perto, mas sem dano)
```

### Fase 3: Compreensão (Gerações 100-200)
```
"Quando feat_laser_dist_feixe_proximo < 0.5, devo me afastar!"
Resultado: +8 pontos (zona segura)
```

### Fase 4: Maestria (Gerações 200+)
```
"Quando feat_laser_tempo_ate_atingir < 0.3, uso dash perpendicular!"
Resultado: +40 pontos (evasão perfeita)
```

### O que Apolo NÃO Sabe

- ❌ Que é um "laser"
- ❌ Que causa dano de contato
- ❌ Que vem da Umbra
- ❌ Que tem 4 rodadas diferentes

### O que Apolo SABE

- ✅ Há linhas de perigo que giram
- ✅ Distância até a linha mais próxima
- ✅ Velocidade e direção da rotação
- ✅ Tempo até ser atingido
- ✅ Ficar longe = bom, ficar perto = ruim
- ✅ Ser atingido = MUITO ruim (-200 pontos)
- ✅ Evasão perfeita = MUITO bom (+40 pontos)

---

## Conclusão

Apolo desenvolve uma "intuição" sobre o laser através de:

1. **Percepção Rica**: 9 features numéricas descrevendo o laser
2. **Recompensas Claras**: Zonas de perigo com penalidades progressivas
3. **Sistema de Emergência**: Reação imediata quando perigo < 100px
4. **Aprendizado Gradual**: Centenas de gerações refinando estratégias

**Resultado**: Apolo aprende a:
- Afastar-se durante carregamento
- Manter distância segura (200-350px)
- Mover perpendicular aos feixes
- Usar dash em emergências
- Navegar entre múltiplos feixes

**Tudo isso sem uma única regra programada - apenas experiência pura.**
