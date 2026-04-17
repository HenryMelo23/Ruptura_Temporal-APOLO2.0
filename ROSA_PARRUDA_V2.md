# Rosa Sanguinária V2: Versão Parruda

## Mudanças Implementadas

### 1. Remoção do Caule ❌
- **Antes**: Rosa tinha caule verde com 2 folhas laterais
- **Agora**: Apenas pétalas + miolo (design mais limpo e focado)
- **Benefício**: Foco total na flor, visual mais impactante

### 2. Aumento do Número de Pétalas 🌹
- **Antes**: 8 pétalas
- **Agora**: 12 pétalas
- **Visual**: Rosa muito mais densa e robusta
- **Distribuição**: 30° entre cada pétala (360° / 12)

### 3. Pétalas Mais Grossas e Robustas 💪

#### Dimensões Atualizadas

| Parâmetro | Antes | Agora | Aumento |
|-----------|-------|-------|---------|
| Largura Base | 18px | 28px | +55% |
| Largura Ponta | 12px | 20px | +67% |
| Raio Ponta (fechada) | 35px | 45px | +29% |
| Raio Ponta (aberta) | 45px | 60px | +33% |
| Espessura Borda | 2px | 3px | +50% |
| Espessura Nervura | 2px | 3px | +50% |
| Tamanho Ponta Brilhante | 3px | 4px | +33% |

#### Nervuras Aumentadas
- **Antes**: 2 nervuras laterais por pétala
- **Agora**: 4 nervuras laterais por pétala
- **Posições**: 20%, 40%, 60%, 80% do comprimento

### 4. Rotação Horária Contínua ⏰

#### Sistema de Rotação

```python
# Nova variável
self.angulo_rotacao_petalas = 0.0  # Graus (0-360)
self.velocidade_rotacao_petalas = 30.0  # graus/segundo base
```

#### Velocidades por Estado

| Estado | Multiplicador | Velocidade | Rotação Completa |
|--------|---------------|------------|------------------|
| REPOUSANDO | 0.3x | 9°/s | 40 segundos |
| CARREGANDO | 2.0x | 60°/s | 6 segundos |
| ATACANDO | 4.0x | 120°/s | 3 segundos |
| RETORNANDO | 1.0x | 30°/s | 12 segundos |

#### Implementação

```python
# Durante atualização
self.angulo_rotacao_petalas += velocidade * dt * multiplicador

# Normaliza para 0-360°
if self.angulo_rotacao_petalas >= 360:
    self.angulo_rotacao_petalas -= 360

# Aplica ao desenhar pétalas
angulo_final = angulo_base + math.radians(self.angulo_rotacao_petalas)
```

### 5. Padrão de Cores em Grupos de 3

**Antes**: Alternância simples (par/ímpar)
```
Pétala 0: Vermelho
Pétala 1: Rosa
Pétala 2: Vermelho
Pétala 3: Rosa
...
```

**Agora**: Grupos de 3 cores
```
Pétala 0: Vermelho Sangue
Pétala 1: Rosa Intenso
Pétala 2: Vermelho Escuro
Pétala 3: Vermelho Sangue
Pétala 4: Rosa Intenso
Pétala 5: Vermelho Escuro
...
```

**Resultado**: Padrão visual mais rico e variado

---

## Comparação Visual

### Antes (V1)
```
        ╭─╮
        │ │ Caule
       ╱│ │╲
      ╱ │ │ ╲ Folhas
     ────┴─┴────
        ✿
    8 pétalas finas
```

### Agora (V2)
```
       ❀❀❀
     ❀❀❀❀❀❀
    ❀❀❀✿❀❀❀
     ❀❀❀❀❀❀
       ❀❀❀
    
  12 pétalas grossas
  Girando no sentido horário
  Sem caule
```

---

## Especificações Técnicas

### Sprite
- **Tamanho**: 140x140 pixels (aumentado de 120x120)
- **Centro**: (70, 70)
- **Camadas**: 2 (pétalas + miolo)

### Pétalas
- **Quantidade**: 12
- **Formato**: Gota robusta
- **Largura Base**: 28px
- **Largura Ponta**: 20px
- **Comprimento**: 45-60px (variável)
- **Nervuras**: 1 central + 4 laterais por pétala
- **Cores**: 3 variações (vermelho sangue, rosa intenso, vermelho escuro)

### Miolo
- **Raio**: 18-21px (pulsante)
- **Camadas**: 3 (amarelo, laranja, dourado)
- **Grãos de Pólen**: 12 (girando)
- **Brilho**: Ponto de luz animado

### Animações
- **Pulsação Miolo**: 3-10 rad/s (dependendo do estado)
- **Abertura Pétalas**: 2-16 rad/s (dependendo do estado)
- **Rotação Horária**: 9-120°/s (dependendo do estado)

---

## Performance

### Antes
- 8 pétalas × 3 nervuras = 24 linhas
- 8 bordas
- Total: ~40 operações de desenho por frame

### Agora
- 12 pétalas × 5 nervuras = 60 linhas
- 12 bordas (mais grossas)
- Total: ~80 operações de desenho por frame

**Impacto**: +100% operações, mas ainda mantém 100 FPS estável

---

## Código de Exemplo

```python
from rosa_sanguinaria import RosaSanguinaria

# Cria rosa parruda
rosa = RosaSanguinaria(400, 300)

# Loop de jogo
while rodando:
    dt = clock.tick(100) / 1000.0
    
    # Atualiza (inclui rotação horária automática)
    rosa.atualizar(dt)
    
    # Renderiza
    rosa.renderizar(tela)
    
    # Debug
    print(f"Rotação Pétalas: {rosa.angulo_rotacao_petalas:.1f}°")
    print(f"Número de Pétalas: {rosa.num_petalas}")
```

---

## Velocidades de Rotação Detalhadas

### REPOUSANDO (Respiração)
```python
velocidade = 30 * 0.3 = 9°/s
tempo_rotacao_completa = 360 / 9 = 40 segundos
```
**Visual**: Pétalas girando muito lentamente, como uma respiração

### CARREGANDO (Preparação)
```python
velocidade = 30 * 2.0 = 60°/s
tempo_rotacao_completa = 360 / 60 = 6 segundos
```
**Visual**: Pétalas girando rapidamente, acumulando energia

### ATACANDO (Propulsão)
```python
velocidade = 30 * 4.0 = 120°/s
tempo_rotacao_completa = 360 / 120 = 3 segundos
```
**Visual**: Pétalas girando muito rápido, como uma serra circular

### RETORNANDO (Desaceleração)
```python
velocidade = 30 * 1.0 = 30°/s
tempo_rotacao_completa = 360 / 30 = 12 segundos
```
**Visual**: Pétalas girando em velocidade moderada

---

## Exemplo de Rotação em Tempo Real

### Sequência de 10 Segundos (Estado ATACANDO)

```
Tempo | Ângulo | Rotações Completas
------|--------|-------------------
0s    | 0°     | 0
1s    | 120°   | 0.33
2s    | 240°   | 0.67
3s    | 360°   | 1.00 ✓
4s    | 480°   | 1.33 (normalizado: 120°)
5s    | 600°   | 1.67 (normalizado: 240°)
6s    | 720°   | 2.00 ✓
7s    | 840°   | 2.33 (normalizado: 120°)
8s    | 960°   | 2.67 (normalizado: 240°)
9s    | 1080°  | 3.00 ✓
10s   | 1200°  | 3.33 (normalizado: 120°)
```

**Resultado**: 3 rotações completas em 10 segundos durante ataque

---

## Conclusão

A Rosa Sanguinária V2 é:

✅ **Mais Parruda**: 12 pétalas grossas (vs 8 finas)  
✅ **Mais Limpa**: Sem caule, foco na flor  
✅ **Mais Dinâmica**: Rotação horária contínua  
✅ **Mais Detalhada**: 4 nervuras laterais por pétala  
✅ **Mais Robusta**: +55% largura nas pétalas  
✅ **Mais Hipnotizante**: Rotação variável por estado  

**Uma flor mortal e hipnotizante que gira como uma serra circular!** 🌹⚙️
