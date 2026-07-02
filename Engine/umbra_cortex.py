"""Camada cognitiva da Umbra.

Este modulo fica acima do DQN antigo: ele transforma percepcao, dossie,
profecias e memoria recente em uma intencao tatica. A saida ainda respeita
as acoes disponiveis do boss, entao a Umbra continua jogavel e previsivel
para QA, mas deixa de ser apenas uma roleta matematica.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import random
from typing import Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple


ACOES_MENTE = [
    "ATAQUE",
    "SIFON",
    "TELEPORTE",
    "TELEPORTE_JUKE",
    "VORTICE",
    "PRISAO",
    "MIASMA",
    "DESCARGA_ELETRICA",
    "CAMINHO_ESPINHOS",
    "LASER_SOBRECARGA",
    "PRAGA_RATOS",
    "TRANSMUTAR_VORTICE",
    "TRANSMUTAR_GRAVIDADE",
    "TRANSMUTAR_NECROSE",
    "TRANSMUTAR_RESSONANCIA",
    "TRANSMUTAR_HEMORRAGIA",
    "TRANSMUTAR_ATRITO",
    "TRANSMUTAR_RASTRO",
]

ACOES_MOVIMENTO = ["FUGIR", "INTERCEPTAR", "ORBITAR", "CERCAR"]


@dataclass
class PercepcaoUmbra:
    agora: int
    boss_pos: Tuple[float, float]
    player_pos: Tuple[float, float]
    player_vel: Tuple[float, float]
    vida_umbra: float
    vida_umbra_max: float
    mapa_atual: str
    sob_fogo: float
    armadilhas_ativas: Dict[str, float]
    resumo_predatorio: Dict[str, float]
    modificadores: List[Dict[str, float]]
    distancia: float = 0.0
    vida_perc: float = 1.0
    player_no_canto: float = 0.0
    player_na_borda: float = 0.0
    player_parado: float = 0.0
    player_previsivel: float = 0.0


@dataclass
class PlanoUmbra:
    acao: str
    intencao: str
    confianca: float
    pesos: Dict[str, float]
    tracos: List[str] = field(default_factory=list)


def _clamp(v: float, minimo: float = 0.0, maximo: float = 1.0) -> float:
    return max(minimo, min(maximo, float(v)))


def _sigmoid(v: float) -> float:
    if v >= 0:
        z = math.exp(-v)
        return 1.0 / (1.0 + z)
    z = math.exp(v)
    return z / (1.0 + z)


def _normalizar(scores: Mapping[str, float]) -> Dict[str, float]:
    if not scores:
        return {}
    minimo = min(scores.values())
    maximo = max(scores.values())
    if abs(maximo - minimo) < 1e-6:
        return {k: 0.5 for k in scores}
    return {k: round((v - minimo) / (maximo - minimo), 4) for k, v in scores.items()}


class RedeInstintoUmbra:
    """MLP pequeno e deterministico para priorizar intencoes.

    A rede e propositalmente leve: a Umbra ja possui DQN legado para valores
    por acao. Aqui usamos uma rede de instinto para misturar sobrevivencia,
    leitura do jogador e memoria curta sem depender de GPU durante a luta.
    """

    entradas = [
        "vida_baixa",
        "vida_critica",
        "distancia_curta",
        "distancia_longa",
        "sob_fogo",
        "player_canto",
        "player_borda",
        "player_parado",
        "previsibilidade",
        "dependencia_dash",
        "dependencia_orbe",
        "agressividade",
        "adaptabilidade",
        "armadilhas_ativas",
    ]

    intencoes = [
        "sobreviver",
        "pressionar",
        "zonear",
        "punir_padrao",
        "quebrar_ritmo",
        "reposicionar",
        "variar_dimensao",
    ]

    def __init__(self) -> None:
        self._pesos = self._criar_pesos()
        self._memoria_curta = {i: 0.0 for i in self.intencoes}

    def _criar_pesos(self) -> Dict[str, Dict[str, float]]:
        return {
            "sobreviver": {
                "vida_baixa": 1.8, "vida_critica": 2.5, "sob_fogo": 1.0,
                "distancia_curta": 0.7, "adaptabilidade": -0.3,
            },
            "pressionar": {
                "distancia_longa": 1.1, "player_borda": 0.8, "player_canto": 1.0,
                "agressividade": -0.2, "previsibilidade": 0.5,
            },
            "zonear": {
                "player_parado": 1.2, "player_borda": 0.5, "dependencia_orbe": 0.7,
                "distancia_curta": 0.3, "armadilhas_ativas": -0.8,
            },
            "punir_padrao": {
                "previsibilidade": 1.5, "dependencia_dash": 1.0, "player_parado": 0.7,
                "adaptabilidade": -0.8,
            },
            "quebrar_ritmo": {
                "adaptabilidade": 1.0, "agressividade": 0.8, "sob_fogo": 0.4,
                "previsibilidade": -0.4,
            },
            "reposicionar": {
                "distancia_curta": 1.0, "sob_fogo": 0.9, "player_canto": -0.3,
                "vida_baixa": 0.6,
            },
            "variar_dimensao": {
                "armadilhas_ativas": -0.6, "adaptabilidade": 0.7, "distancia_longa": 0.4,
                "previsibilidade": 0.3,
            },
        }

    def avaliar(self, features: Mapping[str, float]) -> Dict[str, float]:
        bruto: Dict[str, float] = {}
        for intencao, pesos in self._pesos.items():
            soma = -0.25
            for nome, peso in pesos.items():
                soma += features.get(nome, 0.0) * peso
            soma += self._memoria_curta.get(intencao, 0.0)
            bruto[intencao] = _sigmoid(soma)
        return bruto

    def reforcar(self, intencao: str, valor: float) -> None:
        if intencao not in self._memoria_curta:
            return
        atual = self._memoria_curta[intencao]
        self._memoria_curta[intencao] = _clamp(atual + valor, -0.35, 0.35)

    def decair_memoria(self) -> None:
        for chave in list(self._memoria_curta):
            self._memoria_curta[chave] *= 0.985


class UmbraCortex:
    """Orquestra percepcao, intencao e plano de acao da Umbra."""

    _INTENCAO_ACOES = {
        "sobreviver": {
            "SIFON": 1.4, "TELEPORTE": 1.1, "TRANSMUTAR_GRAVIDADE": 0.6,
            "TRANSMUTAR_RASTRO": 0.4,
        },
        "pressionar": {
            "ATAQUE": 1.1, "INTERCEPTAR": 0.8, "PRAGA_RATOS": 1.1,
            "TRANSMUTAR_RASTRO": 0.6, "DESCARGA_ELETRICA": 0.5,
        },
        "zonear": {
            "VORTICE": 1.1, "PRISAO": 1.0, "CAMINHO_ESPINHOS": 1.2,
            "MIASMA": 0.8, "DESCARGA_ELETRICA": 0.9,
        },
        "punir_padrao": {
            "PRISAO": 1.2, "LASER_SOBRECARGA": 1.3, "CAMINHO_ESPINHOS": 0.9,
            "ATAQUE": 0.8, "TELEPORTE_JUKE": 0.7,
        },
        "quebrar_ritmo": {
            "TELEPORTE_JUKE": 1.1, "TELEPORTE": 0.8, "TRANSMUTAR_ATRITO": 0.9,
            "TRANSMUTAR_HEMORRAGIA": 0.8, "LASER_SOBRECARGA": 0.8,
        },
        "reposicionar": {
            "TELEPORTE": 1.3, "TELEPORTE_JUKE": 0.7, "FUGIR": 0.9,
            "ORBITAR": 0.6,
        },
        "variar_dimensao": {
            "TRANSMUTAR_VORTICE": 0.8, "TRANSMUTAR_GRAVIDADE": 0.8,
            "TRANSMUTAR_NECROSE": 0.8, "TRANSMUTAR_RESSONANCIA": 0.8,
            "TRANSMUTAR_HEMORRAGIA": 0.8, "TRANSMUTAR_ATRITO": 0.8,
            "TRANSMUTAR_RASTRO": 0.8,
        },
    }

    _MAPA_NATURAL = {
        "Sprites/Fase1.png": "VORTICE",
        "Sprites/Fase2.png": "PRISAO",
        "Sprites/Fase3.png": "MIASMA",
        "Sprites/Fase4.png": "DESCARGA_ELETRICA",
        "Sprites/Fase6.png": "CAMINHO_ESPINHOS",
        "Sprites/Fase7.png": "LASER_SOBRECARGA",
        "Sprites/Fase9.png": "PRAGA_RATOS",
    }

    def __init__(self, seed: Optional[int] = None) -> None:
        self.rede = RedeInstintoUmbra()
        self.random = random.Random(seed)
        self._ultima_acao: Optional[str] = None
        self._ultima_intencao: Optional[str] = None
        self._ultimo_plano: Optional[PlanoUmbra] = None

    def perceber(
        self,
        agora: int,
        boss_pos: Tuple[float, float],
        player_pos: Tuple[float, float],
        historico_player: Sequence[Tuple[float, float]],
        disparos_player: Sequence[object],
        estado_ia: MutableMapping[str, object],
        config_boss: Mapping[str, object],
    ) -> PercepcaoUmbra:
        bx, by = boss_pos
        px, py = player_pos
        vx, vy = 0.0, 0.0
        if historico_player and len(historico_player) >= 2:
            vx = px - historico_player[-2][0]
            vy = py - historico_player[-2][1]

        vida_atual = float(config_boss.get("vida_atual", 1) or 1)
        vida_max = float(config_boss.get("vida_max", max(vida_atual, 1)) or 1)
        distancia = math.hypot(px - bx, py - by)
        margem = 90.0
        largura = float(config_boss.get("largura_mapa", 1360) or 1360)
        altura = float(config_boss.get("altura_mapa", 768) or 768)
        player_na_borda = float(px < margem or px > largura - margem or py < margem or py > altura - margem)
        player_no_canto = float(
            (px < margem or px > largura - margem) and
            (py < margem or py > altura - margem)
        )
        player_parado = 0.0
        if historico_player and len(historico_player) >= 10:
            inicio = historico_player[-10]
            player_parado = float(math.hypot(px - inicio[0], py - inicio[1]) < 28)

        armadilhas = {}
        for chave in (
            "vortice_ativo", "prisao_ativa", "caminho_espinhos", "laser_ativo",
            "descarga_eletrica", "miasma_ativo", "praga_ratos", "parede_ativa",
        ):
            armadilhas[chave] = 1.0 if estado_ia.get(chave) else 0.0

        resumo = dict(estado_ia.get("_resumo_predatorio", {}) or {})
        modificadores = list(estado_ia.get("_modificadores_umbra", []) or [])

        return PercepcaoUmbra(
            agora=agora,
            boss_pos=(bx, by),
            player_pos=(px, py),
            player_vel=(vx, vy),
            vida_umbra=vida_atual,
            vida_umbra_max=vida_max,
            mapa_atual=str(config_boss.get("mapa_atual", "")),
            sob_fogo=min(1.0, len(disparos_player) / 8.0),
            armadilhas_ativas=armadilhas,
            resumo_predatorio=resumo,
            modificadores=modificadores,
            distancia=distancia,
            vida_perc=_clamp(vida_atual / max(1.0, vida_max)),
            player_no_canto=player_no_canto,
            player_na_borda=player_na_borda,
            player_parado=player_parado,
            player_previsivel=float(resumo.get("previsibilidade", 0.0) or 0.0),
        )

    def _features(self, p: PercepcaoUmbra) -> Dict[str, float]:
        armadilhas = sum(p.armadilhas_ativas.values()) / max(1, len(p.armadilhas_ativas))
        resumo = p.resumo_predatorio
        return {
            "vida_baixa": _clamp((0.65 - p.vida_perc) / 0.65),
            "vida_critica": _clamp((0.32 - p.vida_perc) / 0.32),
            "distancia_curta": _clamp((360.0 - p.distancia) / 360.0),
            "distancia_longa": _clamp((p.distancia - 460.0) / 540.0),
            "sob_fogo": _clamp(p.sob_fogo),
            "player_canto": p.player_no_canto,
            "player_borda": p.player_na_borda,
            "player_parado": p.player_parado,
            "previsibilidade": _clamp(float(resumo.get("previsibilidade", p.player_previsivel) or 0.0)),
            "dependencia_dash": _clamp(float(resumo.get("dependencia_dash", 0.0) or 0.0)),
            "dependencia_orbe": _clamp(float(resumo.get("dependencia_orbe", 0.0) or 0.0)),
            "agressividade": _clamp(float(resumo.get("agressividade", 0.0) or 0.0)),
            "adaptabilidade": _clamp(float(resumo.get("adaptabilidade", 0.0) or 0.0)),
            "armadilhas_ativas": _clamp(armadilhas),
        }

    def escolher(
        self,
        percepcao: PercepcaoUmbra,
        acoes_disponiveis: Iterable[str],
        decisao_base: Optional[str] = None,
    ) -> PlanoUmbra:
        disponiveis = list(dict.fromkeys(acoes_disponiveis))
        if not disponiveis:
            disponiveis = ["ATAQUE"]

        self.rede.decair_memoria()
        features = self._features(percepcao)
        intencoes = self.rede.avaliar(features)
        intencao = max(intencoes, key=intencoes.get)
        confianca_intencao = intencoes[intencao]

        pesos: Dict[str, float] = {acao: 0.0 for acao in disponiveis}
        for acao in disponiveis:
            pesos[acao] += self._INTENCAO_ACOES.get(intencao, {}).get(acao, 0.0)

            mapa_natural = self._MAPA_NATURAL.get(percepcao.mapa_atual)
            if acao == mapa_natural:
                pesos[acao] += 0.45

            if acao == decisao_base:
                pesos[acao] += 0.35

            if self._ultima_acao == acao:
                pesos[acao] -= 0.35

        # Ajustes humanos: sobrevivencia e pressao tem prioridade situacional clara.
        if percepcao.vida_perc < 0.35 and "SIFON" in pesos:
            pesos["SIFON"] += 1.6
        if percepcao.vida_perc < 0.25 and "SIFON" in pesos:
            pesos["SIFON"] += 0.9
        if percepcao.sob_fogo > 0.0 and "TELEPORTE" in pesos:
            pesos["TELEPORTE"] += 0.35 + percepcao.sob_fogo * 0.35
        if percepcao.player_no_canto and "VORTICE" in pesos:
            pesos["VORTICE"] += 0.45
        if percepcao.player_parado and "CAMINHO_ESPINHOS" in pesos:
            pesos["CAMINHO_ESPINHOS"] += 0.55
        if percepcao.player_previsivel > 0.45 and "LASER_SOBRECARGA" in pesos:
            pesos["LASER_SOBRECARGA"] += percepcao.player_previsivel * 0.55

        if decisao_base in pesos and max(pesos.values()) - pesos[decisao_base] < 0.18:
            acao = decisao_base
        else:
            acao = max(pesos, key=pesos.get)

        normalizados = _normalizar(pesos)
        ordenados = sorted(normalizados.items(), key=lambda item: item[1], reverse=True)
        segundo = ordenados[1][1] if len(ordenados) > 1 else 0.0
        confianca = _clamp((ordenados[0][1] - segundo) * 0.65 + confianca_intencao * 0.35)
        tracos = [
            f"intencao:{intencao}",
            f"vida:{percepcao.vida_perc:.2f}",
            f"dist:{percepcao.distancia:.0f}",
        ]
        if decisao_base and decisao_base != acao:
            tracos.append(f"dqn:{decisao_base}")

        self._ultima_acao = acao
        self._ultima_intencao = intencao
        self.rede.reforcar(intencao, 0.015)
        plano = PlanoUmbra(acao=acao, intencao=intencao, confianca=round(confianca, 3), pesos=normalizados, tracos=tracos)
        self._ultimo_plano = plano
        return plano

    def ajustar_movimento(
        self,
        decisao_base: str,
        percepcao: PercepcaoUmbra,
        estrategias: Iterable[str],
    ) -> PlanoUmbra:
        disponiveis = list(dict.fromkeys(estrategias))
        if not disponiveis:
            disponiveis = ACOES_MOVIMENTO[:]

        features = self._features(percepcao)
        intencoes = self.rede.avaliar(features)
        intencao = max(intencoes, key=intencoes.get)
        pesos = {acao: 0.0 for acao in disponiveis}
        for acao in disponiveis:
            pesos[acao] += self._INTENCAO_ACOES.get(intencao, {}).get(acao, 0.0)
            if acao == decisao_base:
                pesos[acao] += 0.5
        if percepcao.vida_perc < 0.45 and "FUGIR" in pesos:
            pesos["FUGIR"] += 0.5
        if percepcao.player_na_borda and "CERCAR" in pesos:
            pesos["CERCAR"] += 0.45
        if percepcao.distancia > 520 and "INTERCEPTAR" in pesos:
            pesos["INTERCEPTAR"] += 0.35
        if percepcao.distancia < 260 and "ORBITAR" in pesos:
            pesos["ORBITAR"] += 0.25

        acao = max(pesos, key=pesos.get)
        normalizados = _normalizar(pesos)
        return PlanoUmbra(
            acao=acao,
            intencao=intencao,
            confianca=round(max(normalizados.values()) if normalizados else 0.0, 3),
            pesos=normalizados,
            tracos=[f"mov:{intencao}", f"base:{decisao_base}"],
        )


def obter_cortex(estado_ia: MutableMapping[str, object]) -> UmbraCortex:
    cortex = estado_ia.get("_umbra_cortex")
    if not isinstance(cortex, UmbraCortex):
        cortex = UmbraCortex()
        estado_ia["_umbra_cortex"] = cortex
    return cortex


def registrar_plano_no_estado(estado_ia: MutableMapping[str, object], plano: PlanoUmbra) -> None:
    estado_ia["mente_umbra"] = {
        "acao": plano.acao,
        "intencao": plano.intencao,
        "confianca": plano.confianca,
        "tracos": list(plano.tracos),
    }
    estado_ia["ultimos_pesos_calculados"] = dict(plano.pesos)
    estado_ia["estado_composto"] = f"cortex_{plano.intencao}_{plano.acao}".lower()
