# -*- coding: utf-8 -*-

AUREAS_DADOS = [
    {
        "id": "Racional",
        "nome": "RACIONAL",
        "categoria": "Analise e Precisao Temporal",
        "descricao": "Como funciona: ficar totalmente imovel por 5s gera pontos bonus. Ao usar o Teleporte, a Dilatacao Temporal pode ativar: por 8s o mundo desacelera e Apolo age melhor. Quando acaba, o Efeito Elastico desfaz o controle e todos os inimigos aceleram +50% por 3s; depois voltam ao normal.",
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
        }
    },
    {
        "id": "Impulsiva",
        "nome": "IMPULSIVA",
        "categoria": "Agressividade e Velocidade",
        "descricao": "Como funciona: 5 abates ativam Frenesi, dando dano e velocidade. Mais 5 abates antes do timer acabar mantem o estado; se sobrarem pelo menos 1s, o nivel de Frenesi sobe e os multiplicadores crescem. Se o timer zerar, o Frenesi some sem punicao. Se Apolo levar hit durante o Frenesi, ele quebra na hora e arma Panico: o proximo dano recebido escala pelo nivel alcancado.",
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
        }
    },
    {
        "id": "Devota",
        "nome": "DEVOTA",
        "categoria": "Protecao e Sobrevivencia",
        "descricao": "Como funciona: a aura cria um escudo com 3 cargas, e cada carga anula totalmente 1 hit. Quando a terceira carga quebra, o escudo se desfaz e Apolo entra em sobrecarga por 4s: -30% velocidade e 2x dano causado. Ao fim da recarga, o escudo volta com 3 cargas novas.",
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
        }
    },
    {
        "id": "Vanguarda",
        "nome": "VANGUARDA",
        "categoria": "Dominio de Area e Incendio",
        "descricao": "Como funciona: ao sofrer hit, Apolo ativa um circulo de fogo pulsante por 5s. O raio incendeia inimigos ao redor enquanto esta ativo; inimigos queimando continuam marcados ate a queimadura acabar. Cada inimigo queimando aumenta o cooldown do Teleporte em 15%. Quando nao ha circulo ativo nem inimigos queimando, o fogo desaparece.",
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
        }
    }
]

