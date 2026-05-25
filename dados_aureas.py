# -*- coding: utf-8 -*-

AUREAS_DADOS = [
    {
        "id": "Racional",
        "nome": "RACIONAL",
        "categoria": "Analise e Precisao Temporal",
        "descricao": "Foca em precisao cientifica e calculo frio para otimizar anomalias temporais e acertos criticos.",
        "lore": "\"A mente fria nao preve o futuro. Ela obriga o futuro a se revelar.\"",
        "imagem_path": "Sprites/aurea_cientista.png",
        "cor": (0, 180, 255),
        "estilo": "racional",
        "beneficios": {
            0: "Nenhum efeito ativo.",
            1: "Ganho de energia base. Critico +3%",
            2: "Ganho de energia +4. Critico +5%",
            3: "Ganho de energia +5. Critico +8%",
            4: "Ganho de energia +6. Critico +10%",
            5: "Ganho de energia +8. Critico +15% (Maximo)"
        }
    },
    {
        "id": "Impulsiva",
        "nome": "IMPULSIVA",
        "categoria": "Agressividade e Velocidade",
        "descricao": "Libera ondas de energia destrutiva ao usar habilidades, concedendo velocidade e dano aumentados por abate.",
        "lore": "\"A hesitacao e uma fresta pela qual o tempo escorre. Nao pense, aja.\"",
        "imagem_path": "Sprites/aurea_impulsiva.png",
        "cor": (255, 60, 60),
        "estilo": "impulsiva",
        "beneficios": {
            0: "Nenhum efeito ativo.",
            1: "Duracao do buff: 3.5s. Multiplicador de dano: 1.35x",
            2: "Duracao do buff: 4.0s. Multiplicador de dano: 1.40x",
            3: "Duracao do buff: 4.5s. Multiplicador de dano: 1.45x",
            4: "Duracao do buff: 5.0s. Multiplicador de dano: 1.50x",
            5: "Duracao do buff: 5.5s. Multiplicador de dano: 1.55x (Maximo)"
        }
    },
    {
        "id": "Devota",
        "nome": "DEVOTA",
        "categoria": "Protecao e Sobrevivencia",
        "descricao": "Manifesta uma barreira temporal que absorve qualquer ataque. O tempo de recarga da barreira diminui a cada nivel.",
        "lore": "\"O tempo e a melhor armadura. Ele consome tudo, exceto a fe.\"",
        "imagem_path": "Sprites/aurea_devota.png",
        "cor": (255, 200, 0),
        "estilo": "devota",
        "beneficios": {
            0: "Nenhum efeito ativo.",
            1: "Intervalo do escudo: 27s.",
            2: "Intervalo do escudo: 24s.",
            3: "Intervalo do escudo: 21s.",
            4: "Intervalo do escudo: 18s.",
            5: "Intervalo do escudo: 15s (Maximo)"
        }
    },
    {
        "id": "Vanguarda",
        "nome": "VANGUARDA",
        "categoria": "Dominio de Area e Incendio",
        "descricao": "Incendia o chao ao avancar, criando zonas temporais de dano continuo e drenagem vital.",
        "lore": "\"A marcha do progresso nao pode ser contida por meros segundos.\"",
        "imagem_path": "Sprites/aurea_vanguarda.png",
        "cor": (230, 0, 230),
        "estilo": "vanguarda",
        "beneficios": {
            0: "Nenhum efeito ativo.",
            1: "Duracao: 6s. Dreno vital: 1.2%",
            2: "Duracao: 7s. Dreno vital: 1.4%",
            3: "Duracao: 8s. Dreno vital: 1.6%",
            4: "Duracao: 9s. Dreno vital: 1.8%",
            5: "Duracao: 10s. Dreno vital: 2.0% (Maximo)"
        }
    }
]
