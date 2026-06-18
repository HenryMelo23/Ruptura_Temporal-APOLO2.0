"""
umbra_dossie.py — Sistema de Dossiê Predatório da Umbra
Registra e persiste o comportamento do jogador ao longo dos combates.

NÃO altera dano, vida, velocidade ou comportamento da Umbra.
Apenas observa, calcula métricas e salva/carrega dados.
"""

import json
import os
import time
import math
import shutil
from datetime import datetime

DEBUG_DOSSIE = False

ARQUIVO_DOSSIE = "memoria_predatoria_umbra.json"

def _log(msg):
    pass


# Arquétipos reconhecidos pelo classificador
ARQUETIPOS = [
    "REFUGIADO_DE_CANTO",
    "DEPENDENTE_DE_DASH",
    "CACADOR_DE_ORBES",
    "AGRESSOR_IMPULSIVO",
    "ATIRADOR_DISTANTE",
    "CORREDOR_CIRCULAR",
    "SOBREVIVENTE_ADAPTATIVO",
    "INDEFINIDO",
]

# Histerese: diferença mínima de confiança para trocar arquétipo
_HISTERESE_CONFIANCA = 0.15
# Ou trocar se o novo aparecer N vezes consecutivas
_CONSECUTIVAS_PARA_TROCAR = 3
# Tamanho do histórico de arquétipos
_TAMANHO_HISTORICO = 10


def _perfil_padrao():
    """Retorna a subestrutura de perfil do jogador com valores iniciais."""
    return {
        "arquetipo_principal": "INDEFINIDO",
        "arquetipo_secundario": "INDEFINIDO",
        "confianca": 0.0,
        "historico_arquetipos": [],
    }


def _dados_padrao():
    """Retorna a estrutura completa com valores zerados."""
    return {
        # === Globais ===
        "encontros_total": 0,
        "mortes_do_jogador_para_umbra": 0,
        "vitorias_do_jogador_contra_umbra": 0,
        "tempo_total_em_combate": 0.0,
        "ultima_atualizacao": None,

        # === Métricas de comportamento ===
        "total_frames_observados": 0,
        "tempo_em_borda": 0,
        "tempo_em_canto": 0,
        "vezes_fugiu_esquerda": 0,
        "vezes_fugiu_direita": 0,
        "vezes_fugiu_cima": 0,
        "vezes_fugiu_baixo": 0,
        "uso_dash_total": 0,
        "uso_dash_por_minuto": 0.0,
        "dano_causado_total": 0.0,
        "dano_recebido_total": 0.0,
        "tiros_disparados": 0,
        "tiros_acertados": 0,
        "orbes_coletadas": 0,
        "tentativas_de_ir_para_orbe": 0,
        "tempo_medio_para_buscar_orbe": 0.0,
        "ataques_corpo_a_corpo_ou_proximos": 0,
        "ataques_distantes": 0,
        "tempo_parado": 0,
        "mudancas_bruscas_de_direcao": 0,
        "repeticoes_de_padrao_movimento": 0,
        "vezes_morreu_em_canto": 0,
        "vezes_morreu_apos_dash": 0,
        "vezes_sobreviveu_com_vida_baixa": 0,

        # === Perfil comportamental ===
        "perfil_jogador": _perfil_padrao(),

        # === Adaptações da Umbra ===
        "adaptacoes_umbra": {
            "modificadores_ativos": [],
            "vezes_aplicadas": {},
            "ultima_luta": {},
        },

        # === Profecias Falsificáveis ===
        "profecias": {
            "criadas": 0,
            "confirmadas": 0,
            "quebradas": 0,
            "expiradas": 0,
            "por_tipo": {},
        },
    }


class DossieUmbra:
    """Observador passivo do comportamento do jogador contra a Umbra."""

    # Margens usadas para definir "borda" e "canto" (em pixels)
    MARGEM_BORDA = 80
    LIMIAR_PARADO = 2.0            # pixels de deslocamento por frame
    LIMIAR_MUDANCA_DIRECAO = 120   # graus de diferença entre vetores consecutivos
    LIMIAR_VIDA_BAIXA = 0.20      # 20% da vida máxima
    LIMIAR_PERTO = 200             # px para considerar "corpo a corpo / perto"

    def __init__(self, largura_mapa=1024, altura_mapa=768):
        self._largura_mapa = largura_mapa
        self._altura_mapa = altura_mapa

        self.dados = _dados_padrao()
        self.carregar()

        # --- Estado volátil do encontro atual (não persistido) ---
        self._encontro_ativo = False
        self._tempo_inicio_encontro = 0.0
        self._dashes_encontro = 0
        self._pos_anterior = None
        self._direcao_anterior = None
        self._ultimos_movimentos = []   # janela deslizante de direções
        self._vida_player_anterior = None
        self._ultimo_dash_tick = 0

        # Orbe tracking
        self._orbe_visivel_desde = None
        self._soma_tempo_buscar_orbe = 0.0
        self._contagem_orbe_tempo = 0

        _log("DossieUmbra inicializado.")

    # =================================================================
    # PERSISTÊNCIA
    # =================================================================
    def carregar(self):
        if not os.path.exists(ARQUIVO_DOSSIE):
            _log("Arquivo não encontrado, criando novo.")
            self.dados = _dados_padrao()
            self.salvar()
            return

        try:
            with open(ARQUIVO_DOSSIE, "r", encoding="utf-8") as f:
                carregado = json.load(f)

            # Preenche chaves ausentes (forward-compatible)
            base = _dados_padrao()
            for chave in base:
                if chave not in carregado:
                    carregado[chave] = base[chave]

            self.dados = carregado
            _log(f"Dossiê carregado — {self.dados['encontros_total']} encontros.")
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            _log(f"JSON corrompido ({e}), backup + reset.")
            backup = ARQUIVO_DOSSIE + ".bak"
            try:
                shutil.copy2(ARQUIVO_DOSSIE, backup)
            except Exception:
                pass
            self.dados = _dados_padrao()
            self.salvar()

    def salvar(self):
        self.dados["ultima_atualizacao"] = datetime.now().isoformat()
        try:
            with open(ARQUIVO_DOSSIE, "w", encoding="utf-8") as f:
                json.dump(self.dados, f, indent=2, ensure_ascii=False)
            _log("Dossiê salvo.")
        except Exception as e:
            _log(f"Erro ao salvar: {e}")

    # =================================================================
    # CICLO DE ENCONTRO
    # =================================================================
    def iniciar_encontro(self):
        self._encontro_ativo = True
        self._tempo_inicio_encontro = time.time()
        self._dashes_encontro = 0
        self._pos_anterior = None
        self._direcao_anterior = None
        self._ultimos_movimentos = []
        self._vida_player_anterior = None
        self._ultimo_dash_tick = 0
        self._orbe_visivel_desde = None
        self._soma_tempo_buscar_orbe = 0.0
        self._contagem_orbe_tempo = 0

        self.dados["encontros_total"] += 1
        _log(f"Encontro #{self.dados['encontros_total']} iniciado.")

    def finalizar_encontro(self, resultado="derrota"):
        """resultado: 'vitoria' ou 'derrota'"""
        if not self._encontro_ativo:
            return

        duracao = time.time() - self._tempo_inicio_encontro
        self.dados["tempo_total_em_combate"] += duracao

        if duracao > 0:
            self.dados["uso_dash_por_minuto"] = round(
                self.dados["uso_dash_total"] / (self.dados["tempo_total_em_combate"] / 60.0), 2
            )

        # Atualiza tempo médio para buscar orbe
        if self._contagem_orbe_tempo > 0:
            self.dados["tempo_medio_para_buscar_orbe"] = round(
                self._soma_tempo_buscar_orbe / self._contagem_orbe_tempo, 2
            )

        self._encontro_ativo = False
        self.atualizar_arquetipo()
        _log(f"Encontro finalizado ({resultado}) — {duracao:.1f}s")

    def sincronizar_stats_profecia(self, stats_profecia):
        """
        Recebe stats do ProfeciaUmbra (dict) e acumula no JSON persistido.
        Chamado pelo game loop ao finalizar o encontro.
        """
        if not stats_profecia:
            return
        if "profecias" not in self.dados:
            self.dados["profecias"] = {
                "criadas": 0, "confirmadas": 0,
                "quebradas": 0, "expiradas": 0, "por_tipo": {},
            }
        p = self.dados["profecias"]
        for k in ("criadas", "confirmadas", "quebradas", "expiradas"):
            p[k] = p.get(k, 0) + stats_profecia.get(k, 0)

        for tipo, vals in stats_profecia.get("por_tipo", {}).items():
            if tipo not in p["por_tipo"]:
                p["por_tipo"][tipo] = {"criadas": 0, "confirmadas": 0, "quebradas": 0, "expiradas": 0}
            for k in ("criadas", "confirmadas", "quebradas", "expiradas"):
                p["por_tipo"][tipo][k] = p["por_tipo"][tipo].get(k, 0) + vals.get(k, 0)

        self.salvar()
        _log(f"Stats profecia sincronizadas: +{stats_profecia.get('criadas', 0)} criadas")

    # =================================================================
    # REGISTRO POR FRAME
    # =================================================================
    def registrar_frame(self, player_pos, boss_pos, vida_player, vida_boss, estado_ia=None):
        """Chamado a cada frame do loop principal durante o combate contra Umbra."""
        if not self._encontro_ativo:
            return

        if player_pos is None or boss_pos is None:
            return

        px, py = player_pos
        bx, by = boss_pos
        self.dados["total_frames_observados"] += 1

        # --- Borda / Canto ---
        margem = self.MARGEM_BORDA
        na_borda = (
            px < margem or px > self._largura_mapa - margem or
            py < margem or py > self._altura_mapa - margem
        )
        no_canto = (
            (px < margem or px > self._largura_mapa - margem) and
            (py < margem or py > self._altura_mapa - margem)
        )
        if na_borda:
            self.dados["tempo_em_borda"] += 1
        if no_canto:
            self.dados["tempo_em_canto"] += 1

        # --- Parado ---
        if self._pos_anterior is not None:
            dx = px - self._pos_anterior[0]
            dy = py - self._pos_anterior[1]
            deslocamento = math.hypot(dx, dy)

            if deslocamento < self.LIMIAR_PARADO:
                self.dados["tempo_parado"] += 1

            # --- Direção de fuga (quando se afasta do boss) ---
            dist_anterior = math.hypot(
                self._pos_anterior[0] - bx, self._pos_anterior[1] - by
            )
            dist_atual = math.hypot(px - bx, py - by)
            if dist_atual > dist_anterior and deslocamento > self.LIMIAR_PARADO:
                # Jogador se afastou → registrar direção de fuga
                if abs(dx) > abs(dy):
                    if dx < 0:
                        self.dados["vezes_fugiu_esquerda"] += 1
                    else:
                        self.dados["vezes_fugiu_direita"] += 1
                else:
                    if dy < 0:
                        self.dados["vezes_fugiu_cima"] += 1
                    else:
                        self.dados["vezes_fugiu_baixo"] += 1

            # --- Mudança brusca de direção ---
            if deslocamento > self.LIMIAR_PARADO:
                angulo_atual = math.degrees(math.atan2(dy, dx))
                if self._direcao_anterior is not None:
                    diff = abs(angulo_atual - self._direcao_anterior)
                    if diff > 180:
                        diff = 360 - diff
                    if diff > self.LIMIAR_MUDANCA_DIRECAO:
                        self.dados["mudancas_bruscas_de_direcao"] += 1
                self._direcao_anterior = angulo_atual

                # --- Repetições de padrão de movimento ---
                direcao_quantizada = round(angulo_atual / 45) * 45
                self._ultimos_movimentos.append(direcao_quantizada)
                if len(self._ultimos_movimentos) > 30:
                    self._ultimos_movimentos.pop(0)
                if len(self._ultimos_movimentos) >= 10:
                    # Detecta se os últimos 5 são iguais aos 5 anteriores
                    recente = self._ultimos_movimentos[-5:]
                    anterior = self._ultimos_movimentos[-10:-5]
                    if recente == anterior:
                        self.dados["repeticoes_de_padrao_movimento"] += 1

        # --- Vida baixa ---
        if vida_player is not None and self._vida_player_anterior is not None:
            vida_max = max(vida_player, self._vida_player_anterior, 1)
            if vida_player < vida_max * self.LIMIAR_VIDA_BAIXA and vida_player > 0:
                self.dados["vezes_sobreviveu_com_vida_baixa"] += 1

        self._pos_anterior = (px, py)
        self._vida_player_anterior = vida_player

    # =================================================================
    # REGISTROS PONTUAIS
    # =================================================================
    def registrar_dash(self, player_pos=None):
        self.dados["uso_dash_total"] += 1
        self._dashes_encontro += 1
        self._ultimo_dash_tick = time.time()
        _log("Dash registrado.")

    def registrar_orbe_coletada(self, player_pos=None, vida_antes=None, vida_depois=None):
        self.dados["orbes_coletadas"] += 1
        if self._orbe_visivel_desde is not None:
            tempo_busca = time.time() - self._orbe_visivel_desde
            self._soma_tempo_buscar_orbe += tempo_busca
            self._contagem_orbe_tempo += 1
            self._orbe_visivel_desde = None
        _log("Orbe coletada.")

    def registrar_orbe_spawnada(self):
        """Chamado quando uma nova esfera de energia aparece no mapa."""
        self._orbe_visivel_desde = time.time()
        self.dados["tentativas_de_ir_para_orbe"] += 1

    def registrar_tiro(self, disparou=True, acertou=False):
        if disparou:
            self.dados["tiros_disparados"] += 1
        if acertou:
            self.dados["tiros_acertados"] += 1

    def registrar_dano_causado(self, valor, distancia_ao_boss=None):
        if valor is None:
            return
        self.dados["dano_causado_total"] += valor
        if distancia_ao_boss is not None:
            if distancia_ao_boss < self.LIMIAR_PERTO:
                self.dados["ataques_corpo_a_corpo_ou_proximos"] += 1
            else:
                self.dados["ataques_distantes"] += 1

    def registrar_dano_recebido(self, valor):
        if valor is None:
            return
        self.dados["dano_recebido_total"] += valor

    def registrar_morte(self, contexto=None):
        self.dados["mortes_do_jogador_para_umbra"] += 1

        # Verificações de contexto
        if self._pos_anterior is not None:
            px, py = self._pos_anterior
            margem = self.MARGEM_BORDA
            no_canto = (
                (px < margem or px > self._largura_mapa - margem) and
                (py < margem or py > self._altura_mapa - margem)
            )
            if no_canto:
                self.dados["vezes_morreu_em_canto"] += 1

        if self._ultimo_dash_tick > 0 and (time.time() - self._ultimo_dash_tick) < 2.0:
            self.dados["vezes_morreu_apos_dash"] += 1

        self.finalizar_encontro("derrota")
        _log("Morte registrada.")

    def registrar_vitoria(self, contexto=None):
        self.dados["vitorias_do_jogador_contra_umbra"] += 1
        self.finalizar_encontro("vitoria")
        _log("Vitória registrada.")

    # =================================================================
    # MÉTRICAS NORMALIZADAS (0.0 a 1.0)
    # =================================================================
    def obter_metricas_normalizadas(self):
        d = self.dados
        frames = max(d["total_frames_observados"], 1)
        encontros = max(d["encontros_total"], 1)
        tiros = max(d["tiros_disparados"], 1)
        dano_total = max(d["dano_causado_total"] + d["dano_recebido_total"], 1.0)

        # medo: foge muito, fica em borda, pouca agressão
        fuga_total = (
            d["vezes_fugiu_esquerda"] + d["vezes_fugiu_direita"] +
            d["vezes_fugiu_cima"] + d["vezes_fugiu_baixo"]
        )
        medo = min(1.0, (fuga_total / frames) * 30 + (d["tempo_em_borda"] / frames) * 2)

        # agressividade: dano causado vs dano recebido + tiros acertados
        precisao = d["tiros_acertados"] / tiros
        ratio_dano = d["dano_causado_total"] / dano_total
        agressividade = min(1.0, (ratio_dano * 0.6) + (precisao * 0.4))

        # dependencia_dash: dashes por minuto normalizado (>20/min = 1.0)
        dependencia_dash = min(1.0, d["uso_dash_por_minuto"] / 20.0)

        # dependencia_orbe: orbes coletadas vs encontros
        dependencia_orbe = min(1.0, d["orbes_coletadas"] / (encontros * 3.0))

        # previsibilidade: repetições + baixa mudança de direção
        previsibilidade = min(1.0, d["repeticoes_de_padrao_movimento"] / max(frames / 60, 1))

        # tendencia_borda: tempo em borda vs total frames
        tendencia_borda = min(1.0, d["tempo_em_borda"] / frames * 3.0)

        # tendencia_canto: tempo em canto vs total frames
        tendencia_canto = min(1.0, d["tempo_em_canto"] / frames * 10.0)

        # preferencia_distancia: ataques distantes vs próximos
        total_ataques = max(d["ataques_corpo_a_corpo_ou_proximos"] + d["ataques_distantes"], 1)
        preferencia_distancia = d["ataques_distantes"] / total_ataques

        # adaptabilidade: mudanças bruscas + precisão + sobrevivência com vida baixa
        adapt_raw = (
            d["mudancas_bruscas_de_direcao"] / max(frames / 30, 1) * 0.3 +
            precisao * 0.3 +
            d["vezes_sobreviveu_com_vida_baixa"] / max(frames / 120, 1) * 0.4
        )
        adaptabilidade = min(1.0, adapt_raw)

        return {
            "medo": round(medo, 3),
            "agressividade": round(agressividade, 3),
            "dependencia_dash": round(dependencia_dash, 3),
            "dependencia_orbe": round(dependencia_orbe, 3),
            "previsibilidade": round(previsibilidade, 3),
            "tendencia_borda": round(tendencia_borda, 3),
            "tendencia_canto": round(tendencia_canto, 3),
            "preferencia_distancia": round(preferencia_distancia, 3),
            "adaptabilidade": round(adaptabilidade, 3),
        }

    # =================================================================
    # CLASSIFICADOR DE ARQUÉTIPOS
    # =================================================================
    def calcular_arquetipo(self):
        """
        Analisa as métricas normalizadas e retorna:
          (arquetipo_principal, arquetipo_secundario, confianca)
        """
        m = self.obter_metricas_normalizadas()
        d = self.dados
        encontros = max(d["encontros_total"], 1)
        frames = max(d["total_frames_observados"], 1)

        # Dados insuficientes → INDEFINIDO
        if d["total_frames_observados"] < 300 or d["encontros_total"] < 1:
            return ("INDEFINIDO", "INDEFINIDO", 0.0)

        # Pontuação por arquétipo (quanto maior, mais forte a correspondência)
        scores = {}

        # --- REFUGIADO_DE_CANTO ---
        s = 0.0
        s += m["tendencia_canto"] * 0.40
        s += m["tendencia_borda"] * 0.25
        s += (1.0 - m["agressividade"]) * 0.20
        s += m["medo"] * 0.15
        scores["REFUGIADO_DE_CANTO"] = s

        # --- DEPENDENTE_DE_DASH ---
        s = 0.0
        s += m["dependencia_dash"] * 0.40
        mortes_total = max(d["mortes_do_jogador_para_umbra"], 1)
        ratio_morte_dash = d["vezes_morreu_apos_dash"] / mortes_total
        s += min(1.0, ratio_morte_dash * 2.0) * 0.30
        s += min(1.0, d["uso_dash_por_minuto"] / 15.0) * 0.30
        scores["DEPENDENTE_DE_DASH"] = s

        # --- CACADOR_DE_ORBES ---
        s = 0.0
        s += m["dependencia_orbe"] * 0.45
        tentativas_norm = min(1.0, d["tentativas_de_ir_para_orbe"] / max(encontros * 2, 1))
        s += tentativas_norm * 0.30
        # Busca sob risco: coletou orbes mesmo com vida baixa?
        orbes_norm = min(1.0, d["orbes_coletadas"] / max(encontros, 1))
        s += orbes_norm * 0.25
        scores["CACADOR_DE_ORBES"] = s

        # --- AGRESSOR_IMPULSIVO ---
        s = 0.0
        s += m["agressividade"] * 0.30
        s += (1.0 - m["preferencia_distancia"]) * 0.25  # prefere curta distância
        dano_total = max(d["dano_causado_total"] + d["dano_recebido_total"], 1.0)
        # Alto dano causado E alto dano recebido = briga de rua
        ratio_causado = d["dano_causado_total"] / dano_total
        ratio_recebido = d["dano_recebido_total"] / dano_total
        s += min(1.0, ratio_causado + ratio_recebido) * 0.25  # ambos altos = 1.0
        s += (1.0 - m["medo"]) * 0.20
        scores["AGRESSOR_IMPULSIVO"] = s

        # --- ATIRADOR_DISTANTE ---
        s = 0.0
        s += m["preferencia_distancia"] * 0.40
        tiros_por_frame = min(1.0, d["tiros_disparados"] / max(frames / 10, 1))
        s += tiros_por_frame * 0.30
        total_ataques = max(d["ataques_corpo_a_corpo_ou_proximos"] + d["ataques_distantes"], 1)
        poucos_perto = 1.0 - (d["ataques_corpo_a_corpo_ou_proximos"] / total_ataques)
        s += poucos_perto * 0.30
        scores["ATIRADOR_DISTANTE"] = s

        # --- CORREDOR_CIRCULAR ---
        s = 0.0
        # Muita movimentação: pouco tempo parado
        s += (1.0 - min(1.0, d["tempo_parado"] / max(frames * 0.3, 1))) * 0.35
        # Padrão repetitivo
        s += m["previsibilidade"] * 0.35
        # Não fica em canto/borda (corre pelo centro)
        s += (1.0 - m["tendencia_canto"]) * 0.15
        s += (1.0 - m["tendencia_borda"]) * 0.15
        scores["CORREDOR_CIRCULAR"] = s

        # --- SOBREVIVENTE_ADAPTATIVO ---
        s = 0.0
        s += m["adaptabilidade"] * 0.45
        s += (1.0 - m["previsibilidade"]) * 0.30
        # Alterna estratégias: mudanças bruscas frequentes
        mudancas_norm = min(1.0, d["mudancas_bruscas_de_direcao"] / max(frames / 20, 1))
        s += mudancas_norm * 0.25
        scores["SOBREVIVENTE_ADAPTATIVO"] = s

        # Ordenar por score descendente
        ranking = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        principal = ranking[0][0]
        confianca_principal = round(min(1.0, ranking[0][1]), 3)
        secundario = ranking[1][0] if len(ranking) > 1 else "INDEFINIDO"

        # Se a confiança do principal for muito baixa, manter INDEFINIDO
        if confianca_principal < 0.15:
            principal = "INDEFINIDO"
            secundario = "INDEFINIDO"
            confianca_principal = 0.0

        return (principal, secundario, confianca_principal)

    def atualizar_arquetipo(self):
        """
        Calcula o arquétipo atual, aplica suavização por histerese
        e persistência consecutiva, atualiza o JSON e salva.
        """
        novo_principal, novo_secundario, nova_confianca = self.calcular_arquetipo()

        # Garante que perfil_jogador exista no JSON
        if "perfil_jogador" not in self.dados:
            self.dados["perfil_jogador"] = _perfil_padrao()

        perfil = self.dados["perfil_jogador"]
        antigo_principal = perfil.get("arquetipo_principal", "INDEFINIDO")
        confianca_antiga = perfil.get("confianca", 0.0)
        historico = perfil.get("historico_arquetipos", [])

        # Adiciona ao histórico
        historico.append(novo_principal)
        if len(historico) > _TAMANHO_HISTORICO:
            historico = historico[-_TAMANHO_HISTORICO:]
        perfil["historico_arquetipos"] = historico

        # --- Lógica de suavização ---
        deve_trocar = False

        if antigo_principal == "INDEFINIDO":
            # Primeiro arquétipo real detectado: trocar sempre
            deve_trocar = True
        elif novo_principal == antigo_principal:
            # Mesmo arquétipo: apenas atualizar confiança
            perfil["confianca"] = nova_confianca
            perfil["arquetipo_secundario"] = novo_secundario
        else:
            # Arquétipo diferente: verificar histerese
            ganho_confianca = nova_confianca - confianca_antiga
            if ganho_confianca >= _HISTERESE_CONFIANCA:
                deve_trocar = True
            else:
                # Verificar se apareceu N vezes consecutivas no histórico
                ultimos = historico[-_CONSECUTIVAS_PARA_TROCAR:]
                if len(ultimos) >= _CONSECUTIVAS_PARA_TROCAR and all(
                    a == novo_principal for a in ultimos
                ):
                    deve_trocar = True

        if deve_trocar:
            perfil["arquetipo_principal"] = novo_principal
            perfil["arquetipo_secundario"] = novo_secundario
            perfil["confianca"] = nova_confianca
            _log(f"Arquétipo atualizado: {novo_principal} (conf={nova_confianca})")

        self.dados["perfil_jogador"] = perfil
        self.salvar()

    # =================================================================
    # RESUMO PREDATÓRIO
    # =================================================================
    def obter_resumo_predatorio(self):
        """
        Retorna dicionário consolidado com arquétipo e métricas-chave.
        Pronto para ser consumido por qualquer sistema de decisão.
        """
        m = self.obter_metricas_normalizadas()

        if "perfil_jogador" not in self.dados:
            self.dados["perfil_jogador"] = _perfil_padrao()

        perfil = self.dados["perfil_jogador"]

        return {
            "arquetipo_principal": perfil.get("arquetipo_principal", "INDEFINIDO"),
            "arquetipo_secundario": perfil.get("arquetipo_secundario", "INDEFINIDO"),
            "confianca": perfil.get("confianca", 0.0),
            "medo": m["medo"],
            "agressividade": m["agressividade"],
            "dependencia_dash": m["dependencia_dash"],
            "dependencia_orbe": m["dependencia_orbe"],
            "previsibilidade": m["previsibilidade"],
            "tendencia_canto": m["tendencia_canto"],
            "adaptabilidade": m["adaptabilidade"],
        }

    def imprimir_resumo_predatorio(self):
        """
        Imprime no terminal o arquétipo e métricas.
        Só executa se DEBUG_DOSSIE = True.
        """
        if not DEBUG_DOSSIE:
            return

        r = self.obter_resumo_predatorio()
        return r

    # =================================================================
    # MODIFICADORES ADAPTATIVOS PARA A UMBRA
    # =================================================================

    # Mapa: arquétipo → lista de modificadores (máximo 2 por arquétipo)
    _MAPA_MODIFICADORES = {
        "REFUGIADO_DE_CANTO": [
            {"id": "CORTAR_BORDAS", "intensidade": 0.25,
             "descricao": "Pressionar jogador para fora dos cantos"},
        ],
        "DEPENDENTE_DE_DASH": [
            {"id": "PUNIR_DASH_PREVISIVEL", "intensidade": 0.20,
             "descricao": "Atrasar ataques para pegar o fim do dash"},
        ],
        "CACADOR_DE_ORBES": [
            {"id": "ISCA_DE_ORBE", "intensidade": 0.20,
             "descricao": "Posicionar entre jogador e orbe"},
        ],
        "AGRESSOR_IMPULSIVO": [
            {"id": "CONTRA_IMPULSO", "intensidade": 0.20,
             "descricao": "Recuo e punição curta quando jogador avança"},
        ],
        "ATIRADOR_DISTANTE": [
            {"id": "QUEBRAR_DISTANCIA", "intensidade": 0.25,
             "descricao": "Aproximação e mudança de ângulo"},
        ],
        "CORREDOR_CIRCULAR": [
            {"id": "QUEBRAR_ROTACAO", "intensidade": 0.20,
             "descricao": "Ataques em área e reposicionamento"},
        ],
        "SOBREVIVENTE_ADAPTATIVO": [
            {"id": "RESPEITAR_ADAPTATIVO", "intensidade": 0.10,
             "descricao": "Variar decisões sem hard counter"},
        ],
        "INDEFINIDO": [],
    }

    def obter_modificadores_umbra(self):
        """
        Retorna lista com no máximo 2 modificadores comportamentais
        baseados no arquétipo principal e secundário do jogador.

        Cada item: {"id": str, "intensidade": float, "descricao": str}
        """
        if "perfil_jogador" not in self.dados:
            return []

        perfil = self.dados["perfil_jogador"]
        principal = perfil.get("arquetipo_principal", "INDEFINIDO")
        secundario = perfil.get("arquetipo_secundario", "INDEFINIDO")
        confianca = perfil.get("confianca", 0.0)

        # Confiança muito baixa → sem adaptação
        if confianca < 0.20:
            _log("Confiança baixa demais para adaptar.")
            return []

        mods = []

        # Modificadores do arquétipo principal (intensidade total)
        for mod in self._MAPA_MODIFICADORES.get(principal, []):
            mods.append({
                "id": mod["id"],
                "intensidade": round(mod["intensidade"] * confianca, 3),
                "descricao": mod["descricao"],
            })

        # Modificador do secundário (intensidade reduzida a 40%)
        if len(mods) < 2 and secundario != principal:
            for mod in self._MAPA_MODIFICADORES.get(secundario, []):
                if not any(m["id"] == mod["id"] for m in mods):
                    mods.append({
                        "id": mod["id"],
                        "intensidade": round(mod["intensidade"] * confianca * 0.4, 3),
                        "descricao": mod["descricao"],
                    })
                    if len(mods) >= 2:
                        break

        # Limitar a 2 modificadores
        mods = mods[:2]

        # Persistir no JSON
        if "adaptacoes_umbra" not in self.dados:
            self.dados["adaptacoes_umbra"] = {
                "modificadores_ativos": [],
                "vezes_aplicadas": {},
                "ultima_luta": {},
            }

        ids_ativos = [m["id"] for m in mods]
        self.dados["adaptacoes_umbra"]["modificadores_ativos"] = ids_ativos
        for mid in ids_ativos:
            self.dados["adaptacoes_umbra"]["vezes_aplicadas"][mid] = (
                self.dados["adaptacoes_umbra"]["vezes_aplicadas"].get(mid, 0) + 1
            )
        self.dados["adaptacoes_umbra"]["ultima_luta"] = {
            "arquetipo": principal,
            "secundario": secundario,
            "confianca": confianca,
            "modificadores": ids_ativos,
        }

        self.salvar()
        _log(f"Modificadores ativos: {ids_ativos} (arq={principal}, conf={confianca})")
        return mods
