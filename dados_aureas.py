# -*- coding: utf-8 -*-

AUREAS_DADOS = [
    {
        "id": "Racional",
        "nome": "RACIONAL",
        "categoria": "Analise e Precisao Temporal",
        "descricao": "Utilidade: controle de ritmo e reposicionamento seguro. Ficar totalmente imovel por 5s gera pontos bonus (+3 + nivel). Ao usar Teleporte com a recarga pronta, ativa Dilatacao Temporal por 8s: inimigos e projeteis ficam 58% mais lentos, Apolo ganha +35% de movimento e atira 28% mais rapido. Quando acaba, vem o Rebote por 3s: inimigos/projeteis aceleram 50%.",
        "resumo": "Controle de ritmo: ficar imovel gera pontos; Teleporte pronto desacelera inimigos/projeteis e acelera Apolo por 8s. Depois ha Rebote: inimigos aceleram por 3s.",
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
            "- Teleporte pronto: 8s de mundo lento e Apolo mais rapido.",
            "- Custo: depois da Dilatacao, inimigos aceleram por 3s."
        ]
    },
    {
        "id": "Impulsiva",
        "nome": "IMPULSIVA",
        "categoria": "Agressividade e Velocidade",
        "descricao": "Utilidade: agressao continua e limpeza rapida de grupos. A cada 5 abates sem sofrer dano, ativa um Frenesi temporario ligado a dano e/ou velocidade. Nas fases com sistema completo, renovar com tempo sobrando aumenta o nivel do Frenesi e os multiplicadores; se Apolo levar hit durante o Frenesi, ele quebra e arma Panico, fazendo o proximo dano recebido escalar pelo nivel alcancado.",
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
        "descricao": "Utilidade: sobreviver a erro, colisao ou disparo perigoso. A aura cria um escudo automatico que anula dano quando esta ativo e depois entra em recarga reduzida por upgrade. Nas fases com sistema completo, o escudo tem 3 cargas; ao quebrar a ultima, Apolo fica 30% mais lento por 4s, mas causa 2x dano no mesmo periodo.",
        "resumo": "Sobrevivencia: escudo automatico anula dano quando ativo e recarrega sozinho. Upgrade reduz a recarga; sistema completo usa 3 cargas.",
        "lore": "\"O tempo e a melhor armadura. Ele consome tudo, exceto a fe.\"",
        "imagem_path": "Sprites/aurea_devota.png",
        "cor": (255, 200, 0),
        "estilo": "devota",
        "beneficios": {
            0: "Nenhum efeito ativo.",
            1: "3 cargas anulam 3 hits. Na quebra: -30% velocidade e 2x dano por 4s. Depois recarrega em 27s.",
            2: "3 cargas anulam 3 hits. Na quebra: -30% velocidade e 2x dano por 4s. Depois recarrega em 24s.",
            3: "3 cargas anulam 3 hits. Na quebra: -30% velocidade e 2x dano por 4s. Depois recarrega em 21s.",
            4: "3 cargas anulam 3 hits. Na quebra: -30% velocidade e 2x dano por 4s. Depois recarrega em 18s.",
            5: "3 cargas anulam 3 hits. Na quebra: -30% velocidade e 2x dano por 4s. Depois recarrega em 15s."
        },
        "destaques": [
            "- Escudo automatico bloqueia dano quando esta ativo.",
            "- Upgrade reduz a recarga, de 27s ate 15s.",
            "- Sistema completo: 3 cargas; quebra final da -30% velocidade e 2x dano."
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
        "descricao": "Utilidade: duplicar pressao ofensiva em janelas curtas. A cada 20s, a aura fica pronta; quando Geovana atira, ecos temporais parados surgem no lugar dela e repetem tiros com 1s de atraso. Cada ativacao comeca com 4 ecos, podendo chegar a 5 se um eco finalizar um inimigo. Os disparos dos ecos causam dano reduzido e usam energia verde no centro com raios roxos. Depois que o ultimo eco e gasto, Geovana sofre desorientacao temporal: o Teleporte recebe 2s extras de recarga.",
        "resumo": "Cria ecos temporais parados que repetem seus tiros com atraso. Se um eco matar, a proxima ativacao ganha +1 eco. Depois vem desorientacao: Teleporte recarrega mais lento por 2s.",
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
            "- Ecos repetem tiros com 1s de atraso e dano reduzido.",
            "- Se um eco finalizar inimigo, a proxima ativacao tem 5 ecos.",
            "- Custo: depois do ultimo eco, Teleporte recebe +2s de recarga."
        ]
    }
]

