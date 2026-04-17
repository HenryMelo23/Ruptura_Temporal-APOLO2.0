# Arquitetura do Mec-Predador: Documentação Técnica

## Visão Geral

O Mec-Predador é uma criatura biomecânica alienígena quadrúpede implementada como uma simulação física de alto desempenho operando a 100 FPS. A arquitetura abandona modelos estáticos em favor de uma máquina de estados dinâmica com motor de partículas integrado.

---

## 1. Especificações Visuais

### Estética
- **Estilo**: Pixel art detalhada (era 32-bits)
- **Tema**: Terror biomecânico alienígena
- **Anatomia**: Quadrúpede complexo com mandíbulas articuladas

### Paleta de Cores

```python
# Fundo
VAZIO_ESPACIAL = (15, 15, 20)  # Cinza profundo

# Corpo Biomecânico
VERDE_ESCURO = (25, 80, 45)    # Carapaça orgânica
VERDE_CLARO = (50, 180, 90)    # Tecido vivo
ROXO_PROFUNDO = (60, 20, 80)   # Metalurgia pesada
ROXO_CLARO = (140, 60, 180)    # Blindagem segmentada

# Detalhes Orgânicos
ROSA_NEON = (255, 50, 150)     # Presas e conduítes
ROSA_NEON_BRILHO = (255, 120, 200)

# Energia
AMARELO_ENERGIA = (255, 240, 80)   # Núcleo do reator
LARANJA_ENERGIA = (255, 140, 40)   # Feixes de energia

# Rastro Cinético
CIANO_VIBRANTE = (0, 255, 255)     # Rastro inicial
CIANO_DISSIPATIVO = (0, 180, 200)  # Rastro dissipando
```

---

## 2. Máquina de Estados

### Estados Disponíveis

```python
class EstadoMecPredador(Enum):
    REPOUSANDO = "REPOUSANDO"
    CARREGANDO = "CARREGANDO"
    ATACANDO = "ATACANDO"
    RETORNANDO = "RETORNANDO"
```

### Diagrama de Transição

```
┌─────────────┐
│ REPOUSANDO  │ ◄──────────────────────┐
└──────┬──────┘                        │
       │ iniciar_ataque()              │
       │ (dist > 100px)                │
       ▼                               │
┌─────────────┐                        │
│ CARREGANDO  │                        │
│  (2000ms)   │                        │
└──────┬──────┘                        │
       │ tempo >= 2000ms               │
       ▼                               │
┌─────────────┐                        │
│  ATACANDO   │                        │
│ (dash 800px/s)                       │
└──────┬──────┘                        │
       │ colisão com alvo              │
       ▼                               │
┌─────────────┐                        │
│ RETORNANDO  │                        │
│ (200px/s)   │ ───────────────────────┘
└─────────────┘
```

### Lógica de Cada Estado

#### REPOUSANDO
```python
def _atualizar_repousando(self, dt: float):
    # Pulsação orgânica constante
    self.fase_pulsacao += dt * 3
    
    # Permanece na origem
    self.x = self.origem_x
    self.y = self.origem_y
```

**Características**:
- Aguarda na posição de origem
- Pulsação visual orgânica (3 rad/s)
- Pronto para receber gatilho de ataque

#### CARREGANDO
```python
def _atualizar_carregando(self, dt: float):
    self.tempo_estado += dt * 1000  # ms
    
    # Fixa posição
    self.x = self.origem_x
    self.y = self.origem_y
    
    # Gera partículas de energia
    self._gerar_particulas_carregamento()
    
    # Atualiza física das partículas
    nucleo_x = self.x + self.nucleo_offset_x
    nucleo_y = self.y + self.nucleo_offset_y
    forca_atracao = 500  # pixels/s²
    
    for p in self.particulas_energia:
        p.atualizar(dt, nucleo_x, nucleo_y, forca_atracao)
    
    # Pulsação intensa
    self.fase_pulsacao += dt * 8
    
    # Transição após 2000ms EXATOS
    if self.tempo_estado >= 2000:
        self.estado = EstadoMecPredador.ATACANDO
```

**Características**:
- Duração fixa: 2000ms (não negociável)
- Posição travada na origem
- Motor de partículas ativo (atração gravitacional)
- Pulsação intensa (8 rad/s)
- Acúmulo visual de energia no núcleo

#### ATACANDO
```python
def _atualizar_atacando(self, dt: float):
    # Gera rastro cinético
    self._gerar_rastro_cinetico()
    
    # Move em direção ao alvo
    chegou = self._mover_para_alvo(dt, 800)  # 800 px/s
    
    # Atualiza rastro
    for r in self.particulas_rastro:
        r.atualizar(dt)
    
    # Transição ao colidir
    if chegou:
        self.estado = EstadoMecPredador.RETORNANDO
        self.alvo_x = self.origem_x
        self.alvo_y = self.origem_y
```

**Características**:
- Velocidade extrema: 800 pixels/segundo
- Movimento retilíneo contínuo (dash)
- Rastro cinético ciano denso
- Colisão zera velocidade instantaneamente

#### RETORNANDO
```python
def _atualizar_retornando(self, dt: float):
    # Move de volta à origem (mais lento)
    chegou = self._mover_para_alvo(dt, 200)  # 200 px/s
    
    # Atualiza rastro residual
    for r in self.particulas_rastro:
        r.atualizar(dt)
    
    # Pulsação suave
    self.fase_pulsacao += dt * 2
    
    # Transição ao chegar na origem
    if chegou:
        self.estado = EstadoMecPredador.REPOUSANDO
```

**Características**:
- Velocidade tática: 200 pixels/segundo (4x mais lento)
- Movimento fluido de recuo
- Rastro residual dissipando
- Retorna ao estado de repouso

---

## 3. Sistema de Física Vetorial

### Movimento Euclidiano Puro

```python
def _mover_para_alvo(self, dt: float, velocidade: float):
    """Movimento vetorial sem teletransporte"""
    # Calcula vetor direção
    dx = self.alvo_x - self.x
    dy = self.alvo_y - self.y
    dist = math.hypot(dx, dy)
    
    if dist > 1:
        # Normaliza vetor (magnitude = 1)
        dx_norm = dx / dist
        dy_norm = dy / dist
        
        # Aplica velocidade
        deslocamento = velocidade * dt
        
        if deslocamento >= dist:
            # Chegou ao destino
            self.x = self.alvo_x
            self.y = self.alvo_y
            self.vx = 0
            self.vy = 0
            return True
        else:
            # Move incrementalmente
            self.x += dx_norm * deslocamento
            self.y += dy_norm * deslocamento
            self.vx = dx_norm * velocidade
            self.vy = dy_norm * velocidade
            return False
    else:
        self.vx = 0
        self.vy = 0
        return True
```

**Princípios**:
1. Cálculo de vetor direção (dx, dy)
2. Normalização para magnitude unitária
3. Aplicação de velocidade escalar
4. Movimento incremental frame-a-frame
5. Detecção precisa de chegada

**Vantagens**:
- Movimento suave e contínuo
- Sem saltos ou teletransporte
- Velocidade constante
- Independente de framerate (usa dt)

---

## 4. Motor de Partículas

### Partícula de Energia (Carregamento)

```python
@dataclass
class ParticulaEnergia:
    x: float
    y: float
    vx: float
    vy: float
    vida: float  # 0.0 a 1.0
    tamanho: float
    cor: Tuple[int, int, int]
    
    def atualizar(self, dt: float, alvo_x: float, alvo_y: float, 
                  forca_atracao: float):
        # Vetor direção ao núcleo
        dx = alvo_x - self.x
        dy = alvo_y - self.y
        dist = math.hypot(dx, dy)
        
        if dist > 1:
            # Normaliza e aplica força gravitacional
            dx_norm = dx / dist
            dy_norm = dy / dist
            
            self.vx += dx_norm * forca_atracao * dt
            self.vy += dy_norm * forca_atracao * dt
        
        # Atualiza posição
        self.x += self.vx * dt
        self.y += self.vy * dt
        
        # Decai vida
        self.vida -= 0.3 * dt
        
        return self.vida > 0
```

**Física**:
- Atração gravitacional ao núcleo (500 px/s²)
- Velocidade inicial aleatória
- Decaimento temporal (0.3/s)
- Cores alternadas (amarelo/laranja)

**Geração**:
```python
def _gerar_particulas_carregamento(self):
    for _ in range(3):  # 3 partículas por frame
        angulo = random.uniform(0, 2 * math.pi)
        raio = random.uniform(80, 150)
        
        px = self.x + self.nucleo_offset_x + math.cos(angulo) * raio
        py = self.y + self.nucleo_offset_y + math.sin(angulo) * raio
        
        vx = random.uniform(-50, 50)
        vy = random.uniform(-50, 50)
        
        cor = random.choice([AMARELO_ENERGIA, LARANJA_ENERGIA])
        
        particula = ParticulaEnergia(
            x=px, y=py, vx=vx, vy=vy,
            vida=1.0, tamanho=random.uniform(2, 5), cor=cor
        )
        self.particulas_energia.append(particula)
```

### Partícula de Rastro (Ataque)

```python
@dataclass
class ParticulaRastro:
    x: float
    y: float
    tamanho: float
    vida: float  # 0.0 a 1.0
    cor: Tuple[int, int, int]
    
    def atualizar(self, dt: float):
        # Dissipação temporal
        self.vida -= 1.2 * dt
        self.tamanho *= 0.95
        return self.vida > 0
```

**Física**:
- Dissipação rápida (1.2/s)
- Redução de tamanho (5% por frame)
- Cor ciano vibrante

**Geração**:
```python
def _gerar_rastro_cinetico(self):
    # Emite na traseira da criatura
    rastro_x = self.x - self.vx * 0.05
    rastro_y = self.y - self.vy * 0.05
    
    for _ in range(2):  # 2 partículas por frame
        offset_x = random.uniform(-10, 10)
        offset_y = random.uniform(-10, 10)
        
        particula = ParticulaRastro(
            x=rastro_x + offset_x,
            y=rastro_y + offset_y,
            tamanho=random.uniform(5, 12),
            vida=1.0,
            cor=CIANO_VIBRANTE
        )
        self.particulas_rastro.append(particula)
```

---

## 5. Renderização Procedural

### Anatomia Quadrúpede

```python
def _desenhar_corpo_quadrupede(self, tela, offset_x, offset_y):
    x_base = int(self.x) + offset_x
    y_base = int(self.y) + offset_y
    
    # Pulsação orgânica
    pulso = math.sin(self.fase_pulsacao) * 2
    
    # === PERNAS TRASEIRAS ===
    # Esquerda
    pygame.draw.line(tela, ROXO_PROFUNDO, 
                    (x_base + 10, y_base + 40), 
                    (x_base + 5, y_base + 55), 4)
    pygame.draw.circle(tela, VERDE_ESCURO, 
                      (x_base + 5, y_base + 55), 4)
    
    # Direita
    pygame.draw.line(tela, ROXO_PROFUNDO, 
                    (x_base + 20, y_base + 40), 
                    (x_base + 15, y_base + 55), 4)
    pygame.draw.circle(tela, VERDE_ESCURO, 
                      (x_base + 15, y_base + 55), 4)
    
    # === CORPO (blindagem segmentada) ===
    # Segmento traseiro
    pygame.draw.ellipse(tela, VERDE_ESCURO, 
                       (x_base, y_base + 20, 35, 25))
    pygame.draw.ellipse(tela, ROXO_PROFUNDO, 
                       (x_base + 3, y_base + 23, 29, 19), 2)
    
    # Segmento central
    pygame.draw.ellipse(tela, VERDE_CLARO, 
                       (x_base + 20, y_base + 15, 40, 30))
    pygame.draw.ellipse(tela, ROXO_CLARO, 
                       (x_base + 23, y_base + 18, 34, 24), 2)
    
    # === PERNAS DIANTEIRAS ===
    # Esquerda
    pygame.draw.line(tela, ROXO_PROFUNDO, 
                    (x_base + 45, y_base + 35), 
                    (x_base + 40, y_base + 52), 5)
    pygame.draw.circle(tela, VERDE_CLARO, 
                      (x_base + 40, y_base + 52), 5)
    
    # Direita
    pygame.draw.line(tela, ROXO_PROFUNDO, 
                    (x_base + 55, y_base + 35), 
                    (x_base + 50, y_base + 52), 5)
    pygame.draw.circle(tela, VERDE_CLARO, 
                      (x_base + 50, y_base + 52), 5)
    
    # === CABEÇA (mandíbulas articuladas) ===
    # Crânio
    pygame.draw.ellipse(tela, VERDE_ESCURO, 
                       (x_base + 50, y_base + 10, 30, 25))
    
    # Blindagem craniana
    pygame.draw.arc(tela, ROXO_PROFUNDO, 
                   (x_base + 52, y_base + 12, 26, 21), 
                   0, math.pi, 3)
    
    # Mandíbulas (superior e inferior)
    pontos_sup = [
        (x_base + 75, y_base + 15),
        (x_base + 85, y_base + 18),
        (x_base + 80, y_base + 22)
    ]
    pygame.draw.polygon(tela, ROSA_NEON, pontos_sup)
    
    pontos_inf = [
        (x_base + 75, y_base + 25),
        (x_base + 85, y_base + 22),
        (x_base + 80, y_base + 28)
    ]
    pygame.draw.polygon(tela, ROSA_NEON, pontos_inf)
    
    # Presas
    pygame.draw.line(tela, ROSA_NEON_BRILHO, 
                    (x_base + 82, y_base + 20), 
                    (x_base + 88, y_base + 20), 2)
    
    # === NÚCLEO DE ENERGIA ===
    nucleo_x = x_base + self.nucleo_offset_x
    nucleo_y = y_base + self.nucleo_offset_y
    
    # Brilho pulsante
    raio_brilho = 12 + int(pulso)
    pygame.draw.circle(tela, LARANJA_ENERGIA, 
                      (nucleo_x, nucleo_y), raio_brilho)
    
    # Núcleo interno
    pygame.draw.circle(tela, AMARELO_ENERGIA, 
                      (nucleo_x, nucleo_y), 8)
    
    # Conduítes de energia
    for i in range(3):
        offset = i * 8
        pygame.draw.line(tela, AMARELO_ENERGIA, 
                       (nucleo_x, nucleo_y), 
                       (x_base + 30 + offset, y_base + 25), 2)
```

### Pipeline de Renderização

```python
def renderizar(self, tela: pygame.Surface):
    # 1. Rastro cinético (camada de fundo)
    self._desenhar_rastro_cinetico(tela)
    
    # 2. Partículas de energia (carregamento)
    if self.estado == EstadoMecPredador.CARREGANDO:
        self._desenhar_particulas_energia(tela)
    
    # 3. Corpo biomecânico (camada principal)
    self._desenhar_corpo_quadrupede(tela, 0, 0)
    
    # 4. Indicador de estado (debug)
    fonte = pygame.font.Font(None, 20)
    texto = fonte.render(self.estado.value, True, (255, 255, 255))
    tela.blit(texto, (int(self.x), int(self.y) - 20))
```

---

## 6. API Pública

### Inicialização

```python
predador = MecPredador(x=300, y=400)
```

### Controle de Ataque

```python
# Inicia ataque (valida distância > 100px)
sucesso = predador.iniciar_ataque(alvo_x=800, alvo_y=400)

if sucesso:
    print("Ataque iniciado!")
else:
    print("Alvo muito próximo ou predador ocupado")
```

### Loop de Jogo

```python
while rodando:
    dt = clock.tick(100) / 1000.0  # Delta time em segundos
    
    # Atualiza física e estados
    predador.atualizar(dt)
    
    # Renderiza
    tela.fill(VAZIO_ESPACIAL)
    predador.renderizar(tela)
    pygame.display.flip()
```

### Detecção de Colisão

```python
hitbox = predador.obter_hitbox()

if hitbox.collidepoint(jogador_x, jogador_y):
    print("Jogador atingido!")
```

---

## 7. Otimizações de Performance

### Gerenciamento de Partículas

```python
# Remove partículas mortas automaticamente
self.particulas_energia = [
    p for p in self.particulas_energia 
    if p.atualizar(dt, nucleo_x, nucleo_y, forca_atracao)
]

self.particulas_rastro = [
    r for r in self.particulas_rastro 
    if r.atualizar(dt)
]
```

### Delta Time Independente

```python
# Movimento independente de framerate
deslocamento = velocidade * dt  # pixels

# Física de partículas
self.x += self.vx * dt
self.vida -= taxa_decaimento * dt
```

### Renderização Condicional

```python
# Partículas de energia apenas durante carregamento
if self.estado == EstadoMecPredador.CARREGANDO:
    self._desenhar_particulas_energia(tela)
```

---

## 8. Constantes de Configuração

```python
# Performance
FPS_TARGET = 100

# Temporização
DURACAO_CARREGAMENTO = 2000  # ms (não negociável)

# Física
VELOCIDADE_ATAQUE = 800      # pixels/segundo
VELOCIDADE_RETORNO = 200     # pixels/segundo
DISTANCIA_MINIMA_ALVO = 100  # pixels

# Partículas
FORCA_ATRACAO_ENERGIA = 500  # pixels/s²
TAXA_DECAIMENTO_ENERGIA = 0.3  # por segundo
TAXA_DECAIMENTO_RASTRO = 1.2   # por segundo
```

---

## 9. Exemplo de Integração

```python
import pygame
from mec_predador import MecPredador, Paleta, FPS_TARGET

pygame.init()
tela = pygame.display.set_mode((1920, 1080))
clock = pygame.time.Clock()

# Cria predador
predador = MecPredador(300, 540)

# Alvo
alvo_x, alvo_y = 1600, 540

rodando = True
while rodando:
    dt = clock.tick(FPS_TARGET) / 1000.0
    
    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            rodando = False
        
        if evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_SPACE:
                predador.iniciar_ataque(alvo_x, alvo_y)
    
    # Atualiza
    predador.atualizar(dt)
    
    # Renderiza
    tela.fill(Paleta.VAZIO_ESPACIAL)
    pygame.draw.circle(tela, (255, 0, 0), (alvo_x, alvo_y), 10)
    predador.renderizar(tela)
    pygame.display.flip()

pygame.quit()
```

---

## 10. Conclusão

O Mec-Predador é uma implementação completa de uma criatura biomecânica com:

✅ Máquina de estados robusta (4 estados)  
✅ Física vetorial euclidiana pura  
✅ Motor de partículas dual (energia + rastro)  
✅ Renderização procedural detalhada  
✅ Performance otimizada @ 100 FPS  
✅ API pública simples e intuitiva  

**Pronto para integração em qualquer projeto Pygame.**
