import pygame
import math
import random
from Variaveis import espacamento, largura_mapa, altura_mapa, largura_personagem, altura_personagem, largura_boss, altura_boss
import json
import sys
import os
import json

# ============================================================
# SISTEMA ADAPTATIVO DA UMBRA — FLAGS DE CONTROLE
# ============================================================
ADAPTACAO_UMBRA_ATIVA = True
DEBUG_ADAPTACAO_UMBRA = False

def _log_adapt(msg):
    pass

def _tem_mod(estado_ia, mod_id):
    """Retorna intensidade do modificador se ativo, 0.0 caso contrário."""
    if not ADAPTACAO_UMBRA_ATIVA:
        return 0.0
    for m in estado_ia.get('_modificadores_umbra', []):
        if m['id'] == mod_id:
            return m['intensidade']
    return 0.0

def _cooldown_mod_ok(estado_ia, mod_id, cooldown_ms=3000):
    """Verifica cooldown do modificador. Marca timestamp se disponível."""
    import pygame
    agora = pygame.time.get_ticks()
    key = f'_cd_mod_{mod_id}'
    if agora - estado_ia.get(key, 0) >= cooldown_ms:
        estado_ia[key] = agora
        return True
    return False

def _carregar_mods_lazy(estado_ia):
    """Carrega modificadores do JSON uma única vez no início da luta."""
    if '_modificadores_umbra' in estado_ia:
        return
    if not ADAPTACAO_UMBRA_ATIVA:
        estado_ia['_modificadores_umbra'] = []
        return
    try:
        with open("memoria_predatoria_umbra.json", "r", encoding="utf-8") as f:
            dados = json.load(f)
        perfil = dados.get("perfil_jogador", {})
        principal = perfil.get("arquetipo_principal", "INDEFINIDO")
        secundario = perfil.get("arquetipo_secundario", "INDEFINIDO")
        confianca = perfil.get("confianca", 0.0)
        if confianca < 0.20:
            estado_ia['_modificadores_umbra'] = []
            return
        MAPA = {
            "REFUGIADO_DE_CANTO": ("CORTAR_BORDAS", 0.25),
            "DEPENDENTE_DE_DASH": ("PUNIR_DASH_PREVISIVEL", 0.20),
            "CACADOR_DE_ORBES": ("ISCA_DE_ORBE", 0.20),
            "AGRESSOR_IMPULSIVO": ("CONTRA_IMPULSO", 0.20),
            "ATIRADOR_DISTANTE": ("QUEBRAR_DISTANCIA", 0.25),
            "CORREDOR_CIRCULAR": ("QUEBRAR_ROTACAO", 0.20),
            "SOBREVIVENTE_ADAPTATIVO": ("RESPEITAR_ADAPTATIVO", 0.10),
        }
        mods = []
        if principal in MAPA:
            mid, base = MAPA[principal]
            mods.append({"id": mid, "intensidade": round(base * confianca, 3)})
        if secundario in MAPA and secundario != principal and len(mods) < 2:
            mid, base = MAPA[secundario]
            mods.append({"id": mid, "intensidade": round(base * confianca * 0.4, 3)})
        estado_ia['_modificadores_umbra'] = mods[:2]
        _log_adapt(f"Arq={principal}/{secundario} conf={confianca} → {[m['id'] for m in mods]}")
        # Carregar resumo predatório para sistema de profecia
        try:
            from umbra_dossie import DossieUmbra
            dt = DossieUmbra.__new__(DossieUmbra)
            dt.dados = dados
            from Variaveis import largura_mapa as lm, altura_mapa as am
            dt._largura_mapa = lm
            dt._altura_mapa = am
            estado_ia['_resumo_predatorio'] = dt.obter_resumo_predatorio()
        except Exception:
            estado_ia['_resumo_predatorio'] = {}
    except Exception:
        estado_ia['_modificadores_umbra'] = []
        estado_ia['_resumo_predatorio'] = {}

def _aplicar_bias_decisao(decisao, acoes, estado_ia, dist_p):
    """Aplica bias probabilístico pós-DQN. Nunca garante 100%."""
    import random
    original = decisao

    # CORTAR_BORDAS: favorecer CERCAR/INTERCEPTAR
    i = _tem_mod(estado_ia, "CORTAR_BORDAS")
    if i > 0 and decisao not in ("CERCAR", "INTERCEPTAR", "SIFON") and _cooldown_mod_ok(estado_ia, "CORTAR_BORDAS", 5000):
        if random.random() < i:
            pref = [a for a in acoes if a in ("CERCAR", "INTERCEPTAR")]
            if pref:
                decisao = random.choice(pref)

    # CONTRA_IMPULSO: favorecer recuo/teleporte quando jogador está perto
    i = _tem_mod(estado_ia, "CONTRA_IMPULSO")
    if i > 0 and dist_p < 250 and _cooldown_mod_ok(estado_ia, "CONTRA_IMPULSO", 4000):
        if random.random() < i:
            pref = [a for a in acoes if a in ("TELEPORTE", "TELEPORTE_JUKE")]
            if pref:
                decisao = random.choice(pref)

    # QUEBRAR_DISTANCIA: favorecer transmutação/teleporte quando longe
    i = _tem_mod(estado_ia, "QUEBRAR_DISTANCIA")
    if i > 0 and dist_p > 500 and _cooldown_mod_ok(estado_ia, "QUEBRAR_DISTANCIA", 6000):
        if random.random() < i:
            pref = [a for a in acoes if a.startswith("TRANSMUTAR_") or a == "TELEPORTE"]
            if pref:
                decisao = random.choice(pref)

    # QUEBRAR_ROTACAO: favorecer habilidades de área
    i = _tem_mod(estado_ia, "QUEBRAR_ROTACAO")
    if i > 0 and _cooldown_mod_ok(estado_ia, "QUEBRAR_ROTACAO", 5000):
        if random.random() < i:
            pref = [a for a in acoes if a in ("VORTICE", "PRISAO", "CAMINHO_ESPINHOS", "DESCARGA_ELETRICA")]
            if pref:
                decisao = random.choice(pref)

    # ISCA_DE_ORBE: favorecer INTERCEPTAR (posicionar no caminho do jogador)
    i = _tem_mod(estado_ia, "ISCA_DE_ORBE")
    if i > 0 and _cooldown_mod_ok(estado_ia, "ISCA_DE_ORBE", 4000):
        if random.random() < i and "INTERCEPTAR" in acoes:
            decisao = "INTERCEPTAR"

    # RESPEITAR_ADAPTATIVO: variação extra (impede hard-counter)
    i = _tem_mod(estado_ia, "RESPEITAR_ADAPTATIVO")
    if i > 0 and _cooldown_mod_ok(estado_ia, "RESPEITAR_ADAPTATIVO", 8000):
        if random.random() < i * 0.5:
            decisao = random.choice(acoes)

    if decisao != original:
        _log_adapt(f"Bias: {original} → {decisao}")
    return decisao

def _aplicar_bias_movimento(decisao, estado_ia, dist_p):
    """Aplica bias de movimento pós-DQN. Probabilístico."""
    import random
    original = decisao

    i = _tem_mod(estado_ia, "CORTAR_BORDAS")
    if i > 0 and decisao == "FUGIR" and random.random() < i * 0.6:
        decisao = "CERCAR"

    i = _tem_mod(estado_ia, "CONTRA_IMPULSO")
    if i > 0 and dist_p < 250 and decisao in ("INTERCEPTAR", "CERCAR") and random.random() < i * 0.5:
        decisao = "FUGIR"

    i = _tem_mod(estado_ia, "QUEBRAR_DISTANCIA")
    if i > 0 and dist_p > 500 and decisao in ("FUGIR", "ORBITAR") and random.random() < i * 0.6:
        decisao = "INTERCEPTAR"

    i = _tem_mod(estado_ia, "ISCA_DE_ORBE")
    if i > 0 and decisao == "FUGIR" and random.random() < i * 0.4:
        decisao = "INTERCEPTAR"

    if decisao != original:
        _log_adapt(f"Mov bias: {original} → {decisao}")
    return decisao


# ============================================================
# SISTEMA DE PROFECIA FALSIFICÁVEL
# ============================================================
def _init_profecia_lazy(estado_ia):
    """Inicializa ProfeciaUmbra no estado (uma vez por luta)."""
    if '_profecia' in estado_ia:
        return
    try:
        from umbra_profecia import ProfeciaUmbra
        estado_ia['_profecia'] = ProfeciaUmbra()
    except Exception:
        estado_ia['_profecia'] = None

def _build_ctx_profecia(agora, px, py, bx, by, dist_p, historico, estado_ia):
    """Monta contexto para o sistema de profecia."""
    vx, vy = 0.0, 0.0
    if historico and len(historico) >= 2:
        vx = px - historico[-2][0]
        vy = py - historico[-2][1]
    speed = math.hypot(vx, vy)
    return {
        'agora': agora,
        'player_pos': (px, py),
        'boss_pos': (bx, by),
        'player_vel': (vx, vy),
        'vida_perc': estado_ia.get('_vida_jogador_perc', 1.0),
        'dist': dist_p,
        'dash_detectado': speed > 15,
        'orbe_pos': estado_ia.get('_orbe_pos'),
        'tiro_disparado': estado_ia.get('_tiro_disparado', False),
    }

def _processar_profecia(agora, estado_ia, px, py, bx, by, dist_p, historico):
    """Cria/avalia profecias. Chamado em processar_ia_umbra."""
    if not ADAPTACAO_UMBRA_ATIVA:
        return
    _init_profecia_lazy(estado_ia)
    prof = estado_ia.get('_profecia')
    if prof is None:
        return

    ctx = _build_ctx_profecia(agora, px, py, bx, by, dist_p, historico, estado_ia)

    # 1. Avaliar profecia existente
    prof.avaliar_profecia(ctx)

    # 2. Tentar criar nova
    resumo = estado_ia.get('_resumo_predatorio', {})
    prof.criar_profecia(ctx, resumo)

def _aplicar_bonus_profecia(decisao, acoes, estado_ia, agora):
    """Aplica bonus/penalidade de profecia confirmada/quebrada."""
    prof = estado_ia.get('_profecia')
    if prof is None:
        return decisao
    bonus = prof.obter_bonus_tatico(agora)
    if bonus is None:
        return decisao

    original = decisao
    intensidade = bonus['intensidade']

    if bonus['tipo'] == 'profecia_confirmada' and intensidade > 0:
        # Confirmada: favorecer INTERCEPTAR (corte de rota)
        if random.random() < intensidade and 'INTERCEPTAR' in acoes:
            decisao = 'INTERCEPTAR'
    elif bonus['tipo'] == 'profecia_quebrada' and intensidade < 0:
        # Quebrada: decisão mais aleatória (Umbra hesita)
        if random.random() < abs(intensidade):
            decisao = random.choice(acoes)

    if decisao != original:
        _log_adapt(f"Profecia bonus: {original} → {decisao} ({bonus['tipo']})")
    return decisao


class MemoriaEvolutivaUmbra:
    """Memoria leve da Umbra para o pacote PLAYER.

    Mantem a mesma interface da versao DQN, mas nao importa PyTorch e nao salva
    pesos .pt. A decisao mistura regras taticas simples, exploracao e tendencias
    bayesianas do jogador para preservar uma Umbra reativa em builds leves.
    """

    def __init__(self, arquivo="saves/memoria_umbra_player.json"):
        self.arquivo = arquivo
        self.exploracao = 0.22
        self.input_size = 24
        self.acoes_base = [
            "FUGIR", "INTERCEPTAR", "ORBITAR", "CERCAR", "ATAQUE", "SIFON", "TELEPORTE",
            "TRANSMUTAR_VORTICE", "TRANSMUTAR_GRAVIDADE", "TRANSMUTAR_NECROSE",
            "TRANSMUTAR_RESSONANCIA", "TRANSMUTAR_HEMORRAGIA", "TRANSMUTAR_ATRITO",
            "TRANSMUTAR_RASTRO", "VORTICE", "PRISAO", "MIASMA", "DESCARGA_ELETRICA",
            "PRAGA_RATOS", "LASER_SOBRECARGA", "CAMINHO_ESPINHOS", "NENHUMA"
        ]
        self.output_size = len(self.acoes_base)
        self.tendencias = {"TOTAL": 0, "ESQUERDA": 0, "DIREITA": 0, "CIMA": 0, "BAIXO": 0}
        self.ultimo_estado_tensor = None
        self.ultima_acao_idx = None
        self.recompensas = {acao: 0.0 for acao in self.acoes_base}
        self._carregar()

    def _carregar(self):
        if os.path.exists(self.arquivo):
            try:
                with open(self.arquivo, "r") as f:
                    dados = json.load(f)
                if isinstance(dados.get("recompensas"), dict):
                    for acao, valor in dados["recompensas"].items():
                        if acao in self.recompensas:
                            self.recompensas[acao] = float(valor)
                if isinstance(dados.get("exploracao"), (int, float)):
                    self.exploracao = max(0.05, min(0.6, float(dados["exploracao"])))
            except Exception:
                pass
        if os.path.exists("saves/tendencias_umbra.json"):
            try:
                with open("saves/tendencias_umbra.json", "r") as f:
                    self.tendencias = json.load(f)
            except Exception:
                pass

    def salvar(self):
        os.makedirs(os.path.dirname(self.arquivo) or ".", exist_ok=True)
        with open(self.arquivo, "w") as f:
            json.dump({
                "modo": "player_sem_torch",
                "exploracao": self.exploracao,
                "recompensas": self.recompensas,
            }, f, indent=4)
        with open("saves/tendencias_umbra.json", "w") as f:
            json.dump(self.tendencias, f)

    def registrar_esquiva_player(self, vx, vy):
        t = self.tendencias
        if abs(vx) > 0.5 or abs(vy) > 0.5:
            if vx > 1:
                t["DIREITA"] += 1
            elif vx < -1:
                t["ESQUERDA"] += 1
            if vy > 1:
                t["BAIXO"] += 1
            elif vy < -1:
                t["CIMA"] += 1
            t["TOTAL"] += 1

    def calcular_bias_bayesiano(self):
        t = self.tendencias
        total = max(1, t.get("TOTAL", 0))
        bias_x = (t.get("DIREITA", 0) - t.get("ESQUERDA", 0)) / total
        bias_y = (t.get("BAIXO", 0) - t.get("CIMA", 0)) / total
        return bias_x, bias_y

    def discretizar_estado(self, vida_perc, dist_player, sob_fogo, historico_player, mapa_atual="Fase_Base", player_pos=None, boss_pos=None, armadilhas=None, ameaca_vec=(0.0, 0.0)):
        feat_vida = float(vida_perc)
        feat_dist = float(dist_player) / 2000.0
        feat_fogo = 1.0 if sob_fogo else 0.0

        vx_p, vy_p = 0.0, 0.0
        if historico_player and len(historico_player) >= 3:
            p1, p3 = historico_player[-3], historico_player[-1]
            vx_p = (p3[0] - p1[0]) / 30.0
            vy_p = (p3[1] - p1[1]) / 30.0

        feat_vx = max(-1.0, min(1.0, vx_p))
        feat_vy = max(-1.0, min(1.0, vy_p))
        dx, dy = 0.0, 0.0
        p_borda_x, p_borda_y, b_borda_x, b_borda_y = 1.0, 1.0, 1.0, 1.0
        p_canto, p_dist_centro = 0.0, 0.0

        if player_pos and boss_pos:
            px = player_pos[0] if isinstance(player_pos, (tuple, list)) else player_pos.get("x", 0)
            py = player_pos[1] if isinstance(player_pos, (tuple, list)) else player_pos.get("y", 0)
            bx = boss_pos[0] if isinstance(boss_pos, (tuple, list)) else boss_pos.get("x", 0)
            by = boss_pos[1] if isinstance(boss_pos, (tuple, list)) else boss_pos.get("y", 0)
            dx = (bx - px) / 1000.0
            dy = (by - py) / 1000.0
            meio_w, meio_h = largura_mapa / 2.0, altura_mapa / 2.0
            p_borda_x = min(px, largura_mapa - px) / max(1.0, meio_w)
            p_borda_y = min(py, altura_mapa - py) / max(1.0, meio_h)
            b_borda_x = min(bx, largura_mapa - bx) / max(1.0, meio_w)
            b_borda_y = min(by, altura_mapa - by) / max(1.0, meio_h)
            if p_borda_x < 0.25 and p_borda_y < 0.25:
                p_canto = 1.0
            p_dist_centro = math.hypot(px - meio_w, py - meio_h) / max(1.0, math.hypot(meio_w, meio_h))

        feat_armadilhas = [0.0] * 8
        if armadilhas:
            keys = ["vortice_ativo", "prisao_ativa", "caminho_espinhos", "laser_ativo", "descarga_eletrica", "miasma_ativo", "praga_ratos", "parede_ativa"]
            for i, k in enumerate(keys):
                if armadilhas.get(k):
                    feat_armadilhas[i] = 1.0

        map_val = 0.0
        if mapa_atual:
            map_str = str(mapa_atual).lower()
            if "fase" in map_str:
                num = "".join(filter(str.isdigit, map_str))
                if num:
                    map_val = float(num) / 10.0

        return {
            "vida": feat_vida,
            "dist": feat_dist,
            "sob_fogo": feat_fogo,
            "vx": feat_vx,
            "vy": feat_vy,
            "dx": dx,
            "dy": dy,
            "armadilhas": feat_armadilhas,
            "mapa": map_val,
            "ameaca": (ameaca_vec[0], ameaca_vec[1]),
            "player_borda_x": p_borda_x,
            "player_borda_y": p_borda_y,
            "boss_borda_x": b_borda_x,
            "boss_borda_y": b_borda_y,
            "player_canto": p_canto,
            "player_dist_centro": p_dist_centro,
        }

    def _score_acao(self, acao, estado):
        vida = estado.get("vida", 1.0)
        dist = estado.get("dist", 0.5)
        sob_fogo = estado.get("sob_fogo", 0.0)
        canto = estado.get("player_canto", 0.0)
        boss_borda = min(estado.get("boss_borda_x", 1.0), estado.get("boss_borda_y", 1.0))
        score = self.recompensas.get(acao, 0.0) * 0.15

        if acao == "ATAQUE":
            score += 2.0 + min(1.5, dist * 2.0)
        elif acao in ("INTERCEPTAR", "CERCAR"):
            score += 1.0 + canto * 2.0 + (0.6 if dist > 0.35 else 0.0)
        elif acao == "ORBITAR":
            score += 0.8 + (0.8 if 0.18 <= dist <= 0.55 else 0.0)
        elif acao == "FUGIR":
            score += (1.6 if dist < 0.16 else 0.0) + (1.0 if sob_fogo else 0.0)
        elif acao == "TELEPORTE":
            score += (2.0 if dist < 0.20 or sob_fogo else 0.5)
        elif acao == "TELEPORTE_JUKE":
            score += 1.0 + (0.8 if sob_fogo else 0.0)
        elif acao == "SIFON":
            score += 3.0 if vida < 0.55 else -1.0
        elif acao.startswith("TRANSMUTAR_"):
            score += 1.4 + min(1.0, sob_fogo)
        elif acao in ("VORTICE", "PRISAO", "MIASMA", "DESCARGA_ELETRICA", "CAMINHO_ESPINHOS", "LASER_SOBRECARGA", "PRAGA_RATOS"):
            score += 1.5 + canto + (0.4 if boss_borda > 0.25 else 0.0)

        return score + random.uniform(-0.25, 0.25)

    def decidir(self, estado_tensor, acoes_disponiveis):
        if random.random() < self.exploracao:
            acao_escolhida = random.choice(acoes_disponiveis)
            self.ultima_acao_idx = self.acoes_base.index(acao_escolhida) if acao_escolhida in self.acoes_base else 0
            self.ultimo_estado_tensor = estado_tensor
            return acao_escolhida

        best_action = max(acoes_disponiveis, key=lambda acao: self._score_acao(acao, estado_tensor))
        self.ultima_acao_idx = self.acoes_base.index(best_action) if best_action in self.acoes_base else 0
        self.ultimo_estado_tensor = estado_tensor
        return best_action

    def treinar(self, recompensa, prioridade=False):
        if self.ultima_acao_idx is None:
            return
        acao = self.acoes_base[self.ultima_acao_idx]
        peso = 0.08 if prioridade else 0.035
        atual = self.recompensas.get(acao, 0.0)
        self.recompensas[acao] = atual + peso * (float(recompensa) - atual)


def aplicar_inteligencia_q_ao_grafo(pesos, estado_ia, memoria, vida_perc, dist_p, sob_fogo, historico):
    estado_tensor = memoria.discretizar_estado(vida_perc, dist_p, sob_fogo, historico, player_pos=None, boss_pos=None, armadilhas=estado_ia)
    for acao in pesos.keys():
        if acao in memoria.acoes_base:
            pesos[acao] += memoria._score_acao(acao, estado_tensor)
    return pesos

def calcular_distancia(p1, p2):
    r"""
    Calcula a distância euclidiana: $d = \sqrt{(x_2-x_1)^2 + (y_2-y_1)^2}$
    """
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

def calcular_poh(player_pos, boss_pos, historico_player, confianca_ia):
    if len(historico_player) < 60: return 0
    # Vetores de estabilidade
    p_ini, p_mid, p_end = historico_player[0], historico_player[30], historico_player[-1]
    v1 = (p_mid[0] - p_ini[0], p_mid[1] - p_ini[1])
    v2 = (p_end[0] - p_mid[0], p_end[1] - p_mid[1])
    
    estabilidade = 1.0 if (abs(v1[0]-v2[0]) < 5 and abs(v1[1]-v2[1]) < 5) else 0.5
    fator_dist = max(0.3, 1.0 - (calcular_distancia(player_pos, boss_pos) / 1500))
    
    return confianca_ia * estabilidade * fator_dist

def node_ataque_direcionado(agora, estado_ia, bx, by, px, py, historico_player, memoria):
    # PUNIR_DASH_PREVISIVEL: atrasa levemente ataques para pegar fim do dash
    intervalo_base = estado_ia.get('intervalo', 1250)
    i_dash = _tem_mod(estado_ia, "PUNIR_DASH_PREVISIVEL")
    if i_dash > 0 and _cooldown_mod_ok(estado_ia, "PUNIR_DASH_PREVISIVEL", 6000):
        intervalo_base += int(200 * i_dash)  # +40~50ms extra (sutil)
        _log_adapt(f"PUNIR_DASH: intervalo {estado_ia.get('intervalo', 1250)} → {intervalo_base}")
    if agora - estado_ia.get('ultimo_attack', 0) >= intervalo_base:
        centro_bx = bx + (largura_boss // 2)
        centro_by = by + (altura_boss // 2)
        centro_px = px + (largura_personagem // 2)
        centro_py = py + (altura_personagem // 2)
        
        distancia = math.hypot(centro_px - centro_bx, centro_py - centro_by)
        vel_projetil = 11  # Projétil mais veloz
        tempo_voo = distancia / vel_projetil
        
        # Detecta estático e canto
        parado = len(historico_player) >= 5 and all(math.hypot(p[0]-px, p[1]-py) < 4 for p in historico_player[-5:])
        no_canto = px < 80 or px > largura_mapa - 120 or py < 80 or py > altura_mapa - 120

        if parado:
            # Alvo imóvel: tiro 100% direto ao centro, sem ruído
            alvo_x, alvo_y = centro_px, centro_py
        else:
            # Usa velocidade real dos últimos 2 frames como delta calibrado
            if len(historico_player) >= 2:
                vx_real = (centro_px - (historico_player[-2][0] + largura_personagem // 2))
                vy_real = (centro_py - (historico_player[-2][1] + altura_personagem // 2))
            else:
                vx_real, vy_real = 0.0, 0.0
            
            # Lead proporcional: menos lead em distâncias grandes (evita over-shoot)
            fator_lead = max(0.55, 1.0 - (distancia / 1800.0))

            # Se perto de canto, reduz lead para n atirar na parede
            if no_canto:
                fator_lead *= 0.5

            alvo_x = centro_px + vx_real * tempo_voo * fator_lead
            alvo_y = centro_py + vy_real * tempo_voo * fator_lead
            alvo_x = max(50, min(largura_mapa - 50, alvo_x))
            alvo_y = max(50, min(altura_mapa - 50, alvo_y))

        angulo = math.atan2(alvo_y - centro_by, alvo_x - centro_bx)
        
        estado_ia['projeteis'].append({
            "rect": pygame.Rect(centro_bx - 6, centro_by - 6, 12, 12),
            "angulo": angulo,
            "velocidade": vel_projetil,
            "tipo": "comum"
        })
        estado_ia['ultimo_attack'] = agora


def node_caminho_espinhos(agora, estado_ia, bx, by, px, py, historico_player):
    """Padrão A (X): 4 raios diagonais do centro. Padrão B (H3): 3 linhas horizontais.
    Toque = stun 4s + 2 tiros rápidos na Umbra."""
    centro_bx = bx + (largura_boss // 2)
    centro_by = by + (altura_boss // 2)

    padrao = estado_ia.get('espinho_padrao_ultimo', 'B')
    proximo = 'A' if padrao == 'B' else 'B'
    estado_ia['espinho_padrao_ultimo'] = proximo

    if proximo == 'A':
        raios = []
        for ang_base in [math.pi*0.25, math.pi*0.75, math.pi*1.25, math.pi*1.75]:
            raios.append({'origem': (centro_bx, centro_by), 'angulo': ang_base, 'comprimento': 1200})
        estado_ia['caminho_espinhos'] = {
            'padrao': 'X', 'raios': raios, 'largura_maxima': 90,
            'tempo_inicio': agora, 'fase': 'crescimento',
            'duracao_crescimento': 1800, 'duracao_expansao': 1600,
            'ultimo_espinho_hit': 0
        }
    else:
        linhas = []
        for frac in [0.25, 0.50, 0.75]:
            y_linha = int(altura_mapa * frac)
            linhas.append({'origem': (0, y_linha), 'angulo': 0, 'comprimento': largura_mapa})
        estado_ia['caminho_espinhos'] = {
            'padrao': 'H3', 'raios': linhas, 'largura_maxima': 80,
            'tempo_inicio': agora, 'fase': 'crescimento',
            'duracao_crescimento': 1400, 'duracao_expansao': 1600,
            'ultimo_espinho_hit': 0
        }

    estado_ia['ultimo_espinhos'] = agora

# --- NÓDULOS DE PENSAMENTO (AÇÕES DO GRAFO) ---

def node_furia(agora, estado_ia, hitbox_centro, centro_mapa, boss_pos):
    """Nódulo de ataque em espiral 360."""
    dist_ao_centro = calcular_distancia(centro_mapa, (boss_pos['x'], boss_pos['y']))
    
    if estado_ia['furia_fase'] == "caminhando":
        if dist_ao_centro > 15:
            estado_ia['f_fuga_x'] = (centro_mapa[0] - boss_pos['x']) / dist_ao_centro * 5
            estado_ia['f_fuga_y'] = (centro_mapa[1] - boss_pos['y']) / dist_ao_centro * 5
        else:
            estado_ia['furia_fase'] = "espiral"
            estado_ia['angulo_furia'] = 0
    elif estado_ia['furia_fase'] == "espiral":
        estado_ia['projeteis'].append({
            "rect": pygame.Rect(hitbox_centro[0], hitbox_centro[1], 35, 35),
            "angulo": estado_ia['angulo_furia'], "velocidade": 4.0, "tipo": "furia"
        })
        estado_ia['angulo_furia'] += 0.15
        if estado_ia['angulo_furia'] >= 2 * math.pi:
            estado_ia['furia_fase'] = "espera"
            estado_ia['ultimo_furia'] = agora

def node_sifon(agora, estado_ia, boss_pos, centro_mapa):
    """
    Nódulo de Estase e Cura: O Boss torna-se o epicentro do mapa.
    """
    # 1. CÁLCULO DE DESLOCAMENTO AO CENTRO
    dx = centro_mapa[0] - boss_pos['x']
    dy = centro_mapa[1] - boss_pos['y']
    dist_ao_centro = math.hypot(dx, dy)

    # Se ainda não chegou ao centro, move-se rapidamente para lá
    if dist_ao_centro > 5:
        estado_ia['f_fuga_x'] = (dx / dist_ao_centro) * 8
        estado_ia['f_fuga_y'] = (dy / dist_ao_centro) * 8
    else:
        # Chegou ao centro: Ancoragem absoluta
        estado_ia['f_fuga_x'], estado_ia['f_fuga_y'] = 0, 0
        
    # 2. GESTÃO DO TEMPO DE ATIVAÇÃO (4 SEGUNDOS)
    # Verificamos se o tempo de duração expirou
    if agora - estado_ia.get('ultimo_parede', 0) > 6000:
        estado_ia['parede_ativa'] = False
        # O SEGREDO: O cooldown começa a contar AGORA
        estado_ia['ultimo_sifon_fim'] = agora

def node_teleporte(agora, estado_ia, boss_pos, player_pos, historico_player, tipo="fuga"):
    """
    Nódulo de Translocação Visionário: Substitui o acaso por intenção tática.
    """
    bx, by = boss_pos['x'], boss_pos['y']
    px, py = player_pos[0], player_pos[1]
    
    if tipo == "fuga":
        # ESTRATÉGIA DE MAXIMIZAÇÃO DE DISTÂNCIA
        cantos = [(150, 150), (1150, 150), (150, 620), (1150, 620)]
        alvo_x, alvo_y = max(cantos, key=lambda c: math.hypot(c[0] - px, c[1] - py))
    else:
        # ESTRATÉGIA DE INTERCEPTAÇÃO PREDITIVA
        # Se houver histórico, projeta o salto à frente do seu vetor de movimento
        if len(historico_player) >= 2:
            vx = px - historico_player[-2][0]
            vy = py - historico_player[-2][1]
            alvo_x = px + (vx * 25) # Intercepta 25 frames à frente
            alvo_y = py + (vy * 25)
        else:
            # Flanqueamento Lateral em caso de alvo estático
            alvo_x = px + (350 if bx < px else -350)
            alvo_y = py

    alvo_x = max(150, min(1150, alvo_x))
    alvo_y = max(150, min(620, alvo_y))
    
    # Materialização do Projétil Sinalizador
    estado_ia['proj_tele'] = {
        "rect": pygame.Rect(bx, by, 30, 30),
        "angulo": math.atan2(alvo_y - by, alvo_x - bx),
        "tipo": tipo, 
        "alvo_pos": (alvo_x, alvo_y), 
        "velocidade": 12 # Velocidade calibrada para resposta tática
    }
    
    estado_ia['ultimo_teleporte'] = agora
    estado_ia['fase_tele'] = "disparando"

def node_teleporte_sinalizador(agora, estado_ia, boss_pos, alvo_pos, tipo_teleporte='real'):
    """
    Cria o 'Sinalizador de Translocação' (Círculo Azul).
    Ele viajará da posição atual até o alvo_pos.
    """
    # Nota: boss_pos deve ser passado como {'x': ..., 'y': ...}
    start_x, start_y = boss_pos['x'], boss_pos['y']
    target_x, target_y = alvo_pos
    
    dx = target_x - start_x
    dy = target_y - start_y
    dist_total = math.hypot(dx, dy)
    ang = math.atan2(dy, dx)
    
    # Define o projétil sinalizador na memória da IA
    estado_ia['proj_tele'] = {
        'x': start_x, 'y': start_y,       # Posição atual do projétil
        'start_pos': (start_x, start_y),  # Origem
        'target_pos': (target_x, target_y), # Destino final
        'angulo': ang,
        'velocidade': 8,                  # Reduzido a pedido para tempo de respiro
        'dist_total': dist_total,
        'dist_percorrida': 0,
        'tipo': tipo_teleporte,           # 'real' ou 'falso' (Juke)
        'cor_sinal': (0, 255, 180),       # Ciano/Verde Neon
        'raio': 15 
    }
    
    estado_ia['ultimo_teleporte'] = agora
    estado_ia['fase_tele'] = "projetil_viajando"

def node_descarga_eletrica(agora, estado_ia, bx, by, px, py):
    # CALIBRAÇÃO DE CENTRO: Garante que os raios saiam da alma do boss
    centro_bx = bx + (largura_boss // 2)
    centro_by = by + (altura_boss // 2)
    centro_px = px + (largura_personagem // 2)
    centro_py = py + (altura_personagem // 2)

    angulo_disparo = math.atan2(centro_py - centro_by, centro_px - centro_bx)
    estado_ia['descarga_eletrica'] = {
        'x': centro_bx,
        'y': centro_by,
        'angulo_base': angulo_disparo,
        'raio_maximo': 380.0,
        'abertura': 0.9, 
        'duracao': 1800,
        'tempo_inicio': agora,
        'dano_por_tick': 12
    }
    estado_ia['ultimo_descarga'] = agora

# --- MOTOR DE DECISÃO (O GRAFO) ---

def processar_ia_umbra(agora, boss_pos, player_pos, historico_player, disparos_player, estado_ia, config_boss, memoria):
    import math
    import random
    
    bx, by = boss_pos['x'], boss_pos['y']
    px, py = player_pos[0], player_pos[1]
    centro_mapa = estado_ia.get('centro_mapa', (680, 384))
    
    if estado_ia.get('parede_ativa'):
        node_sifon(agora, estado_ia, boss_pos, centro_mapa)
        return estado_ia

    if estado_ia.get('fase_tele') != "espera":
        return estado_ia

    vida_p = config_boss.get('vida_atual', 1600) / max(1, config_boss.get('vida_max', 1600))
    dist_p = math.hypot(px - bx, py - by)
    sob_fogo = len(disparos_player)
    mapa_atual = config_boss.get('mapa_atual')
    
    estado_composto = memoria.discretizar_estado(vida_p, dist_p, sob_fogo, historico_player, mapa_atual, player_pos, boss_pos, estado_ia)

    acoes_disponiveis = ["ATAQUE"]

    if agora - estado_ia.get('ultimo_teleporte', 0) >= 10000:
        acoes_disponiveis.extend(["TELEPORTE", "TELEPORTE_JUKE"])
        
    # SISTEMA INTELIGENTE DE SIFÃO
    # Pré-cooldown: Não pode usar nos primeiros 20s da fase
    tempo_desde_inicio_fase = agora - estado_ia.get('tempo_inicio_fase', 0)
    cooldown_sifao_ok = agora - estado_ia.get('ultimo_sifon_fim', 0) >= 20000
    
    # Só adiciona Sifão se passou o pré-cooldown E o cooldown normal
    if tempo_desde_inicio_fase >= 20000 and (cooldown_sifao_ok or estado_ia.get('ultimo_sifon_fim') == 0):
        acoes_disponiveis.append("SIFON")

    # SISTEMA DE BLOQUEIO DE COMBOS ENTRE DIMENSÕES
    # Previne que Umbra use transmutação enquanto habilidade dimensional está ativa
    # ou logo após usar uma habilidade (tempo mínimo de 5s na dimensão)
    
    tempo_na_dimensao_atual = agora - estado_ia.get('tempo_inicio_dimensao', 0)
    def is_active(ability_key, default_dur):
        ab = estado_ia.get(ability_key)
        if not ab: return False
        dur = ab.get('duracao', default_dur)
        if ability_key == 'caminho_espinhos':
            dur = ab.get('duracao_crescimento', 0) + ab.get('duracao_expansao', 0)
        elif ability_key == 'laser_ativo':
            dur = ab.get('duracao_carga', 0) + ab.get('duracao_disparo', 0)
        return (agora - ab.get('tempo_inicio', 0)) < dur

    habilidade_dimensional_ativa = (
        is_active('vortice_ativo', 8000) or
        is_active('prisao_ativa', 3500) or
        is_active('caminho_espinhos', 3400) or
        is_active('laser_ativo', 5500) or
        is_active('descarga_eletrica', 1800) or
        is_active('miasma_ativo', 4500) or
        is_active('praga_ratos', 9000)
    )
    
    # Verifica se pode transmutar
    pode_transmutar = (
        agora - estado_ia.get('ultimo_transmutar', 0) >= 25000 and  # Cooldown base
        tempo_na_dimensao_atual >= 5000 and  # Mínimo 5s na dimensão atual
        not habilidade_dimensional_ativa  # Nenhuma habilidade ativa
    )
    
    if pode_transmutar:
        ultima_dim = estado_ia.get('ultima_dimensao_usada', "")
        if ultima_dim != "vortice": acoes_disponiveis.append("TRANSMUTAR_VORTICE")
        if ultima_dim != "gravidade": acoes_disponiveis.append("TRANSMUTAR_GRAVIDADE")
        if ultima_dim != "necrose": acoes_disponiveis.append("TRANSMUTAR_NECROSE")
        if ultima_dim != "ressonancia": acoes_disponiveis.append("TRANSMUTAR_RESSONANCIA")
        if ultima_dim != "hemorragia": acoes_disponiveis.append("TRANSMUTAR_HEMORRAGIA")
        if ultima_dim != "atrito": acoes_disponiveis.append("TRANSMUTAR_ATRITO")
        if ultima_dim != "rastro": acoes_disponiveis.append("TRANSMUTAR_RASTRO")

    if mapa_atual == "Sprites/Fase1.png" and agora - estado_ia.get('ultimo_vortice', 0) >= 12000:
        acoes_disponiveis.append("VORTICE")
    elif mapa_atual == "Sprites/Fase2.png" and agora - estado_ia.get('ultimo_prisao', 0) >= 9000:
        acoes_disponiveis.append("PRISAO")
    elif mapa_atual == "Sprites/Fase3.png" and agora - estado_ia.get('ultimo_miasma', 0) >= 10000:
        acoes_disponiveis.append("MIASMA")
    elif mapa_atual == "Sprites/Fase4.png" and agora - estado_ia.get('ultimo_descarga', 0) >= 11000:
        acoes_disponiveis.append("DESCARGA_ELETRICA")
    elif mapa_atual == "Sprites/Fase6.png" and agora - estado_ia.get('ultimo_espinhos', 0) >= 8000:
        acoes_disponiveis.append("CAMINHO_ESPINHOS")
    elif mapa_atual == "Sprites/Fase7.png" and agora - estado_ia.get('ultimo_laser', 0) >= 11000:
        acoes_disponiveis.append("LASER_SOBRECARGA")
    elif mapa_atual == "Sprites/Fase9.png" and agora - estado_ia.get('ultimo_praga_ratos', 0) >= 12000:
        acoes_disponiveis.append("PRAGA_RATOS")

    # Carrega modificadores adaptativos (uma vez por luta)
    _carregar_mods_lazy(estado_ia)

    decisao = memoria.decidir(estado_composto, acoes_disponiveis)

    # === SISTEMA ADAPTATIVO: bias pós-DQN ===
    if ADAPTACAO_UMBRA_ATIVA and estado_ia.get('_modificadores_umbra'):
        decisao = _aplicar_bias_decisao(decisao, acoes_disponiveis, estado_ia, dist_p)

    # === SISTEMA DE PROFECIA ===
    _processar_profecia(agora, estado_ia, px, py, bx, by, dist_p, historico_player)
    if ADAPTACAO_UMBRA_ATIVA:
        decisao = _aplicar_bonus_profecia(decisao, acoes_disponiveis, estado_ia, agora)

    if estado_ia.get('laser_ativo'):
        decisao = "NENHUMA"

    acoes_simultaneas = estado_ia.get('decisoes_ativas', [])
    if decisao not in acoes_simultaneas and decisao != "NENHUMA":
        acoes_simultaneas.append(decisao)
    estado_ia['decisoes_ativas'] = acoes_simultaneas

    if decisao == "SIFON":
        estado_ia['parede_ativa'] = True
        estado_ia['ultimo_parede'] = agora
        estado_ia['dano_recente'] = 0
        
        # SISTEMA DE RECOMPENSA INTELIGENTE PARA SIFÃO
        # Calcula vida percentual da Umbra
        vida_atual_umbra = config_boss.get('vida_atual', 1200)
        vida_max_umbra = config_boss.get('vida_max', 1200)
        percentual_vida = vida_atual_umbra / vida_max_umbra
        
        # Calcula cura que será recebida (5% da vida máxima)
        cura_esperada = vida_max_umbra * 0.05
        
        # Sistema de recompensa baseado em necessidade
        if percentual_vida < 0.3:  # Vida crítica (<30%)
            # EXCELENTE uso: Grande recompensa
            recompensa_sifao = 50.0
        elif percentual_vida < 0.5:  # Vida baixa (<50%)
            # BOM uso: Recompensa moderada
            recompensa_sifao = 25.0
        elif percentual_vida < 0.7:  # Vida média (<70%)
            # USO OK: Pequena recompensa
            recompensa_sifao = 10.0
        else:  # Vida alta (>70%)
            # DESPERDÍCIO: Penalidade proporcional à cura desperdiçada
            # Quanto mais vida tem, maior a penalidade
            fator_desperdicio = (percentual_vida - 0.7) / 0.3  # 0 a 1
            recompensa_sifao = -cura_esperada * fator_desperdicio * 0.5  # Penalidade proporcional
        
        memoria.treinar(recompensa_sifao)
        node_sifon(agora, estado_ia, boss_pos, centro_mapa)

    elif decisao.startswith("TRANSMUTAR_"):
        estado_ia['iniciar_transicao_mapa'] = True
        estado_ia['ultimo_transmutar'] = agora
        estado_ia['primeira_transmutacao_feita'] = True
        estado_ia['dano_recente'] = 0 
        estado_ia['tempo_inicio_dimensao'] = agora
        estado_ia['tempo_inicio_fase'] = agora  # Marca início da nova fase para pré-cooldown do Sifão
        estado_ia['duracao_dimensao'] = 30000
        
        # Reseta cooldowns de TODAS as habilidades dimensionais
        # Isso permite usar a habilidade da nova dimensão imediatamente
        estado_ia['ultimo_vortice'] = 0  # Permite usar imediatamente
        estado_ia['ultimo_prisao'] = 0
        estado_ia['ultimo_miasma'] = 0
        estado_ia['ultimo_descarga'] = 0
        estado_ia['ultimo_espinhos'] = 0
        estado_ia['ultimo_laser'] = 0
        estado_ia['ultimo_praga_ratos'] = 0
        
        dimensao_escolhida = decisao.split("_")[1].lower()
        mapas = {
            "vortice": "Sprites/Fase1.png",
            "gravidade": "Sprites/Fase2.png",
            "necrose": "Sprites/Fase3.png",
            "ressonancia": "Sprites/Fase4.png",
            "hemorragia": "Sprites/Fase6.png",
            "atrito": "Sprites/Fase7.png",
            "rastro": "Sprites/Fase9.png"
        }
        
        estado_ia['mapa_alvo'] = mapas[dimensao_escolhida]
        estado_ia['dimensao_ativa'] = dimensao_escolhida
        estado_ia['ultima_dimensao_usada'] = dimensao_escolhida 
        
        vec_x, vec_y = bx - px, by - py
        mag = math.hypot(vec_x, vec_y)
        alvo_x, alvo_y = (bx + (vec_x/max(1, mag))*600, by + (vec_y/max(1, mag))*600)
        
        from Variaveis import espacamento, largura_mapa, altura_mapa
        alvo_x_f = max(espacamento, min(largura_mapa - 100, alvo_x))
        alvo_y_f = max(espacamento, min(altura_mapa - 150, alvo_y))
        node_teleporte_sinalizador(agora, estado_ia, boss_pos, (alvo_x_f, alvo_y_f))
    
    elif decisao == "VORTICE":
        node_vortice_temporal(agora, estado_ia, px, py, memoria)
        estado_ia['dano_recente'] = 0
    
    elif decisao == "MIASMA":
        node_miasma_toxico(agora, estado_ia)
        estado_ia['dano_recente'] = 0
    
    elif decisao == "DESCARGA_ELETRICA":
        node_descarga_eletrica(agora, estado_ia, bx, by, px, py)
        estado_ia['dano_recente'] = 0

    elif decisao == "PRISAO":
        node_prisao_criogenica(agora, estado_ia, px, py, historico_player)
        estado_ia['dano_recente'] = 0

    elif decisao == "PRAGA_RATOS":
        estado_ia['praga_ratos'] = {
            'tempo_inicio': agora,
            'duracao': 9000
        }
        estado_ia['ultimo_praga_ratos'] = agora
        estado_ia['dano_recente'] = 0

    elif decisao == "LASER_SOBRECARGA":
        estado_ia['laser_ativo'] = {
            'tempo_inicio': agora,
            'fase': 'carregando',
            'rodada': 1,
            'duracao_carga': 1500,
            'duracao_disparo': 4000
        }
        estado_ia['ultimo_laser'] = agora
        estado_ia['carga_atrito'] = 0
        estado_ia['dano_recente'] = 0

    elif decisao == "TELEPORTE":
        vec_x, vec_y = bx - px, by - py
        mag = math.hypot(vec_x, vec_y)
        
        if mag < 200:
            alvo_x, alvo_y = bx + (vec_x/max(1, mag))*600, by + (vec_y/max(1, mag))*600
        else:
            ang_player = math.atan2(py - by, px - bx)
            ang_flanco = ang_player + random.choice([math.pi/2, -math.pi/2])
            alvo_x = px + math.cos(ang_flanco) * 450
            alvo_y = py + math.sin(ang_flanco) * 450

        from Variaveis import espacamento, largura_mapa, altura_mapa
        alvo_x_f = max(espacamento, min(largura_mapa - 100, alvo_x))
        alvo_y_f = max(espacamento, min(altura_mapa - 150, alvo_y))
        
        node_teleporte_sinalizador(agora, estado_ia, boss_pos, (alvo_x_f, alvo_y_f), tipo_teleporte='real')

    elif decisao == "TELEPORTE_JUKE":
        # Fake teleporte, finge ir para o outro lado de Apolo
        vec_x, vec_y = bx - px, by - py
        mag = math.hypot(vec_x, vec_y)
        alvo_x, alvo_y = bx - (vec_x/max(1, mag))*500, by - (vec_y/max(1, mag))*500
        from Variaveis import espacamento, largura_mapa, altura_mapa
        alvo_x_f = max(espacamento, min(largura_mapa - 100, alvo_x))
        alvo_y_f = max(espacamento, min(altura_mapa - 150, alvo_y))
        
        node_teleporte_sinalizador(agora, estado_ia, boss_pos, (alvo_x_f, alvo_y_f), tipo_teleporte='falso')

    elif decisao == "CAMINHO_ESPINHOS":
        node_caminho_espinhos(agora, estado_ia, bx, by, px, py, historico_player)
        estado_ia['dano_recente'] = 0
            
    elif decisao == "ATAQUE":
        node_ataque_direcionado(agora, estado_ia, bx, by, px, py, historico_player, memoria)
        
    return estado_ia


def node_miasma_toxico(agora, estado_ia):
    estado_ia['miasma_ativo'] = {
        'tempo_inicio': agora,
        'duracao': 4500 
    }
    estado_ia['ultimo_miasma'] = agora

def node_vortice_temporal(agora, estado_ia, px, py, memoria):
    """Nódulo de Singularidade: Ancorado no centro do tecido dimensional."""
    alvo_x = largura_mapa // 2
    alvo_y = altura_mapa // 2
    
    estado_ia['vortice_ativo'] = {
        'x': alvo_x, 
        'y': alvo_y,
        'tempo_inicio': agora, 
        'duracao': 8000, 
        'forca': 2.8
    }
    estado_ia['ultimo_vortice'] = agora

def node_prisao_criogenica(agora, estado_ia, px, py, historico_player):
    """Nódulo de Congelamento: Intercepta a rota de fuga com Zero Absoluto."""
    if len(historico_player) >= 5:
        # Calcula o vetor de movimento dos últimos frames
        vx = px - historico_player[-5][0]
        vy = py - historico_player[-5][1]
        
        # Projeta a armadilha à frente do jogador
        alvo_x = px + (vx * 6)
        alvo_y = py + (vy * 6)
    else:
        alvo_x, alvo_y = px, py

    # Contenção nos limites do mapa
    alvo_x = max(80, min(1280, alvo_x))
    alvo_y = max(80, min(680, alvo_y))
    
    estado_ia['prisao_ativa'] = {
        'rect': pygame.Rect(alvo_x - 60, alvo_y - 60, 120, 120),
        'tempo_inicio': agora,
        'duracao': 3500, # 3.5 segundos de armadilha no chão
        'x': alvo_x,
        'y': alvo_y
    }
    estado_ia['ultimo_prisao'] = agora


def movimentacao_inteligente_umbra(agora, boss_pos, player_pos, disparos, estado_mov, dados_player, memoria, historico_player):
    if estado_mov.get('parede_ativa'):
        estado_mov['vel_x'], estado_mov['vel_y'] = 0, 0
        return estado_mov.get('centro_mapa', (680, 384)), "SIFON_STASIS"
    if estado_mov.get('laser_ativo'):
        estado_mov['vel_x'], estado_mov['vel_y'] = 0, 0
        return (boss_pos[0], boss_pos[1]), "LASER_STASIS"

    import math, random
    bx, by = boss_pos[0], boss_pos[1]
    px, py = player_pos[0], player_pos[1]
    dist_p = math.hypot(bx - px, by - py)

    VEL_MAX = 3.0
    AGILIDADE = 0.3
    RAIO_SEGURANCA = 340

    # PROTOCOLO DE VISÃO DE BALA
    tiro_ameaca = None
    ameaca_x, ameaca_y = 0.0, 0.0
    for d in disparos:
        dx_tiro = bx - d["rect"].centerx
        vx_tiro = math.cos(d["angulo"])
        if (dx_tiro > 0 and vx_tiro > 0) or (dx_tiro < 0 and vx_tiro < 0):
            dist_h = math.hypot(d["rect"].centerx - bx, d["rect"].centery - by)
            if dist_h < 400:
                tiro_ameaca = d
                ameaca_x = math.cos(d["angulo"])
                ameaca_y = math.sin(d["angulo"])
                break

    vida_perc = dados_player['vida_atual'] / dados_player['vida_max']
    sob_fogo = 1.0 if tiro_ameaca else 0.0
    estado_atual = memoria.discretizar_estado(vida_perc, dist_p, sob_fogo, historico_player, dados_player.get('mapa_atual', 'Fase_Base'), player_pos, boss_pos, estado_mov, ameaca_vec=(ameaca_x, ameaca_y))
    
    estrategias = ["FUGIR", "INTERCEPTAR", "ORBITAR", "CERCAR"]
    decisao = memoria.decidir(estado_atual, estrategias)

    # === SISTEMA ADAPTATIVO: bias de movimentação ===
    if ADAPTACAO_UMBRA_ATIVA and estado_mov.get('_modificadores_umbra'):
        decisao = _aplicar_bias_movimento(decisao, estado_mov, dist_p)

    meio_w, meio_h = largura_mapa / 2.0, altura_mapa / 2.0

    if decisao == "FUGIR":
        # Fuga Inteligente: Evitar cantos! Procurar o nó mais distante do jogador e seguro das bordas.
        ang_fuga = math.atan2(by - py, bx - px) + random.uniform(-0.2, 0.2)
        distancia_alvo = 600
        alvo_x = bx + math.cos(ang_fuga) * distancia_alvo
        alvo_y = by + math.sin(ang_fuga) * distancia_alvo
        
        # Fuga vetorial para o centro se a fuga linear nos jogar contra a parede
        if alvo_x < 150 or alvo_x > largura_mapa - 150 or alvo_y < 150 or alvo_y > altura_mapa - 150:
            alvo_x = alvo_x * 0.5 + meio_w * 0.5
            alvo_y = alvo_y * 0.5 + meio_h * 0.5

    elif decisao == "INTERCEPTAR":
        # Lead Pursuit (Interceptação por Vetor Preditivo)
        vx_p, vy_p = 0.0, 0.0
        if historico_player and len(historico_player) > 3:
            vx_p = (px - historico_player[-3][0]) / 3
            vy_p = (py - historico_player[-3][1]) / 3
        
        tempo_intercept = dist_p / max(1.0, VEL_MAX)
        alvo_x = px + (vx_p * tempo_intercept * 0.6) + random.uniform(-30, 30)
        alvo_y = py + (vy_p * tempo_intercept * 0.6) + random.uniform(-30, 30)

    elif decisao == "ORBITAR":
        # Orbitar matematicamente perpendicular ao jogador
        ang = math.atan2(by - py, bx - px) + 1.2 + random.uniform(-0.1, 0.1)
        raio_variavel = 450
        alvo_x = px + math.cos(ang) * raio_variavel
        alvo_y = py + math.sin(ang) * raio_variavel
        
    else:  # CERCAR
        # Posicionar-se ativamente entre o Apolo e o centro do mapa para imprensá-lo
        dx_centro = meio_w - px
        dy_centro = meio_h - py
        dist_c = math.hypot(dx_centro, dy_centro)
        
        # O vetor norm_x/y aponta do jogador *para* o centro. A Umbra se coloca neste caminho.
        norm_x = dx_centro / max(1.0, dist_c)
        norm_y = dy_centro / max(1.0, dist_c)
        
        distancia_cerco = 300 + random.uniform(-40, 40)
        alvo_x = px + (norm_x * distancia_cerco)
        alvo_y = py + (norm_y * distancia_cerco)

    limite_x_min = int(espacamento)
    limite_x_max = int(largura_mapa - largura_boss - espacamento)
    limite_y_min = int(espacamento)
    limite_y_max = int(altura_mapa - altura_boss - espacamento)
    estado_mov['alvo_ia'] = (max(limite_x_min, min(limite_x_max, alvo_x)), max(limite_y_min, min(limite_y_max, alvo_y)))
    
    dx_a, dy_a = estado_mov['alvo_ia'][0] - bx, estado_mov['alvo_ia'][1] - by
    mag_a = math.hypot(dx_a, dy_a)
    vec_alvo_x = (dx_a / mag_a) if mag_a > 0 else 0
    vec_alvo_y = (dy_a / mag_a) if mag_a > 0 else 0

    rx, ry = bx - px, by - py
    dist_r = math.hypot(rx, ry)
    f_rep_x = f_rep_y = 0
    
    # Repulsão graduada e suave (Evita a "parede invisível" que fazia ela tremer)
    if dist_r < RAIO_SEGURANCA and dist_r > 0:
        intensidade_repulsao = 2.0 * (1.0 - (dist_r / RAIO_SEGURANCA)) ** 2  # Curva quadrática mais orgânica
        f_rep_x, f_rep_y = (rx / dist_r) * intensidade_repulsao, (ry / dist_r) * intensidade_repulsao

    v_desejada_x = (vec_alvo_x + f_rep_x) * VEL_MAX
    v_desejada_y = (vec_alvo_y + f_rep_y) * VEL_MAX
    
    vx = estado_mov.get('vel_x', 0.0)
    vy = estado_mov.get('vel_y', 0.0)
    
    # Agilidade reduzida para 0.08 cria forte Inércia (Simula peso e curvas mais orgânicas)
    AGILIDADE_NATURAL = 0.08
    import Variaveis
    dt = getattr(Variaveis, 'dt', 1.0)
    fator_agilidade = min(1.0, AGILIDADE_NATURAL * dt)
    vx += (v_desejada_x - vx) * fator_agilidade
    vy += (v_desejada_y - vy) * fator_agilidade
    estado_mov['vel_x'], estado_mov['vel_y'] = vx, vy

    nx = max(int(espacamento), min(int(largura_mapa - largura_boss - espacamento), int(bx + vx * dt)))
    ny = max(int(espacamento), min(int(altura_mapa - altura_boss - espacamento), int(by + vy * dt)))

    return (nx, ny), "GENERATIVE_MOVE"


# --- MOTOR DE VFX PROCEDURAL (PLASMA & PARTÍCULAS) ---

def gerar_burst_desfragmentacao(x, y, estado_ia, cor_base=(0, 255, 100)):
    """
    OTIMIZADO: Gera explosão de fragmentos com MENOS partículas (15-20 ao invés de 15-25).
    Cor padrão: Verde para combinar com projéteis da Umbra.
    """
    if 'vfx_particulas' not in estado_ia:
        estado_ia['vfx_particulas'] = []
        
    # OTIMIZAÇÃO: Reduzido de 15-25 para 10-15 partículas
    for _ in range(random.randint(10, 15)):
        ang = random.uniform(0, math.pi * 2)
        forca = random.uniform(1.0, 4.0)  # OTIMIZAÇÃO: Reduzida força máxima
        vida = random.randint(15, 40)  # OTIMIZAÇÃO: Reduzida vida máxima
        estado_ia['vfx_particulas'].append({
            'x': x, 'y': y,
            'vx': math.cos(ang) * forca,
            'vy': math.sin(ang) * forca,
            'vida': vida,
            'vida_max': vida,
            'cor': cor_base,
            'tam': random.randint(2, 4)  # OTIMIZAÇÃO: Reduzido tamanho máximo
        })

def renderizar_vfx_umbra(tela, agora, estado_ia):
    """
    DESIGN OTIMIZADO: Projéteis verdes da Umbra com menos partículas.
    Renderiza esferas de plasma verde com aura pulsante.
    """
    
    # 1. GESTÃO OTIMIZADA DE PARTÍCULAS (REDUZIDO)
    particulas_vivas = []
    vfx_pool = estado_ia.get('vfx_particulas', [])
    
    # OTIMIZAÇÃO: Processa apenas a cada 2 frames para reduzir carga
    if len(vfx_pool) > 0 and agora % 2 == 0:
        for p in vfx_pool:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['vida'] -= 2  # Decrementa 2 para compensar o skip de frame
            p['vx'] *= 0.94
            p['vy'] *= 0.94
            
            if p['vida'] > 0:
                alfa = int((p['vida'] / p['vida_max']) * 255)
                s = pygame.Surface((p['tam']*2, p['tam']*2), pygame.SRCALPHA)
                cor_rgb = p['cor'][:3] if isinstance(p['cor'], (tuple, list)) and len(p['cor']) >= 3 else (0, 255, 100)
                pygame.draw.circle(s, (*cor_rgb, alfa), (p['tam'], p['tam']), p['tam'])
                tela.blit(s, (p['x'] - p['tam'], p['y'] - p['tam']))
                particulas_vivas.append(p)
    else:
        particulas_vivas = vfx_pool
            
    estado_ia['vfx_particulas'] = particulas_vivas

    # 2. RENDERIZAÇÃO OTIMIZADA DE PROJÉTEIS (VERDE)
    for proj in estado_ia.get('projeteis', []):
        x, y = proj['rect'].center
        tipo = proj.get('tipo', 'comum')
        
        # Cores Verde da Umbra
        if tipo == "furia":
            cor_aura = (138, 43, 226)  # Púrpura de Fúria (mantém especial)
            raio_base = 15
            camadas = 3
        else:
            cor_aura = (0, 255, 100)  # Verde Brilhante
            raio_base = 8
            camadas = 2  # OTIMIZAÇÃO: Reduzido de 3 para 2 camadas
            
        pulsar = math.sin(agora * 0.02) * 2  # OTIMIZAÇÃO: Reduzido amplitude
        
        # A. AURA TRANSLÚCIDA PULSANTE (OTIMIZADA)
        for nivel in range(camadas, 0, -1):
            raio_vfx = raio_base + (nivel * 3) + pulsar  # OTIMIZAÇÃO: Reduzido multiplicador
            opacidade = 70 // nivel  # OTIMIZAÇÃO: Reduzida opacidade base
            circulo_aura = pygame.Surface((raio_vfx * 2, raio_vfx * 2), pygame.SRCALPHA)
            pygame.draw.circle(circulo_aura, (*cor_aura, opacidade), (raio_vfx, raio_vfx), raio_vfx)
            tela.blit(circulo_aura, (x - raio_vfx, y - raio_vfx))
            
        # B. NÚCLEO BRILHANTE (SIMPLIFICADO)
        pygame.draw.circle(tela, (255, 255, 255), (x, y), raio_base)
        pygame.draw.circle(tela, cor_aura, (x, y), raio_base + 1, 1)  # OTIMIZAÇÃO: Reduzida espessura


