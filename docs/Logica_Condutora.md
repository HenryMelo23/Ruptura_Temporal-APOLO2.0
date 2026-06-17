# Manifestação Condutora: Lógica e Mecânicas

A Manifestação "Condutora" é uma das formas de combate mais complexas de *Ruptura Temporal*, atuando como um verdadeiro quebra-cabeça lógico no meio da batalha. Abaixo detalhamos toda a lógica de funcionamento, mecânicas, regras de teleporte e como os códigos governam essa manifestação.

---

## 1. Fios Condutores e Circuitos (Ataques Básicos)
A Condutora não atira projéteis simples. Seus ataques são fluxos que criam uma rede elétrica.

### Como Funciona:
- **Marcação ("Fio"):** Ao atingir um inimigo com o auto-attack, a função `marcar_alvo()` injeta a chave `"fio_condutor"` no dicionário daquele alvo. Se ele já tiver o fio, o ataque aumenta a `"carga"` do fio (até um máximo de 5).
- **Conexão de Malha:** A cada quadro, a função `_conexoes()` avalia todos os inimigos marcados. Se a distância entre dois alvos for menor ou igual ao `FIO_RAIO_CONEXAO` (190 pixels base), um elo invisível liga ambos.
- **Limites de Circuito:** Um alvo não pode estar ligado a todos; o limite é de 3 conexões simultâneas por inimigo (`FIO_MAX_LINKS_POR_ALVO`).

### Fontes de Dano Constante (`atualizar_circuitos`):
1. **Dano por Pulso (Tick):** A cada 720ms (`FIO_TICK_MS`), inimigos conectados sofrem um choque elétrico. O dano escala com a quantidade de conexões que o inimigo tem (+22% de dano por cada link).
2. **Dano de Travessia ("Varal"):** A linha desenhada entre o alvo A e o alvo B é física. Inimigos não marcados que andam através dessa linha levam **Dano de Travessia** (14% do dano base) e sofrem cooldowns individuais para não tomarem dano repetido na mesma linha por 460ms (`FIO_TRAVESSIA_MS`).

---

## 2. Circuitos Lógicos e Portas de Computação
A verdadeira natureza da Condutora é gerenciar "Bits" e resolver "Portas Lógicas" (`OR, AND, XOR, NAND, NOR`).

### Atribuição de Bits Inimigos
A função `garantir_bit_logico()` varre os inimigos vivos. Cada inimigo recebe um `"bit_logico"` (0 ou 1). O código é esperto e conta quantos Zeros e Uns existem no mapa. Para manter o equilíbrio e impedir o *softlock* do jogador, ele sempre força a criação do bit menos abundante.

### O Fluxo da Compilação Lógica:
1. **Portas Aleatórias:** O sistema (`_estado_logico`) sorteia a porta atual e a próxima porta (ex: `OR` e a próxima será `XOR`).
2. **Entrada A:** O jogador atira num inimigo. Esse inimigo se torna a `Entrada A`. (Ex: A=1). Essa entrada dura 3 segundos (`ENTRADA_A_DURACAO_MS = 3000`).
3. **Entrada B:** O jogador rapidamente atira num segundo inimigo. Ele vira a `Entrada B`. (Ex: B=0).
4. **Avaliação da Porta (`_avaliar_porta`):** A porta atual (ex: `AND`) processa os bits de A e B. No nosso exemplo: `1 AND 0 = 0` (Falso).
5. **Resultado Positivo (1):**
   - Cria um elo lógico bem-sucedido.
   - Aplica um multiplicador gigantesco no dano do disparo (`LINK_RESULTADO_1_MULT = 1.78x`).
   - O jogador pode fechar a compilação ativando a tecla correspondente (acionando a função `fechar_circuitos(apenas_corretos=True)`).
6. **Resultado Negativo (0) - Ruído Lógico:**
   - Dano medíocre (`LINK_RESULTADO_0_MULT = 0.58x`).
   - O sistema entra em estado de `RUIDO LOGICO` por 1.8 segundos, onde penalidades podem ser aplicadas e a compilação atual falha, soando um *beep* de erro.

### Os Buffs Lógicos (Pós-Compilação)
Se o jogador fechar circuitos corretos (`fechar_circuitos`), a função confere qual porta foi mais utilizada. Ela recompensa o jogador com um "Buff Lógico" atrelado à porta compilada. Se compilar a mesma porta seguida, ele ganha "Stacks" (níveis):

- **OR:** Amplia a área do Fio Condutor (Raio de conexão) em +35% (+15% por stack).
- **AND:** Adiciona poder bruto: +25% de Multiplicador de Dano (+10% por stack).
- **XOR:** Status ágeis: +20% Velocidade de Movimento e +20% de Cadência de Tiro (+8% por stack).
- **NAND:** Defensivo Perfeito: Gera 1 escudo ("Escudo Hits") que absorve 100% de instâncias de dano inimigo.
- **NOR:** Campo Lento: Cria uma área em volta do jogador de raio 260px; qualquer inimigo lá dentro perde 35% de velocidade de movimento.

---

## 3. O Teleporte ("Curto-Circuito")
O arquivo `teleporte_manifestacao.py` dita o funcionamento do *Dash* (Shift) de Geovana quando ativada com a Condutora.

### As Linhas Condutoras (`_teleporte_condutora`)
Quando a Condutora teleporta (Origem -> Destino), ela **não causa explosões**. Em vez disso, ela deixa um traço físico no chão (`_LINHAS_CONDUTORAS`), uma barreira elétrica persistente (dura 3.6 segundos).

### Efeitos da Linha (Armadilha de Terreno)
- Qualquer inimigo que encoste nessa linha sofre minúsculos tiques de dano.
- Eles são automaticamente "marcados" pelo `marcar_alvo()` da Condutora (adquirindo carga de Fio).

### A Mecânica "Curto-Circuito" (A Jogada de Mestre)
A verdadeira força do teleporte se ativa quando o próprio jogador (**Geovana**) cruza fisicamente a linha do teleporte que ela mesma acabou de deixar.

1. **Ativação:** Após ser solta, a linha demora 220ms para "armar" (`armada_ms`).
2. **Cruzamento (`_jogador_cruzou_linha`):** O código detecta o `rect` do jogador cruzando os pontos `origem` e `destino` da linha do teleporte.
3. **Explosão do Curto (`_aplicar_curto_condutor`):** 
   - A linha entra em estado de `curto_aplicado`.
   - **Todo inimigo** que estiver atrelado/encostado nessa linha no momento do curto toma um dano súbito letal (50% do dano base multiplicado pelo bônus de manifestação).
   - O melhor de tudo: Inimigos são **ATORDOADOS** (Stun) imediatamente por massivos **3000ms** (3 segundos) (`inimigo["stun_fim"] = ... + 3000`).

---

## 4. O Cenário contra Chefes (Resumo Teórico)
Por requerer a Porta Lógica e Ligações Condutoras, ela é ineficiente em 1v1 puro, sendo obrigatória a presença de *adds* (lacaios invocações) ou partes quebráveis na luta de Bosses (mencionado no `Teoria_Manifestacoes_Boss.md`). 

O jogador usa o chefe como "Entrada A" ou "Entrada B", completando a lógica com um monstro fraco, garantindo assim buffs gigantescos como a lentidão do `NOR` ou imunidade a dano do `NAND` que podem trivializar padrões inteiros de chefes se jogados no ritmo certo. A armadilha do Teleporte (Curto-Circuito) é vital para prender o chefe e suas invocações por 3 longos segundos durante um grande ataque em área.
