# -*- coding: utf-8 -*-

AUREAS_DADOS = [
    {
        "id": "Racional",
        "nome": "RACIONAL",
        "categoria": "Analise e Precisao Temporal",
        "descricao": "Como funciona: fique totalmente imovel por 5 segundos para gerar pontos bonus. Alem disso, apos sair do teleporte, o mundo desacelera por 3 segundos enquanto Geovana ganha velocidade de movimento e cadencia de ataque.",
        "lore": "\"A mente fria nao preve o futuro. Ela obriga o futuro a se revelar.\"",
        "imagem_path": "Sprites/aurea_cientista.png",
        "cor": (0, 180, 255),
        "estilo": "racional",
        "beneficios": {
            0: "Nenhum efeito ativo.",
            1: "Parado por 5s: +4 pontos. Pos-teleporte: 3s de mundo lento e buff de movimento/ataque.",
            2: "Parado por 5s: +5 pontos. Pos-teleporte: 3s de mundo lento e buff de movimento/ataque.",
            3: "Parado por 5s: +6 pontos. Pos-teleporte: 3s de mundo lento e buff de movimento/ataque.",
            4: "Parado por 5s: +7 pontos. Pos-teleporte: 3s de mundo lento e buff de movimento/ataque.",
            5: "Parado por 5s: +8 pontos. Pos-teleporte: 3s de mundo lento e buff de movimento/ataque (Maximo)."
        }
    },
    {
        "id": "Impulsiva",
        "nome": "IMPULSIVA",
        "categoria": "Agressividade e Velocidade",
        "descricao": "Como funciona: elimine 5 inimigos seguidos sem sofrer dano. Ao completar a sequencia, a aura ativa um buff aleatorio temporario: mais dano fisico ou mais velocidade de movimento. Sofrer dano zera a contagem.",
        "lore": "\"A hesitacao e uma fresta pela qual o tempo escorre. Nao pense, aja.\"",
        "imagem_path": "Sprites/aurea_impulsiva.png",
        "cor": (255, 60, 60),
        "estilo": "impulsiva",
        "beneficios": {
            0: "Nenhum efeito ativo.",
            1: "5 abates sem dano: 3.5s de Dano +35% ou Velocidade +25%.",
            2: "5 abates sem dano: 4.0s de Dano +40% ou Velocidade +30%.",
            3: "5 abates sem dano: 4.5s de Dano +45% ou Velocidade +35%.",
            4: "5 abates sem dano: 5.0s de Dano +50% ou Velocidade +40%.",
            5: "5 abates sem dano: 5.5s de Dano +55% ou Velocidade +45% (Maximo)."
        }
    },
    {
        "id": "Devota",
        "nome": "DEVOTA",
        "categoria": "Protecao e Sobrevivencia",
        "descricao": "Como funciona: a aura cria um escudo automatico. Enquanto ele estiver ativo, o proximo dano recebido e anulado por completo. Depois de quebrar, o escudo volta sozinho quando a recarga termina; evoluir reduz essa recarga.",
        "lore": "\"O tempo e a melhor armadura. Ele consome tudo, exceto a fe.\"",
        "imagem_path": "Sprites/aurea_devota.png",
        "cor": (255, 200, 0),
        "estilo": "devota",
        "beneficios": {
            0: "Nenhum efeito ativo.",
            1: "Escudo anula 1 dano. Volta em 27 segundos.",
            2: "Escudo anula 1 dano. Volta em 24 segundos.",
            3: "Escudo anula 1 dano. Volta em 21 segundos.",
            4: "Escudo anula 1 dano. Volta em 18 segundos.",
            5: "Escudo anula 1 dano. Volta em 15 segundos (Maximo)"
        }
    },
    {
        "id": "Vanguarda",
        "nome": "VANGUARDA",
        "categoria": "Dominio de Area e Incendio",
        "descricao": "Como funciona: aproxime-se ou encoste nos inimigos para marcar alvos com chamas. Enquanto queimam, eles sofrem dano continuo por segundo com base na vida maxima. Evoluir aumenta a duracao e o percentual da queimadura.",
        "lore": "\"A marcha do progresso nao pode ser contida por meros segundos.\"",
        "imagem_path": "Sprites/aurea_vanguarda.png",
        "cor": (230, 0, 230),
        "estilo": "vanguarda",
        "beneficios": {
            0: "Nenhum efeito ativo.",
            1: "Contato/proximidade incendeia por 6s. Dano/s: 1.2% a 3.5% da vida max.",
            2: "Contato/proximidade incendeia por 7s. Dano/s: 1.4% a 4.0% da vida max.",
            3: "Contato/proximidade incendeia por 8s. Dano/s: 1.6% a 4.5% da vida max.",
            4: "Contato/proximidade incendeia por 9s. Dano/s: 1.8% a 5.0% da vida max.",
            5: "Contato/proximidade incendeia por 10s. Dano/s: 2.0% a 5.5% da vida max. (Maximo)"
        }
    }
]

