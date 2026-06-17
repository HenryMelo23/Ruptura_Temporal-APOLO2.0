# Teoria de Interação: Manifestações vs Bosses em Ruptura Temporal

## Filosofia de Design Geral
A estrutura de combate contra chefes (Bosses) exige adaptação. Como os Bosses possuem um grande HP, padrões complexos (fases) e movimentação específica, cada Manifestação deve proporcionar uma abordagem distinta. O design das lutas não pode invalidar nenhuma manifestação, mas deve recompensar o jogador que souber utilizar as forças de cada uma contra o padrão específico do Boss atual.

Abaixo, detalhamos a teoria de interação de cada manifestação existente no jogo frente a um cenário de *Boss Fight*.

---

### 1. Manifestação Elétrica (O Padrão Equilibrado)
- **Mecânica Central:** Disparo contínuo e equilibrado. Onda Cinética (empurrão/dano em área).
- **Interação com Boss:** A opção "porto seguro". Mantém um DPS constante independente do que o boss está fazendo. Não brilha em nenhuma fase específica, mas nunca se torna obsoleta. A "Onda Cinética" pode ser utilizada defensivamente para destruir rapidamente projéteis frágeis do boss ou afastar lacaios (*adds*).
- **Risco:** Baixo.
- **Recompensa:** Média (exige resistência prolongada ao invés de dano massivo pontual).

### 2. Manifestação Lacerante (O Risco Agressivo)
- **Mecânica Central:** Curto alcance, cortes sucessivos que acumulam "Laceração" (inimigo sofre dano ao se mover ou atacar).
- **Interação com Boss:** Bosses atacam e se movem constantemente, o que transforma o debuff "Aberto" da Lacerante em uma máquina de dano passivo. Porém, obriga o jogador a lutar de perto (*melee range*). O Teleporte Lacerante (Shift) é a ferramenta ideal para atravessar fisicamente o boss durante seus ataques e rasgá-lo no processo.
- **Risco:** Muito Alto (exposição aos ataques mais fortes do boss).
- **Recompensa:** Muito Alta (maior DPS direto).

### 3. Manifestação Prismática (Geometria e Posicionamento)
- **Mecânica Central:** Feixes de luz precisos que ricocheteiam. Prisma multiplicador.
- **Interação com Boss:** O jogador transforma a arena do boss a seu favor. Ideal contra bosses mais lentos ou estacionários, onde o jogador pode armar "Prismas de Refração" para fragmentar o dano perfeitamente. O dano máximo vem de calcular o ricochete entre as paredes (ou limite da tela) e as costas do Boss.
- **Risco:** Médio (exige foco extremo no mapa e nos ângulos, tirando os olhos do boss).
- **Recompensa:** Alta (Dano crítico em cadeia).

### 4. Manifestação Retornante (O "Kiting" Perfeito)
- **Mecânica Central:** O projétil causa mais dano na *volta* para a mão de Geovana.
- **Interação com Boss:** A melhor forma para lutas de perseguição (*Kiting*). Bosses agressivos que caminham na direção do jogador sofrem o dano da ida e engolem automaticamente o dano massivo da volta. O jogador não precisa mirar de volta; basta alinhar o próprio corpo atrás do chefe e usar o "Chamado Reverso" no momento em que o boss parar a perseguição.
- **Risco:** Médio (se o jogador parar, o pulso é desperdiçado).
- **Recompensa:** Alta (Sinergia absoluta com evasão contínua).

### 5. Manifestação Parasítica (Maturação e *Burst*)
- **Mecânica Central:** Implanta sementes temporais que crescem com repetições e explodem no comando "Eclosão".
- **Interação com Boss:** Especialista em janelas de vulnerabilidade. O jogador passa as fases perigosas do boss apenas desviando e plantando algumas sementes. Como a semente matura mais rápido quando o alvo ataca, a agressividade do chefe trabalha contra si mesmo. Quando o boss for invocar uma fase ou pausar, a Eclosão detona todas as sementes maduras para um *Burst* gigantesco de dano.
- **Risco:** Baixo a Médio.
- **Recompensa:** Altíssima (consegue pular fases se bem acumulado).

### 6. Manifestação Condutora (O Quebra-Cabeça Lógico)
- **Mecânica Central:** Marcação de dois alvos (Entrada A e B) para resolver uma porta lógica (OR, AND, XOR) e fechar o circuito.
- **Interação com Boss:** Sofre muito em lutas puras de 1v1, pois precisa de múltiplos alvos para a porta lógica. A presença da Condutora **exige** que as *Boss Fights* possuam lacaios invocados (*adds*), orbes de energia quebráveis ou pilares mapeados como inimigos. O jogador amarra o Boss a um lacaio para fechar o circuito com o valor `1` e aplicar dano massivo em ambos simultaneamente.
- **Risco:** Alto (depende da leitura da horda e do cenário).
- **Recompensa:** Alta (Limpa a tela e massacra o Boss ao mesmo tempo).

### 7. Manifestação Gravitante (O Sobrevivencialista)
- **Mecânica Central:** Disparo não-direto; prende órbitas causadoras de dano retardado ao redor do alvo.
- **Interação com Boss:** É a contra-medida perfeita para fases de *Bullet Hell* do Boss. Quando a tela está coberta de ameaças e mirar é impossível, o jogador usa o "Colapso Orbital" e solta órbitas que perseguem o boss e grudam nele. O jogador foca 100% da sua cognição mental em sobreviver e esquivar, enquanto os orbes realizam o trabalho do DPS.
- **Risco:** Muito Baixo.
- **Recompensa:** Média a Constante.

### 8. Manifestação Ancorada (Domínio de Território)
- **Mecânica Central:** Planta âncoras no chão. Fortalece defesas e ataques enquanto Geovana se mantém no "Domínio Fixo".
- **Interação com Boss:** Totalmente dependente do design da luta. Se o chefe utiliza grandes ataques em Área (AoE) que forçam o movimento, a Ancorada é punida severamente. Porém, caso haja "pontos cegos" na arena ou ataques contornáveis pela lentidão de projéteis causada pela habilidade "Domínio Fixo", a Ancorada transforma Geovana numa torre impenetrável de *DPS Burst*.
- **Risco:** Muito Alto (Mobilidade reduzida no território).
- **Recompensa:** Máxima (O maior DPS sustentado de todos caso o território seja mantido).

---

## Sugestões de Design para o Balanceamento dos Bosses
Para garantir que esse ecossistema de mecânicas flua naturalmente e nenhuma manifestação quebre o jogo:

1. **Variabilidade de Padrão:** Bosses devem alternar entre movimento caótico (favorece Lacerante/Retornante) e paradas bruscas com invocações de lacaios (favorece Parasítica/Condutora).
2. **Ameaças Secundárias Obrigatórias:** A presença de invocações (mobs menores) no mapa é estritamente necessária para a **Manifestação Condutora** brilhar em lutas singulares.
3. **Punir Permanência sem Anular Estratégias:** Bosses devem possuir artilharias e zonas vermelhas no chão (*AoE*) para forçar o jogador de **Ancorada** a se mover periodicamente, mas com tempo o suficiente para a manifestação não perder o sentido.
4. **Mecânicas de "Break" (Atordoamento de Chefe):** A janela de vulnerabilidade pós-Break será o ápice visual para combos Prismáticos e Parasíticos.
