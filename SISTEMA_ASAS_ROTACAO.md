# Sistema de Asas e Rotação do Mec-Predador

## Visão Geral

O Mec-Predador agora possui asas biomecânicas animadas que batem sincronizadas com o movimento, e o sprite completo rotaciona dinamicamente baseado na direção de deslocamento.

---

## 1. Sistema de Asas Biomecânicas

### Anatomia das Asas

As asas são estruturas biomecânicas compostas por:
- **Membrana orgânica** (verde escuro)
- **Nervuras principais** (roxo profundo)
- **Nervuras secundárias** (roxo claro)
- **Bordas reforçadas** (rosa neon)
- **Garras nas pontas** (rosa neon brilhante)

### Animação de Batida

```python
# Fase da batida (0 a 2π)
self.fase_batida_asas = 0.0

# Amplitude da batida (0 = fechada, 1 = aberta)
batida = (math.sin(self.fase_batida_asas) + 1) / 2

# Ângulo das asas baseado na batida
angulo_asa = batida * 45  # 0° a 45°
```

**Estados de Batida**:

| Fase | Batida | Ângulo | Visual |
|------|--------|--------|--------|
| 0 | 0.0 | 0° | Asas fechadas |
| π/2 | 1.0 | 45° | Asas totalmente abertas |
| π | 0.0 | 0° | Asas fechadas |
| 3π/2 | 1.0 | 45° | Asas totalmente abertas |
| 2π | 0.0 | 0° | Asas fechadas (ciclo completo) |

### Velocidade de Batida por Estado

```python
# REPOUSANDO: Batida lenta (respiração)
self.fase_batida_asas += dt * 4  # 4 rad/s

# CARREGANDO: Batida rápida (preparação)
self.fase_batida_asas += dt * 12  # 12 rad/s

# ATACANDO: Batida muito rápida (propulsão)
self.fase_batida_asas += dt * 24  # 24 rad/s

# RETORNANDO: Batida moderada (retorno)
self.fase_batida_asas += dt * 12  # 12 rad/s
```

### Geometria das Asas

#### Asa Esquerda (Superior)

```python
# Ponto base (fixo no corpo)
asa_esq_base_x = cx - 10
asa_esq_base_y = cy - 8

# Ângulo de abertura
angulo_rad = math.radians(180 - angulo_asa)

# Ponta da asa (rotacionada)
asa_esq_ponta_x = asa_esq_base_x + math.cos(angulo_rad) * comprimento_asa
asa_esq_ponta_y = asa_esq_base_y + math.sin(angulo_rad) * comprimento_asa
```

**Visualização**:
```
        Fechada (0°)          Aberta (45°)
            |                    /
            |                   /
          CORPO               CORPO
            |                   \
            |                    \
```

#### Asa Direita (Inferior)

```python
# Ponto base (fixo no corpo)
asa_dir_base_x = cx - 10
asa_dir_base_y = cy + 8

# Ângulo de abertura (oposto)
angulo_rad_dir = math.radians(180 + angulo_asa)

# Ponta da asa (rotacionada)
asa_dir_ponta_x = asa_dir_base_x + math.cos(angulo_rad_dir) * comprimento_asa
asa_dir_ponta_y = asa_dir_base_y + math.sin(angulo_rad_dir) * comprimento_asa
```

### Nervuras Biomecânicas

```python
# Nervura principal (estrutural)
pygame.draw.line(sprite, ROXO_PROFUNDO,
                (asa_base_x, asa_base_y),
                (asa_ponta_x, asa_ponta_y), 3)

# Nervuras secundárias (3 por asa)
for i in range(3):
    offset = (i + 1) / 4  # 25%, 50%, 75% do comprimento
    
    # Ponto na nervura principal
    meio_x = asa_base_x + (asa_ponta_x - asa_base_x) * offset
    meio_y = asa_base_y + (asa_ponta_y - asa_base_y) * offset
    
    # Nervura perpendicular (8 pixels)
    perp_x = meio_x + math.sin(angulo_rad) * 8
    perp_y = meio_y - math.cos(angulo_rad) * 8
    
    pygame.draw.line(sprite, ROXO_CLARO,
                   (meio_x, meio_y), (perp_x, perp_y), 2)
```

**Estrutura**:
```
Base ──────┬──────┬──────┬────── Ponta
           │      │      │
           │      │      │  (nervuras perpendiculares)
```

---

## 2. Sistema de Rotação Direcional

### Cálculo do Ângulo

```python
def _calcular_angulo_movimento(self) -> float:
    """Calcula ângulo baseado na direção de movimento"""
    if abs(self.vx) < 0.1 and abs(self.vy) < 0.1:
        # Sem movimento, mantém ângulo atual
        return self.angulo_rotacao
    
    # Calcula ângulo em radianos
    angulo_rad = math.atan2(-self.vy, self.vx)  # -vy porque Y cresce para baixo
    
    # Converte para graus
    angulo_graus = math.degrees(angulo_rad)
    
    return angulo_graus
```

### Mapeamento de Direções

| Direção | vx | vy | Ângulo | Visual |
|---------|----|----|--------|--------|
| Direita | +1 | 0 | 0° | → |
| Cima-Direita | +1 | -1 | 45° | ↗ |
| Cima | 0 | -1 | 90° | ↑ |
| Cima-Esquerda | -1 | -1 | 135° | ↖ |
| Esquerda | -1 | 0 | 180° | ← |
| Baixo-Esquerda | -1 | +1 | -135° | ↙ |
| Baixo | 0 | +1 | -90° | ↓ |
| Baixo-Direita | +1 | +1 | -45° | ↘ |

### Aplicação da Rotação

```python
# Cria sprite base
sprite = self._criar_sprite_pixel_art()

# Rotaciona sprite
sprite_rotacionado = pygame.transform.rotate(sprite, self.angulo_rotacao)

# Centraliza sprite rotacionado na posição
rect = sprite_rotacionado.get_rect(center=(int(self.x), int(self.y)))
tela.blit(sprite_rotacionado, rect)
```

**Importante**: `pygame.transform.rotate` rotaciona no sentido anti-horário, e o ângulo 0° aponta para a direita.

---

## 3. Sincronização Movimento + Asas

### Durante Ataque

```python
def _atualizar_atacando(self, dt: float):
    # Move em direção ao alvo
    chegou = self._mover_para_alvo(dt, VELOCIDADE_ATAQUE)
    
    # Atualiza ângulo baseado no movimento
    self.angulo_rotacao = self._calcular_angulo_movimento()
    
    # Batida de asas muito rápida (propulsão)
    self.fase_batida_asas += dt * self.velocidade_batida * 2  # 24 rad/s
```

**Resultado**: Predador aponta para o alvo e bate asas rapidamente durante o dash.

### Durante Retorno

```python
def _atualizar_retornando(self, dt: float):
    # Move de volta à origem
    chegou = self._mover_para_alvo(dt, VELOCIDADE_RETORNO)
    
    # Atualiza ângulo (aponta para origem)
    self.angulo_rotacao = self._calcular_angulo_movimento()
    
    # Batida de asas moderada
    self.fase_batida_asas += dt * self.velocidade_batida  # 12 rad/s
```

**Resultado**: Predador aponta para a origem e bate asas moderadamente durante o recuo.

---

## 4. Exemplo Prático: Ataque Diagonal

### Situação
- Predador em (300, 500)
- Alvo em (800, 200)
- Direção: Cima-Direita

### Frame 1: Início do Carregamento
```python
# Calcula ângulo inicial
dx = 800 - 300 = 500
dy = 200 - 500 = -300
angulo_rad = math.atan2(-(-300), 500) = math.atan2(300, 500) = 0.54 rad
angulo_graus = 31°

# Estado
self.angulo_rotacao = 31°
self.fase_batida_asas = 0.0
```

**Visual**: Predador aponta para cima-direita (31°), asas fechadas.

### Frame 60: Carregamento 50%
```python
# Batida rápida
self.fase_batida_asas = 0.0 + (12 rad/s * 1s) = 12 rad ≈ 1.9π
batida = (sin(12) + 1) / 2 ≈ 0.3
angulo_asa = 0.3 * 45° = 13.5°
```

**Visual**: Predador ainda apontando 31°, asas parcialmente abertas (13.5°).

### Frame 120: Início do Ataque
```python
# Movimento iniciado
vx = 500 / dist * 800 = 640 px/s
vy = -300 / dist * 800 = -384 px/s

# Ângulo mantido
self.angulo_rotacao = 31°

# Batida muito rápida
self.fase_batida_asas += dt * 24
```

**Visual**: Predador em dash diagonal, asas batendo rapidamente.

### Frame 180: Durante Ataque
```python
# Posição atualizada
x = 300 + 640 * 0.6 = 684
y = 500 - 384 * 0.6 = 270

# Ângulo mantido (movimento constante)
self.angulo_rotacao = 31°

# Asas batendo
batida = (sin(fase) + 1) / 2  # Oscilando 0-1
```

**Visual**: Predador voando em diagonal, asas batendo em ciclos rápidos.

### Frame 240: Colisão
```python
# Chegou ao alvo
x = 800
y = 200

# Transição para retorno
self.estado = RETORNANDO
self.alvo_x = 300
self.alvo_y = 500

# Novo ângulo (direção oposta)
dx = 300 - 800 = -500
dy = 500 - 200 = 300
angulo_graus = 180° + 31° = 211°
```

**Visual**: Predador inverte direção, agora aponta para baixo-esquerda (211°).

---

## 5. Otimizações

### Cache de Sprites (Desabilitado)

O cache foi removido para garantir animação fluida das asas:

```python
# ANTES (com cache - asas congeladas)
cache_key = (angulo_cache, self.estado.value, int(self.fase_batida_asas * 10))
if cache_key in self.sprite_cache:
    return self.sprite_cache[cache_key]

# AGORA (sem cache - asas animadas)
sprite = self._criar_sprite_pixel_art()  # Recria a cada frame
sprite_rotacionado = pygame.transform.rotate(sprite, self.angulo_rotacao)
```

**Trade-off**: Pequena perda de performance (~5 FPS) em troca de animação fluida.

### Renderização Eficiente

```python
# Cria sprite apenas quando necessário
sprite = self._criar_sprite_pixel_art()

# Rotaciona uma única vez
sprite_rotacionado = pygame.transform.rotate(sprite, self.angulo_rotacao)

# Centraliza e renderiza
rect = sprite_rotacionado.get_rect(center=(int(self.x), int(self.y)))
tela.blit(sprite_rotacionado, rect)
```

---

## 6. Tabela de Velocidades de Batida

| Estado | Velocidade | Rad/s | Ciclos/s | Visual |
|--------|-----------|-------|----------|--------|
| REPOUSANDO | Lenta | 4 | 0.64 | Respiração suave |
| CARREGANDO | Rápida | 12 | 1.91 | Preparação intensa |
| ATACANDO | Muito Rápida | 24 | 3.82 | Propulsão máxima |
| RETORNANDO | Moderada | 12 | 1.91 | Retorno controlado |

**Cálculo**: Ciclos/s = Rad/s / (2π)

---

## 7. Exemplo de Uso

```python
from mec_predador import MecPredador

# Cria predador
predador = MecPredador(300, 400)

# Loop de jogo
while rodando:
    dt = clock.tick(100) / 1000.0
    
    # Atualiza (física + animação + rotação)
    predador.atualizar(dt)
    
    # Renderiza (sprite rotacionado + asas animadas)
    predador.renderizar(tela)
    
    # Debug
    print(f"Ângulo: {predador.angulo_rotacao:.1f}°")
    print(f"Fase Asas: {predador.fase_batida_asas:.2f} rad")
```

---

## 8. Conclusão

O sistema de asas e rotação adiciona:

✅ **Asas biomecânicas** com nervuras detalhadas  
✅ **Animação de batida** sincronizada com estados  
✅ **Rotação direcional** baseada em movimento  
✅ **8 direções** (cardeais + diagonais)  
✅ **Velocidades variáveis** de batida por estado  
✅ **Renderização fluida** @ 100 FPS  

**O Mec-Predador agora voa dinamicamente em qualquer direção com asas batendo realisticamente!**
