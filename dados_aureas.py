# -*- coding: utf-8 -*-

AUREAS_DADOS = [
    {
        "id": "Racional",
        "nome": "RACIONAL",
        "categoria": "Analise e Precisao Temporal",
        "descricao": "Ficar parado por 5 segundos gera Pontuacao bonus. A cada 5 segundos de imobilidade, voce ganha pontos extras. O valor do bonus de pontuacao aumenta a cada nivel.",
        "lore": "\"A mente fria nao preve o futuro. Ela obriga o futuro a se revelar.\"",
        "imagem_path": "Sprites/aurea_cientista.png",
        "cor": (0, 180, 255),
        "estilo": "racional",
        "beneficios": {
            0: "Nenhum efeito ativo.",
            1: "Ganha +4 Pontos a cada 5s imóvel.",
            2: "Ganha +5 Pontos a cada 5s imóvel.",
            3: "Ganha +6 Pontos a cada 5s imóvel.",
            4: "Ganha +7 Pontos a cada 5s imóvel.",
            5: "Ganha +8 Pontos a cada 5s imóvel (Máximo)"
        }
    },
    {
        "id": "Impulsiva",
        "nome": "IMPULSIVA",
        "categoria": "Agressividade e Velocidade",
        "descricao": "Ao eliminar 5 inimigos consecutivamente sem receber dano, ativa um Buff temporario aleatorio de Dano ou de Velocidade. Receber qualquer dano reinicia a contagem.",
        "lore": "\"A hesitacao e uma fresta pela qual o tempo escorre. Nao pense, aja.\"",
        "imagem_path": "Sprites/aurea_impulsiva.png",
        "cor": (255, 60, 60),
        "estilo": "impulsiva",
        "beneficios": {
            0: "Nenhum efeito ativo.",
            1: "Duracao: 3.5s | Buff: Dano +35% ou Velocidade +25%",
            2: "Duracao: 4.0s | Buff: Dano +40% ou Velocidade +30%",
            3: "Duracao: 4.5s | Buff: Dano +45% ou Velocidade +35%",
            4: "Duracao: 5.0s | Buff: Dano +50% ou Velocidade +40%",
            5: "Duracao: 5.5s | Buff: Dano +55% ou Velocidade +45% (Máximo)"
        }
    },
    {
        "id": "Devota",
        "nome": "DEVOTA",
        "categoria": "Protecao e Sobrevivencia",
        "descricao": "Manifesta uma barreira temporal protetora que anula totalmente o proximo dano recebido. A barreira se regenera apos um tempo de recarga que diminui a cada nivel.",
        "lore": "\"O tempo e a melhor armadura. Ele consome tudo, exceto a fe.\"",
        "imagem_path": "Sprites/aurea_devota.png",
        "cor": (255, 200, 0),
        "estilo": "devota",
        "beneficios": {
            0: "Nenhum efeito ativo.",
            1: "Escudo anula 1 golpe. Recarga: 27 segundos.",
            2: "Escudo anula 1 golpe. Recarga: 24 segundos.",
            3: "Escudo anula 1 golpe. Recarga: 21 segundos.",
            4: "Escudo anula 1 golpe. Recarga: 18 segundos.",
            5: "Escudo anula 1 golpe. Recarga: 15 segundos (Máximo)"
        }
    },
    {
        "id": "Vanguarda",
        "nome": "VANGUARDA",
        "categoria": "Dominio de Area e Incendio",
        "descricao": "Ao colidir ou tocar em inimigos, voce os incendeia por um tempo. Inimigos em chamas sofrem dano continuo baseado em sua vida maxima a cada segundo.",
        "lore": "\"A marcha do progresso nao pode ser contida por meros segundos.\"",
        "imagem_path": "Sprites/aurea_vanguarda.png",
        "cor": (230, 0, 230),
        "estilo": "vanguarda",
        "beneficios": {
            0: "Nenhum efeito ativo.",
            1: "Chamas duram 6s | Dano por segundo: 1.2% a 3.5% da vida max.",
            2: "Chamas duram 7s | Dano por segundo: 1.4% a 4.0% da vida max.",
            3: "Chamas duram 8s | Dano por segundo: 1.6% a 4.5% da vida max.",
            4: "Chamas duram 9s | Dano por segundo: 1.8% a 5.0% da vida max.",
            5: "Chamas duram 10s | Dano por segundo: 2.0% a 5.5% da vida max. (Máximo)"
        }
    }
]

