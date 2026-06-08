# Guia de Inimigos e Mecânicas — Fase 1 (GAME.py)

Este documento descreve detalhadamente todos os tipos de inimigos encontrados na primeira fase de **Ruptura Temporal**, implementada no arquivo `GAME.py`. O documento abrange seus nomes, comportamentos, atributos matemáticos de progressão e interações estratégicas.

---

## 📊 Tabela Comparativa de Inimigos

A tabela abaixo apresenta uma visão geral comparativa dos atributos base e multiplicadores de cada inimigo em relação aos atributos globais da fase:

| Inimigo | Tipo Interno | Vida (HP) Base / Multiplicador | Velocidade Relativa | Função Principal | Mecânica Especial |
| :--- | :---: | :---: | :---: | :--- | :--- |
| **Errante Temporal** | `1` | `Vida Comum Inicial (1.0x)` | `Velocidade Comum (1.0x)` | Pressão Básica | Perseguição linear direta. |
| **Aglomerador** | `2` | `3.2x Vida Comum` | `1.35x Velocidade Comum` | Tanque / Controle de Área | Divisão ao morrer; fusão em grupo. |
| **Espreitador** | `3` | `0.9x Vida Comum` | `Variável (Base: 1.05x)` | Assassino / Furtivo | Invisibilidade > 300px; arrancada/sprint. |
| **Cristalizador** | `4` | `2.0x Vida Comum` | `0.50x Velocidade Comum` | Suporte Defensivo | Aura protetora (50% mitigação a aliados). |
| **Projetador** | `5` | `1.2x Vida Comum` | `0.80x Velocidade Comum` | Atirador de Elite | Ataques de longo alcance (projéteis). |
| **Curater** | `"curater"` | `2.4x Vida Comum` | `0.45x Velocidade Comum` | Healer Global | Cura aliados feridos; cura jogador ao morrer. |
| **Larápio** | `"larapio"` | `1.2x Vida Comum` | `1.25x Velocidade Comum` | Ladrão / Punição de Cúmulo | Rouba pontos do jogador e foge. |
| **Caranguejo Cósmico** | `Boss` | `5000 (Inicial)` | `Variável (Aumenta sob dano)` | Chefe de Fase | Ataques de área (bolhas, ondas de choque). |

---

## 👾 Detalhamento dos Inimigos

### 1. Errante Temporal (Tipo 1)
* **Descrição da Lore:** Fragmentos de pessoas e criaturas presos no primeiro pulso da ruptura. Eles não pensam em vencer, apenas em voltar para uma linha do tempo que já não existe.
* **Mecânicas e Comportamento:**
  * Movimenta-se em linha reta em direção ao jogador de maneira contínua.
  * Serve como o inimigo base para a escala de dificuldade e spawn da fase.

### 2. Aglomerador (Tipo 2)
* **Descrição da Lore:** Várias linhas temporais falharam no mesmo ponto e se colaram em um único corpo. Quando ele cai, as partes ainda tentam continuar.
* **Mecânicas e Comportamento:**
  * **Tamanho Visual:** Ampliado em **1.6x**.
  * **Divisão ao Morrer:** Ao ser derrotado, divide-se em **2 mini Errantes Temporais** (cada um com 30% da vida máxima base e 90% da velocidade base).
  * **Fusão Forçada (Anomalia de Fusão):** A cada 1 segundo, o jogo verifica se há 3 ou mais Errantes Temporais normais em um raio de 90px (`FUSAO_AGLOMERACAO_RAIO`). Se permanecerem próximos por 1 segundo, eles se fundem em um Aglomerador. A vida do Aglomerador fundido é equivalente a **90% da soma das vidas máximas do grupo**, e sua velocidade aumenta de acordo com a quantidade de inimigos fundidos.

### 3. Espreitador (Tipo 3)
* **Descrição da Lore:** O próprio errante aprendendo a falhar entre os frames da realidade. A ameaça vem do desaparecimento, não de uma silhueta nova.
* **Mecânicas e Comportamento:**
  * **Invisibilidade Dinâmica:** Fica completamente invisível (`invisivel = True`) se a distância até o jogador for superior a 300px.
  * **Oscilação de Opacidade:** Quando visível, sua opacidade (Alpha) oscila dinamicamente entre 40 (quase invisível) e 180 (semi-transparente) em ciclos contínuos.
  * **Arrancada (Sprint):** Quando está em perseguição ativa e o cooldown de sprint expira, ele ganha um aumento temporário de velocidade de corrida (multiplicador de sprint de **1.45x** da velocidade base por 1,5 segundos).

### 4. Cristalizador (Tipo 4)
* **Descrição da Lore:** A ruptura endurece o errante por dentro, cobrindo sua forma comum com uma lógica de cristal. Persegue para fixar a batalha em favor da horda.
* **Mecânicas e Comportamento:**
  * **Aura de Proteção:** Inimigos aliados que estiverem em um raio de até 120px do Cristalizador recebem **50% de redução de dano** (`0.5` de mitigação).
  * **Limitação de Presença:** O jogo impõe um limite estrito de no máximo **1 Cristalizador ativo simultaneamente** na tela.
  * **Vulnerabilidade:** A aura defensiva do Cristalizador **não se aplica a si mesmo**, tornando-o o alvo prioritário natural do jogador.

### 5. Projetador (Tipo 5)
* **Descrição da Lore:** Um errante que aprendeu a estender o próprio colapso pelo espaço, transformando distância em pressão.
* **Mecânicas e Comportamento:**
  * **Ataque à Distância:** Quando a distância até o jogador é inferior ou igual a 280px, o Projetador para de andar e dispara um projétil circular com velocidade constante em direção ao jogador.
  * **Cadência de Tiro:** Dispara a cada 2.5 segundos (`2500 ms`).

### 6. Curater (Tipo `"curater"`)
* **Descrição da Lore:** Nasceu quando a areia cósmica aprendeu a preservar seus próprios erros. Tem cogumelos e brotos verdes que denunciam a mutação de suporte.
* **Mecânicas e Comportamento:**
  * **Cura Aliada Global:** A cada 1 segundo (`1000 ms`), o Curater executa um pulso que cura todos os outros inimigos aliados feridos no mapa em **20% de sua vida perdida**. O Curater não cura a si mesmo nem outros Curaters.
  * **Resistência Passiva:** Possui uma alta mitigação de dano própria (`0.42`), o que significa que ele sofre apenas **42% do dano recebido** (redução de 58%).
  * **Cura de Abate (Bônus para o Jogador):** Ao ser derrotado pelo jogador, o Curater libera um pulso de energia benevolente que **cura o jogador em 50% de sua vida perdida** (`CURATER_CURA_ABATE_VIDA_PERDIDA = 0.50`), tornando seu abate altamente estratégico.

### 7. Larápio (Tipo `"larapio"`)
* **Descrição da Lore:** Entidade nascida da cobiça e da retenção de energia temporal (pontos). Move-se com agilidade felina.
* **Mecânicas e Comportamento:**
  * **Gatilho de Spawn (Cobiça):** Spawna de bordas aleatórias do mapa se o jogador acumular muitos pontos sem gastá-los na loja, baseado em uma probabilidade calculada dinamicamente.
  * **Estado de Caça:** Segue o jogador e tenta se aproximar. Ao entrar em alcance de ataque, inicia um período de preparação (estático por 350ms).
  * **O Roubo:** Se acertar o jogador com sucesso no final da preparação, ele **rouba 25% dos pontos atuais** do jogador e entra instantaneamente no estado **"fugindo"**.
  * **Fuga Inteligente:** Ao fugir, ele corre na direção oposta ao jogador com velocidade ampliada (**1.55x**), priorizando áreas livres e evitando cantos ou bordas do mapa através de um algoritmo de pontuação vetorial. Ele tenta fugir por 5 segundos antes de reavaliar o estado.
  * **Escalonamento de Saque:** A cada roubo realizado com sucesso, as estatísticas do Larápio aumentam permanentemente: sua velocidade aumenta em até **+65%**, seu dano em até **+40%** e sua resistência a danos em até **+25%**.
  * **Agressividade Permanente:** Se o jogador tiver 0 pontos, se o Larápio for atacado repetidamente, ou se ele atingir o limite de **3 roubos bem-sucedidos**, ele abandona a fuga e torna-se permanentemente agressivo, atacando o jogador com velocidade ampliada de perseguição (+8%).
  * **Recuperação de Pontos:** Ao ser derrotado, o Larápio dropa todos os pontos roubados de volta no chão para que o jogador possa recuperá-los.

---

## 👑 Boss 1: Caranguejo Cósmico Gigante (Caranguejo do Nulo)

O primeiro grande desafio do jogo é um crustáceo biomecânico gigante corrompido pela energia do nulo.

### Mecânicas e Comportamento:
1. **Movimentação Errática:** Modifica sua direção de movimento a cada 1 a 3 segundos de forma imprevisível.
2. **Escalonamento por Dano:** À medida que sua vida diminui, sua carapaça se rompe, tornando-o mais leve e mais rápido. Sua velocidade é multiplicada por até **2.5x** da base conforme ele se aproxima da derrota.
3. **Estágios de Transição de Vida (Pulos Dimensionais):**
   * **Gatilhos:** Ao atingir menos de **60%** e menos de **40%** de vida, o Boss entra em estado de transição estática de 6 segundos onde ele pula no ar repetidamente (ciclos de pulo de 1.2 segundos).
   * **Ondas de Choque:** A cada impacto no solo durante a transição, ele gera ondas de choque cósmicas expansivas que causam dano pesado e empurram o jogador.
4. **Combate a Curto Alcance:** Causa dano físico direto massivo ao tocar o jogador, com um cooldown interno de ataque de 2.5 segundos.
5. **Drop do Fragmento Temporal:** Ao morrer, o Boss é removido do mapa de jogo e gera o **Fragmento Temporal** físico. Ao coletá-lo, o jogador inicia a transição dimensional para a Fase 2.

---

## 📈 Sistema de Progressão e Escalonamento da Fase

A cada inimigo comum derrotado pelo jogador, a dificuldade geral da fase sofre um acréscimo harmônico e incremental:

* **Vida Máxima dos Inimigos:** Aumenta proporcionalmente a cada abate (ganho acumulativo de +1.2 a +2.0 de HP por morte, dependendo do nível de evolução).
* **Dano dos Inimigos:** Aumenta gradativamente em todas as fontes físicas (curto alcance, longo alcance e projéteis).
* **Velocidade dos Inimigos:** Aumenta de forma sutil a cada abate para manter a tensão constante no mapa.
* **Escala do Boss (Se ainda não invocado):** A vida máxima base com a qual o Boss irá spawnar quando o jogador invocar (ou pressionar `R`) cresce acumulativamente com cada eliminação realizada durante a fase.
