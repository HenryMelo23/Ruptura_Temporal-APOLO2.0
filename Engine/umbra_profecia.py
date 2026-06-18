"""
umbra_profecia.py — Sistema de Profecia Falsificável da Umbra

A Umbra cria previsões internas sobre o próximo comportamento do jogador.
Se acerta, ganha leve vantagem tática. Se erra, perde a oportunidade.
NÃO altera dano, vida ou velocidade. NÃO lê input diretamente.
"""

import math
import random

DEBUG_PROFECIA_UMBRA = False

def _log_prof(msg):
    pass


TIPOS_PROFECIA = [
    "VAI_USAR_DASH",
    "VAI_BUSCAR_ORBE",
    "VAI_FUGIR_ESQUERDA",
    "VAI_FUGIR_DIREITA",
    "VAI_IR_PARA_CANTO",
    "VAI_ATACAR_DE_LONGE",
    "VAI_APROXIMAR_AGRESSIVO",
    "VAI_FICAR_PARADO_ESPERANDO",
]

_COOLDOWN_MS = 4000
_CONFIANCA_MIN = 0.60
_JANELA_MIN = 1000
_JANELA_MAX = 2500


class ProfeciaUmbra:
    """Motor de previsão falsificável."""

    def __init__(self):
        self.profecia_ativa = None
        self.ultimo_tempo = 0
        # Multiplicador de confiança por tipo (diminui se Umbra erra muito)
        self.fator_tipo = {t: 1.0 for t in TIPOS_PROFECIA}
        self.stats = {
            "criadas": 0, "confirmadas": 0,
            "quebradas": 0, "expiradas": 0, "por_tipo": {},
        }
        # Bonus/penalidade tática resultante
        self.bonus_ativo = None

    # ==============================================================
    # CRIAÇÃO
    # ==============================================================
    def criar_profecia(self, ctx, resumo):
        """
        Tenta criar uma profecia. Retorna a profecia criada ou None.
        ctx:    dict com agora, player_pos, boss_pos, player_vel, vida_perc, dist
        resumo: output de dossie.obter_resumo_predatorio()
        """
        agora = ctx.get("agora", 0)

        if self.profecia_ativa is not None:
            return None
        if agora - self.ultimo_tempo < _COOLDOWN_MS:
            return None

        candidatos = self._gerar_candidatos(ctx, resumo)
        if not candidatos:
            return None

        candidatos.sort(key=lambda c: c[1], reverse=True)
        tipo, conf = candidatos[0]

        # Aplica fator de histórico do tipo
        conf *= self.fator_tipo.get(tipo, 1.0)
        if conf < _CONFIANCA_MIN:
            return None

        conf = round(min(1.0, conf), 3)
        # Janela inversamente proporcional à confiança
        frac = max(0.0, min(1.0, (conf - 0.6) / 0.4))
        janela = int(_JANELA_MAX - frac * (_JANELA_MAX - _JANELA_MIN))

        self.profecia_ativa = {
            "tipo": tipo,
            "confianca": conf,
            "tempo_criacao": agora,
            "janela_validade_ms": janela,
            "ctx_ini": {
                "player_pos": ctx.get("player_pos"),
                "dist": ctx.get("dist", 0),
            },
            "foi_confirmada": False,
            "foi_quebrada": False,
            "expirou": False,
        }
        self.ultimo_tempo = agora
        self.stats["criadas"] += 1
        st = self.stats["por_tipo"].setdefault(
            tipo, {"criadas": 0, "confirmadas": 0, "quebradas": 0, "expiradas": 0}
        )
        st["criadas"] += 1
        _log_prof(f"CRIADA: {tipo} conf={conf} janela={janela}ms")
        return self.profecia_ativa

    # ==============================================================
    # AVALIAÇÃO
    # ==============================================================
    def avaliar_profecia(self, ctx):
        """
        Avalia a profecia ativa. Retorna 'confirmada', 'quebrada', 'expirada' ou None.
        """
        if self.profecia_ativa is None:
            return None

        prof = self.profecia_ativa
        agora = ctx.get("agora", 0)
        elapsed = agora - prof["tempo_criacao"]

        # Expiração
        if elapsed > prof["janela_validade_ms"]:
            return self._finalizar("expirada", prof, agora)

        resultado = self._verificar(prof, ctx, elapsed)
        if resultado:
            return self._finalizar(resultado, prof, agora)

        return None  # Ainda na janela

    def _finalizar(self, resultado, prof, agora):
        tipo = prof["tipo"]
        self.stats[resultado + "s"] += 1
        st = self.stats["por_tipo"].get(tipo, {})
        st[resultado + "s"] = st.get(resultado + "s", 0) + 1

        if resultado == "confirmada":
            self.fator_tipo[tipo] = min(1.2, self.fator_tipo.get(tipo, 1.0) + 0.05)
            self.bonus_ativo = {
                "tipo": "profecia_confirmada",
                "intensidade": prof["confianca"] * 0.15,
                "expira": agora + 3000,
            }
            _log_prof(f"CONFIRMADA: {tipo} -> bonus {self.bonus_ativo['intensidade']:.3f}")
        elif resultado == "quebrada":
            self.fator_tipo[tipo] = max(0.3, self.fator_tipo.get(tipo, 1.0) - 0.10)
            self.bonus_ativo = {
                "tipo": "profecia_quebrada",
                "intensidade": -0.10,
                "expira": agora + 2000,
            }
            _log_prof(f"QUEBRADA: {tipo} -> penalidade")
        else:
            _log_prof(f"EXPIRADA: {tipo}")

        self.profecia_ativa = None
        return resultado

    # ==============================================================
    # VERIFICAÇÃO DE RESULTADO
    # ==============================================================
    def _verificar(self, prof, ctx, elapsed):
        tipo = prof["tipo"]
        px, py = ctx.get("player_pos", (0, 0))
        ini = prof["ctx_ini"]
        px_i, py_i = ini.get("player_pos", (px, py))
        pct_janela = elapsed / max(1, prof["janela_validade_ms"])

        if tipo == "VAI_USAR_DASH":
            if ctx.get("dash_detectado"):
                return "confirmada"
            if pct_janela > 0.6:
                return "quebrada"

        elif tipo == "VAI_BUSCAR_ORBE":
            orbe = ctx.get("orbe_pos")
            if orbe:
                d_ini = math.hypot(px_i - orbe[0], py_i - orbe[1])
                d_now = math.hypot(px - orbe[0], py - orbe[1])
                if d_ini > 0 and d_now < d_ini * 0.5:
                    return "confirmada"
                if d_ini > 0 and d_now > d_ini * 1.3:
                    return "quebrada"

        elif tipo == "VAI_FUGIR_ESQUERDA":
            dx = px - px_i
            if dx < -60:
                return "confirmada"
            if dx > 40:
                return "quebrada"

        elif tipo == "VAI_FUGIR_DIREITA":
            dx = px - px_i
            if dx > 60:
                return "confirmada"
            if dx < -40:
                return "quebrada"

        elif tipo == "VAI_IR_PARA_CANTO":
            try:
                from Variaveis import largura_mapa, altura_mapa
            except ImportError:
                largura_mapa, altura_mapa = 1360, 768
            m = 100
            canto = (px < m or px > largura_mapa - m) and (py < m or py > altura_mapa - m)
            if canto:
                return "confirmada"
            centro = math.hypot(px - largura_mapa / 2, py - altura_mapa / 2)
            if centro < 200:
                return "quebrada"

        elif tipo == "VAI_ATACAR_DE_LONGE":
            dist = ctx.get("dist", 500)
            if dist > 350 and ctx.get("tiro_disparado"):
                return "confirmada"
            if dist < 200:
                return "quebrada"

        elif tipo == "VAI_APROXIMAR_AGRESSIVO":
            dist = ctx.get("dist", 500)
            d_ini = ini.get("dist", 500)
            if d_ini > 0 and dist < d_ini * 0.5:
                return "confirmada"
            if d_ini > 0 and dist > d_ini * 1.2:
                return "quebrada"

        elif tipo == "VAI_FICAR_PARADO_ESPERANDO":
            desloc = math.hypot(px - px_i, py - py_i)
            if desloc < 15 and pct_janela > 0.4:
                return "confirmada"
            if desloc > 80:
                return "quebrada"

        return None

    # ==============================================================
    # GERAÇÃO DE CANDIDATOS
    # ==============================================================
    def _gerar_candidatos(self, ctx, r):
        """Retorna [(tipo, confianca), ...] baseado no contexto e resumo."""
        cands = []
        prev = r.get("previsibilidade", 0)
        base = 0.3 + prev * 0.5  # 0.3 a 0.8

        medo = r.get("medo", 0)
        agress = r.get("agressividade", 0)
        dep_dash = r.get("dependencia_dash", 0)
        dep_orbe = r.get("dependencia_orbe", 0)
        tend_canto = r.get("tendencia_canto", 0)
        adapt = r.get("adaptabilidade", 0)
        vx, vy = ctx.get("player_vel", (0, 0))
        vida = ctx.get("vida_perc", 1.0)
        dist = ctx.get("dist", 500)
        px, py = ctx.get("player_pos", (0, 0))
        bx, by = ctx.get("boss_pos", (0, 0))

        # VAI_USAR_DASH
        if dep_dash > 0.3 and vida < 0.5:
            cands.append(("VAI_USAR_DASH", base * (0.5 + dep_dash * 0.5)))

        # VAI_BUSCAR_ORBE
        if dep_orbe > 0.3 and ctx.get("orbe_pos") is not None:
            cands.append(("VAI_BUSCAR_ORBE", base * (0.5 + dep_orbe * 0.5)))

        # VAI_FUGIR (precisa estar com medo e já se movendo nessa direção)
        if medo > 0.4:
            if vx < -2:
                cands.append(("VAI_FUGIR_ESQUERDA", base * (0.4 + medo * 0.4)))
            elif vx > 2:
                cands.append(("VAI_FUGIR_DIREITA", base * (0.4 + medo * 0.4)))

        # VAI_IR_PARA_CANTO
        if tend_canto > 0.4:
            cands.append(("VAI_IR_PARA_CANTO", base * (0.4 + tend_canto * 0.4)))

        # VAI_ATACAR_DE_LONGE
        if dist > 400 and agress > 0.3:
            cands.append(("VAI_ATACAR_DE_LONGE", base * (0.3 + agress * 0.3) * 0.8))

        # VAI_APROXIMAR_AGRESSIVO
        if dist > 200 and agress > 0.5 and adapt < 0.7:
            dx_b = bx - px
            toward = (dx_b > 0 and vx > 1) or (dx_b < 0 and vx < -1)
            if toward:
                cands.append(("VAI_APROXIMAR_AGRESSIVO", base * (0.4 + agress * 0.4)))

        # VAI_FICAR_PARADO_ESPERANDO
        speed = math.hypot(vx, vy)
        if speed < 1.0 and prev > 0.3:
            cands.append(("VAI_FICAR_PARADO_ESPERANDO", base * 0.5))

        return cands

    # ==============================================================
    # CONSULTA DE BONUS TÁTICO
    # ==============================================================
    def obter_bonus_tatico(self, agora):
        """Retorna dict com bonus/penalidade ativa, ou None."""
        if self.bonus_ativo is None:
            return None
        if agora > self.bonus_ativo["expira"]:
            self.bonus_ativo = None
            return None
        return self.bonus_ativo

    def obter_stats(self):
        return dict(self.stats)
