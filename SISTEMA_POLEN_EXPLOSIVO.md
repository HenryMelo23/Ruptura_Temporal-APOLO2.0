# Sistema de Pólen Explosivo

## Visão Geral

A Rosa Sanguinária agora deixa um rastro mortal de pólen explosivo enquanto se move. Cada pólen explode após 2 segundos, criando uma zona de perigo que persiste no campo de batalha.

---

## 1. Mecânica de Geração

### Regra de Spawn

```python
# A cada 5 pixels percorridos, gera 4 pólens
distancia_para_spawn = 5  # pixels
polens_por_spawn = 4
```

### Cálculo de Distância

```python
def _verificar_distancia_percorrida(self):
    # Calcula distância desde última posição
    dx = self.x - self.ultima_pos_x
    dy = self.y - self.ultima_pos_y
    dist = math.hypot(dx, dy)
    
    self.distancia_percorrida += dist
    
    # A cada 5 pixels, gera pólen
    if self.distancia_percorrida >= 5:
        self._gerar_polen_explosivo()
        self.distancia_percorrida = 0
    
    # Atualiza última posição
    self.ultima_pos_x = self.x
    self.ultima_pos_y = self.y
```

### Geração de Pólen

```python
def _gerar_polen_explosivo(self):
    # Gera 4 pólens em posições ligeiramente aleatórias
    for _ in range(4):
        offset_x = random.uniform(-8, 8)
        offset_y = random.uniform(-8, 8)
        
        polen = PolenExplosivo(
            x=self.x + offset_x,
            y=self.y + offset_y,
            tempo_vida=2.0,  # 2 segundos até explodir
            tamanho=random.uniform(4, 7),
            fase_pulsacao=random.uniform(0, 2π)
        )
        self.polens_explosivos.append(polen)
```

**Resultado**: Cluster de 4 pólens espalhados em ~16 pixels de raio

---

## 2. Pólen Explosivo

### Estrutura de Dados

```python
@dataclass
class PolenExplosivo:
    x: float              # Posição X
    y: float              # Posição Y
    tempo_vida: float     # Tempo até explodir (2s)
    tamanho: float        # Raio base (4-7px)
    fase_pulsacao: float  # Fase da animação
    explodiu: bool        # Flag de explosão
```

### Ciclo de Vida

```
Spawn → Pulsação (2s) → Explosão → Remoção
  ↓         ↓              ↓
Verde    Laranja       Vermelho
(seguro) (alerta)     (perigo!)
```

### Sistema de Cores por Tempo

```python
if tempo_vida > 1.5:
    # Verde/amarelo (seguro) - 75% do tempo
    cor_externa = AMARELO_POLEN
    cor_interna = DOURADO
    
elif tempo_vida > 0.5:
    # Laranja (alerta) - 50% do tempo
    cor_externa = LARANJA_MIOLO
    cor_interna = AMARELO_POLEN
    
else:
    # Vermelho (perigo!) - últimos 25%
    cor_externa = VERMELHO_ENERGIA
    cor_interna = ROSA_ENERGIA
```

**Timeline Visual**:
```
2.0s ●────────────────────────────────────────● 0.0s
     Verde          Laranja         Vermelho
     (seguro)       (alerta)        (PERIGO!)
     
     1.5s ────────── 0.5s ────────── 0.0s
```

### Pulsação Acelerada

```python
# Pulsação aumenta conforme se aproxima da explosão
urgencia = max(0, 1 - (tempo_vida / 2.0))  # 0 a 1
pulso = sin(fase_pulsacao) * (3 + urgencia * 5)

raio = tamanho_base + pulso
```

**Amplitude da Pulsação**:

| Tempo Restante | Urgência | Amplitude | Raio Min | Raio Max |
|----------------|----------|-----------|----------|----------|
| 2.0s | 0.0 | 3px | 4px | 10px |
| 1.5s | 0.25 | 4.25px | 4px | 11.25px |
| 1.0s | 0.5 | 5.5px | 4px | 12.5px |
| 0.5s | 0.75 | 6.75px | 4px | 13.75px |
| 0.0s | 1.0 | 8px | 4px | 15px |

**Resultado**: Pólen pulsa cada vez mais intensamente antes de explodir

---

## 3. Explosão

### Estrutura de Dados

```python
@dataclass
class ExplosaoPolem:
    x: float          # Centro da explosão
    y: float          # Centro da explosão
    raio: float       # Raio atual
    raio_max: float   # Raio máximo (80px)
    vida: float       # 0.0 a 1.0
```

### Expansão

```python
# Expande rapidamente
raio += 200 * dt  # 200 pixels/segundo

# Decai vida
vida -= 2.0 * dt  # 0.5 segundos de duração
```

**Timeline de Expansão**:
```
Tempo | Raio | Vida
------|------|------
0.0s  | 0px  | 1.0
0.1s  | 20px | 0.8
0.2s  | 40px | 0.6
0.3s  | 60px | 0.4
0.4s  | 80px | 0.2
0.5s  | 100px| 0.0 (fim)
```

**Raio Máximo**: 80 pixels (limitado)

### Renderização em Camadas

```python
# Múltiplos círculos para efeito de explosão
raios = [raio, raio * 0.7, raio * 0.4]
cores = [
    VERMELHO_ENERGIA,  # Camada externa
    ROSA_ENERGIA,      # Camada média
    AMARELO_POLEN      # Núcleo
]
```

**Visualização**:
```
    ╭─────────────╮
   ╱ Vermelho     ╲  ← Raio completo
  │  ╭─────────╮  │
  │ ╱  Rosa    ╲ │  ← 70% do raio
  │ │ ╭─────╮ │ │
  │ │ │Amar.│ │ │  ← 40% do raio
  │ │ ╰─────╯ │ │
  │ ╲         ╱ │
   ╲           ╱
    ╰─────────╯
```

### Sistema de Alpha

```python
alpha = int(vida * 255)  # 0-255

# Explosão fica transparente conforme desaparece
```

---

## 4. Detecção de Colisão

### Hitbox da Explosão

```python
def obter_hitbox(self) -> pygame.Rect:
    return pygame.Rect(
        int(self.x - self.raio),
        int(self.y - self.raio),
        int(self.raio * 2),
        int(self.raio * 2)
    )
```

### API para Detecção

```python
# Obter explosões ativas
explosoes = rosa.obter_explosoes_ativas()

# Verificar colisão
for explosao in explosoes:
    hitbox = explosao.obter_hitbox()
    if hitbox.collidepoint(jogador_x, jogador_y):
        # Jogador atingido!
        aplicar_dano(jogador)
```

---

## 5. Comportamento da Rosa

### Durante Ataque

```python
def _atualizar_atacando(self, dt):
    # Move em direção ao alvo
    self._mover_para_alvo(dt, VELOCIDADE_ATAQUE)
    
    # Verifica distância e gera pólen
    self._verificar_distancia_percorrida()
    
    # Ao colidir com alvo
    if chegou:
        # Rosa PARA no local da colisão
        # Continua girando no lugar
        self.estado = RETORNANDO
```

**Importante**: Rosa fica no local da colisão, não volta imediatamente!

### Exemplo de Trajetória

```
Origem (300, 500)
    │
    │ ●●●● (pólen a cada 5px)
    │
    │ ●●●●
    │
    │ ●●●●
    │
    ▼
Alvo (800, 200)
    ↻ (rosa gira no local)
    
    ●●●● (pólen continua sendo gerado)
    
    ← (retorna à origem)
```

---

## 6. Estatísticas de Geração

### Velocidade de Ataque: 800 px/s

```python
# Cálculo de pólen gerado por segundo
pixels_por_segundo = 800
pixels_por_spawn = 5
spawns_por_segundo = 800 / 5 = 160

polens_por_spawn = 4
polens_por_segundo = 160 * 4 = 640 pólens/s
```

**Durante 1 segundo de ataque**: 640 pólens gerados!

### Distância de 500 pixels

```python
distancia = 500
spawns = 500 / 5 = 100
total_polens = 100 * 4 = 400 pólens
```

**Resultado**: Rastro denso de 400 pólens em 500 pixels

### Explosões Simultâneas

```python
# Todos os pólens explodem após 2s
tempo_explosao = 2.0

# Se rosa continuar gerando pólen por 2s
polens_gerados_em_2s = 640 * 2 = 1280

# Explosões simultâneas (pico)
explosoes_simultaneas = ~100-200 (dependendo do timing)
```

---

## 7. Exemplo Prático

### Cenário: Ataque de 300 pixels

```
Frame 0: Rosa inicia ataque
  Posição: (300, 500)
  Pólen: 0

Frame 10 (0.1s): Percorreu 80px
  Posição: (380, 500)
  Spawns: 80 / 5 = 16
  Pólen: 16 * 4 = 64 pólens

Frame 20 (0.2s): Percorreu 160px
  Posição: (460, 500)
  Spawns: 32
  Pólen: 128 pólens
  
Frame 30 (0.3s): Percorreu 240px
  Posição: (540, 500)
  Spawns: 48
  Pólen: 192 pólens

Frame 37.5 (0.375s): Chegou ao alvo (300px)
  Posição: (600, 500)
  Spawns: 60
  Pólen: 240 pólens
  Estado: Rosa para e gira no local

Frame 200 (2.0s): Primeiras explosões
  Pólen restante: 240 - 64 = 176
  Explosões: 64 (primeiros pólens explodem)

Frame 210 (2.1s): Mais explosões
  Explosões: 128 (mais pólens explodem)

Frame 237.5 (2.375s): Últimas explosões
  Explosões: 240 (todos explodiram)
  Campo de batalha: Zona de perigo de 300px
```

---

## 8. Estratégias de Jogo

### Para o Jogador

1. **Evite o Rastro**: Não siga a rosa durante o ataque
2. **Observe as Cores**: Verde = seguro, Vermelho = fuja!
3. **Timing**: Espere as explosões antes de se aproximar
4. **Zona Segura**: Fique longe do ponto de colisão

### Para a Rosa

1. **Ataque Direto**: Cria linha de pólen até o alvo
2. **Ataque Circular**: Cerca o jogador com pólen
3. **Ataque em Zigue-Zague**: Cobre área maior
4. **Ataque Repetido**: Sobrepõe camadas de pólen

---

## 9. Configuração

### Parâmetros Ajustáveis

```python
# Geração
PIXELS_POR_SPAWN = 5        # Distância entre spawns
POLENS_POR_SPAWN = 4        # Quantidade por spawn

# Pólen
TEMPO_VIDA_POLEN = 2.0      # Segundos até explodir
TAMANHO_POLEN_MIN = 4       # Pixels
TAMANHO_POLEN_MAX = 7       # Pixels
OFFSET_SPAWN = 8            # Dispersão do cluster

# Explosão
RAIO_MAX_EXPLOSAO = 80      # Pixels
VELOCIDADE_EXPANSAO = 200   # Pixels/segundo
DURACAO_EXPLOSAO = 0.5      # Segundos
```

---

## 10. Performance

### Otimizações

```python
# Remove pólen que explodiu
polens_para_remover = []
for polen in self.polens_explosivos:
    if polen.explodiu:
        polens_para_remover.append(polen)

for polen in polens_para_remover:
    self.polens_explosivos.remove(polen)

# Remove explosões que terminaram
self.explosoes = [
    exp for exp in self.explosoes
    if exp.atualizar(dt)
]
```

### Limites Recomendados

- **Pólen Ativo**: < 500 (boa performance)
- **Explosões Simultâneas**: < 100 (boa performance)
- **Total no Campo**: < 1000 objetos

---

## 11. Conclusão

O sistema de pólen explosivo adiciona:

✅ **Controle de Área**: Rosa domina o espaço por onde passa  
✅ **Perigo Persistente**: Ameaça continua após o ataque  
✅ **Feedback Visual**: Cores indicam perigo iminente  
✅ **Gameplay Dinâmico**: Jogador deve planejar movimento  
✅ **Efeito Cascata**: Múltiplas explosões simultâneas  
✅ **Zona de Negação**: Áreas se tornam inacessíveis  

**A Rosa Sanguinária agora é uma ameaça territorial que controla o campo de batalha!** 🌹💥
