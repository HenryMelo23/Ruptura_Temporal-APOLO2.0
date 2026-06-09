# -*- coding: utf-8 -*-

AUREAS_DADOS = [
    {
        "id": "Racional",
        "nome": "RACIONAL",
        "categoria": "Analise e Precisao Temporal",
        "descricao": "Utilidade: controle de ritmo e reposicionamento seguro. Ficar totalmente imovel por 5s gera pontos bonus (+3 + nivel). Ao usar Teleporte com a recarga pronta, ativa Dilatacao Temporal por 8s: inimigos e projeteis ficam 58% mais lentos, Geovana ganha +35% de movimento e atira 28% mais rapido. Quando acaba, vem o Rebote por 3s: inimigos/projeteis aceleram 50%.",
        "resumo": "Controle de ritmo: ficar imovel gera pontos; Teleporte pronto desacelera inimigos/projeteis e acelera Geovana por 8s. Depois ha Rebote: inimigos aceleram por 3s.",
        "lore": "\"A mente fria nao preve o futuro. Ela obriga o futuro a se revelar.\"",
        "imagem_path": "Sprites/aurea_cientista.png",
        "cor": (0, 180, 255),
        "estilo": "racional",
        "beneficios": {
            0: "Nenhum efeito ativo.",
            1: "Parado 5s: +4 pontos. Teleporte ativa 8s de lentidao global; ao desfazer, inimigos +50% por 3s.",
            2: "Parado 5s: +5 pontos. Teleporte ativa 8s de lentidao global; ao desfazer, inimigos +50% por 3s.",
            3: "Parado 5s: +6 pontos. Teleporte ativa 8s de lentidao global; ao desfazer, inimigos +50% por 3s.",
            4: "Parado 5s: +7 pontos. Teleporte ativa 8s de lentidao global; ao desfazer, inimigos +50% por 3s.",
            5: "Parado 5s: +8 pontos. Teleporte ativa 8s de lentidao global; ao desfazer, inimigos +50% por 3s."
        },
        "destaques": [
            "- Fique parado 5s para ganhar pontuacao bonus.",
            "- Teleporte pronto: 8s de mundo lento e Geovana mais rapida.",
            "- Custo: depois da Dilatacao, inimigos aceleram por 3s."
        ]
    },
    {
        "id": "Impulsiva",
        "nome": "IMPULSIVA",
        "categoria": "Agressividade e Velocidade",
        "descricao": "Utilidade: agressao continua e limpeza rapida de grupos. A cada 5 abates sem sofrer dano, ativa um Frenesi temporario ligado a dano e/ou velocidade. Nas fases com sistema completo, renovar com tempo sobrando aumenta o nivel do Frenesi e os multiplicadores; se Geovana levar hit durante o Frenesi, ele quebra e arma Panico, fazendo o proximo dano recebido escalar pelo nivel alcancado.",
        "resumo": "Agressao continua: 5 abates sem dano ativam Frenesi de dano/velocidade. Manter sequencia renova o efeito; sofrer hit quebra a pressao.",
        "lore": "\"A hesitacao e uma fresta pela qual o tempo escorre. Nao pense, aja.\"",
        "imagem_path": "Sprites/aurea_impulsiva.png",
        "cor": (255, 60, 60),
        "estilo": "impulsiva",
        "beneficios": {
            0: "Nenhum efeito ativo.",
            1: "Frenesi dura 3.5s. A cada ciclo de 5 abates: renova; com 1s sobrando: sobe nivel. Hit sofrido quebra e arma Panico.",
            2: "Frenesi dura 4.0s. A cada ciclo de 5 abates: renova; com 1s sobrando: sobe nivel. Hit sofrido quebra e arma Panico.",
            3: "Frenesi dura 4.5s. A cada ciclo de 5 abates: renova; com 1s sobrando: sobe nivel. Hit sofrido quebra e arma Panico.",
            4: "Frenesi dura 5.0s. A cada ciclo de 5 abates: renova; com 1s sobrando: sobe nivel. Hit sofrido quebra e arma Panico.",
            5: "Frenesi dura 5.5s. A cada ciclo de 5 abates: renova; com 1s sobrando: sobe nivel. Hit sofrido quebra e arma Panico."
        },
        "destaques": [
            "- 5 abates sem dano ativam Frenesi.",
            "- Frenesi melhora dano/velocidade e favorece jogo agressivo.",
            "- Custo: sofrer hit quebra a sequencia; no sistema completo arma Panico."
        ]
    },
    {
        "id": "Devota",
        "nome": "DEVOTA",
        "categoria": "Protecao e Sobrevivencia",
        "descricao": "Utilidade: transformar erro em contra-ataque. A aura cria 3 cargas de escudo que anulam impactos. Cada bloqueio cura 10% da vida perdida e concede +25% dano por 3s. Ao quebrar a ultima carga, Geovana recebe Fe Ardente: +65% dano por 4.5s, com apenas -10% velocidade. Upgrade reduz a recarga.",
        "resumo": "Sobrevivencia ofensiva: 3 cargas anulam hits, curam parte da vida perdida e viram janela de dano.",
        "lore": "\"O tempo e a melhor armadura. Ele consome tudo, exceto a fe.\"",
        "imagem_path": "Sprites/aurea_devota.png",
        "cor": (255, 200, 0),
        "estilo": "devota",
        "beneficios": {
            0: "Nenhum efeito ativo.",
            1: "3 cargas anulam hits. Bloqueio cura 10% da vida perdida e da +25% dano por 3s. Recarga: 19.5s.",
            2: "3 cargas anulam hits. Fe Ardente na ultima quebra: +65% dano por 4.5s e so -10% velocidade. Recarga: 17s.",
            3: "3 cargas anulam hits. Bloqueios viram cura e janela de contra-ataque. Recarga: 14.5s.",
            4: "3 cargas anulam hits. Mais uptime defensivo para lutas longas. Recarga: 12s.",
            5: "3 cargas anulam hits. Devota sustenta erro, cura e resposta agressiva. Recarga: 9.5s."
        },
        "destaques": [
            "- 3 cargas de escudo anulam impactos.",
            "- Cada bloqueio cura parte da vida perdida e aumenta o dano por poucos segundos.",
            "- Quando a ultima carga quebra, Fe Ardente entrega um pico de dano com lentidao leve."
        ]
    },
    {
        "id": "Vanguarda",
        "nome": "VANGUARDA",
        "categoria": "Dominio de Area e Incendio",
        "descricao": "Utilidade: transformar proximidade perigosa em dano de area. Inimigos tocados ou proximos podem ficar em chamas e sofrem dano por segundo baseado em vida maxima. Nas fases com sistema completo, sofrer hit ativa um circulo de fogo por 5s que incendeia alvos ao redor. Upgrade aumenta a duracao da queimadura; cada inimigo queimando aumenta o cooldown do Teleporte em 15%.",
        "resumo": "Area e queimadura: inimigos proximos/tocados podem pegar fogo e tomar dano continuo. Upgrade aumenta a duracao; queimando aumenta cooldown do Teleporte.",
        "lore": "\"A marcha do progresso nao pode ser contida por meros segundos.\"",
        "imagem_path": "Sprites/aurea_vanguarda.png",
        "cor": (230, 0, 230),
        "estilo": "vanguarda",
        "beneficios": {
            0: "Nenhum efeito ativo.",
            1: "Hit recebido desenha fogo por 5s. Queimadura dura 6s. Cada inimigo queimando: Teleporte +15%.",
            2: "Hit recebido desenha fogo por 5s. Queimadura dura 7s. Cada inimigo queimando: Teleporte +15%.",
            3: "Hit recebido desenha fogo por 5s. Queimadura dura 8s. Cada inimigo queimando: Teleporte +15%.",
            4: "Hit recebido desenha fogo por 5s. Queimadura dura 9s. Cada inimigo queimando: Teleporte +15%.",
            5: "Hit recebido desenha fogo por 5s. Queimadura dura 10s. Cada inimigo queimando: Teleporte +15%."
        },
        "destaques": [
            "- Inimigos proximos/tocados podem queimar.",
            "- Queimadura causa dano por segundo e dura mais com upgrade.",
            "- Custo: cada inimigo queimando aumenta o cooldown do Teleporte em 15%."
        ]
    },
    {
        "id": "Insana",
        "nome": "INSANA",
        "categoria": "Insanidade Temporal e Ecos",
        "descricao": "Utilidade: duplicar pressao ofensiva e desviar pressao inimiga em janelas curtas. A cada 20s, a aura fica pronta; quando Geovana atira, ecos temporais parados surgem no lugar dela, atraem a prioridade dos inimigos e repetem tiros com 1s de atraso. Cada ativacao comeca com 4 ecos, podendo chegar a 5 se um eco finalizar um inimigo. Os disparos dos ecos causam dano reduzido e usam energia verde no centro com raios roxos. Depois que o ultimo eco e gasto, Geovana sofre desorientacao temporal: o Teleporte recebe 2s extras de recarga.",
        "resumo": "Cria ecos temporais parados que atraem inimigos e repetem seus tiros com atraso. Se um eco matar, a proxima ativacao ganha +1 eco. Depois vem desorientacao: Teleporte recarrega mais lento por 2s.",
        "lore": "\"Nem toda Geovana que atira ainda esta viva no mesmo segundo.\"",
        "imagem_path": "Sprites/aurea_insana.png",
        "cor": (160, 55, 255),
        "estilo": "insana",
        "beneficios": {
            0: "Nenhum efeito ativo.",
            1: "4 ecos por ativacao. Tiros dos ecos causam 48% do dano. Cooldown 19s apos o ultimo eco.",
            2: "4 ecos por ativacao. Tiros dos ecos causam 51% do dano. Cooldown 18s apos o ultimo eco.",
            3: "4 ecos por ativacao. Tiros dos ecos causam 54% do dano. Cooldown 17s apos o ultimo eco.",
            4: "4 ecos por ativacao. Tiros dos ecos causam 57% do dano. Cooldown 16s apos o ultimo eco.",
            5: "4 ecos por ativacao. Tiros dos ecos causam 60% do dano. Cooldown 15s apos o ultimo eco."
        },
        "destaques": [
            "- A cada 20s, seus tiros criam ecos parados.",
            "- Inimigos priorizam os ecos enquanto eles existem.",
            "- Ecos repetem tiros com 1s de atraso e dano reduzido.",
            "- Se um eco finalizar inimigo, a proxima ativacao tem 5 ecos.",
            "- Custo: depois do ultimo eco, Teleporte recebe +2s de recarga."
        ]
    },
    {
        "id": "Voraz",
        "nome": "VORAZ",
        "categoria": "Fome, Consumo e Risco",
        "descricao": "Utilidade: agressao sustentada por coleta ativa. Inimigos derrotados deixam poeira voraz laranja por poucos segundos; coletar essa poeira enche a barra Fome e cura 2% da vida perdida, aumentando 2.5% por ciclo de Fome ate 14.5%. Ao completar a barra, ela sobe para X1, X2 e assim por diante: cada ciclo exige bem mais Fome, a barra cai mais rapido e a parte alta da barra e mais dificil de manter. Com Fome sustentada, os tiros ficam maiores, causam um bonus leve de dano e habilidades recarregam ate 12% mais rapido. Inimigos proximos sao puxados com pouca forca e contato causa mordidas a cada 1.3s: cada mordida causa 10% do dano do auto attack, +2.5% por ciclo de Fome, e usa a mesma cura por Fome. Se ficar mais de 30s sem coletar poeira, a aura cobra 1% da vida a cada 1.5s.",
        "resumo": "Coleta agressiva: poeira voraz enche Fome e cura 2% da vida perdida +2.5% por ciclo, ate 14.5%. Mordidas causam 10% do auto attack +2.5% por ciclo de Fome. Sem coleta por 30s, drena vida.",
        "lore": "\"A ruptura nao abre uma boca. Ela ensina Geovana a sentir uma.\"",
        "imagem_path": "Sprites/aurea_voraz.png",
        "cor": (255, 112, 24),
        "estilo": "voraz",
        "beneficios": {
            0: "Nenhum efeito ativo.",
            1: "Poeira alimenta Fome e cura 2% da vida perdida, +2.5% por ciclo de Fome, ate 14.5%. Mordidas causam 10% do auto attack +2.5% por ciclo.",
            2: "Fome sustentada aumenta levemente dano dos tiros, tamanho dos tiros e velocidade de recarga. A barra escala ao completar ciclos XN.",
            3: "Puxao e mordidas ajudam no corpo a corpo, mas o dano da mordida segue 10% do auto attack +2.5% por ciclo de Fome.",
            4: "Tiros crescem com Fome sustentada e a pressao ofensiva dura melhor se voce continuar coletando poeira.",
            5: "Maior recompensa agressiva, mas ciclos altos decaem rapido, exigem coleta constante e mantem o mesmo calculo claro de mordida."
        },
        "destaques": [
            "- Abates deixam poeira laranja voraz por poucos segundos.",
            "- Coletar poeira enche Fome e cura 2% da vida perdida, +2.5% por ciclo de Fome, ate 14.5%.",
            "- Cada ciclo exige muito mais Fome; barra alta cai mais rapido.",
            "- Mordidas causam 10% do auto attack, +2.5% por ciclo de Fome, e usam a mesma cura por Fome.",
            "- Custo: 30s sem coletar poeira drena 1% de vida a cada 1.5s."
        ]
    }
]

