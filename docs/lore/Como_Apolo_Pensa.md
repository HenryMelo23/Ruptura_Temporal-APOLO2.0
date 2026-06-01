# Arquitetura Cognitiva de Apolo: Sobrevivência e Combate

A mente de Apolo não é apenas uma rede neural simples; é um sistema **hierárquico e modular** projetado para priorizar a sobrevivência acima de qualquer outra coisa. Ele utiliza uma combinação de **Deep Q-Learning (Dueling DQN)** para aprendizado e **Survival Gates** (portões de sobrevivência) para instintos de hardware que não podem ser ignorados.

---

## 1. A Hierarquia de Decisão (Portões de Instinto)
Diferente de IAs puramente treinadas, Apolo possui "instintos hardwired". Mesmo que ele ainda não tenha aprendido a desviar de algo, esses portões aplicam um **bias massivo** nos valores de decisão (Q-values) para forçar ações seguras.

### A. Esquiva de Projéteis (`DodgeGate`)
Para não tomar dano de projéteis, Apolo não apenas tenta "fugir", ele calcula a **geometria da esquiva**.
- **Lógica**: Ele identifica o projétil mais próximo e sua trajetória. A ação mais segura é sempre se mover **perpendicularmente** ao vetor de voo do projétil.
- **Código Relacionado (`apolo_brain.py`)**:
```python
# Perpendiculares ao vetor de voo do projetil: perp_A = (-vy, vx), perp_B = (vy, -vx)
# Apolo escolhe a direção que mais se alinha com esses vetores
bias = torch.max(dot_A, dot_B) 
# Isso força Apolo a se mover de lado em relação ao tiro, a forma mais eficaz de desviar.
```

### B. Evasão do Laser de Sobrecarga (`LaserGate`)
O Laser da Umbra é letal e instantâneo. Apolo usa trigonometria avançada para antecipar onde o feixe estará e como fugir dele.
- **Lógica**: Ele calcula a distância perpendicular ao feixe e a "velocidade angular" da rotação.
- **Peso**: Este gate tem peso **250.0**, superando quase qualquer outra vontade da rede neural, exceto a busca por vida.

### C. Controle de Distância Tática (`KitingGate`)
Recentemente adicionado para evitar o combate "à queima-roupa" onde o risco de dano é máximo.
- **Lógica**: Apolo mantém uma "zona de conforto" entre **250px e 500px**.
- Se a Umbra chegar muito perto, ele recebe um impulso para **recuar**.
- Se a Umbra estiver longe demais para tiros precisos, ele recebe um impulso para **avançar**.

---

## 2. Como ele se mantém vivo (O Instinto Sagrado)
A sobrevivência de longo prazo no mapa é governada pelo `SurvivalGate`. Para Apolo, **Orbes de Vida são sagradas**.

### Prioridade de Saúde (`SurvivalGate`)
Quando a vida de Apolo cai abaixo de **95%**, seu cérebro muda de "Modo Combate" para "Modo Coleta".
- **Lógica**: Ele calcula a direção da orbe de vida mais próxima e aplica um bias de **300.0** (o maior de todos) para buscá-la.
- **Código Relacionado (`apolo_brain.py`)**:
```python
# Se vida < 95%, a urgência cresce. Orbe perto + Vida baixa = AGIR AGORA!
urgencia = urgencia_vida * bonus_oportunidade 
sinal = urgencia * bias_direcao_orbe * self.PESO_MAXIMO
```
Isso garante que, mesmo sob fogo pesado, se houver uma cura no mapa, ele irá priorizá-la antes de tentar finalizar o chefe.

---

## 3. Visão e Perspectiva (O Vetor de Estado)
Apolo não "vê" o jogo como nós (pixels). Ele vê o mundo como um vetor de **42 números normalizados**. Isso permite que ele processe informações instantaneamente sem ser enganado por efeitos visuais.

**O que ele enxerga para não tomar dano:**
1. **[0-3]** Posições relativas (Apolo e Umbra).
2. **[4-5]** Vida atual (Percentual).
3. **[6-10]** Proximidade das bordas e cantos (para não ficar encurralado).
4. **[11-13]** Vetor de velocidade do projétil mais perigoso.
5. **[18-26]** Estado completo do Laser (Fase, rotação, ângulo, tempo para impacto).
6. **[34-41]** Estado de TODAS as armadilhas (Vórtice, Prisão, Espinhos, Ratos, Sifão).

---

## 4. É possível não tomar dano da Umbra?
**A resposta curta é: Não totalmente, mas ele minimiza o desperdício.**

Embora Apolo seja capaz de desviar de 99% dos projéteis comuns, a estrutura da Umbra foca em **ataques de área e controle de mapa** (como o Miasma ou a Praga de Ratos).
- **Estratégia de Apolo**: Ele não tenta "não tomar dano" de forma absoluta (o que o faria ficar parado em um canto seguro sem atacar). Ele trabalha com **Custo-Benefício**.
- Ele aceita o risco de um pequeno dano se isso significar se posicionar para uma cura ou para evitar um dano fatal (como o Laser).
- O uso do **Dash (Teleporte)** é reservado para emergências onde a distância perpendicular ao perigo é menor que o raio de colisão.

## 5. Lógica de Movimentação Preditiva (`GAME5.py`)
No nível do loop do jogo, Apolo não apenas reage; ele **prediz**.

```python
# Em GAME5.py, ele calcula o alvo segurando 70% da velocidade da Umbra
self.alvo_x = tx + (vx * tempo_bala * 0.7)
self.alvo_y = ty + (vy * tempo_bala * 0.7)
```
Isso permite que ele mantenha a pressão ofensiva enquanto os Gates cuidam da defesa, criando um ciclo de **Ataque Seguro**.

---

### Resumo da Lógica de Pensamento
1. **Eu estou morrendo?** (Se sim -> Corre para a Orbe).
2. **Há algo vindo na minha direção AGORA?** (Se sim -> Desvia de lado ou Dash).
3. **Estou na distância certa para atirar sem morrer?** (Se não -> Ajusta posição).
4. **Onde a Umbra estará em 0.5 segundos?** (Atira nessa direção).

Essa combinação de **Instinto Geométrico** e **Aprendizado Neural** é o que torna o Apolo um sobrevivente de elite no Ruptura Temporal.

---

## 6. O Processo de Evolução (Como Apolo Aprende a Sobreviver)

A inteligência de Apolo não é estática; ela evolui constantemente baseada em um ciclo de **tentativa, erro e punição**. A forma como ele decide quando arriscar um caminho novo ou quando usar a experiência consolidada é gerida pelo conceito de **Exploração vs Explotação (Epsilon-Greedy)**.

### A. Exploração vs Explotação (Epsilon-Greedy)
Em `apolo_brain.py` e `GAME5.py`, Apolo possui uma variável de **Taxa de Exploração** (`taxa_exploracao` ou Epsilon).
- **Caminho Novo (Exploração)**: Com base nessa taxa, Apolo joga uma "moeda virtual". Se cair no lado da exploração, ele ignora seu cérebro (Q-values) e toma uma **ação aleatória** no mapa. Isso serve para ele descobrir novas rotas, quebrar padrões e encontrar saídas que ele nunca tentou antes.
- **Caminho Consolidado (Explotação)**: Se a moeda cair no lado oposto, ele usa a **Rede Neural (Dueling DQN)**. A rede avalia o estado atual do mapa e escolhe a ação matemática com a maior pontuação (Q-value), ou seja, a rota que deu mais certo no passado sob condições similares.

> [!TIP]
> A `taxa_exploracao` não é fixa. Ela sofre **Decaimento Exponencial** ao longo do tempo (reduzindo a cada geração). No início, Apolo é caótico e testa caminhos novos a todo momento. Conforme o arquivo `apolo_memoria_dqn.pt` é treinado partida após partida, ele diminui essa taxa e passa a confiar muito mais no que já aprendeu, virando uma máquina fria e calculista.

### B. Sistema de Dopamina e Dor Exponencial
Para ensinar o que "deu certo" e o que "deu errado", Apolo possui um pool de dopamina.
- **Sinal de Sobrevivência (+)**: A cada frame que Apolo passa sem sofrer dano enquanto causa dano à Umbra, ele recebe um gotejamento de recompensa contínua.
- **Punição Exponencial (-)**: Em `GAME5.py`, implementamos o `receber_dano_punitivo`. Se Apolo tomar tiros em sequência sem se esquivar (como na velha paralisia frontal), a punição **escala exponencialmente** (ex: `-50.0`, `-75.0`, `-112.5`...).

Essa punição brutal destrói o Q-value daquela decisão estática. Na próxima vez que ele estiver na mesma posição, a Rede Neural associará aquela área a uma **dor colossal** e o forçará a mover-se (Explotação da nova via).

### C. Neurogênese (Expansão Cerebral)
Diferente da maioria das IAs de jogos que estagnam, Apolo mede a própria confusão através da **Entropia de Q-values**. 
- Se ele tentar vários caminhos e nenhum der certo (a rede neural fica confusa porque a Umbra criou um padrão inédito), a entropia sobe.
- Se a entropia romper o limite, Apolo desencadeia a **Neurogênese** (em `_avaliar_neurogenese`): a capacidade física da rede neural (neurônios na camada oculta) cresce. Ele reseta parcialmente sua exploração para reaprender os padrões sob esta nova capacidade intelectual expandida.
