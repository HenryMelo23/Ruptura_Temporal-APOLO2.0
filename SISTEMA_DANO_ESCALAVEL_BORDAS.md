# SISTEMA DE DANO ESCALÁVEL - BORDAS TÓXICAS

## PROBLEMA ORIGINAL

As bordas tóxicas (dimensão Rastro) causavam dano fixo de 5% da vida máxima a cada 1 segundo, resultando em morte quase instantânea se o jogador ficasse preso.

---

## SOLUÇÃO IMPLEMENTADA

Sistema de dano escalável que começa baixo e aumenta gradualmente quanto mais tempo o jogador permanece nas bordas venenosas.

---

## MECÂNICA DO SISTEMA

### Parâmetros Principais

```python
INTERVALO_DANO = 800ms          # Dano aplicado a cada 800ms (conforme solicitado)
DANO_INICIAL = 0.5%             # Dano inicial (da vida máxima)
ESCALA_POR_SEGUNDO = 0.3%       # Aumento de dano por segundo
DANO_MÁXIMO = 5%                # Dano máximo (após ~15 segundos)
```

### Fórmula de Dano

```python
dano_percentual = min(0.05, 0.005 + (tempo_segundos * 0.003))
dano_bordas = vida_maxima * dano_percentual
```

**Onde**:
- `tempo_segundos` = tempo acumulado nas bordas / 1000
- `0.005` = dano inicial (0.5%)
- `0.003` = escala por segundo (0.3%)
- `0.05` = dano máximo (5%)

---

## PROGRESSÃO DE DANO

### Tabela de Dano ao Longo do Tempo

| Tempo nas Bordas | Dano por Tick | Dano Total (10 ticks) | Vida Perdida (1000 HP) |
|------------------|---------------|------------------------|------------------------|
| 0-0.8s           | 0.5%          | 5%                     | 50 HP                  |
| 0.8-1.6s         | 0.74%         | 7.4%                   | 74 HP                  |
| 1.6-2.4s         | 0.98%         | 9.8%                   | 98 HP                  |
| 2.4-3.2s         | 1.22%         | 12.2%                  | 122 HP                 |
| 3.2-4.0s         | 1.46%         | 14.6%                  | 146 HP                 |
| 4.0-4.8s         | 1.70%         | 17.0%                  | 170 HP                 |
| 8.0-8.8s         | 2.90%         | 29.0%                  | 290 HP                 |
| 12.0-12.8s       | 4.10%         | 41.0%                  | 410 HP                 |
| 15.0s+           | 5.00% (MAX)   | 50.0%                  | 500 HP                 |

### Gráfico de Progressão

```
Dano %
  5% ┤                                    ████████████
     │                              ██████
  4% ┤                        ██████
     │                  ██████
  3% ┤            ██████
     │      ██████
  2% ┤ █████
     │█
  1% ┤
     │
  0% └─────────────────────────────────────────────────> Tempo (s)
     0    2    4    6    8   10   12   14   16   18   20
```

---

## RASTREAMENTO DE TEMPO

### Variáveis Globais Adicionadas

```python
tempo_entrada_bordas = 0        # Timestamp de quando entrou nas bordas
tempo_acumulado_bordas = 0      # Tempo total acumulado nas bordas
ultimo_tick_dano_bordas = 0     # Timestamp do último tick de dano
estava_nas_bordas = False       # Flag de estado anterior
```

### Lógica de Rastreamento

```python
if nas_bordas:
    if not estava_nas_bordas:
        # Acabou de entrar
        tempo_entrada_bordas = agora
        tempo_acumulado_bordas = 0
        estava_nas_bordas = True
    
    # Atualiza tempo acumulado
    tempo_acumulado_bordas = agora - tempo_entrada_bordas
    
    # Aplica dano a cada 800ms
    if agora - ultimo_tick_dano_bordas >= 800:
        # Calcula dano escalável
        tempo_segundos = tempo_acumulado_bordas / 1000.0
        dano_percentual = min(0.05, 0.005 + (tempo_segundos * 0.003))
        dano_bordas = vida_maxima * dano_percentual
        
        vida -= dano_bordas
        ultimo_tick_dano_bordas = agora
else:
    # Saiu das bordas
    if estava_nas_bordas:
        estava_nas_bordas = False
        tempo_acumulado_bordas = 0
```

---

## FEEDBACK VISUAL ESCALÁVEL

### Cor do Texto de Dano

A cor do feedback visual muda conforme a intensidade do dano:

```python
intensidade = min(1.0, tempo_segundos / 10.0)
cor_r = int(40 + (intensidade * 180))   # 40 -> 220 (verde -> vermelho)
cor_g = int(180 - (intensidade * 80))   # 180 -> 100 (brilhante -> escuro)
cor_b = 60                               # Constante
```

**Progressão de Cores**:
- **0s**: RGB(40, 180, 60) - Verde claro (baixo perigo)
- **5s**: RGB(130, 140, 60) - Amarelo esverdeado (perigo médio)
- **10s+**: RGB(220, 100, 60) - Laranja avermelhado (perigo alto)

### Texto de Dano

```python
efeitos_texto.append({
    "texto": f"-{int(dano_bordas)} VENENO!",
    "x": pos_x_personagem + random.randint(-20, 20),
    "y": pos_y_personagem - 30,
    "tempo_inicio": agora,
    "cor": (cor_r, cor_g, cor_b)
})
```

---

## SISTEMA DE APRENDIZADO (IA)

### Recompensa Escalável para Umbra

```python
memoria_umbra.treinar(2.0 + (intensidade * 3.0))
```

**Progressão**:
- **0s**: +2.0 (recompensa base)
- **5s**: +3.5 (recompensa média)
- **10s+**: +5.0 (recompensa máxima)

### Punição Escalável para Apolo

```python
if apolo.estado_anterior in apolo.q_table:
    punicao_apolo = -5.0 - (intensidade * 10.0)
    apolo.q_table[apolo.estado_anterior][apolo.acao_anterior] += punicao_apolo
```

**Progressão**:
- **0s**: -5.0 (punição leve)
- **5s**: -10.0 (punição média)
- **10s+**: -15.0 (punição severa)

---

## COMPARAÇÃO: ANTES vs DEPOIS

### ANTES (Sistema Fixo)

```
Tempo: 0s  -> Dano: 5% (50 HP)
Tempo: 1s  -> Dano: 5% (50 HP)
Tempo: 2s  -> Dano: 5% (50 HP)
Tempo: 3s  -> Dano: 5% (50 HP)
Tempo: 4s  -> Dano: 5% (50 HP)
Total 4s: 250 HP (MORTE RÁPIDA)
```

### DEPOIS (Sistema Escalável)

```
Tempo: 0.8s  -> Dano: 0.5% (5 HP)
Tempo: 1.6s  -> Dano: 0.74% (7.4 HP)
Tempo: 2.4s  -> Dano: 0.98% (9.8 HP)
Tempo: 3.2s  -> Dano: 1.22% (12.2 HP)
Tempo: 4.0s  -> Dano: 1.46% (14.6 HP)
Total 4s: 49 HP (SOBREVIVÍVEL)
```

**Diferença**: 201 HP de diferença nos primeiros 4 segundos!

---

## ESTRATÉGIA DE GAMEPLAY

### Para o Jogador

1. **Primeiros 3 segundos**: Dano baixo, pode arriscar ficar nas bordas
2. **3-8 segundos**: Dano moderado, precisa sair logo
3. **8+ segundos**: Dano alto, morte iminente

### Para o Apolo (IA)

- Aprende a evitar bordas rapidamente
- Punição escalável ensina urgência
- Recompensa por sair das bordas antes do dano alto

---

## TESTES RECOMENDADOS

### Teste 1: Entrada e Saída Rápida
```
1. Entrar nas bordas
2. Sair após 1 segundo
3. Verificar: ~5-7 HP de dano
```

### Teste 2: Permanência Média
```
1. Entrar nas bordas
2. Permanecer por 5 segundos
3. Verificar: ~70-90 HP de dano total
```

### Teste 3: Permanência Longa
```
1. Entrar nas bordas
2. Permanecer por 15 segundos
3. Verificar: ~400-500 HP de dano total
```

### Teste 4: Reset ao Sair
```
1. Entrar nas bordas por 5 segundos
2. Sair completamente
3. Entrar novamente
4. Verificar: Dano volta ao inicial (0.5%)
```

---

## ARQUIVOS MODIFICADOS

**GAME5.py**:
- Linha ~545: Adicionadas variáveis globais de rastreamento
- Linha ~307: Declaração global das novas variáveis
- Linha ~2556: Nova lógica de dano escalável

---

## PARÂMETROS AJUSTÁVEIS

Se precisar ajustar o balanceamento:

```python
# Dano inicial (linha ~2571)
dano_percentual = min(0.05, 0.005 + (tempo_segundos * 0.003))
                              ↑                        ↑
                         Dano inicial            Escala/segundo

# Intervalo de dano (linha ~2568)
if agora - ultimo_tick_dano_bordas >= 800:
                                       ↑
                                  Intervalo (ms)

# Dano máximo (linha ~2571)
dano_percentual = min(0.05, ...)
                       ↑
                  Dano máximo (5%)
```

---

## STATUS

✅ Sistema de dano escalável implementado
✅ Rastreamento de tempo nas bordas
✅ Feedback visual progressivo
✅ Aprendizado de IA escalável
✅ Reset ao sair das bordas

**Resultado**: Bordas tóxicas agora são desafiadoras mas justas, dando ao jogador tempo para reagir.
