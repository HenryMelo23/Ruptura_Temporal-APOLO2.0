# Mecânicas e Lógicas de Áureas e Manifestações

Este documento detalha o funcionamento mecânico e a lógica de programação de cada Áurea e de cada Manifestação ativa do jogo.

---

## 1. Áureas

As Áureas modificam o estilo de jogo da personagem Geovana, concedendo habilidades passivas e ativas, além de aplicar penalidades ou custos que devem ser gerenciados pelo jogador.

### Racional
* **Passiva (Imobilidade):** Permanecer totalmente imóvel por 5 segundos gera pontuação bônus (+3 pontos mais o nível do upgrade da áurea).
* **Ativa (Dilatação Temporal):** Ao utilizar o Teleporte com a recarga (cooldown) totalmente pronta, ativa-se o efeito de Dilatação Temporal por 8 segundos. Sob este efeito:
  * Inimigos e projéteis no cenário ficam 58% mais lentos.
  * Geovana ganha +35% de velocidade de movimento.
  * Geovana atira 28% mais rápido.
* **Penalidade (Rebote):** Após o encerramento dos 8 segundos de Dilatação Temporal, inicia-se o estado de Rebote por 3 segundos. Durante o Rebote, todos os inimigos e projéteis são acelerados em 50%.

### Impulsiva
* **Passiva (Frenesi):** A cada 5 inimigos derrotados sem que Geovana sofra dano, ativa-se o Frenesi. O Frenesi concede bônus de velocidade e dano. A duração base do efeito é de 3.5 segundos (aumentando em 0.5s por nível de upgrade, chegando a 5.5s no nível 5).
* **Multiplicadores e Renovação:** Se o ciclo de 5 abates sem dano for completado enquanto o Frenesi estiver ativo com pelo menos 1 segundo restante, o nível do Frenesi e seus respectivos multiplicadores de dano/velocidade aumentam.
* **Penalidade (Pânico):** Se Geovana sofrer qualquer dano enquanto o Frenesi estiver ativo, o bônus é imediatamente cancelado e a mecânica de Pânico é armada, fazendo com que o próximo golpe recebido cause dano multiplicado com base no nível de Frenesi acumulado.

### Devota
* **Passiva (Cargas de Escudo):** Geovana inicia o jogo ou recarrega 3 cargas de escudo divino que anulam completamente os impactos recebidos.
* **Bloqueio e Cura:** Cada vez que uma carga de escudo anula um impacto, cura Geovana em 10% de sua vida perdida e concede +25% de dano adicional por 3 segundos.
* **Ativa (Fé Ardente):** Quando a última das 3 cargas do escudo é quebrada por um golpe inimigo, Geovana entra no estado de Fé Ardente por 4.5 segundos. Esse estado concede +65% de dano adicional, aplicando uma penalidade leve de -10% de velocidade de movimento.
* **Recarga:** A recarga total do escudo diminui progressivamente com o nível de upgrade da áurea (19.5s no nível 1, reduzindo até 9.5s no nível 5).

### Vanguarda
* **Passiva (Incêndio por Área):** Inimigos muito próximos ou que entram em contato direto com Geovana têm chance de ser incendiados, sofrendo dano por segundo contínuo baseado em sua vida máxima. A duração da queimadura começa em 6 segundos no nível 1 e aumenta até 10 segundos no nível 5.
* **Ativa (Círculo de Fogo):** Ao receber qualquer dano de inimigos, Geovana ativa instantaneamente um círculo de fogo ao redor de si por 5 segundos, incendiando todos os inimigos na área.
* **Penalidade (Recarga de Teleporte):** Cada inimigo que estiver ativamente queimando no cenário aumenta em 15% o tempo de recarga (cooldown) do Teleporte de Geovana.

### Insana
* **Passiva (Prontidão):** A áurea fica pronta a cada 20 segundos (tempo reduzido de 19s a 15s conforme o nível de upgrade).
* **Ativa (Ecos Temporais):** Quando a áurea está pronta, o próximo disparo de Geovana cria ecos temporais estáticos na posição em que ela atirou.
  * Os ecos chamam a prioridade de ataque (aggro) dos inimigos ao seu redor.
  * Os ecos repetem os tiros de Geovana com um atraso de 1 segundo.
  * O dano dos disparos dos ecos é reduzido, correspondendo a 17% do dano básico no nível 1, escalando até 37% no nível 5.
* **Quantidade de Ecos:** Cada ativação gera inicialmente 4 ecos. Se um eco conseguir desferir o golpe final em qualquer inimigo, a próxima ativação da áurea gerará +1 eco extra (limite máximo de 5 ecos por ativação).
* **Penalidade (Desorientação):** Após o desaparecimento do último eco temporal ativo, Geovana sofre Desorientação Temporal, que adiciona 2 segundos à recarga do seu Teleporte.

### Voraz
* **Passiva (Coágulos de Sangue):** Inimigos derrotados deixam coágulos de sangue flutuantes que duram 3 segundos no cenário. Coletá-los preenche a barra de Fome e cura Geovana em 2% de sua vida perdida (essa cura aumenta em +2.5% para cada ciclo de Fome ativo, até o limite de 14.5%).
* **Ciclos de Fome (X1, X2, etc.):** Preencher completamente a barra de Fome sobe o nível do ciclo. Ciclos de Fome mais altos exigem mais pontos para serem preenchidos, decaem significativamente mais rápido e são mais difíceis de manter.
* **Efeitos de Fome Sustentada:** Manter a barra de Fome ativa aumenta o tamanho dos disparos de Geovana, concede bônus de dano a eles e acelera a recarga de suas habilidades em até 12%.
* **Atração e Mordidas:** Inimigos próximos sofrem um leve puxão gravitacional na direção de Geovana. Inimigos que colidirem com ela sofrem mordidas automáticas a cada 1.3 segundos. Cada mordida causa 10% do dano do ataque básico (+2.5% por ciclo de Fome) e cura Geovana de forma idêntica à coleta de coágulos.
* **Penalidade (Dreno de Vida):** Caso o jogador fique mais de 30 segundos sem coletar nenhum coágulo de sangue, a fome drena a vida de Geovana, aplicando dano contínuo de 1% de sua vida máxima a cada 1.5 segundos.

### Nula
* **Passiva (Campo de Anulação):** Geovana possui uma barra de recurso chamada *Vazio*. Esta barra acumula carga quando:
  * Geovana passa alguns segundos sem realizar ataques.
  * Geovana desvia de projéteis de raspão (esquiva precisa).
  * Geovana utiliza o Teleporte sem atingir nenhum inimigo.
  * Inimigos morrem sem estar sob o efeito de debuffs (veneno, queimadura, laceração ou sementes).
* **Ativa (Nulificação):** Ao preencher completamente a barra de Vazio, o próximo disparo básico de Geovana aplica o efeito de *Nulificação*:
  * Remove buffs temporários do alvo.
  * Reduz a resistência do inimigo por alguns segundos.
  * Impede o inimigo de aplicar debuffs em Geovana por um curto tempo.
  * Se o alvo for um inimigo comum com vida alta, causa dano extra.
  * Contra chefes, em vez de remover mecânicas principais, a Nulificação apenas reduz levemente algum atributo do boss por poucos segundos.
* **Penalidade (Custo da Neutralidade):** Enquanto a barra de Vazio estiver carregando, Geovana recebe menos benefício de efeitos explosivos ou caóticos (venenos duram um pouco menos, queimaduras têm duração reduzida e efeitos em cadeia têm menor probabilidade de se propagar).
* **Evolução por Nível:**
  * **Nível 1:** Nulificação dura pouco tempo e reduz a resistência do inimigo levemente.
  * **Nível 2:** A barra de Vazio carrega mais rápido ao desviar de projéteis.
  * **Nível 3:** A Nulificação remove 1 buff de inimigos elites.
  * **Nível 4:** Inimigos nulificados causam menos dano.
  * **Nível 5:** Ao nulificar um inimigo, cria-se uma pequena zona silenciosa no chão.

### Abissal
* **Passiva (Pressão do Abismo):** Durante o combate, Geovana acumula lentamente camadas de *Profundidade*. O acúmulo acelera quando:
  * Há muitos inimigos vivos simultaneamente na tela.
  * Geovana fica cercada por adversários.
  * Chefes permanecem vivos por muito tempo na arena.
  * Geovana causa dano contínuo sem finalizar (matar) os inimigos.
* **Ativa (Maré Negra):** Cada camada de Profundidade acumulada aumenta a pressão abissal, aplicando lentidão leve, redução de aceleração, maior dificuldade de escapar de áreas de dano e dano adicional a inimigos com vida baixa. Ao atingir o nível máximo de Profundidade, ativa-se a *Maré Negra* por alguns segundos:
  * Inimigos próximos são levemente puxados para zonas de sombra no cenário.
  * Inimigos com pouca vida sofrem dano contínuo.
  * Elites recebem uma marca abissal que aumenta o dano recebido de qualquer fonte por pouco tempo.
* **Penalidade (Peso Abissal):** Quanto maior a quantidade de camadas de Profundidade acumuladas, mais pesada Geovana fica, resultando em redução leve de sua velocidade de movimento, alcance do Teleporte ligeiramente menor e redução na frequência de dash/teleporte enquanto a Maré Negra estiver carregando.
* **Evolução por Nível:**
  * **Nível 1:** A Profundidade aplica lentidão leve aos inimigos.
  * **Nível 2:** O recurso Profundidade carrega mais rápido quando Geovana estiver cercada.
  * **Nível 3:** A duração do efeito da Maré Negra é aumentada.
  * **Nível 4:** Inimigos marcados pela marca abissal sofrem mais dano.
  * **Nível 5:** Ao ativar a Maré Negra, inimigos muito fracos são puxados e executados visualmente (sem afetar chefes de forma desbalanceada).

### Profética
* **Passiva (Presságio):** A cada poucos segundos, a áurea marca um inimigo com um *Presságio* visualizado como um pequeno símbolo acima do alvo. O símbolo prevê um comportamento do alvo:
  * O inimigo vai atacar.
  * O inimigo vai avançar.
  * O inimigo vai se aproximar demais.
  * O inimigo vai morrer em breve.
  * O projétil/ameaça específica será muito perigosa.
* **Ativa (Reação Correta):** O jogador deve ler a previsão e agir de acordo com a resposta correta para ganhar recompensas:
  * *Presságio: Inimigo vai atacar* -> *Resposta correta: Acertar antes do ataque* -> *Recompensa: Dano bônus*.
  * *Presságio: Inimigo vai avançar* -> *Resposta correta: Teleporte antes do contato* -> *Recompensa: Recarga parcial*.
  * *Presságio: Inimigo vai morrer* -> *Resposta correta: Finalizar o alvo* -> *Recompensa: Moedas/pontos extras*.
  * *Presságio: Projétil/ameaça perigosa* -> *Resposta correta: Manter distância* -> *Recompensa: Escudo curto ou velocidade breve*.
* **Penalidade (Destino Quebrado):** Se o jogador ignorar ou falhar na reação correta ao Presságio ativo, Geovana recebe *Destino Quebrado*, aplicando uma pequena redução de sorte, pior chance na próxima escolha de recompensa/carta, leve aumento temporário no cooldown do Teleporte ou perda do bônus acumulado.
* **Evolução por Nível:**
  * **Nível 1:** Presságios simples começam a aparecer a cada X segundos.
  * **Nível 2:** O valor das recompensas ao acertar a reação aumenta.
  * **Nível 3:** Os símbolos visuais dos Presságios ficam mais nítidos e claros na tela.
  * **Nível 4:** Acertos consecutivos de reações aos Presságios acumulam bônus.
  * **Nível 5:** Ao acertar 3 Presságios seguidos, ativa-se o estado de *Clarividência* por alguns segundos (destaca inimigos perigosos, desacelera levemente projéteis perto de Geovana e aumenta a recompensa da próxima ação correta).

### Sanguinária
* **Passiva (Ferida Aberta):** Ao desferir dano repetido contra o mesmo alvo, Geovana aplica o efeito de *Ferida Aberta*. Inimigos feridos sofrem dano extra de ataques seguintes, deixam um rastro curto de sangue/energia no chão e ficam mais vulneráveis a golpes finalizadores (esta mecânica não concede cura a Geovana).
* **Ativa (Sede de Ruptura):** Causar dano em inimigos feridos concede cargas de *Sede*. Sob Sede alta, o dano contra inimigos feridos é aumentado, efeitos de impacto de ataques ficam mais fortes e abates em inimigos feridos reduzem levemente o cooldown da habilidade secundária.
* **Explosão (Carnificina Controlada):** Ao atingir um determinado número de inimigos sob efeito de Ferida Aberta, o próximo ataque contra um alvo ferido gera uma explosão de cortes vermelhos em pequena área (independe de tipo de arma e não aplica o estado Aberto).
* **Penalidade (Instinto de Caça):** Se Geovana passar muito tempo sem golpear inimigos sob efeito de Ferida Aberta, a Sede decai e se volta contra ela, aplicando perda de cargas de Sede acumuladas, pequena vulnerabilidade temporária a dano e redução de dano a inimigos não feridos por alguns segundos.
* **Evolução por Nível:**
  * **Nível 1:** Aplica Ferida Aberta após causar dano contínuo no mesmo inimigo.
  * **Nível 2:** Inimigos feridos sofrem mais dano adicional de Geovana.
  * **Nível 3:** Abates em alvos feridos reduzem levemente o cooldown da habilidade secundária.
  * **Nível 4:** As cargas de Sede demoram mais tempo para começar a decair.
  * **Nível 5:** A explosão especial Carnificina Controlada é ativada com menos feridas acumuladas em combate.

---

## 2. Manifestações

As Manifestações definem o comportamento do disparo principal e da habilidade secundária da arma de Geovana.

### Manifestação Elétrica
* **Disparo:** Lança um projétil elétrico rápido em linha reta com rastro ciano, que gera uma explosão de faíscas no ponto de impacto.
* **Habilidade (Onda Cinética):** Descarrega uma onda de choque em área que empurra Geovana para trás com o recuo, causa dano aos inimigos ao redor e propaga corrente elétrica (dano compartilhado) para alvos próximos.

### Manifestação Lacerante
* **Disparo (Corte de Ruptura):** Desfere lâminas temporais de alcance reduzido que atravessam inimigos em linha reta e aplicam uma carga do efeito Laceração. Ao acumular 3 cargas de Laceração, o inimigo entra no estado "Aberto", sofrendo dano adicional ao se movimentar ou realizar ataques.
* **Habilidade (Fenda Carnívora):** Abre uma fissura vermelha linear à frente. Após um breve aviso visual, a fissura explode em múltiplos cortes, causando dano aos alvos alinhados e consumindo os acúmulos de Laceração dos inimigos para causar dano extra.
* **Teleporte (Rastro Lacerante):** O Teleporte (Shift) abre um rasgo espacial entre a origem e o destino. Inimigos tocados por esse rasgo recebem dano leve e uma carga de Laceração.

### Manifestação Prismática
* **Disparo (Feixe Prismático):** Dispara um feixe de luz linear, fino e veloz, com dano básico reduzido. O feixe ricocheteia uma vez ao colidir com paredes ou inimigos marcados, ganhando dano extra após o ricochete. Se o feixe ricocheteado atingir o mesmo alvo original, causa um crítico prismático.
* **Habilidade (Prisma de Refração):** Cria um pequeno prisma no cursor por alguns segundos. Qualquer disparo que atravessar o prisma se divide em 3 feixes menores de luz. Inimigos que encostarem no prisma recebem dano leve e quebram a estrutura.
* **Teleporte (Lente Prismática):** O Teleporte projeta luz e materializa um prisma maior no ponto de destino. Esse prisma especial recebe os feixes refratados pelo prisma comum e os divide novamente, permitindo combos geométricos.

### Manifestação Retornante
* **Disparo (Pulso Retornante):** Lança um pulso de energia que atravessa todos os inimigos no caminho. Na ida, causa dano baixo. Ao atingir a distância máxima, o pulso faz a curva e retorna até Geovana, causando dano alto e aplicando bônus de acerto pelas costas (crítico de retorno) nos alvos que atravessar de volta.
* **Habilidade (Chamado Reverso):** Marca todos os projéteis retornantes atualmente ativos em campo e força o retorno imediato deles em linha reta para Geovana, aplicando um multiplicador de dano aumentado na volta rápida.

### Manifestação Parasítica
* **Disparo (Semente Parasítica):** Causa pouco dano no impacto inicial e planta uma semente dimensional no corpo do hospedeiro. Acertar repetidamente o mesmo inimigo fortalece e acelera a infecção; inimigos agrupados ou realizando ações de ataque aceleram o amadurecimento natural da semente.
* **Habilidade (Eclosão):** Força todas as sementes implantadas nos inimigos a explodirem imediatamente. Sementes que atingiram a maturação total causam dano alto em área e espalham sementes menores para alvos próximos; sementes imaturas explodem causando apenas dano individual baixo.

### Manifestação Condutora
* **Disparo (Pulso Lógico):** Inimigos na tela exibem valores binários flutuantes (0 ou 1). O primeiro tiro de Geovana que atinge um inimigo o define como "Entrada A". O segundo acerto em outro inimigo define a "Entrada B", avaliando a porta lógica ativa na fila (OR, XOR, AND, NAND, NOR) para ligá-los por um fio condutor.
* **Habilidade (Fechamento de Circuito):** Detona os fios lógicos criados. Conexões cujo resultado binário da porta lógica avalie como 1 explodem causando alto dano em cadeia; conexões que resultem em 0 causam dano fraco e aplicam "Ruído Lógico" (velocidade reduzida em Geovana temporariamente).
* **Teleporte (Salto em Circuito):** O Teleporte cria uma linha de condutividade elétrica entre o ponto de partida e o de chegada. Inimigos cruzados pela linha sofrem "Curto", resultando em atordoamento (stun) por 3 segundos e dano equivalente a 50% do ataque básico.

### Manifestação Gravitante
* **Disparo (Orbe Gravitante):** Prende uma orbe energética que entra em órbita ao redor do inimigo atingido. A orbe gira em torno do alvo causando ticks de dano contínuos e explode após alguns segundos. Se o inimigo morrer antes da explosão, a orbe tenta migrar para outro hospedeiro próximo.
* **Habilidade (Colapso Orbital):** Conjura 3 orbes gravitacionais ao redor de Geovana. Elas disparam automaticamente contra inimigos próximos que entram em alcance, iniciando órbitas de dano contínuo neles.

### Manifestação Ancorada
* **Disparo (Âncora de Ruptura):** Cada disparo básico planta uma âncora energética no solo. Enquanto Geovana permanecer dentro do raio de ação das âncoras no chão, ela ganha bônus de dano, cadência de tiro aumentada e os inimigos que cruzarem o limite das âncoras sofrem dano leve contínuo.
* **Habilidade (Domínio Fixo):** Estabelece um círculo de domínio ao redor de Geovana por alguns segundos. Dentro desse círculo, seus ataques são fortalecidos, os projéteis inimigos são desacelerados e os inimigos recebem marcas para sofrerem dano aumentado.
