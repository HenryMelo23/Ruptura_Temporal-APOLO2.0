# Guia Completo: Sistema de Áureas

## O que são Áureas?

Áureas são passivas permanentes que modificam o estilo de jogo do Apolo. Cada áurea oferece um bônus único que pode ser melhorado através de upgrades usando moedas coletadas durante as batalhas.

## Seleção de Áurea

- **Quando**: Antes de iniciar uma partida
- **Como**: Menu de seleção com navegação por setas (← →)
- **Confirmação**: ENTER ou ESPAÇO
- **Áureas Disponíveis**: 4 (+ 1 misteriosa bloqueada)

## Sistema de Upgrades

### Como Funciona:
1. Colete moedas durante as batalhas
2. Acesse o menu de upgrades entre partidas
3. Gaste 1 moeda por nível de upgrade
4. Cada nível aumenta o poder da passiva

### Arquivo de Persistência:
- **Localização**: `aureas_upgrade.json`
- **Estrutura**:
```json
{
    "Racional": 0,
    "Impulsiva": 0,
    "Devota": 0,
    "Vanguarda": 0
}
```

---

## 1. Áurea Racional (Cientista)

### 🎯 Conceito
"A paciência é recompensada. Observe, analise, e seja recompensado pela sua disciplina."

### 📊 Mecânica
Gera pontos passivamente quando o jogador fica parado por 5 segundos ou mais.

### ⚙️ Implementação Técnica

#### Variáveis:
```python
tempo_parado_person = pygame.time.get_ticks()  # Timestamp da última movimentação
ultimo_x = pos_x_personagem  # Posição X anterior
ultimo_y = pos_y_personagem  # Posição Y anterior
nivel_racional = upgrades.get("Racional", 0)  # Nível de upgrade
```

#### Lógica:
```python
if aurea == "Racional":
    if pos_x_personagem == ultimo_x and pos_y_personagem == ultimo_y:
        if tempo_atual - tempo_parado_person >= 5000:  # 5 segundos
            ganho = 3 + nivel_racional  # Base 3 + nível
            pontuacao += ganho
            pontuacao_exib += ganho
            tempo_parado_person = tempo_atual
            
            # Efeito visual
            efeitos_texto.append({
                "texto": f"+{ganho}",
                "x": pos_x_personagem + offset_aleatorio,
                "y": pos_y_personagem - 10,
                "tempo_inicio": tempo_atual,
                "cor": (50, 255, 50)  # Verde
            })
```

### 📈 Progressão por Nível

| Nível | Ganho por Tick | Ganho/Minuto* |
|-------|----------------|---------------|
| 0     | 3 pontos       | 36 pontos     |
| 1     | 4 pontos       | 48 pontos     |
| 2     | 5 pontos       | 60 pontos     |
| 3     | 6 pontos       | 72 pontos     |
| 5     | 8 pontos       | 96 pontos     |
| 10    | 13 pontos      | 156 pontos    |

*Assumindo que o jogador fica parado continuamente

### 🎮 Estilo de Jogo
- **Ideal para**: Jogadores defensivos e pacientes
- **Estratégia**: Encontrar posições seguras e aguardar
- **Sinergia**: Combina bem com builds de tanque/resistência
- **Contra-indicado**: Jogadores agressivos que se movem constantemente

### 🌍 Onde Funciona
- ✅ Todas as dimensões
- ✅ Durante qualquer fase da batalha
- ✅ Não requer inimigos vivos
- ✅ Funciona mesmo com IA controlando

---

## 2. Áurea Impulsiva

### 🎯 Conceito
"A adrenalina da batalha te fortalece. Quanto mais você elimina, mais poderoso você se torna."

### 📊 Mecânica
Após eliminar 5 inimigos consecutivos sem tomar dano, ativa um buff aleatório (Dano ou Velocidade) por tempo limitado.

### ⚙️ Implementação Técnica

#### Variáveis:
```python
eliminacoes_consecutivas_impulsiva = 0  # Contador de kills
impulsiva_ativa = False  # Flag do buff ativo
tipo_buff_impulsiva = None  # "dano" ou "velocidade"
tempo_inicio_buff_impulsiva = 0  # Timestamp de ativação
nivel_impulsiva = upgrades.get("Impulsiva", 0)  # Nível de upgrade
```

#### Lógica de Ativação:
```python
if aurea == "Impulsiva":
    if eliminacoes_consecutivas_impulsiva >= 5 and not impulsiva_ativa:
        impulsiva_ativa = True
        tipo_buff_impulsiva = random.choice(["dano", "velocidade"])
        tempo_inicio_buff_impulsiva = pygame.time.get_ticks()
        eliminacoes_consecutivas_impulsiva = 0  # Reset
```

#### Lógica de Buff:
```python
if impulsiva_ativa:
    duracao_buff = 3000 + nivel_impulsiva * 500  # Base 3s + 0.5s/nível
    
    if pygame.time.get_ticks() - tempo_inicio_buff_impulsiva >= duracao_buff:
        impulsiva_ativa = False
        tipo_buff_impulsiva = None
    else:
        if tipo_buff_impulsiva == "dano":
            multiplicador_dano = 1.3 + (0.05 * nivel_impulsiva)  # +30% base
        elif tipo_buff_impulsiva == "velocidade":
            multiplicador_velocidade = 1.2 + (0.05 * nivel_impulsiva)  # +20% base
```

#### Reset ao Tomar Dano:
```python
if aurea == "Impulsiva" and dano_recebido > 0:
    eliminacoes_consecutivas_impulsiva = 0  # Perde o progresso
```

#### Efeito Visual:
```python
if impulsiva_ativa:
    disparo_paths = ["Sprites/Fogo_impulso1.png", "Sprites/Fogo_impulso2.png"]
    # Projéteis ficam com efeito de fogo
```

### 📈 Progressão por Nível

#### Buff de Dano:
| Nível | Multiplicador | Dano Extra | Duração |
|-------|---------------|------------|---------|
| 0     | 1.30x         | +30%       | 3.0s    |
| 1     | 1.35x         | +35%       | 3.5s    |
| 2     | 1.40x         | +40%       | 4.0s    |
| 3     | 1.45x         | +45%       | 4.5s    |
| 5     | 1.55x         | +55%       | 5.5s    |
| 10    | 1.80x         | +80%       | 8.0s    |

#### Buff de Velocidade:
| Nível | Multiplicador | Velocidade Extra | Duração |
|-------|---------------|------------------|---------|
| 0     | 1.20x         | +20%             | 3.0s    |
| 1     | 1.25x         | +25%             | 3.5s    |
| 2     | 1.30x         | +30%             | 4.0s    |
| 3     | 1.35x         | +35%             | 4.5s    |
| 5     | 1.45x         | +45%             | 5.5s    |
| 10    | 1.70x         | +70%             | 8.0s    |

### 🎮 Estilo de Jogo
- **Ideal para**: Jogadores agressivos e habilidosos
- **Estratégia**: Eliminar inimigos rapidamente sem tomar dano
- **Sinergia**: Combina bem com builds de dano/velocidade
- **Desafio**: Requer habilidade para manter streak
- **Risco**: Perder progresso ao tomar dano

### 🌍 Onde Funciona
- ✅ Todas as dimensões
- ✅ Requer inimigos para eliminar
- ⚠️ Não funciona com IA (requer kills manuais)
- ✅ Buff aleatório adiciona variabilidade

### 💡 Dicas
- Foque em eliminar inimigos fracos primeiro
- Evite dano a todo custo durante o streak
- Use dash para evasão sem perder DPS
- Buff de velocidade ajuda na evasão
- Buff de dano acelera próximo streak

---

## 3. Áurea Devota

### 🎯 Conceito
"A fé te protege. Um escudo divino absorve o primeiro golpe a cada intervalo."

### 📊 Mecânica
Gera um escudo que absorve completamente o próximo dano recebido. O escudo se regenera automaticamente após 30 segundos.

### ⚙️ Implementação Técnica

#### Variáveis:
```python
escudo_devota_ativo = True  # Inicia com escudo ativo
tempo_ultimo_escudo = pygame.time.get_ticks()  # Timestamp do último escudo
intervalo_escudo = 30000  # 30 segundos em milissegundos
nivel_devota = upgrades.get("Devota", 0)  # Nível de upgrade
```

#### Lógica de Regeneração:
```python
if not escudo_devota_ativo and tempo_atual - tempo_ultimo_escudo >= intervalo_escudo:
    escudo_devota_ativo = True
    tempo_ultimo_escudo = tempo_atual
    # Efeito visual de "escudo ativado"
```

#### Lógica de Absorção:
```python
if dano_recebido > 0:
    if escudo_devota_ativo:
        escudo_devota_ativo = False  # Consome o escudo
        # Dano é completamente negado
    else:
        vida -= dano_recebido  # Dano normal
```

#### Indicador Visual:
```python
if aurea == "Devota" and escudo_devota_ativo:
    cor_barra = (0, 150, 255)  # Barra de vida azul quando escudo ativo
else:
    cor_barra = cor_normal  # Cor normal
```

### 📈 Progressão por Nível

| Nível | Intervalo | Escudos/Minuto | Dano Negado* |
|-------|-----------|----------------|--------------|
| 0     | 30s       | 2.0            | Ilimitado    |
| 1     | 28s       | 2.14           | Ilimitado    |
| 2     | 26s       | 2.31           | Ilimitado    |
| 3     | 24s       | 2.50           | Ilimitado    |
| 5     | 20s       | 3.00           | Ilimitado    |
| 10    | 15s       | 4.00           | Ilimitado    |

*O escudo absorve qualquer quantidade de dano, incluindo hits letais

**Nota**: A progressão exata do intervalo precisa ser implementada. Atualmente o intervalo é fixo em 30s.

### 🎮 Estilo de Jogo
- **Ideal para**: Jogadores que preferem segurança
- **Estratégia**: Gerenciar cooldown do escudo
- **Sinergia**: Combina bem com builds de sobrevivência
- **Vantagem**: Perdoa erros ocasionais
- **Timing**: Saber quando o escudo está disponível

### 🌍 Onde Funciona
- ✅ Todas as dimensões
- ✅ Contra qualquer fonte de dano
- ✅ Funciona com IA controlando
- ✅ Absorve até dano letal (1-hit protection)
- ✅ Indicador visual claro (barra azul)

### 💡 Dicas
- Monitore a cor da barra de vida (azul = protegido)
- Não desperdice o escudo em dano pequeno
- Use para tankar hits poderosos (laser, ratos)
- Jogue mais agressivo quando escudo ativo
- Jogue defensivo quando escudo em cooldown

### ⚠️ Limitações
- Absorve apenas 1 hit por ciclo
- Não acumula múltiplos escudos
- Cooldown fixo (não reduz com habilidades)

---

## 4. Áurea Vanguarda

### 🎯 Conceito
"Ainda não implementada. Uma áurea misteriosa aguarda para ser descoberta."

### 📊 Status
- ❌ Não implementada no código atual
- ✅ Aparece no menu de seleção
- ✅ Sistema de upgrade preparado
- ⚠️ Sem mecânica definida

### 💭 Possíveis Implementações Futuras
- Buff de movimento ao iniciar combate
- Dano extra no primeiro hit
- Redução de cooldowns ao entrar em nova dimensão
- Bônus por ser o primeiro a atacar

### 🌍 Onde Funciona
- ❌ Não funciona (não implementada)

---

## 5. Áurea Misteriosa (?)

### 🎯 Conceito
"Uma áurea secreta que aguarda para ser desbloqueada."

### 📊 Status
- 🔒 Bloqueada
- ❌ Não selecionável
- ❓ Condições de desbloqueio desconhecidas
- 💎 Possivelmente relacionada a conquistas

### 🔓 Possíveis Formas de Desbloquear
- Completar todas as dimensões
- Atingir certo nível em todas as outras áureas
- Derrotar a Umbra X vezes
- Coletar X moedas totais
- Easter egg ou código secreto

---

## Comparação de Áureas

| Áurea | Tipo | Dificuldade | Requer Skill | Funciona com IA | Melhor Para |
|-------|------|-------------|--------------|-----------------|-------------|
| **Racional** | Passiva | Fácil | Baixa | ✅ Sim | Iniciantes, Defensivo |
| **Impulsiva** | Ativa | Difícil | Alta | ❌ Não | Veteranos, Agressivo |
| **Devota** | Defensiva | Média | Média | ✅ Sim | Todos, Sobrevivência |
| **Vanguarda** | ? | ? | ? | ? | Não implementada |
| **Misteriosa** | ? | ? | ? | ? | Bloqueada |

---

## Sistema de Arquivos

### aurea_selecionada.json
Armazena a áurea atualmente selecionada:
```json
{
    "aurea": "Racional"
}
```

### aureas_upgrade.json
Armazena os níveis de upgrade de cada áurea:
```json
{
    "Racional": 0,
    "Impulsiva": 0,
    "Devota": 0,
    "Vanguarda": 0
}
```

### Sprites
- `Sprites/aurea_cientista.png` - Racional
- `Sprites/aurea_impulsiva.png` - Impulsiva
- `Sprites/aurea_devota.png` - Devota
- `Sprites/aurea_vanguarda.png` - Vanguarda
- `Sprites/aurea_misteriosa.png` - Misteriosa (?)

---

## Economia de Moedas

### Ganho de Moedas
- Eliminar inimigos
- Completar dimensões
- Bônus de performance
- Áurea Racional (indiretamente via pontos)

### Gasto de Moedas
- 1 moeda = 1 nível de upgrade
- Sem limite de nível (teoricamente)
- Upgrades são permanentes
- Não há reset de upgrades

### Estratégia de Investimento

#### Early Game (0-10 moedas):
- **Devota Nv.3**: Segurança básica
- **Racional Nv.2**: Renda passiva
- **Impulsiva Nv.1**: Se for habilidoso

#### Mid Game (10-30 moedas):
- Focar na áurea principal
- Levar até nível 5-7
- Diversificar secundárias

#### Late Game (30+ moedas):
- Maximizar áurea favorita (Nv.10+)
- Balancear outras áureas
- Experimentar builds diferentes

---

## Builds Recomendadas

### Build Tanque (Sobrevivência)
- **Áurea Principal**: Devota (Nv.10)
- **Secundária**: Racional (Nv.5)
- **Estilo**: Defensivo, paciente
- **Vantagem**: Alta sobrevivência
- **Desvantagem**: Dano baixo

### Build Speedrun (Agressivo)
- **Áurea Principal**: Impulsiva (Nv.10)
- **Secundária**: Nenhuma
- **Estilo**: Agressivo, arriscado
- **Vantagem**: Clears rápidos
- **Desvantagem**: Requer skill

### Build Híbrida (Balanceada)
- **Áurea Principal**: Devota (Nv.5)
- **Secundária**: Racional (Nv.5)
- **Estilo**: Adaptável
- **Vantagem**: Versátil
- **Desvantagem**: Não excel em nada

### Build Farming (Moedas)
- **Áurea Principal**: Racional (Nv.10)
- **Secundária**: Devota (Nv.3)
- **Estilo**: Passivo, seguro
- **Vantagem**: Máximo de pontos
- **Desvantagem**: Lento

---

## Interação com IA (Apolo)

### Áureas que Funcionam com IA:
- ✅ **Racional**: IA pode ficar parada estrategicamente
- ❌ **Impulsiva**: IA não rastreia kills manuais
- ✅ **Devota**: Escudo funciona automaticamente
- ❓ **Vanguarda**: Não implementada

### Considerações para Treino:
- Racional pode incentivar comportamento passivo
- Devota permite IA aprender com mais erros
- Impulsiva não afeta treino da IA

---

## Troubleshooting

### Áurea não está funcionando
1. Verifique `aurea_selecionada.json`
2. Confirme que a áurea está implementada
3. Verifique condições de ativação

### Upgrades não salvam
1. Verifique permissões de escrita
2. Confirme formato do JSON
3. Verifique `aureas_upgrade.json`

### Escudo Devota não regenera
1. Aguarde 30 segundos completos
2. Verifique se não está em cooldown
3. Monitore `tempo_ultimo_escudo`

### Impulsiva não ativa
1. Confirme 5 kills consecutivos
2. Verifique se não tomou dano
3. Confirme que buff não está ativo

---

## Futuras Implementações

### Sugestões:
1. **Implementar Vanguarda**
2. **Desbloquear Misteriosa**
3. **Adicionar mais áureas**
4. **Sistema de combo entre áureas**
5. **Áureas lendárias (raras)**
6. **Progressão de intervalo para Devota**
7. **Indicadores visuais melhorados**
8. **Sons específicos por áurea**
9. **Conquistas por áurea**
10. **Estatísticas de uso**

---

## Conclusão

O sistema de áureas adiciona profundidade estratégica ao jogo, permitindo que jogadores personalizem seu estilo de jogo. Cada áurea oferece uma experiência única, e o sistema de upgrades garante progressão a longo prazo.

**Escolha sabiamente, e que sua áurea te guie à vitória!**
