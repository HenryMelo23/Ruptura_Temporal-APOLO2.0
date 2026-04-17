# Rosa Sanguinária: Documentação de Design

## Visão Geral

A Rosa Sanguinária é uma flor biomecânica mortal com design elegante e minimalista. Composta apenas por pétalas animadas, miolo pulsante e caule com folhas, ela mantém toda a funcionalidade do Mec-Predador com uma estética floral hipnotizante.

---

## 1. Anatomia da Rosa

### Componentes Principais

```
        ╭─────╮
       ╱ Miolo ╲      ← Núcleo pulsante (amarelo/laranja/dourado)
      ╱         ╲
     │  Pétalas  │    ← 8 pétalas animadas (vermelho/rosa)
      ╲         ╱
       ╲       ╱
        │Caule│       ← Caule verde com folhas
        │     │
       ╱│     │╲
      ╱ Folhas ╲     ← 2 folhas laterais
```

### Dimensões

- **Sprite Total**: 120x120 pixels
- **Raio das Pétalas**: 35-45 pixels (varia com abertura)
- **Miolo**: 18-21 pixels (pulsante)
- **Caule**: 8x30 pixels
- **Folhas**: ~20 pixels cada

---

## 2. Paleta de Cores

### Pétalas (Gradiente Vermelho/Rosa)

```python
VERMELHO_SANGUE = (180, 20, 30)    # Pétalas pares (base)
VERMELHO_ESCURO = (120, 15, 25)    # Bordas escuras
ROSA_INTENSO = (255, 50, 80)       # Pétalas ímpares
ROSA_CLARO = (255, 120, 150)       # Detalhes claros
ROSA_NEON = (255, 80, 180)         # Pontas brilhantes
```

**Padrão de Alternância**:
```
Pétala 0: Vermelho Sangue
Pétala 1: Rosa Intenso
Pétala 2: Vermelho Sangue
Pétala 3: Rosa Intenso
...
```

### Miolo (Gradiente Amarelo/Laranja)

```python
AMARELO_POLEN = (255, 220, 80)     # Centro (pólen)
LARANJA_MIOLO = (255, 160, 40)     # Camada média
DOURADO = (255, 200, 100)          # Camada externa
```

**Estrutura em Camadas**:
```
┌─────────────────┐
│   Externo       │ ← Dourado (raio maior)
│  ┌───────────┐  │
│  │  Médio    │  │ ← Laranja
│  │ ┌───────┐ │  │
│  │ │Interno│ │  │ ← Amarelo Pólen
│  │ └───────┘ │  │
│  └───────────┘  │
└─────────────────┘
```

### Caule e Folhas

```python
VERDE_CAULE = (40, 100, 50)        # Caule principal
VERDE_FOLHA = (60, 140, 70)        # Folhas
VERDE_ESCURO = (30, 80, 40)        # Detalhes/nervuras
```

### Energia e Rastro

```python
VERMELHO_ENERGIA = (255, 30, 50)   # Partículas de carregamento
ROSA_ENERGIA = (255, 100, 180)     # Partículas alternadas
VERMELHO_RASTRO = (255, 50, 100)   # Rastro durante ataque
ROSA_RASTRO = (255, 150, 200)      # Rastro dissipando
```

---

## 3. Sistema de Pétalas

### Geometria das Pétalas

Cada pétala tem formato de **gota** (teardrop):

```python
# Parâmetros
raio_base = 15          # Distância do miolo
raio_ponta = 35-45      # Comprimento (varia com abertura)
largura_base = 18       # Largura na base
largura_ponta = 12      # Largura na ponta

# Pontos da pétala
Base Esquerda ────┐
                  │
Base Direita ─────┤
                  │
Ponta Esquerda ───┤
                  │
Ponta (afiada) ───┤  ← Ponto único (formato de gota)
                  │
Ponta Direita ────┘
```

### Distribuição Angular

8 pétalas distribuídas uniformemente:

```python
for i in range(8):
    angulo = (i / 8) * 2π
    
    # Pétalas em:
    # 0°, 45°, 90°, 135°, 180°, 225°, 270°, 315°
```

**Visualização**:
```
        0° (→)
    315°    45°
        ╲  ╱
270° ────✿──── 90°
        ╱  ╲
    225°    135°
       180° (←)
```

### Animação de Abertura/Fechamento

```python
# Fase da animação (0 a 2π)
self.fase_petalas = 0.0

# Abertura (0 = fechada, 1 = aberta)
abertura = (sin(fase_petalas) + 1) / 2

# Extensão das pétalas
raio_ponta = 35 + abertura * 10  # 35px a 45px

# Rotação adicional ao abrir
rotacao_abertura = abertura * 0.2  # Pétalas giram levemente
```

**Estados de Abertura**:

| Fase | Abertura | Raio | Visual |
|------|----------|------|--------|
| 0 | 0.0 | 35px | ✿ Fechada |
| π/2 | 1.0 | 45px | ❀ Totalmente aberta |
| π | 0.0 | 35px | ✿ Fechada |
| 3π/2 | 1.0 | 45px | ❀ Totalmente aberta |

### Detalhes das Pétalas

#### Nervura Central

```python
# Linha da base até a ponta
pygame.draw.line(sprite, cor_detalhe,
               (base_x, base_y), (ponta_x, ponta_y), 2)
```

#### Nervuras Laterais

```python
# Ponto médio da pétala
meio_x = (base_x + ponta_x) / 2
meio_y = (base_y + ponta_y) / 2

# Nervuras perpendiculares (6 pixels)
nerv_esq_x = meio_x + cos(angulo_perp) * 6
nerv_dir_x = meio_x - cos(angulo_perp) * 6
```

**Estrutura**:
```
Base
 │
 ├──── Nervura Esquerda
 │
Meio
 │
 ├──── Nervura Direita
 │
Ponta ●
```

#### Ponta Brilhante

```python
# Círculo rosa neon na ponta
pygame.draw.circle(sprite, ROSA_NEON, (ponta_x, ponta_y), 3)
```

---

## 4. Sistema do Miolo

### Estrutura em Camadas

```python
# Raio pulsante
raio_externo = 18 + pulso  # 18-21px
raio_medio = 14 + pulso    # 14-17px
raio_interno = 10          # Fixo

# Camadas
pygame.draw.circle(sprite, LARANJA_MIOLO, (cx, cy), raio_externo)
pygame.draw.circle(sprite, DOURADO, (cx, cy), raio_medio)
pygame.draw.circle(sprite, AMARELO_POLEN, (cx, cy), raio_interno)
```

### Grãos de Pólen

12 grãos distribuídos em círculo:

```python
num_graos = 12
raio_graos = 8  # Distância do centro

for i in range(12):
    angulo = (i / 12) * 2π + fase_pulsacao * 0.5  # Giram lentamente
    
    grao_x = cx + cos(angulo) * raio_graos
    grao_y = cy + sin(angulo) * raio_graos
    
    tamanho = 2 if i % 2 == 0 else 1  # Alternados
```

**Visualização**:
```
    ●   ●   ●
  ●   ╭───╮   ●
 ●   │  ✦  │   ●  ← Grãos de pólen girando
  ●   ╰───╯   ●
    ●   ●   ●
```

### Brilho Central

```python
# Ponto de luz no canto superior esquerdo
pygame.draw.circle(sprite, (255, 255, 200), (cx - 3, cy - 3), 3)
```

---

## 5. Caule e Folhas

### Caule Principal

```python
# Retângulo vertical
caule_largura = 8
caule_altura = 30

pygame.draw.rect(sprite, VERDE_CAULE,
                (cx - 4, cy + 25, 8, 30))

# Textura (3 linhas horizontais)
for i in range(3):
    y_offset = cy + 30 + i * 10
    pygame.draw.line(sprite, VERDE_ESCURO,
                   (cx - 2, y_offset), (cx + 2, y_offset), 1)
```

### Folhas

#### Folha Esquerda

```python
pontos = [
    (cx - 4, cy + 35),   # Base (no caule)
    (cx - 20, cy + 30),  # Ponta esquerda
    (cx - 18, cy + 40),  # Ponta inferior
    (cx - 4, cy + 40)    # Base inferior
]

# Preenchimento
pygame.draw.polygon(sprite, VERDE_FOLHA, pontos)

# Borda
pygame.draw.polygon(sprite, VERDE_ESCURO, pontos, 2)

# Nervura central
pygame.draw.line(sprite, VERDE_ESCURO,
               (cx - 4, cy + 37), (cx - 18, cy + 35), 1)
```

#### Folha Direita

Simétrica à esquerda, espelhada no eixo Y.

**Visualização**:
```
      ╭─╮
      │ │ Caule
     ╱│ │╲
    ╱ │ │ ╲
   ╱  │ │  ╲ Folhas
  ────┴─┴────
```

---

## 6. Animação por Estado

### REPOUSANDO

```python
# Pulsação suave
self.fase_pulsacao += dt * 3  # 3 rad/s

# Pétalas respirando
self.fase_petalas += dt * 2   # 2 rad/s
```

**Visual**: Rosa descansando, pétalas semi-abertas, miolo pulsando suavemente.

### CARREGANDO

```python
# Pulsação intensa
self.fase_pulsacao += dt * 10  # 10 rad/s

# Pétalas abrindo rapidamente
self.fase_petalas += dt * 8    # 8 rad/s

# Partículas de energia convergindo
_gerar_particulas_carregamento()
```

**Visual**: Rosa carregando energia, pétalas se abrindo, partículas vermelhas/rosas sendo atraídas ao miolo.

### ATACANDO

```python
# Pétalas totalmente abertas e girando
self.fase_petalas += dt * 16   # 16 rad/s

# Rastro de pétalas
_gerar_rastro()

# Rotação direcional
self.angulo_rotacao = calcular_angulo_movimento()
```

**Visual**: Rosa em dash, pétalas totalmente abertas, deixando rastro vermelho/rosa, rotacionada na direção do movimento.

### RETORNANDO

```python
# Pétalas fechando gradualmente
self.fase_petalas += dt * 8    # 8 rad/s

# Pulsação moderada
self.fase_pulsacao += dt * 2   # 2 rad/s
```

**Visual**: Rosa retornando, pétalas fechando, movimento mais lento.

---

## 7. Comparação: Mec-Predador vs Rosa Sanguinária

| Aspecto | Mec-Predador | Rosa Sanguinária |
|---------|--------------|------------------|
| **Tema** | Biomecânico alienígena | Flor mortal |
| **Cores** | Verde/Roxo/Rosa | Vermelho/Rosa/Amarelo |
| **Partes Móveis** | Asas (2) | Pétalas (8) |
| **Complexidade** | Alta (pernas, corpo, asas) | Média (pétalas, miolo, caule) |
| **Animação** | Batida de asas | Abertura de pétalas |
| **Estética** | Terror biomecânico | Beleza mortal |
| **Tamanho** | 140x100px | 120x120px |

---

## 8. Tabela de Velocidades

| Estado | Pulsação | Pétalas | Movimento | Visual |
|--------|----------|---------|-----------|--------|
| REPOUSANDO | 3 rad/s | 2 rad/s | 0 px/s | Respiração |
| CARREGANDO | 10 rad/s | 8 rad/s | 0 px/s | Preparação |
| ATACANDO | - | 16 rad/s | 800 px/s | Ataque |
| RETORNANDO | 2 rad/s | 8 rad/s | 200 px/s | Retorno |

---

## 9. Exemplo de Uso

```python
from rosa_sanguinaria import RosaSanguinaria

# Cria rosa
rosa = RosaSanguinaria(400, 300)

# Loop de jogo
while rodando:
    dt = clock.tick(100) / 1000.0
    
    # Atualiza
    rosa.atualizar(dt)
    
    # Renderiza
    rosa.renderizar(tela)
    
    # Inicia ataque
    if clique:
        rosa.iniciar_ataque(mouse_x, mouse_y)
```

---

## 10. Detalhes Técnicos

### Renderização em Camadas

```python
def renderizar(self, tela):
    # 1. Rastro (fundo)
    _desenhar_rastro(tela)
    
    # 2. Partículas de energia
    if estado == CARREGANDO:
        _desenhar_particulas_energia(tela)
    
    # 3. Sprite rotacionado
    sprite = _criar_sprite_rosa()
    sprite_rotacionado = pygame.transform.rotate(sprite, angulo)
    tela.blit(sprite_rotacionado, posicao)
```

### Ordem de Desenho do Sprite

```python
def _criar_sprite_rosa(self):
    # 1. Caule (fundo)
    _desenhar_caule(sprite, cx, cy)
    
    # 2. Pétalas (meio)
    _desenhar_petalas(sprite, cx, cy, abertura)
    
    # 3. Miolo (frente)
    _desenhar_miolo(sprite, cx, cy, pulso)
```

---

## 11. Conclusão

A Rosa Sanguinária é uma criatura elegante e mortal que combina:

✅ **Design minimalista** (pétalas + miolo + caule)  
✅ **Paleta vibrante** (vermelho/rosa/amarelo)  
✅ **Animação fluida** (abertura de pétalas)  
✅ **Rotação direcional** (8 direções)  
✅ **Performance otimizada** (100 FPS)  
✅ **Estética hipnotizante** (beleza mortal)  

**Uma flor que mata com elegância!** 🌹💀
