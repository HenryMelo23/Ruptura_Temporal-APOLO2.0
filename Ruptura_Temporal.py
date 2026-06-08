
#Este projeto estÃ¡ licenciado sob a Creative Commons Attribution-NonCommercial-ShareAlike 4.0.
#Uso comercial Ã© estritamente proibido. ModificaÃ§Ãµes e redistribuiÃ§Ãµes sÃ£o permitidas sob as mesmas condiÃ§Ãµes.



import Caminhos
import pygame
import sys
import importlib
import os
import json
import uuid
import math
import random
import pyperclip
from qa_logger import instalar_captura_global, instalar_filtro_prints, registrar_erro
from Config_Teclas import tela_de_controles,carregar_config_teclas
from Variaveis import largura_tela, altura_tela, python
from rede import descobrir_host_udp, conectar_ao_host
from audio_manager import carregar_config_audio, aplicar_volume_musica, aplicar_volume_som
from utils import configurar_tela, tocar_trailer_se_necessario, redimensionar_cover, carregar_upgrade_aureas
from sons_procedurais import tocar_hover, tocar_selecionar
from dados_aureas import AUREAS_DADOS
from Tela_Manifestacoes import tela_manifestacoes
import ui_helpers

instalar_captura_global()
instalar_filtro_prints()


def _normalizar_texto_render(texto):
    if not isinstance(texto, str):
        return texto

    def _bytes_mojibake(valor):
        dados = bytearray()
        for char in valor:
            codigo = ord(char)
            if codigo <= 255:
                dados.append(codigo)
                continue
            try:
                dados.extend(char.encode("cp1252"))
            except UnicodeEncodeError:
                return None
        return bytes(dados)

    texto = texto.replace("\ufeff", "")
    marcadores = ("Ã", "Â", "â", "�")
    for _ in range(4):
        if not any(m in texto for m in marcadores):
            break
        dados = _bytes_mojibake(texto)
        if not dados:
            break
        try:
            novo = dados.decode("utf-8")
        except UnicodeError:
            break
        if novo == texto:
            break
        texto = novo

    return texto.replace("•", "-").replace("\xa0", " ")


class _FonteTextoSeguro:
    def __init__(self, fonte_real):
        self._fonte_real = fonte_real

    def render(self, texto, *args, **kwargs):
        return self._fonte_real.render(_normalizar_texto_render(texto), *args, **kwargs)

    def size(self, texto):
        return self._fonte_real.size(_normalizar_texto_render(texto))

    def metrics(self, texto):
        return self._fonte_real.metrics(_normalizar_texto_render(texto))

    def __getattr__(self, nome):
        return getattr(self._fonte_real, nome)


if not hasattr(pygame.font, "_rt_font_original"):
    pygame.font._rt_font_original = pygame.font.Font

    def _font_segura(*args, **kwargs):
        return _FonteTextoSeguro(pygame.font._rt_font_original(*args, **kwargs))

    pygame.font.Font = _font_segura


# --- DeclaraÃ§Ã£o de VariÃ¡veis Globais (InicializaÃ§Ã£o Adiada para Evitar Telas Pretas por Dupla ImportaÃ§Ã£o) ---
tela = None
fundo_menu1 = None
fundo_menu2 = None
fundo_menu3 = None
fundo_menu4 = None
fundo_menu5 = None
imagens_fundo = []

caminho_fonte_letras = "Texto/Broken.otf"
tamanho_fonte_letras = 20
caminho_fonte_letra1 = "Texto/World.otf"
caminho_fonte_titulo = "Texto/Top_Menu.otf"
tamanho_fonte_titulo = 72

cor_letra = (40, 10, 88)
branco = (255, 255, 255)
cor_fundo_botao = (255, 255, 255, 100)
contorno_rosa = (255, 105, 180)
Letras_Of = caminho_fonte_letras

fonte_titulo = None
fonte_coop = None
fonte_letras = None
fonte_letra1 = None
fonte = None
fonte_instrucao = None
fonte_config = None
fonte_opcao = None
fonte_fallback_titulo = None
fonte_fallback_config = None

titulo_jogo = "Ruptura Temporal (2.0)"
posicao_titulo = (largura_tela // 2, altura_tela // 8)


class PopUpAplicar:
    def __init__(self, largura_tela, altura_tela):
        self.largura_tela = largura_tela
        self.altura_tela = altura_tela
        self.ativo = False
        self.estado = "INATIVO" # "ENTRADA", "ESTAVEL", "EXPLOSAO", "INATIVO"spwa
        self.tempo_inicio_estado = 0
        self.duracao_entrada = 800  # ms
        self.duracao_estavel = 700 # ms
        self.duracao_explosao = 600 # ms

        self.w_popup = 360
        self.h_popup = 110
        self.x_popup = (largura_tela - self.w_popup) // 2
        self.y_popup = (altura_tela - self.h_popup) // 2
        self.centro = (largura_tela // 2, altura_tela // 2)

        self.particulas = []
        self.raio_ondas = []

    def disparar(self, agora):
        self.ativo = True
        self.estado = "ENTRADA"
        self.tempo_inicio_estado = agora
        self.raio_ondas = []
        self.particulas = []

        # Gerar partículas que vão se juntar
        num_particulas = 80
        for _ in range(num_particulas):
            tx = random.randint(self.x_popup, self.x_popup + self.w_popup)
            ty = random.randint(self.y_popup, self.y_popup + self.h_popup)

            # Ponto de origem: círculo distante ao redor do centro
            angulo = random.uniform(0, 2 * math.pi)
            distancia = random.uniform(300, 500)
            ox = self.centro[0] + math.cos(angulo) * distancia
            oy = self.centro[1] + math.sin(angulo) * distancia

            cor = random.choice([
                (0, 191, 255),  # Azul elétrico
                (0, 255, 230),  # Ciano neon
                (100, 200, 255) # Azul claro
            ])

            self.particulas.append({
                "ox": ox, "oy": oy,
                "tx": tx, "ty": ty,
                "x": ox, "y": oy,
                "cor": cor,
                "tamanho": random.randint(2, 5),
                "alpha": 0
            })

    def update(self, agora):
        if not self.ativo:
            return

        tempo_decorrido = agora - self.tempo_inicio_estado

        if self.estado == "ENTRADA":
            progresso = min(1.0, tempo_decorrido / self.duracao_entrada)
            t = progresso
            ease = 1 - (1 - t) ** 3 # easeOutCubic

            for p in self.particulas:
                p["x"] = p["ox"] + (p["tx"] - p["ox"]) * ease
                p["y"] = p["oy"] + (p["ty"] - p["oy"]) * ease
                p["alpha"] = int(progresso * 255)

            if tempo_decorrido >= self.duracao_entrada:
                self.estado = "ESTAVEL"
                self.tempo_inicio_estado = agora
                # Gerar algumas partículas de ambiente
                self.particulas = []
                for _ in range(15):
                    self.particulas.append(self._criar_particula_estavel())

        elif self.estado == "ESTAVEL":
            for p in self.particulas:
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                p["vida"] -= 1
                if p["vida"] <= 0:
                    p.update(self._criar_particula_estavel())

            if tempo_decorrido >= self.duracao_estavel:
                self._explodir(agora)

        elif self.estado == "EXPLOSAO":
            inativas = 0
            for p in self.particulas:
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                p["vx"] *= 0.95
                p["vy"] *= 0.95
                p["alpha"] = max(0, p["alpha"] - 6)
                if p["alpha"] <= 0:
                    inativas += 1

            for onda in self.raio_ondas:
                onda["raio"] += onda["velocidade"]
                onda["alpha"] = max(0, onda["alpha"] - 8)

            todas_ondas_sumiram = all(o["alpha"] <= 0 for o in self.raio_ondas)
            if (inativas == len(self.particulas) and todas_ondas_sumiram) or tempo_decorrido >= self.duracao_explosao:
                self.ativo = False
                self.estado = "INATIVO"

    def _criar_particula_estavel(self):
        x = random.randint(self.x_popup, self.x_popup + self.w_popup)
        y = random.randint(self.y_popup, self.y_popup + self.h_popup)
        return {
            "x": x, "y": y,
            "vx": random.uniform(-0.3, 0.3),
            "vy": random.uniform(-0.3, 0.3),
            "cor": random.choice([(0, 191, 255), (0, 255, 230)]),
            "tamanho": random.randint(1, 3),
            "alpha": random.randint(100, 200),
            "vida": random.randint(30, 80)
        }

    def _explodir(self, agora):
        self.estado = "EXPLOSAO"
        self.tempo_inicio_estado = agora

        self.raio_ondas = [
            {"raio": 10, "velocidade": 9, "alpha": 255, "espessura": 4},
            {"raio": 25, "velocidade": 7, "alpha": 200, "espessura": 2}
        ]

        self.particulas = []
        num_particulas = 90
        for _ in range(num_particulas):
            x = random.randint(self.x_popup, self.x_popup + self.w_popup)
            y = random.randint(self.y_popup, self.y_popup + self.h_popup)

            dx = x - self.centro[0]
            dy = y - self.centro[1]
            dist = math.hypot(dx, dy)
            if dist == 0:
                ang = random.uniform(0, 2 * math.pi)
                vx = math.cos(ang) * random.uniform(4, 10)
                vy = math.sin(ang) * random.uniform(4, 10)
            else:
                fator = random.uniform(3, 8)
                vx = (dx / dist) * fator + random.uniform(-2, 2)
                vy = (dy / dist) * fator + random.uniform(-2, 2)

            self.particulas.append({
                "x": x, "y": y,
                "vx": vx, "vy": vy,
                "cor": random.choice([(0, 191, 255), (0, 255, 230), (255, 255, 255)]),
                "tamanho": random.randint(2, 5),
                "alpha": 255
            })

    def draw(self, tela):
        if not self.ativo:
            return

        # Desenhar partículas (entrada ou explosão)
        if self.estado in ["ENTRADA", "EXPLOSAO"]:
            for p in self.particulas:
                if p["alpha"] <= 0:
                    continue
                s = pygame.Surface((p["tamanho"] * 2, p["tamanho"] * 2), pygame.SRCALPHA)
                pygame.draw.circle(s, (p["cor"][0], p["cor"][1], p["cor"][2], p["alpha"]), (p["tamanho"], p["tamanho"]), p["tamanho"])
                tela.blit(s, (int(p["x"]) - p["tamanho"], int(p["y"]) - p["tamanho"]))

        # Desenhar ondas de choque (explosão)
        if self.estado == "EXPLOSAO":
            for onda in self.raio_ondas:
                if onda["alpha"] <= 0:
                    continue
                s_circ = pygame.Surface((onda["raio"] * 2 + 10, onda["raio"] * 2 + 10), pygame.SRCALPHA)
                pygame.draw.circle(s_circ, (0, 191, 255, onda["alpha"]), (onda["raio"] + 5, onda["raio"] + 5), onda["raio"], onda["espessura"])
                tela.blit(s_circ, (self.centro[0] - onda["raio"] - 5, self.centro[1] - onda["raio"] - 5))

        # Desenhar painel principal (glassmorphism)
        if self.estado in ["ENTRADA", "ESTAVEL"]:
            alpha = 255
            if self.estado == "ENTRADA":
                tempo_decorrido = pygame.time.get_ticks() - self.tempo_inicio_estado
                percent = min(1.0, tempo_decorrido / self.duracao_entrada)
                if percent < 0.5:
                    return # não desenha o painel principal, apenas as partículas
                alpha = int((percent - 0.5) * 2 * 255)

            popup_surf = pygame.Surface((self.w_popup, self.h_popup), pygame.SRCALPHA)
            bg_alpha = int(alpha * 0.85)
            pygame.draw.rect(popup_surf, (8, 12, 28, bg_alpha), (0, 0, self.w_popup, self.h_popup), border_radius=12)
            pygame.draw.rect(popup_surf, (0, 255, 230, alpha), (0, 0, self.w_popup, self.h_popup), width=3, border_radius=12)

            # Detalhes decorativos nos cantos
            pygame.draw.line(popup_surf, (255, 255, 255, alpha), (15, 0), (35, 0), 3)
            pygame.draw.line(popup_surf, (255, 255, 255, alpha), (self.w_popup - 35, 0), (self.w_popup - 15, 0), 3)
            pygame.draw.line(popup_surf, (255, 255, 255, alpha), (0, 15), (0, 35), 3)
            pygame.draw.line(popup_surf, (255, 255, 255, alpha), (self.w_popup, 15), (self.w_popup, 35), 3)

            # Texto
            try:
                fonte_pop = pygame.font.Font(caminho_fonte_titulo, 22)
                fonte_pop_sub = pygame.font.Font(caminho_fonte_letras, 14)
            except Exception:
                fonte_pop = pygame.font.Font(None, 24)
                fonte_pop_sub = pygame.font.Font(None, 16)

            texto_p = "ALTERACOES APLICADAS"
            texto_surf = fonte_pop.render(texto_p, True, (0, 255, 204, alpha))
            tx = (self.w_popup - texto_surf.get_width()) // 2
            ty = (self.h_popup - texto_surf.get_height()) // 2 - 12

            sub_texto = "Configuracoes salvas com sucesso!"
            sub_surf = fonte_pop_sub.render(sub_texto, True, (255, 255, 255, int(alpha * 0.7)))
            tsx = (self.w_popup - sub_surf.get_width()) // 2
            tsy = ty + texto_surf.get_height() + 8

            popup_surf.blit(texto_surf, (tx, ty))
            popup_surf.blit(sub_surf, (tsx, tsy))

            if self.estado == "ESTAVEL":
                for p in self.particulas:
                    px_rel = p["x"] - self.x_popup
                    py_rel = p["y"] - self.y_popup
                    if 0 <= px_rel <= self.w_popup and 0 <= py_rel <= self.h_popup:
                        pygame.draw.circle(popup_surf, (p["cor"][0], p["cor"][1], p["cor"][2], p["alpha"]), (int(px_rel), int(py_rel)), p["tamanho"])

            tela.blit(popup_surf, (self.x_popup, self.y_popup))

    def __init__(self, largura_tela, altura_tela):
        self.largura_tela = largura_tela
        self.altura_tela = altura_tela
        self.ativo = False
        self.estado = "INATIVO"
        self.tempo_inicio_estado = 0
        self.duracao_entrada = 520
        self.duracao_estavel = 700
        self.duracao_raio = 460
        self.duracao_explosao = 760

        self.w_popup = 360
        self.h_popup = 110
        self.x_popup = (largura_tela - self.w_popup) // 2
        self.y_popup = (altura_tela - self.h_popup) // 2
        self.centro = (largura_tela // 2, altura_tela // 2)
        self.raio_origem = (int(largura_tela * 0.92), -34)
        self.raio_alvo = self.centro

        self.particulas = []
        self.estavel_particulas = []
        self.raio_ondas = []
        self.raio_seed = []
        self.ramificacoes = []

    def disparar(self, agora):
        self.ativo = True
        self.estado = "ENTRADA"
        self.tempo_inicio_estado = agora
        self.particulas = []
        self.estavel_particulas = []
        self.raio_ondas = []
        self.ramificacoes = []
        self.raio_seed = [random.uniform(-1.0, 1.0) for _ in range(18)]

        for _ in range(42):
            tx = random.randint(self.x_popup, self.x_popup + self.w_popup)
            ty = random.randint(self.y_popup, self.y_popup + self.h_popup)
            angulo = random.uniform(0, math.tau)
            distancia = random.uniform(300, 520)
            ox = self.centro[0] + math.cos(angulo) * distancia
            oy = self.centro[1] + math.sin(angulo) * distancia
            self.particulas.append({
                "ox": ox, "oy": oy,
                "tx": tx, "ty": ty,
                "x": ox, "y": oy,
                "cor": random.choice([(30, 170, 255), (0, 245, 255), (135, 220, 255)]),
                "tamanho": random.randint(2, 5),
                "alpha": 0,
            })

    def update(self, agora):
        if not self.ativo:
            return

        tempo_decorrido = agora - self.tempo_inicio_estado

        if self.estado == "ENTRADA":
            progresso = min(1.0, tempo_decorrido / self.duracao_entrada)
            ease = 1 - (1 - progresso) ** 3
            for p in self.particulas:
                p["x"] = p["ox"] + (p["tx"] - p["ox"]) * ease
                p["y"] = p["oy"] + (p["ty"] - p["oy"]) * ease
                p["alpha"] = int(progresso * 255)
            if tempo_decorrido >= self.duracao_entrada:
                self.estado = "ESTAVEL"
                self.tempo_inicio_estado = agora
                self.particulas = []
                self.estavel_particulas = [self._criar_particula_estavel() for _ in range(18)]

        elif self.estado == "ESTAVEL":
            for p in self.estavel_particulas:
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                p["vida"] -= 1
                if p["vida"] <= 0:
                    p.update(self._criar_particula_estavel())
            if tempo_decorrido >= self.duracao_estavel:
                self._iniciar_raio(agora)

        elif self.estado == "RAIO":
            if tempo_decorrido >= self.duracao_raio:
                self._explodir(agora)

        elif self.estado == "EXPLOSAO":
            inativas = 0
            for p in self.particulas:
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                p["vx"] *= p["drag"]
                p["vy"] = p["vy"] * p["drag"] + p["grav"]
                p["vida"] -= 1
                p["alpha"] = max(0, int(255 * (p["vida"] / p["vida_max"])))
                if p["alpha"] <= 0:
                    inativas += 1

            for onda in self.raio_ondas:
                onda["raio"] += onda["velocidade"]
                onda["alpha"] = max(0, onda["alpha"] - onda["fade"])

            ondas_sumiram = all(onda["alpha"] <= 0 for onda in self.raio_ondas)
            if (inativas == len(self.particulas) and ondas_sumiram) or tempo_decorrido >= self.duracao_explosao:
                self.ativo = False
                self.estado = "INATIVO"

    def _iniciar_raio(self, agora):
        self.estado = "RAIO"
        self.tempo_inicio_estado = agora
        self.particulas = []
        self.raio_alvo = (
            self.x_popup + self.w_popup // 2 + random.randint(-22, 22),
            self.y_popup + self.h_popup // 2 + random.randint(-10, 10),
        )
        self.ramificacoes = []

        for _ in range(44):
            lado = random.randrange(4)
            if lado == 0:
                destino = (random.randint(self.x_popup, self.x_popup + self.w_popup), self.y_popup)
            elif lado == 1:
                destino = (self.x_popup + self.w_popup, random.randint(self.y_popup, self.y_popup + self.h_popup))
            elif lado == 2:
                destino = (random.randint(self.x_popup, self.x_popup + self.w_popup), self.y_popup + self.h_popup)
            else:
                destino = (self.x_popup, random.randint(self.y_popup, self.y_popup + self.h_popup))

            sx, sy = self.raio_alvo
            dx = destino[0] - sx
            dy = destino[1] - sy
            passos = random.randint(3, 6)
            pontos = []
            for i in range(passos + 1):
                t = i / passos
                pontos.append((
                    sx + dx * t + random.uniform(-18, 18) * (1.0 - t),
                    sy + dy * t + random.uniform(-10, 10),
                ))

            self.ramificacoes.append({
                "pontos": pontos,
                "delay": random.uniform(0.08, 0.28),
                "cor": random.choice([(0, 210, 255), (40, 130, 255), (160, 240, 255)]),
                "largura": random.choice([1, 1, 2]),
            })

    def _explodir(self, agora):
        self.estado = "EXPLOSAO"
        self.tempo_inicio_estado = agora
        self.raio_ondas = [
            {"raio": 10, "velocidade": 19, "alpha": 245, "espessura": 5, "fade": 18},
            {"raio": 34, "velocidade": 13, "alpha": 190, "espessura": 3, "fade": 15},
            {"raio": 68, "velocidade": 8, "alpha": 130, "espessura": 2, "fade": 11},
        ]
        self.particulas = []
        impacto_x, impacto_y = self.raio_alvo
        for i in range(260):
            ang = (i / 260) * math.tau + random.uniform(-0.035, 0.035)
            borda_x = self.x_popup + self.w_popup * random.random()
            borda_y = self.y_popup + self.h_popup * random.random()
            x = impacto_x * 0.62 + borda_x * 0.38 + random.uniform(-16, 16)
            y = impacto_y * 0.62 + borda_y * 0.38 + random.uniform(-12, 12)
            velocidade = random.uniform(3.8, 13.5) * (1.0 + 0.45 * random.random())
            vx = math.cos(ang) * velocidade + (x - impacto_x) * 0.018
            vy = math.sin(ang) * velocidade + (y - impacto_y) * 0.018
            vida = random.randint(30, 52)
            self.particulas.append({
                "x": x, "y": y,
                "vx": vx, "vy": vy,
                "grav": random.uniform(0.015, 0.06),
                "drag": random.uniform(0.925, 0.968),
                "cor": random.choice([(0, 210, 255), (0, 255, 255), (80, 160, 255), (210, 250, 255)]),
                "tamanho": random.choice([1, 1, 2, 2, 3, 4]),
                "alpha": 255,
                "vida": vida,
                "vida_max": vida,
            })

    def draw(self, tela):
        if not self.ativo:
            return

        if self.estado == "ENTRADA":
            self._draw_particulas_entrada(tela)

        if self.estado in ["ENTRADA", "ESTAVEL", "RAIO"]:
            alpha = 255
            if self.estado == "ENTRADA":
                tempo_decorrido = pygame.time.get_ticks() - self.tempo_inicio_estado
                percent = max(0.0, min(1.0, tempo_decorrido / self.duracao_entrada))
                if percent < 0.5:
                    return
                alpha = int((percent - 0.5) * 2 * 255)
            elif self.estado == "RAIO":
                tempo_decorrido = pygame.time.get_ticks() - self.tempo_inicio_estado
                p = max(0.0, min(1.0, tempo_decorrido / self.duracao_raio))
                alpha = max(45, int(255 * (1.0 - max(0.0, p - 0.66) / 0.34)))
            self._draw_popup_panel(tela, alpha)

        if self.estado == "RAIO":
            self._draw_raio(tela)

        if self.estado == "EXPLOSAO":
            self._draw_explosao(tela)

    def _draw_particulas_entrada(self, tela):
        for p in self.particulas:
            if p["alpha"] <= 0:
                continue
            tamanho = p["tamanho"]
            s = pygame.Surface((tamanho * 2 + 8, tamanho * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(s, (*p["cor"], p["alpha"] // 3), (tamanho + 4, tamanho + 4), tamanho + 4)
            pygame.draw.circle(s, (*p["cor"], p["alpha"]), (tamanho + 4, tamanho + 4), tamanho)
            tela.blit(s, (int(p["x"]) - tamanho - 4, int(p["y"]) - tamanho - 4), special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_popup_panel(self, tela, alpha):
        popup_surf = pygame.Surface((self.w_popup, self.h_popup), pygame.SRCALPHA)
        pygame.draw.rect(popup_surf, (5, 10, 26, int(alpha * 0.84)), (0, 0, self.w_popup, self.h_popup), border_radius=12)
        pygame.draw.rect(popup_surf, (0, 235, 255, alpha), (0, 0, self.w_popup, self.h_popup), width=3, border_radius=12)
        pygame.draw.rect(popup_surf, (60, 110, 255, int(alpha * 0.42)), (5, 5, self.w_popup - 10, self.h_popup - 10), width=1, border_radius=9)

        brilho = max(0, int(alpha * 0.65))
        pygame.draw.line(popup_surf, (255, 255, 255, brilho), (15, 0), (48, 0), 3)
        pygame.draw.line(popup_surf, (255, 255, 255, brilho), (self.w_popup - 48, 0), (self.w_popup - 15, 0), 3)
        pygame.draw.line(popup_surf, (255, 255, 255, brilho), (0, 15), (0, 48), 3)
        pygame.draw.line(popup_surf, (255, 255, 255, brilho), (self.w_popup, 15), (self.w_popup, 48), 3)

        try:
            fonte_pop = pygame.font.Font(caminho_fonte_titulo, 22)
            fonte_pop_sub = pygame.font.Font(caminho_fonte_letras, 14)
        except Exception:
            fonte_pop = pygame.font.Font(None, 24)
            fonte_pop_sub = pygame.font.Font(None, 16)

        texto_surf = fonte_pop.render("ALTERACOES APLICADAS", True, (0, 255, 220, alpha))
        tx = (self.w_popup - texto_surf.get_width()) // 2
        ty = (self.h_popup - texto_surf.get_height()) // 2 - 12
        sub_surf = fonte_pop_sub.render("Configuracoes salvas com sucesso!", True, (230, 250, 255, int(alpha * 0.72)))
        popup_surf.blit(texto_surf, (tx, ty))
        popup_surf.blit(sub_surf, ((self.w_popup - sub_surf.get_width()) // 2, ty + texto_surf.get_height() + 8))

        if self.estado == "ESTAVEL":
            for p in self.estavel_particulas:
                px_rel = p["x"] - self.x_popup
                py_rel = p["y"] - self.y_popup
                if 0 <= px_rel <= self.w_popup and 0 <= py_rel <= self.h_popup:
                    pygame.draw.circle(popup_surf, (*p["cor"], p["alpha"]), (int(px_rel), int(py_rel)), p["tamanho"])

        if self.estado == "RAIO":
            tempo_decorrido = pygame.time.get_ticks() - self.tempo_inicio_estado
            prog = max(0.0, min(1.0, tempo_decorrido / self.duracao_raio))
            impacto_rel = (self.raio_alvo[0] - self.x_popup, self.raio_alvo[1] - self.y_popup)
            pygame.draw.circle(popup_surf, (0, 245, 255, int(190 * min(1.0, prog * 2))), impacto_rel, int(18 + 26 * prog), 2)
            espalhar = max(0.0, min(1.0, (prog - 0.34) / 0.44))
            for ramo in self.ramificacoes:
                rprog = max(0.0, min(1.0, (espalhar - ramo["delay"]) / 0.55))
                if rprog <= 0:
                    continue
                pontos = [(int(x - self.x_popup), int(y - self.y_popup)) for x, y in ramo["pontos"]]
                usar = max(2, int(2 + (len(pontos) - 1) * rprog))
                pygame.draw.lines(popup_surf, (*ramo["cor"], int(160 * (1.0 - prog * 0.45))), False, pontos[:usar], ramo["largura"])
                pygame.draw.lines(popup_surf, (230, 255, 255, int(95 * (1.0 - prog * 0.35))), False, pontos[:usar], 1)

        tela.blit(popup_surf, (self.x_popup, self.y_popup))

    def _pontos_raio(self, progresso):
        ox, oy = self.raio_origem
        ax, ay = self.raio_alvo
        pontos = []
        total = 13
        dx = ax - ox
        dy = ay - oy
        normal_len = max(1.0, math.hypot(dx, dy))
        nx = -dy / normal_len
        ny = dx / normal_len
        chegada = min(1.0, progresso * 1.22)
        for i in range(total + 1):
            t = i / total
            jitter = self.raio_seed[i % len(self.raio_seed)] * (34 + 18 * math.sin(pygame.time.get_ticks() * 0.02 + i))
            pontos.append((int(ox + dx * t * chegada + nx * jitter * (0.25 + t)), int(oy + dy * t * chegada + ny * jitter * (0.25 + t))))
        pontos[-1] = (int(ox + dx * chegada), int(oy + dy * chegada))
        return pontos

    def _draw_raio(self, tela):
        tempo_decorrido = pygame.time.get_ticks() - self.tempo_inicio_estado
        prog = max(0.0, min(1.0, tempo_decorrido / self.duracao_raio))
        pontos = self._pontos_raio(prog)
        min_x = max(0, min(p[0] for p in pontos) - 90)
        min_y = max(0, min(p[1] for p in pontos) - 90)
        max_x = min(self.largura_tela, max(p[0] for p in pontos) + 90)
        max_y = min(self.altura_tela, max(p[1] for p in pontos) + 90)
        camada = pygame.Surface((max(1, max_x - min_x), max(1, max_y - min_y)), pygame.SRCALPHA)
        locais = [(x - min_x, y - min_y) for x, y in pontos]
        flash = 0.55 + 0.45 * math.sin(tempo_decorrido * 0.075)
        pygame.draw.lines(camada, (0, 85, 255, int(82 * flash)), False, locais, 18)
        pygame.draw.lines(camada, (0, 220, 255, int(165 * flash)), False, locais, 9)
        pygame.draw.lines(camada, (235, 255, 255, 245), False, locais, 3)

        if prog > 0.28:
            ix, iy = self.raio_alvo[0] - min_x, self.raio_alvo[1] - min_y
            choque = min(1.0, (prog - 0.28) / 0.52)
            pygame.draw.circle(camada, (0, 210, 255, int(130 * (1.0 - choque * 0.45))), (ix, iy), 34 + int(70 * choque), 3)
            pygame.draw.circle(camada, (0, 245, 255, int(210 * (1.0 - choque * 0.45))), (ix, iy), 10 + int(30 * choque), 2)
            pygame.draw.circle(camada, (245, 255, 255, 230), (ix, iy), max(5, int(14 - 7 * choque)))

        tela.blit(camada, (min_x, min_y), special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_explosao(self, tela):
        if not self.particulas:
            return
        min_x = max(0, int(min(p["x"] for p in self.particulas)) - 18)
        min_y = max(0, int(min(p["y"] for p in self.particulas)) - 18)
        max_x = min(self.largura_tela, int(max(p["x"] for p in self.particulas)) + 18)
        max_y = min(self.altura_tela, int(max(p["y"] for p in self.particulas)) + 18)
        camada = pygame.Surface((max(1, max_x - min_x), max(1, max_y - min_y)), pygame.SRCALPHA)
        for p in self.particulas:
            if p["alpha"] <= 0:
                continue
            x = int(p["x"] - min_x)
            y = int(p["y"] - min_y)
            r = p["tamanho"]
            pygame.draw.circle(camada, (*p["cor"], p["alpha"]), (x, y), r)
            if r >= 3:
                pygame.draw.circle(camada, (220, 255, 255, p["alpha"] // 3), (x, y), r + 3, 1)
        tela.blit(camada, (min_x, min_y), special_flags=pygame.BLEND_RGBA_ADD)
ajuste_vertical = int(altura_tela * 0.12)

opcoes = ["Iniciar Jornada", "Catalogo", "ConfiguraÃ§Ã£o", "Sair"]
indice_selecionado = 0
DELAY_ENTRE_OPCOES = 100
ultima_mudanca_de_opcao = 0

tempo_exibicao_fundo1 = 5000
tempo_troca_fundo = 150
indice_fundo = 0
exibindo_fundo1 = True
ultima_troca = 0
controle = None
analogo_movido = False

def render_glitch_text_with_fallback(texto, fonte_glitch, fonte_fallback, cor):
    """
    Rendeiriza texto caractere por caractere. Usa a fonte_fallback se o caractere for acentuado
    ou especial, pois a fonte Doctor Glitch/Top_Menu nÃ£o possui suporte a estes glifos.
    """
    texto = _normalizar_texto_render(texto)
    surfaces = []
    largura_total = 0
    altura_max = 0

    for char in texto:
        # Verifica se o caractere precisa de fallback (acentos latinos, Ã‡, etc.)
        ord_char = ord(char)
        if ord_char > 127 or char in "ÇçÃãÕõÉéÍíÓóÚúÂâÊêÔôÀà":
            char_surf = fonte_fallback.render(char, True, cor)
        else:
            char_surf = fonte_glitch.render(char, True, cor)
        surfaces.append(char_surf)
        largura_total += char_surf.get_width()
        altura_max = max(altura_max, char_surf.get_height())

    surf_final = pygame.Surface((largura_total, altura_max), pygame.SRCALPHA)
    x_offset = 0
    for char_surf in surfaces:
        y_offset = (altura_max - char_surf.get_height()) // 2
        surf_final.blit(char_surf, (x_offset, y_offset))
        x_offset += char_surf.get_width()

    return surf_final

def inicializar_menu():
    global tela, fundo_menu1, fundo_menu2, fundo_menu3, fundo_menu4, fundo_menu5, imagens_fundo
    global fonte_titulo, fonte_coop, fonte_letras, fonte_letra1, fonte, fonte_instrucao, fonte_config, fonte_opcao
    global fonte_fallback_titulo, fonte_fallback_config
    global ultima_troca, ultima_mudanca_de_opcao, controle

    if tela is not None:
        try:
            if tela is pygame.display.get_surface() and tela.get_size() == (largura_tela, altura_tela):
                tela.fill((0, 0, 0))
                return
            tela = None
        except pygame.error:
            tela = None

    pygame.init()
    pygame.mouse.set_visible(False)
    centro_tela = (largura_tela // 2, altura_tela // 2)
    pygame.mouse.set_pos(centro_tela)

    tela = configurar_tela(largura_tela, altura_tela)
    tocar_trailer_se_necessario(tela)
    pygame.display.set_caption("Menu do Jogo")

    fundo_menu1 = pygame.image.load("Sprites/Melhoria_1.png")
    fundo_menu2 = pygame.image.load("Sprites/Melhoria_2.png")
    fundo_menu3 = pygame.image.load("Sprites/Melhoria_3.png")
    fundo_menu4 = pygame.image.load("Sprites/Melhoria_4.png")
    fundo_menu5 = pygame.image.load("Sprites/Melhoria_5.png")

    fundo_menu1 = redimensionar_cover(fundo_menu1, largura_tela, altura_tela)
    fundo_menu2 = redimensionar_cover(fundo_menu2, largura_tela, altura_tela)
    fundo_menu3 = redimensionar_cover(fundo_menu3, largura_tela, altura_tela)
    fundo_menu4 = redimensionar_cover(fundo_menu4, largura_tela, altura_tela)
    fundo_menu5 = redimensionar_cover(fundo_menu5, largura_tela, altura_tela)

    imagens_fundo.extend([fundo_menu1, fundo_menu4, fundo_menu2, fundo_menu4, fundo_menu5, fundo_menu3, fundo_menu2, fundo_menu3,
                          fundo_menu4, fundo_menu5, fundo_menu3, fundo_menu2, fundo_menu5])

    fonte_titulo = pygame.font.Font(caminho_fonte_titulo, tamanho_fonte_titulo)
    ajuste_tamanho_fonte = int(tamanho_fonte_titulo * 0.80)
    fonte_coop = pygame.font.Font(caminho_fonte_titulo, ajuste_tamanho_fonte)

    fonte_letras = pygame.font.Font(caminho_fonte_letras, tamanho_fonte_letras)
    fonte_letra1 = pygame.font.Font(caminho_fonte_letra1, tamanho_fonte_letras)
    fonte = fonte_letras
    fonte_instrucao = pygame.font.Font(caminho_fonte_letras, 18)
    fonte_config = pygame.font.Font(caminho_fonte_titulo, 48)
    fonte_opcao = pygame.font.Font(caminho_fonte_letra1, 32)
    fonte_fallback_titulo = pygame.font.Font(caminho_fonte_letra1, tamanho_fonte_titulo)
    fonte_fallback_config = pygame.font.Font(caminho_fonte_letra1, 48)

    ultima_troca = pygame.time.get_ticks()
    ultima_mudanca_de_opcao = pygame.time.get_ticks()

    pygame.mixer.init()
    pygame.mixer.music.load("Sounds/Menu.mp3")
    config_audio = carregar_config_audio()
    aplicar_volume_musica(config_audio)
    pygame.mixer.music.play(-1)

    pygame.joystick.init()
    if pygame.joystick.get_count() > 0:
        controle = pygame.joystick.Joystick(0)
        controle.init()
    else:
        controle = None



def tela_inserir_nome(tela):
    nome = ""
    clock = pygame.time.Clock()
    fonte_input = pygame.font.Font("Texto/World.otf", 48)
    fonte_instrucao = pygame.font.Font(caminho_fonte_letras, 18)

    while True:
        tela.fill((10, 10, 10))

        texto_titulo = fonte_titulo.render("IDENTIFIQUE-SE", True, (0, 255, 204))
        tela.blit(texto_titulo, (largura_tela // 2 - texto_titulo.get_width() // 2, altura_tela // 4))

        texto_nome = fonte_input.render(nome + "_", True, branco)
        tela.blit(texto_nome, (largura_tela // 2 - texto_nome.get_width() // 2, altura_tela // 2))

        instrucao = fonte_instrucao.render("Pressione ENTER para confirmar sua existencia", True, (150, 150, 150))
        tela.blit(instrucao, (largura_tela // 2 - instrucao.get_width() // 2, altura_tela - 80))

        pygame.display.flip()

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif evento.type == pygame.KEYDOWN:
                if evento.key in [pygame.K_RETURN, pygame.K_KP_ENTER] and len(nome) > 0:
                    with open("saves/nome_jogador.json", "w") as f:
                        json.dump({"nome": nome}, f)
                    return
                elif evento.key == pygame.K_BACKSPACE:
                    nome = nome[:-1]
                else:
                    if len(nome) < 16 and evento.unicode.isprintable():
                        nome += evento.unicode
        clock.tick(60)

def mostrar_erro_lan(tela, font_titulo, font_desc):
    largura, altura = tela.get_size()
    duracao = 3000
    inicio = pygame.time.get_ticks()

    while pygame.time.get_ticks() - inicio < duracao:
        tela.fill((15, 12, 20))

        # Grade cibernÃ©tica sutil
        for gx in range(40, largura, 80):
            for gy in range(40, altura, 80):
                pygame.draw.circle(tela, (255, 80, 80, 12), (gx, gy), 1)

        # Mensagem de erro centralizada
        txt_err = font_titulo.render("SEM CONEXAO ENCONTRADA", True, (255, 80, 80))
        txt_desc = font_desc.render("Nao foi possivel encontrar nenhuma partida LAN ativa na rede local.", True, (200, 200, 200))
        txt_desc2 = font_desc.render("Certifique-se de que o host iniciou a partida e tente novamente.", True, (140, 140, 150))

        tela.blit(txt_err, (largura // 2 - txt_err.get_width() // 2, altura // 2 - 50))
        tela.blit(txt_desc, (largura // 2 - txt_desc.get_width() // 2, altura // 2 + 10))
        tela.blit(txt_desc2, (largura // 2 - txt_desc2.get_width() // 2, altura // 2 + 40))

        pygame.display.flip()
        pygame.time.Clock().tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type in [pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN]:
                return # Pula o aviso com qualquer entrada


def tela_escolha_dificuldade(tela, fonte, mostrar_tutorial=False):
    import random
    import math
    import json
    import os

    pygame.mouse.set_visible(False)
    largura, altura = tela.get_size()
    clock = pygame.time.Clock()
    selecionado = 0  # Normal como padrao seguro.
    modo_interacao = "teclado"
    analogo_movido = False
    aviso_texto = ""
    aviso_fim = 0

    def carregar_fonte(path, tamanho, fallback=None):
        try:
            return pygame.font.Font(path, tamanho)
        except Exception:
            return fallback or pygame.font.Font(None, tamanho)

    font_titulo = carregar_fonte(caminho_fonte_titulo, 42, fonte)
    font_botao = carregar_fonte(caminho_fonte_letra1, 28, fonte)
    font_info = carregar_fonte(caminho_fonte_letras, 18, fonte)
    font_peq = carregar_fonte(caminho_fonte_letras, 15, fonte)

    opcoes_dificuldade = [
        {
            "nome": "Normal",
            "modo_cartas": "loja",
            "tema": "cosmo",
            "bloqueado": False,
            "motivo": "",
            "bg_cor": (8, 20, 42),
            "accent_cor": (0, 230, 255),
            "titulo_sub": "MODO LOJA",
            "desc": "Adquira cartas na loja inter-fases usando Poeira Cosmica. O modo classico ideal para aprender e evoluir.",
        },
        {
            "nome": "Dificil",
            "modo_cartas": "drops",
            "tema": "inferno",
            "bloqueado": bool(mostrar_tutorial),
            "motivo": "Dificil bloqueado com tutorial ativo.",
            "bg_cor": (42, 12, 8),
            "accent_cor": (255, 92, 24),
            "titulo_sub": "MODO DROPS",
            "desc": "Inimigos dropam cartas ao morrer. Sem loja inter-fases. Recomendado apenas para veteranos buscando o desafio maximo.",
        },
    ]

    base_x = [largura // 2 - 170, largura // 2 + 170]
    rects = [pygame.Rect(0, 0, 1, 1), pygame.Rect(0, 0, 1, 1)]
    btn_voltar = pygame.Rect(40, 34, 126, 38)

    bg_cor_atual = list(opcoes_dificuldade[selecionado]["bg_cor"])
    accent_cor_atual = list(opcoes_dificuldade[selecionado]["accent_cor"])
    card_scale = [0.88, 0.88]
    card_y_offset = [10, 10]
    card_alpha = [130, 130]

    # Particles system
    particulas = []
    for _ in range(70):
        particulas.append({
            "x": random.uniform(0, largura),
            "y": random.uniform(0, altura),
            "r": random.uniform(1.2, 4.5),
            "alpha": random.randint(50, 220),
            "speed_y": random.uniform(-1.5, -0.4),
            "drift_speed": random.uniform(0.01, 0.04),
            "drift_phase": random.uniform(0, math.pi * 2),
            "breathe_speed": random.uniform(0.02, 0.06),
            "breathe_dir": random.choice([-1, 1])
        })

    def mostrar_aviso(texto):
        nonlocal aviso_texto, aviso_fim
        aviso_texto = texto
        aviso_fim = pygame.time.get_ticks() + 1900

    def mover_selecao(delta):
        nonlocal selecionado
        selecionado = (selecionado + delta) % len(opcoes_dificuldade)
        tocar_hover()

    def confirmar_selecao():
        opcao = opcoes_dificuldade[selecionado]
        if opcao["bloqueado"]:
            tocar_hover()
            mostrar_aviso(opcao["motivo"])
            return None
        tocar_selecionar()
        return opcao["modo_cartas"]

    def desenhar_texto_wrap_local(superficie, texto, rect, fonte_usada, cor, line_gap=0):
        palavras = texto.split(" ")
        linhas = []
        linha_atual = []
        for palavra in palavras:
            teste = " ".join(linha_atual + [palavra])
            if fonte_usada.size(teste)[0] <= rect.width:
                linha_atual.append(palavra)
            else:
                if linha_atual:
                    linhas.append(" ".join(linha_atual))
                linha_atual = [palavra]
        if linha_atual:
            linhas.append(" ".join(linha_atual))

        y_txt = rect.top
        altura_linha = fonte_usada.get_linesize() + line_gap
        for i_linha, linha in enumerate(linhas):
            if y_txt + altura_linha > rect.bottom:
                break
            if y_txt + 2 * altura_linha > rect.bottom and i_linha < len(linhas) - 1:
                linha = linha + "..."
                while len(linha) > 3 and fonte_usada.size(linha)[0] > rect.width:
                    linha = linha[:-4] + "..."
            render = fonte_usada.render(linha, True, cor)
            superficie.blit(render, (rect.left, y_txt))
            y_txt += altura_linha

    def desenhar_card(opcao, rect, ativo, alpha, agora):
        surf_card = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)

        if opcao["tema"] == "inferno":
            cor_bg = (55, 12, 8, 210 if ativo else 130)
            cor_borda = (255, 92, 24, 255 if ativo else 120)
        else:
            cor_bg = (8, 24, 55, 210 if ativo else 130)
            cor_borda = (0, 230, 255, 255 if ativo else 120)

        if opcao["bloqueado"]:
            cor_bg = (30, 28, 32, 170)
            cor_borda = (130, 110, 110, 120)
            if ativo:
                cor_borda = (255, 120, 80, 255)

        pygame.draw.rect(surf_card, cor_bg, (0, 0, rect.w, rect.h), border_radius=12)
        pygame.draw.rect(surf_card, cor_borda, (0, 0, rect.w, rect.h), width=2 if ativo else 1, border_radius=12)

        if ativo:
            glow_cor = (255, 92, 24, 30) if opcao["tema"] == "inferno" else (0, 230, 255, 30)
            pygame.draw.rect(surf_card, glow_cor, (5, 5, rect.w - 10, rect.h - 10), border_radius=10)

        cor_titulo = (255, 240, 220) if opcao["tema"] == "inferno" else (220, 245, 255)
        if opcao["bloqueado"]:
            cor_titulo = (150, 140, 140)
        texto_titulo = font_botao.render(opcao["nome"].upper(), True, cor_titulo)
        rect_tit = texto_titulo.get_rect(center=(rect.w // 2, 34))
        surf_card.blit(texto_titulo, rect_tit)

        cor_sub = (255, 180, 120) if opcao["tema"] == "inferno" else (100, 220, 255)
        if opcao["bloqueado"]:
            cor_sub = (120, 110, 110)
        texto_sub = font_peq.render(opcao["titulo_sub"], True, cor_sub)
        rect_sub = texto_sub.get_rect(center=(rect.w // 2, 66))
        surf_card.blit(texto_sub, rect_sub)

        cor_div = (255, 92, 24, 70) if opcao["tema"] == "inferno" else (0, 230, 255, 70)
        if opcao["bloqueado"]:
            cor_div = (100, 100, 100, 40)
        pygame.draw.line(surf_card, cor_div, (30, 85), (rect.w - 30, 85), 1)

        desc_rect = pygame.Rect(20, 100, rect.w - 40, rect.h - 110)
        cor_desc = (230, 210, 200) if opcao["tema"] == "inferno" else (200, 220, 235)
        if opcao["bloqueado"]:
            cor_desc = (115, 110, 110)
        desenhar_texto_wrap_local(surf_card, opcao["desc"], desc_rect, font_info, cor_desc, line_gap=2)

        if opcao["bloqueado"]:
            for x_line in range(-rect.h, rect.w, 18):
                pygame.draw.line(surf_card, (255, 80, 50, 15), (x_line, rect.h), (x_line + rect.h, 0), 1)

            txt_travado = font_info.render("BLOQUEADO", True, (255, 100, 80) if ativo else (160, 120, 120))
            rect_trav = txt_travado.get_rect(center=(rect.w // 2, rect.h - 26))
            surf_card.blit(txt_travado, rect_trav)

        surf_card.set_alpha(int(alpha))
        tela.blit(surf_card, rect.topleft)

    while True:
        agora = pygame.time.get_ticks()
        mx, my = ui_helpers.obter_pos_mouse_superficie(tela)

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if evento.type == pygame.MOUSEMOTION:
                modo_interacao = "mouse"
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                modo_interacao = "mouse"
                pos_evento = ui_helpers.converter_pos_mouse_jogo(evento.pos)
                if btn_voltar.collidepoint(pos_evento):
                    tocar_selecionar()
                    return None
                for i, rect in enumerate(rects):
                    if rect.collidepoint(pos_evento):
                        selecionado = i
                        resultado = confirmar_selecao()
                        if resultado is not None:
                            return resultado
            elif evento.type == pygame.KEYDOWN:
                modo_interacao = "teclado"
                if evento.key == pygame.K_ESCAPE:
                    tocar_selecionar()
                    return None
                elif evento.key in [pygame.K_LEFT, pygame.K_a]:
                    mover_selecao(-1)
                elif evento.key in [pygame.K_RIGHT, pygame.K_d]:
                    mover_selecao(1)
                elif evento.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    resultado = confirmar_selecao()
                    if resultado is not None:
                        return resultado
            elif evento.type == pygame.JOYAXISMOTION and controle is not None:
                modo_interacao = "teclado"
                if evento.axis == 0:
                    if evento.value > 0.5 and not analogo_movido:
                        mover_selecao(1)
                        analogo_movido = True
                    elif evento.value < -0.5 and not analogo_movido:
                        mover_selecao(-1)
                        analogo_movido = True
                    elif abs(evento.value) < 0.3:
                        analogo_movido = False
            elif evento.type == pygame.JOYHATMOTION and controle is not None:
                modo_interacao = "teclado"
                dx, _ = evento.value
                if dx > 0:
                    mover_selecao(1)
                elif dx < 0:
                    mover_selecao(-1)
            elif evento.type == pygame.JOYBUTTONDOWN and controle is not None:
                modo_interacao = "teclado"
                if evento.button == 0:
                    resultado = confirmar_selecao()
                    if resultado is not None:
                        return resultado
                elif evento.button == 1:
                    tocar_selecionar()
                    return None

        # Update card layout and targets dynamically based on scaling
        for i in range(2):
            if i == selecionado:
                target_scale = 1.12
                target_y_offset = -12
                target_alpha = 255
            else:
                target_scale = 0.88
                target_y_offset = 12
                target_alpha = 135

            card_scale[i] += (target_scale - card_scale[i]) * 0.1
            card_y_offset[i] += (target_y_offset - card_y_offset[i]) * 0.1
            card_alpha[i] += (target_alpha - card_alpha[i]) * 0.1

        card_w, card_h = 250, 240
        for i in range(2):
            w_scaled = int(card_w * card_scale[i])
            h_scaled = int(card_h * card_scale[i])
            x_pos = int(base_x[i] - w_scaled // 2)
            y_pos = int(altura // 2 - h_scaled // 2 + card_y_offset[i])
            rects[i] = pygame.Rect(x_pos, y_pos, w_scaled, h_scaled)

        if modo_interacao == "mouse":
            for i, rect in enumerate(rects):
                if rect.collidepoint(mx, my) and selecionado != i:
                    selecionado = i
                    tocar_hover()

        # Update LERP colors
        target_bg = opcoes_dificuldade[selecionado]["bg_cor"]
        target_accent = opcoes_dificuldade[selecionado]["accent_cor"]
        for c in range(3):
            bg_cor_atual[c] += (target_bg[c] - bg_cor_atual[c]) * 0.08
            accent_cor_atual[c] += (target_accent[c] - accent_cor_atual[c]) * 0.08

        cor_acento = tuple(int(c) for c in accent_cor_atual)
        ui_helpers.desenhar_fundo_menu_ruptura(tela, agora, particulas, tuple(int(c) for c in bg_cor_atual), cor_acento, 1.0)
        ui_helpers.desenhar_cabecalho_menu(
            tela,
            "ESCOLHA A DIFICULDADE",
            "Defina como as cartas entram na jornada.",
            font_titulo,
            font_info,
            cor_acento,
            y=88,
        )

        # Render Cards
        for i, opcao in enumerate(opcoes_dificuldade):
            desenhar_card(opcao, rects[i], i == selecionado, card_alpha[i], agora)

        hover_voltar = modo_interacao == "mouse" and btn_voltar.collidepoint(mx, my)
        ui_helpers.desenhar_botao_voltar_menu(tela, btn_voltar, font_info, hover_voltar, cor_acento, "ESC Voltar")

        # Warning panel (if any)
        if aviso_texto and agora < aviso_fim:
            aviso = font_info.render(aviso_texto, True, (255, 180, 100))
            painel = pygame.Surface((aviso.get_width() + 42, 42), pygame.SRCALPHA)
            pygame.draw.rect(painel, (24, 10, 8, 220), painel.get_rect(), border_radius=7)
            pygame.draw.rect(painel, (255, 92, 32, 120), painel.get_rect(), width=1, border_radius=7)
            painel.blit(aviso, (21, 20 - aviso.get_height() // 2))
            tela.blit(painel, (largura // 2 - painel.get_width() // 2, altura // 2 + card_h // 2 + 36))

        ui_helpers.desenhar_rodape_menu(tela, "A/D ou SETAS: alternar | ENTER/ESPACO: selecionar | ESC: voltar", font_info, cor_acento, altura - 36)

        ui_helpers.desenhar_cursor_personalizado(tela)
        pygame.display.flip()
        clock.tick(60)

def tela_escolha_modo():
    import socket, pyperclip, random
    from rede import descobrir_host_udp
    from ui_helpers import obter_superficie_palco
    pygame.init()
    largura, altura = largura_tela, altura_tela
    tela = obter_superficie_palco() or pygame.display.set_mode((largura, altura))
    pygame.display.set_caption("Escolher Modo de Jogo")

    # Carregar fontes com fallback seguro
    try:
        font_titulo = pygame.font.Font("Texto/Top_Menu.otf", 44)
    except:
        font_titulo = pygame.font.Font(None, 44)

    try:
        font_card_title = pygame.font.Font("Texto/World.otf", 26)
    except:
        font_card_title = pygame.font.Font(None, 26)

    try:
        font_card_desc = pygame.font.Font("Texto/rainyhearts.ttf", 20)
    except:
        font_card_desc = pygame.font.Font(None, 20)

    try:
        font_btn = pygame.font.Font("Texto/World.otf", 24)
    except:
        font_btn = pygame.font.Font(None, 24)

    clock = pygame.time.Clock()

    # Fase: "principal" (Solo ou Coop) ou "coop_sub" (Criar ou Entrar)
    fase_tela = "principal"
    selecionado_principal = 0  # 0: Jogar Solo, 1: Cooperativo
    selecionado_sub = 0        # 0: Criar, 1: Entrar, 2: Voltar
    modo_interacao = "teclado"

    particulas = ui_helpers.criar_particulas_menu(largura, altura, 42, (0, 220, 255))

    btn_back_rect = pygame.Rect(40, 34, 118, 36)

    while True:
        agora = pygame.time.get_ticks()

        cor_tela = (0, 220, 255) if fase_tela == "principal" else (170, 100, 255)
        ui_helpers.desenhar_fundo_menu_ruptura(tela, agora, particulas, (5, 8, 17), cor_tela, 0.9)
        subtitulo = "Escolha como a ruptura vai abrir a partida."
        if fase_tela == "coop_sub":
            subtitulo = "Conecte uma fenda cooperativa em rede local."
        ui_helpers.desenhar_cabecalho_menu(tela, "MODO DE JOGO", subtitulo, font_titulo, font_card_desc, cor_tela, y=88)

        mx, my = ui_helpers.obter_pos_mouse_superficie(tela)
        clicado = False

        is_hover_back = modo_interacao == "mouse" and btn_back_rect.collidepoint(mx, my)
        ui_helpers.desenhar_botao_voltar_menu(tela, btn_back_rect, font_card_desc, is_hover_back, cor_tela, "ESC Voltar")

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                return None, None
            elif evento.type == pygame.MOUSEMOTION:
                if evento.rel != (0, 0):
                    modo_interacao = "mouse"
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                if evento.button == 1:
                    modo_interacao = "mouse"
                    clicado = True
                    pos_evento = ui_helpers.converter_pos_mouse_jogo(evento.pos)
                    if btn_back_rect.collidepoint(pos_evento):
                        tocar_selecionar()
                        if fase_tela == "coop_sub":
                            fase_tela = "principal"
                            selecionado_sub = 0
                        else:
                            return None, None
            elif evento.type == pygame.KEYDOWN:
                modo_interacao = "teclado"
                if evento.key == pygame.K_ESCAPE:
                    tocar_selecionar()
                    if fase_tela == "coop_sub":
                        fase_tela = "principal"
                        selecionado_sub = 0
                    else:
                        return None, None
                elif evento.key in [pygame.K_LEFT, pygame.K_a, pygame.K_UP, pygame.K_w]:
                    tocar_hover()
                    if fase_tela == "principal":
                        selecionado_principal = (selecionado_principal - 1) % 2
                    elif fase_tela == "coop_sub":
                        selecionado_sub = (selecionado_sub - 1) % 3
                elif evento.key in [pygame.K_RIGHT, pygame.K_d, pygame.K_DOWN, pygame.K_s]:
                    tocar_hover()
                    if fase_tela == "principal":
                        selecionado_principal = (selecionado_principal + 1) % 2
                    elif fase_tela == "coop_sub":
                        selecionado_sub = (selecionado_sub + 1) % 3
                elif evento.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    tocar_selecionar()
                    if fase_tela == "principal":
                        if selecionado_principal == 0:
                            return "offline", None
                        else:
                            fase_tela = "coop_sub"
                            selecionado_sub = 0
                    elif fase_tela == "coop_sub":
                        if selecionado_sub == 0:
                            return "host", None
                        elif selecionado_sub == 1:
                            ip_encontrado = descobrir_host_udp(timeout=4)
                            if ip_encontrado:
                                return "join", ip_encontrado
                            else:
                                mostrar_erro_lan(tela, font_card_title, font_card_desc)
                        elif selecionado_sub == 2:
                            fase_tela = "principal"
                            selecionado_sub = 0

            # Suporte a Controle / Gamepad
            elif evento.type == pygame.JOYBUTTONDOWN and controle is not None:
                if evento.button == 0:  # BotÃ£o A
                    tocar_selecionar()
                    if fase_tela == "principal":
                        if selecionado_principal == 0:
                            return "offline", None
                        else:
                            fase_tela = "coop_sub"
                            selecionado_sub = 0
                    elif fase_tela == "coop_sub":
                        if selecionado_sub == 0:
                            return "host", None
                        elif selecionado_sub == 1:
                            ip_encontrado = descobrir_host_udp(timeout=4)
                            if ip_encontrado:
                                return "join", ip_encontrado
                            else:
                                mostrar_erro_lan(tela, font_card_title, font_card_desc)
                        elif selecionado_sub == 2:
                            fase_tela = "principal"
                            selecionado_sub = 0
                elif evento.button == 1:  # BotÃ£o B
                    tocar_selecionar()
                    if fase_tela == "coop_sub":
                        fase_tela = "principal"
                        selecionado_sub = 0
                    else:
                        return None, None

        # Renderizar Fase Principal: Cards lado a lado
        if fase_tela == "principal":
            card_y = altura // 2 - 90
            card_w = 265
            card_h = 245

            # --- CARD ESQUERDO: JOGAR SOLO ---
            card_l_x = largura // 2 - 295
            rect_solo = pygame.Rect(card_l_x, card_y, card_w, card_h)
            is_hover_solo = modo_interacao == "mouse" and rect_solo.collidepoint(mx, my)
            if is_hover_solo:
                if selecionado_principal != 0:
                    selecionado_principal = 0
                    tocar_hover()
                if clicado:
                    tocar_selecionar()
                    return "offline", None

            is_sel_solo = (selecionado_principal == 0)
            bg_color_solo = (20, 16, 32, 205) if is_sel_solo else (12, 10, 18, 140)
            border_color_solo = (0, 255, 204) if is_sel_solo else (70, 70, 85)
            border_w_solo = 2 if is_sel_solo else 1

            solo_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            pygame.draw.rect(solo_surf, bg_color_solo, (0, 0, card_w, card_h), border_radius=12)
            pygame.draw.rect(solo_surf, border_color_solo, (0, 0, card_w, card_h), width=border_w_solo, border_radius=12)

            if is_sel_solo:
                # Efeito glow interno ciano
                pygame.draw.rect(solo_surf, (0, 255, 204, 25), (5, 5, card_w - 10, card_h - 10), border_radius=8)

            tela.blit(solo_surf, (card_l_x, card_y))

            title_solo = font_card_title.render("JOGAR SOLO", True, (255, 255, 255) if is_sel_solo else (170, 170, 180))
            tela.blit(title_solo, (card_l_x + card_w // 2 - title_solo.get_width() // 2, card_y + 35))

            lines_solo = [
                "Jogue no modo offline.",
                "Enfronte desafios e",
                "domine o espaco-tempo",
                "em uma jornada solitaria."
            ]
            for li, l_txt in enumerate(lines_solo):
                txt_line = font_card_desc.render(l_txt, True, (215, 220, 230) if is_sel_solo else (130, 130, 140))
                tela.blit(txt_line, (card_l_x + card_w // 2 - txt_line.get_width() // 2, card_y + 95 + li * 24))

            # --- CARD DIREITO: COOPERATIVO ---
            card_r_x = largura // 2 + 30
            rect_coop = pygame.Rect(card_r_x, card_y, card_w, card_h)
            is_hover_coop = modo_interacao == "mouse" and rect_coop.collidepoint(mx, my)
            if is_hover_coop:
                if selecionado_principal != 1:
                    selecionado_principal = 1
                    tocar_hover()
                if clicado:
                    tocar_selecionar()
                    fase_tela = "coop_sub"
                    selecionado_sub = 0

            is_sel_coop = (selecionado_principal == 1)
            bg_color_coop = (24, 16, 36, 205) if is_sel_coop else (12, 10, 18, 140)
            border_color_coop = (180, 100, 255) if is_sel_coop else (70, 70, 85)
            border_w_coop = 2 if is_sel_coop else 1

            coop_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            pygame.draw.rect(coop_surf, bg_color_coop, (0, 0, card_w, card_h), border_radius=12)
            pygame.draw.rect(coop_surf, border_color_coop, (0, 0, card_w, card_h), width=border_w_coop, border_radius=12)

            if is_sel_coop:
                # Efeito glow interno roxo
                pygame.draw.rect(coop_surf, (180, 100, 255, 25), (5, 5, card_w - 10, card_h - 10), border_radius=8)

            tela.blit(coop_surf, (card_r_x, card_y))

            title_coop = font_card_title.render("MULTIPLAYER", True, (255, 255, 255) if is_sel_coop else (170, 170, 180))
            tela.blit(title_coop, (card_r_x + card_w // 2 - title_coop.get_width() // 2, card_y + 35))

            lines_coop = [
                "Jogue em Rede Local (LAN).",
                "Conecte-se com outro",
                "jogador para explorar",
                "a fenda cooperativamente."
            ]
            for li, l_txt in enumerate(lines_coop):
                txt_line = font_card_desc.render(l_txt, True, (215, 220, 230) if is_sel_coop else (130, 130, 140))
                tela.blit(txt_line, (card_r_x + card_w // 2 - txt_line.get_width() // 2, card_y + 95 + li * 24))

        # Renderizar Subfase: OpÃ§Ãµes Multiplayer LAN
        elif fase_tela == "coop_sub":
            sub_y = altura // 2 - 50
            btn_w = 340
            btn_h = 52

            opcoes_sub = [
                ("Criar Sala (Host)", "host"),
                ("Entrar em Sala (Join)", "join"),
                ("Voltar", "voltar")
            ]

            txt_subtitle = font_card_desc.render("CONEXAO DE MULTIJOGADOR EM REDE LOCAL", True, (180, 100, 255))
            tela.blit(txt_subtitle, (largura // 2 - txt_subtitle.get_width() // 2, 125))

            for idx, (label, mode) in enumerate(opcoes_sub):
                btn_x = largura // 2 - btn_w // 2
                item_y = sub_y + idx * 70
                rect_btn = pygame.Rect(btn_x, item_y, btn_w, btn_h)

                is_hover = modo_interacao == "mouse" and rect_btn.collidepoint(mx, my)
                if is_hover:
                    if selecionado_sub != idx:
                        selecionado_sub = idx
                        tocar_hover()
                    if clicado:
                        tocar_selecionar()
                        if mode == "host":
                            return "host", None
                        elif mode == "join":
                            ip_encontrado = descobrir_host_udp(timeout=4)
                            if ip_encontrado:
                                return "join", ip_encontrado
                            else:
                                mostrar_erro_lan(tela, font_card_title, font_card_desc)
                        elif mode == "voltar":
                            fase_tela = "principal"
                            selecionado_sub = 0

                is_sel = (selecionado_sub == idx)
                bg_color = (25, 20, 42, 210) if is_sel else (12, 10, 18, 140)
                border_color = (180, 100, 255) if is_sel else (65, 55, 80)
                border_w = 2 if is_sel else 1

                btn_surf = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
                pygame.draw.rect(btn_surf, bg_color, (0, 0, btn_w, btn_h), border_radius=8)
                pygame.draw.rect(btn_surf, border_color, (0, 0, btn_w, btn_h), width=border_w, border_radius=8)
                tela.blit(btn_surf, (btn_x, item_y))

                txt_lbl = font_btn.render(label, True, (255, 255, 255) if is_sel else (175, 175, 185))
                tela.blit(txt_lbl, (btn_x + btn_w // 2 - txt_lbl.get_width() // 2, item_y + btn_h // 2 - txt_lbl.get_height() // 2))

        rodape = "A/D ou SETAS: navegar | ENTER/ESPACO: selecionar | ESC: voltar"
        ui_helpers.desenhar_rodape_menu(tela, rodape, font_card_desc, cor_tela, altura - 36)
        ui_helpers.desenhar_cursor_personalizado(tela)
        pygame.display.flip()
        clock.tick(60)



def tela_selecao_aurea(tela, fonte):
    pygame.mouse.set_visible(False)
    # Carregar som do tick
    try:
        som_tick = aplicar_volume_som(pygame.mixer.Sound("Sounds/Estalo.mp3"))
    except Exception:
        som_tick = None

    aureas = [
        {
            "nome": "Racional",
            "imagem": "Sprites/aurea_cientista.png",
            "ativa": True,
            "cor_tema": (0, 191, 255),       # Azul ElÃ©trico / Ciano
            "bg_tema": (8, 20, 42),          # Fundo Deep Blue
            "categoria": "ANÃLISE E PRECISÃƒO TEMPORAL",
            "efeito": "Gera pontos bÃ´nus ao ficar imÃ³vel por 5s. Ao teleportar, ativa a DilataÃ§Ã£o Temporal por 8s, desacelerando inimigos/projÃ©teis em 58% (cooldown de 30s).",
            "atributos": [
                "â€¢ Passiva: +3 (+nÃ­vel) pontos a cada 5s imÃ³vel.",
                "â€¢ DilataÃ§Ã£o: inimigos e projÃ©teis ficam 58% mais lentos.",
                "â€¢ Buffs: +35% de velocidade e +28% de cadÃªncia de tiro para."
            ],
            "lore": "A mente fria calcula trajetÃ³rias e enxerga padrÃµes em meio ao caos da ruptura temporal."
        },
        {
            "nome": "Impulsiva",
            "imagem": "Sprites/aurea_impulsiva.png",
            "ativa": True,
            "cor_tema": (255, 99, 71),       # Vermelho Coral / Laranja
            "bg_tema": (42, 14, 8),          # Fundo Deep Red/Orange
            "categoria": "COMBATE VELOZ E AGRESSIVO",
            "efeito": "Elimine 5 inimigos seguidos sem sofrer dano para ativar um buff temporÃ¡rio aleatÃ³rio de dano ou velocidade.",
            "atributos": [
                "â€¢ Gatilho: 5 abates consecutivos sem dano.",
                "â€¢ Efeito: dano fÃ­sico ou velocidade por poucos segundos.",
                "â€¢ Sofrer dano zera a sequÃªncia."
            ],
            "lore": "AÃ§Ã£o imediata. O instinto puro reage antes que o prÃ³prio tempo possa processar."
        },
        {
            "nome": "Devota",
            "imagem": "Sprites/aurea_devota.png",
            "ativa": True,
            "cor_tema": (255, 215, 0),       # Dourado Divino
            "bg_tema": (36, 30, 8),          # Fundo Deep Gold
            "categoria": "SOBREVIVÃŠNCIA E PROTEÃ‡ÃƒO SAGRADA",
            "efeito": "Cria um escudo automÃ¡tico. Enquanto ativo, ele anula completamente o prÃ³ximo dano recebido.",
            "atributos": [
                "â€¢ Gatilho: escudo nasce ativo e volta sozinho.",
                "â€¢ Efeito: bloqueia 1 colisÃ£o, tiro ou golpe.",
                "â€¢ EvoluÃ§Ã£o: reduz a recarga do escudo."
            ],
            "lore": "A fÃ© inabalÃ¡vel manifesta-se como uma barreira divina que desafia a prÃ³pria causalidade."
        },
        {
            "nome": "Vanguarda",
            "imagem": "Sprites/aurea_vanguarda.png",
            "ativa": True,
            "cor_tema": (230, 0, 120),       # Magenta / Carmesim
            "bg_tema": (36, 8, 28),          # Fundo Deep Purple/Magenta
            "categoria": "DANO EM ÃREA E INCÃŠNDIO CONTÃNUO",
            "efeito": "Aproxime-se ou encoste nos inimigos para incendiÃ¡-los. Alvos em chamas recebem dano contÃ­nuo.",
            "atributos": [
                "â€¢ Gatilho: contato ou proximidade com inimigos.",
                "â€¢ Efeito: queimadura por segundo baseada na vida mÃ¡xima.",
                "â€¢ EvoluÃ§Ã£o: aumenta duraÃ§Ã£o e dano da chama."
            ],
            "lore": "Liderando o avanÃ§o, o pioneiro incendeia o solo para que nada o siga no fluxo temporal."
        },
        {
            "nome": "AleatÃ³ria",
            "imagem": "Sprites/aurea_misteriosa.png",
            "ativa": True,
            "cor_tema": (0, 255, 180),       # Verde Esmeralda / Neon
            "bg_tema": (8, 32, 24),          # Fundo Deep Green
            "categoria": "SURPRESA E DESTINO INCERTO",
            "efeito": "Escolhe uma das seis Ã¡ureas ativas ao iniciar a jornada, mudando a estratÃ©gia da partida.",
            "atributos": [
                "â€¢ Pode vir Racional, Impulsiva, Devota, Vanguarda, Insana ou Voraz.",
                "â€¢ A escolha Ã© definida ao confirmar.",
                "â€¢ Boa para partidas de adaptaÃ§Ã£o."
            ],
            "lore": "O destino Ã© incerto, e o tempo se desdobra em infinitas possibilidades."
        }
    ]

    aureas.insert(-1, {
        "nome": "Insana",
        "imagem": "Sprites/aurea_insana.png",
        "ativa": True,
        "cor_tema": (160, 55, 255),
        "bg_tema": (24, 10, 38),
        "categoria": "ECOS TEMPORAIS E DESORIENTACAO",
        "efeito": "Cria ecos temporais parados que repetem seus disparos com atraso, causando dano reduzido.",
        "atributos": [
            "Comeca com 4 ecos, podendo chegar a 5.",
            "Ecos disparam 1s depois do tiro original.",
            "Depois da aura, o Teleporte sofre +2s de recarga."
        ],
        "lore": "A ruptura deixa Geovana ouvir versoes atrasadas de si mesma, todas atirando de volta para o presente."
    })

    aureas.insert(-1, {
        "nome": "Voraz",
        "imagem": "Sprites/aurea_voraz.png",
        "ativa": True,
        "cor_tema": (255, 112, 24),
        "bg_tema": (42, 18, 8),
        "categoria": "FOME, CONSUMO E RISCO",
        "efeito": "Poeira voraz alimenta a barra Fome e cura 5% da vida perdida. Fome sustentada melhora tiros/dano e ativa mordidas que curam; sem coleta por 30s drena vida.",
        "atributos": [
            "Abates deixam poeira voraz temporaria.",
            "Coletar poeira cura 5% da vida perdida.",
            "Fome sustentada aumenta o tamanho e o dano dos tiros.",
            "Mordidas curam pela vida perdida (ate 60% em boss).",
            "Custo: ficar 30s sem coletar drena 1% de vida a cada 1.5s."
        ],
        "lore": "A ruptura nao abre uma boca. Ela ensina Geovana a sentir uma."
    })

    dados_aureas_por_id = {dado["id"]: dado for dado in AUREAS_DADOS}
    for item in aureas:
        dado = dados_aureas_por_id.get(item["nome"])
        if not dado:
            continue
        item["categoria"] = dado["categoria"].upper()
        item["efeito"] = dado.get("resumo", dado["descricao"])
        item["atributos"] = dado.get("destaques", item["atributos"])
        item["lore"] = dado["lore"].strip('"')

    upgrades = carregar_upgrade_aureas("saves/aureas_upgrade.json")

    selecionado = 0
    scroll_y = 0
    clock = pygame.time.Clock()
    largura, altura = tela.get_size()

    # Fontes especÃ­ficas
    import random
    caminho_fonte_aureas = "Texto/rainyhearts.ttf"
    fonte_nome = pygame.font.Font(caminho_fonte_aureas, 34)
    fonte_desc = pygame.font.Font(caminho_fonte_aureas, 18)
    fonte_status = pygame.font.Font(caminho_fonte_aureas, 16)
    fonte_lore = pygame.font.Font(caminho_fonte_aureas, 13)
    fonte_instrucao = pygame.font.Font(caminho_fonte_aureas, 18)
    fonte_categoria = pygame.font.Font(caminho_fonte_aureas, 16)

    # VariÃ¡veis de animaÃ§Ã£o (InterpolaÃ§Ã£o LERP)
    cor_fundo_atual = list(aureas[selecionado]["bg_tema"])

    # Propriedades dos cards
    card_x = [largura // 2 for _ in aureas]
    card_scale = [0.85 for _ in aureas]
    card_y_offset = [20 for _ in aureas]
    card_alpha = [100 for _ in aureas]

    # Carregar imagens das Ã¡ureas antecipadamente
    imagens_aureas = []
    for item in aureas:
        try:
            img = pygame.image.load(item["imagem"]).convert_alpha()
        except:
            img = pygame.Surface((180, 240))
            img.fill((30, 30, 30))
            pygame.draw.line(img, (100, 100, 100), (0, 0), (180, 240), 2)
            pygame.draw.line(img, (100, 100, 100), (180, 0), (0, 240), 2)
        imagens_aureas.append(img)

    # Sistema de PartÃ­culas Celestiais
    particulas = []
    for _ in range(50):
        particulas.append({
            "x": random.randint(0, largura),
            "y": random.randint(0, altura),
            "vel_y": random.uniform(-1.2, -0.4),
            "tamanho": random.uniform(2.0, 5.0),
            "alpha": random.randint(50, 200),
            "breathe_speed": random.uniform(0.02, 0.05),
            "breathe_dir": 1
        })

    # Controle de repetiÃ§Ã£o do analÃ³gico
    analogo_movido = False
    modo_interacao = "teclado"
    btn_back_rect = pygame.Rect(40, 34, 118, 36)

    def obter_linhas_wrap(texto, largura_max, fonte_usada):
        palavras = texto.split(" ")
        linhas = []
        linha_atual = []
        for palavra in palavras:
            teste = " ".join(linha_atual + [palavra])
            if fonte_usada.size(teste)[0] <= largura_max:
                linha_atual.append(palavra)
            else:
                if linha_atual:
                    linhas.append(" ".join(linha_atual))
                linha_atual = [palavra]
        if linha_atual:
            linhas.append(" ".join(linha_atual))
        return linhas

    def mover_selecao(direcao):
        nonlocal selecionado, scroll_y
        selecionado = (selecionado + direcao) % len(aureas)
        while not aureas[selecionado]["ativa"]:
            selecionado = (selecionado + direcao) % len(aureas)
        scroll_y = 0

    def distancia_circular(indice, centro):
        total = max(1, len(aureas))
        dist = int(indice) - int(centro)
        metade = total / 2.0
        if dist > metade:
            dist -= total
        elif dist < -metade:
            dist += total
        return dist

    def desenhar_texto_wrap_local(superficie, texto, rect, fonte_usada, cor, line_gap=0):
        palavras = texto.split(" ")
        linhas = []
        linha_atual = []
        for palavra in palavras:
            teste = " ".join(linha_atual + [palavra])
            if fonte_usada.size(teste)[0] <= rect.width:
                linha_atual.append(palavra)
            else:
                if linha_atual:
                    linhas.append(" ".join(linha_atual))
                linha_atual = [palavra]
        if linha_atual:
            linhas.append(" ".join(linha_atual))

        y_txt = rect.top
        altura_linha = fonte_usada.get_linesize() + line_gap
        for i_linha, linha in enumerate(linhas):
            if y_txt + altura_linha > rect.bottom:
                break
            if y_txt + 2 * altura_linha > rect.bottom and i_linha < len(linhas) - 1:
                linha = linha + "..."
                while len(linha) > 3 and fonte_usada.size(linha)[0] > rect.width:
                    linha = linha[:-4] + "..."
            render = fonte_usada.render(linha, True, cor)
            superficie.blit(render, (rect.left, y_txt))
            y_txt += altura_linha

    largura_painel = largura - 160
    altura_painel = 215
    x_painel = 80
    y_painel = altura - altura_painel - 70
    rect_painel = pygame.Rect(x_painel, y_painel, largura_painel, altura_painel)

    while True:
        agora = pygame.time.get_ticks()
        mx, my = ui_helpers.obter_pos_mouse_superficie(tela)
        clicado = False

        # 1. Processamento de Eventos
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif evento.type == pygame.MOUSEMOTION:
                if evento.rel != (0, 0):
                    modo_interacao = "mouse"
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                if evento.button == 1:
                    modo_interacao = "mouse"
                    clicado = True
                    pos_evento = ui_helpers.converter_pos_mouse_jogo(evento.pos)
                    if btn_back_rect.collidepoint(pos_evento):
                        tocar_selecionar()
                        return "voltar"
                elif evento.button == 4:  # Scroll Up
                    if rect_painel.collidepoint(mx, my):
                        scroll_y -= 24
                elif evento.button == 5:  # Scroll Down
                    if rect_painel.collidepoint(mx, my):
                        scroll_y += 24
            elif evento.type == pygame.KEYDOWN:
                modo_interacao = "teclado"
                anterior = selecionado
                if evento.key == pygame.K_ESCAPE:
                    tocar_selecionar()
                    return "voltar"
                elif evento.key in [pygame.K_RIGHT, pygame.K_d]:
                    mover_selecao(1)
                elif evento.key in [pygame.K_LEFT, pygame.K_a]:
                    mover_selecao(-1)
                elif evento.key in [pygame.K_UP, pygame.K_w]:
                    scroll_y -= 24
                elif evento.key in [pygame.K_DOWN, pygame.K_s]:
                    scroll_y += 24
                elif evento.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    if aureas[selecionado]["ativa"]:
                        tocar_selecionar()
                        nome_aurea = aureas[selecionado]["nome"]
                        if nome_aurea == "AleatÃ³ria":
                            nome_aurea = random.choice(["Racional", "Impulsiva", "Devota", "Vanguarda", "Insana", "Voraz"])

                        # Salva a escolha
                        os.makedirs("saves", exist_ok=True)
                        with open("saves/aurea_selecionada.json", "w") as file:
                            json.dump({"aurea": nome_aurea}, file)
                        return "confirmar"

                if selecionado != anterior:
                    tocar_hover()

            # Suporte a Controle / Gamepad
            elif evento.type == pygame.JOYAXISMOTION and controle is not None:
                modo_interacao = "teclado"
                if evento.axis == 0:  # AnalÃ³gico Horizontal
                    anterior = selecionado
                    if evento.value > 0.5 and not analogo_movido:
                        mover_selecao(1)
                        analogo_movido = True
                        tocar_hover()
                    elif evento.value < -0.5 and not analogo_movido:
                        mover_selecao(-1)
                        analogo_movido = True
                        tocar_hover()
                    elif abs(evento.value) < 0.3:
                        analogo_movido = False

            elif evento.type == pygame.JOYHATMOTION and controle is not None:
                modo_interacao = "teclado"
                anterior = selecionado
                # D-Pad
                dx, dy = evento.value
                if dx > 0:
                    mover_selecao(1)
                    tocar_hover()
                elif dx < 0:
                    mover_selecao(-1)
                    tocar_hover()
                if dy > 0:
                    scroll_y -= 25
                elif dy < 0:
                    scroll_y += 25

            elif evento.type == pygame.JOYBUTTONDOWN and controle is not None:
                modo_interacao = "teclado"
                if evento.button == 0:  # BotÃ£o A do controle para confirmar
                    if aureas[selecionado]["ativa"]:
                        tocar_selecionar()
                        nome_aurea = aureas[selecionado]["nome"]
                        if nome_aurea == "AleatÃ³ria":
                            nome_aurea = random.choice(["Racional", "Impulsiva", "Devota", "Vanguarda", "Insana", "Voraz"])
                        os.makedirs("saves", exist_ok=True)
                        with open("saves/aurea_selecionada.json", "w") as file:
                            json.dump({"aurea": nome_aurea}, file)
                        return "confirmar"
                elif evento.button == 1:  # BotÃ£o B do controle para voltar
                    tocar_selecionar()
                    return "voltar"

        if controle is not None:
            # Ler eixo vertical do analógico esquerdo (eixo 1) para scroll
            val_y = controle.get_axis(1)
            if abs(val_y) > 0.3:
                scroll_y += val_y * 8

        # DetecÃ§Ã£o de hover e cliques do mouse nas Ã¡ureas
        largura_quadro = 160
        altura_quadro = 220
        for i, aurea in enumerate(aureas):
            if not aurea["ativa"]:
                continue
            curr_scale = card_scale[i]
            w_scaled = int(largura_quadro * curr_scale)
            h_scaled = int(altura_quadro * curr_scale)
            x_pos = int(card_x[i] - w_scaled // 2)
            y_pos = int(altura * 0.44 - h_scaled // 2 + card_y_offset[i])
            rect_card = pygame.Rect(x_pos, y_pos, w_scaled, h_scaled)

            if clicado and rect_card.collidepoint(mx, my):
                if selecionado != i:
                    mover_selecao(1 if distancia_circular(i, selecionado) > 0 else -1)
                    tocar_hover()
                else:
                    tocar_selecionar()
                    nome_aurea = aurea["nome"]
                    if nome_aurea == "AleatÃ³ria":
                        nome_aurea = random.choice(["Racional", "Impulsiva", "Devota", "Vanguarda", "Insana", "Voraz"])

                    os.makedirs("saves", exist_ok=True)
                    with open("saves/aurea_selecionada.json", "w") as file:
                        json.dump({"aurea": nome_aurea}, file)
                    return "confirmar"

        # 2. InterpolaÃ§Ã£o de Fundo
        bg_alvo = aureas[selecionado]["bg_tema"]
        for c in range(3):
            cor_fundo_atual[c] += (bg_alvo[c] - cor_fundo_atual[c]) * 0.08
        cor_accent = aureas[selecionado]["cor_tema"]
        ui_helpers.desenhar_fundo_menu_ruptura(
            tela,
            agora,
            particulas,
            tuple(int(c) for c in cor_fundo_atual),
            cor_accent,
            1.0,
        )
        ui_helpers.desenhar_cabecalho_menu(
            tela,
            "AUREAS",
            "A aura e sua regra passiva: escolha como Geovana reage a ruptura.",
            fonte_titulo,
            fonte_instrucao,
            cor_accent,
            y=80,
        )

        # 5. CÃ¡lculo das PosiÃ§Ãµes e Escalas dos Cards (AnimaÃ§Ã£o Fluida)
        largura_quadro = 150
        altura_quadro = 198
        espacamento_cards = 242
        centro_carrossel_y = int(altura * 0.44)

        for i, aurea in enumerate(aureas):
            # Define alvos
            dist = distancia_circular(i, selecionado)
            target_x = largura // 2 + dist * espacamento_cards

            if i == selecionado:
                target_scale = 1.28
                target_y_offset = -12
                target_alpha = 255
            else:
                target_scale = 0.85
                target_y_offset = 8
                target_alpha = 118

            # InterpolaÃ§Ã£o suave
            card_x[i] += (target_x - card_x[i]) * 0.1
            card_scale[i] += (target_scale - card_scale[i]) * 0.1
            card_y_offset[i] += (target_y_offset - card_y_offset[i]) * 0.1
            card_alpha[i] += (target_alpha - card_alpha[i]) * 0.1

        # 6. Renderizar Cards
        for i, aurea in enumerate(aureas):
            curr_scale = card_scale[i]
            w_scaled = int(largura_quadro * curr_scale)
            h_scaled = int(altura_quadro * curr_scale)
            x_pos = int(card_x[i] - w_scaled // 2)
            y_pos = int(centro_carrossel_y - h_scaled // 2 + card_y_offset[i])

            # SuperfÃ­cie temporÃ¡ria para o card com canal alpha
            surf_card = pygame.Surface((w_scaled, h_scaled), pygame.SRCALPHA)

            # Fundo glassmorphic do card
            alpha_fundo = int(50 + (card_alpha[i] / 255.0) * 110)
            pygame.draw.rect(surf_card, (20, 20, 25, alpha_fundo), (0, 0, w_scaled, h_scaled), border_radius=12)

            # Imagem da Ãurea
            img_scaled = pygame.transform.scale(imagens_aureas[i], (w_scaled - 12, h_scaled - 12))

            # Aplicar transparÃªncia Ã  imagem da Ãurea
            surf_img_alpha = pygame.Surface(img_scaled.get_size(), pygame.SRCALPHA)
            surf_img_alpha.blit(img_scaled, (0, 0))
            # Aplica canal alpha geral da imagem
            surf_img_alpha.fill((255, 255, 255, int(card_alpha[i])), special_flags=pygame.BLEND_RGBA_MULT)
            surf_card.blit(surf_img_alpha, (6, 6))

            # Desenhar Borda do Card
            cor_borda = aurea["cor_tema"] + (int(card_alpha[i]),)
            largura_linha = 3 if i == selecionado else 1
            pygame.draw.rect(surf_card, cor_borda, (0, 0, w_scaled, h_scaled), width=largura_linha, border_radius=12)

            # Efeito Glow ConcÃªntrico se estiver selecionado
            if i == selecionado:
                for g in range(1, 5):
                    glow_alpha = int((1.0 - g/5.0) * 80)
                    glow_color = aurea["cor_tema"] + (glow_alpha,)
                    glow_surf = pygame.Surface((w_scaled + g*4, h_scaled + g*4), pygame.SRCALPHA)
                    pygame.draw.rect(glow_surf, glow_color, (0, 0, w_scaled + g*4, h_scaled + g*4), width=1, border_radius=12 + g)
                    tela.blit(glow_surf, (x_pos - g*2, y_pos - g*2))

            # Blitar card final na tela
            tela.blit(surf_card, (x_pos, y_pos))

            # Badge do NÃ­vel (se aplicÃ¡vel)
            nome_aurea = aurea["nome"]
            if nome_aurea != "?" and nome_aurea != "AleatÃ³ria" and aurea["ativa"]:
                nivel = upgrades.get(nome_aurea, 0)
                if nivel > 0:
                    badge_texto = f"Nv. {nivel}"
                    render_badge = fonte_status.render(badge_texto, True, (255, 255, 255))

                    largura_badge = render_badge.get_width() + 16
                    altura_badge = 20
                    surf_badge = pygame.Surface((largura_badge, altura_badge), pygame.SRCALPHA)

                    pygame.draw.rect(surf_badge, (20, 20, 20, 230), (0, 0, largura_badge, altura_badge), border_radius=4)
                    pygame.draw.rect(surf_badge, aurea["cor_tema"], (0, 0, largura_badge, altura_badge), width=1, border_radius=4)
                    surf_badge.blit(render_badge, (8, (altura_badge - render_badge.get_height()) // 2))

                    # Desenhar no canto superior direito do card
                    tela.blit(surf_badge, (x_pos + w_scaled - largura_badge - 6, y_pos - 8))

        # 7. Renderizar Painel Descritivo Glassmorphic (Apenas para a selecionada)
        aurea_sel = aureas[selecionado]

        largura_painel = largura - 160
        altura_painel = 215
        x_painel = 80
        y_painel = altura - altura_painel - 70

        surf_painel = pygame.Surface((largura_painel, altura_painel), pygame.SRCALPHA)
        # Fundo do painel
        pygame.draw.rect(surf_painel, (10, 10, 15, 210), (0, 0, largura_painel, altura_painel), border_radius=16)
        # Borda brilhante combinando com o tema da Ã¡urea
        cor_borda_p = aurea_sel["cor_tema"] + (180,)
        pygame.draw.rect(surf_painel, cor_borda_p, (0, 0, largura_painel, altura_painel), width=2, border_radius=16)

        # Desenhar ConteÃºdo do Painel
        # TÃ­tulo da Ãurea
        nome_display = aurea_sel["nome"].upper()
        if nome_display not in ["?", "ALEATÃ“RIA"] and upgrades.get(aurea_sel["nome"], 0) > 0:
            nome_display += f" (NÃVEL {upgrades[aurea_sel['nome']]})"

        render_nome = fonte_nome.render(nome_display, True, aurea_sel["cor_tema"])
        surf_painel.blit(render_nome, (24, 16))

        # SubtÃ­tulo / Categoria
        render_cat = fonte_categoria.render(aurea_sel["categoria"], True, (150, 150, 150))
        surf_painel.blit(render_cat, (26, 48))

        # Linha DivisÃ³ria Vertical
        x_divisor = largura_painel // 2
        pygame.draw.line(surf_painel, (50, 50, 60, 150), (x_divisor, 16), (x_divisor, altura_painel - 16), 1)

        # DescriÃ§Ã£o principal
        desc_rect = pygame.Rect(24, 76, x_divisor - 48, 82)
        desenhar_texto_wrap_local(surf_painel, aurea_sel["efeito"], desc_rect, fonte_desc, (230, 230, 230), 1)

        # Atributos (Lado Direito) com Viewport Rolável
        y_attr = 18
        render_func = fonte_categoria.render("FUNCIONAMENTO", True, aurea_sel["cor_tema"])
        surf_painel.blit(render_func, (x_divisor + 24, y_attr))

        # Dimensões do Viewport
        w_view = largura_painel - x_divisor - 48
        h_view = altura_painel - 48 - 16
        x_view = x_divisor + 24
        y_view = 48

        # Calcular linhas embrulhadas e altura total
        linhas_por_attr = []
        total_h = 0
        espaco_entre_attrs = 12
        altura_linha = fonte_status.get_linesize()

        for attr in aurea_sel["atributos"]:
            linhas = obter_linhas_wrap(attr, w_view, fonte_status)
            h_attr = len(linhas) * altura_linha
            linhas_por_attr.append((linhas, h_attr))
            total_h += h_attr + espaco_entre_attrs

        if len(aurea_sel["atributos"]) > 0:
            total_h -= espaco_entre_attrs

        # Limitar o scroll
        max_scroll_y = max(0, total_h - h_view)
        scroll_y = max(0, min(scroll_y, max_scroll_y))

        # Desenhar conteúdo rolável em uma sub-superfície
        surf_content = pygame.Surface((w_view, max(1, total_h)), pygame.SRCALPHA)
        curr_y = 0
        for linhas, h_attr in linhas_por_attr:
            for i_linha, linha in enumerate(linhas):
                render_l = fonte_status.render(linha, True, (190, 190, 200))
                surf_content.blit(render_l, (0, curr_y))
                curr_y += altura_linha
            curr_y += espaco_entre_attrs

        # Recortar e blitar a parte visível (viewport)
        surf_viewport = pygame.Surface((w_view, h_view), pygame.SRCALPHA)
        surf_viewport.blit(surf_content, (0, -scroll_y))
        surf_painel.blit(surf_viewport, (x_view, y_view))

        # Barra de Rolagem (Scrollbar) se necessário
        if total_h > h_view:
            track_rect = pygame.Rect(largura_painel - 16, y_view, 4, h_view)
            pygame.draw.rect(surf_painel, (50, 50, 60, 100), track_rect, border_radius=2)

            thumb_h = max(15, int(h_view * (h_view / total_h)))
            thumb_y = y_view + int((scroll_y / max_scroll_y) * (h_view - thumb_h))
            thumb_rect = pygame.Rect(largura_painel - 16, thumb_y, 4, thumb_h)
            pygame.draw.rect(surf_painel, aurea_sel["cor_tema"], thumb_rect, border_radius=2)

        # Lore/Flavor text
        lore_rect = pygame.Rect(24, 165, x_divisor - 48, 40)
        desenhar_texto_wrap_local(surf_painel, f'"{aurea_sel["lore"]}"', lore_rect, fonte_lore, (120, 120, 130), 0)

        # Renderiza o painel final na tela
        tela.blit(surf_painel, (x_painel, y_painel))

        # 8. Barra de instruÃ§Ã£o no rodapÃ©
        texto_instr = "A/D ou SETAS: navegar | ENTER/ESPACO: selecionar | ESC: voltar"
        ui_helpers.desenhar_rodape_menu(tela, texto_instr, fonte_instrucao, cor_accent, altura - 28)

        # 9. BotÃ£o Voltar no Canto Superior Esquerdo (Desenhado dinamicamente com a cor do tema da Ãurea)
        is_hover_back = modo_interacao == "mouse" and btn_back_rect.collidepoint(mx, my)
        ui_helpers.desenhar_botao_voltar_menu(tela, btn_back_rect, fonte_desc, is_hover_back, cor_accent, "ESC Voltar")

        ui_helpers.desenhar_cursor_personalizado(tela)
        pygame.display.flip()
        clock.tick(60)

def tela_decisao_tutorial(tela, fonte):
    opcoes = ["Sim", "NÃ£o"]
    selecionado = 0
    clock = pygame.time.Clock()

    while True:
        tela.fill((10, 10, 10))
        texto_titulo = fonte.render("Deseja jogar o tutorial?", True, (255, 255, 255))
        tela.blit(texto_titulo, (largura_tela // 2 - texto_titulo.get_width() // 2, altura_tela // 4))

        mx, my = ui_helpers.obter_pos_mouse_superficie(tela)
        clicado = False

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                if evento.button == 1:
                    clicado = True
            elif evento.type == pygame.KEYDOWN:
                if evento.key in [pygame.K_LEFT, pygame.K_a]:
                    selecionado = (selecionado - 1) % len(opcoes)
                    tocar_hover()
                elif evento.key in [pygame.K_RIGHT, pygame.K_d]:
                    selecionado = (selecionado + 1) % len(opcoes)
                    tocar_hover()
                elif evento.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    tocar_selecionar()
                    with open("saves/tutorial_config.json", "w") as file:
                        json.dump({"mostrar_tutorial": opcoes[selecionado] == "Sim"}, file)
                    return opcoes[selecionado] == "Sim"

        for i, texto in enumerate(opcoes):
            rx = largura_tela // 2 - 100 + i * 150
            ry = altura_tela // 2

            # Caixa de colisÃ£o para a opÃ§Ã£o
            rect_opcao = pygame.Rect(rx - 10, ry - 5, 80, 40)
            if rect_opcao.collidepoint(mx, my):
                if selecionado != i:
                    selecionado = i
                    tocar_hover()
                if clicado:
                    tocar_selecionar()
                    with open("saves/tutorial_config.json", "w") as file:
                        json.dump({"mostrar_tutorial": opcoes[selecionado] == "Sim"}, file)
                    return opcoes[selecionado] == "Sim"

            cor = (255, 255, 255) if i == selecionado else (120, 120, 120)
            render = fonte.render(texto, True, cor)
            tela.blit(render, (rx, ry))

        ui_helpers.desenhar_cursor_personalizado(tela)
        pygame.display.flip()
        clock.tick(60)

def _snapshot_config(config):
    return json.dumps(config, sort_keys=True, ensure_ascii=False)


def _tem_alteracoes_pendentes(config, config_salva):
    return _snapshot_config(config) != _snapshot_config(config_salva)


def _confirmar_saida_alteracoes(tela, fonte_titulo_dialogo, fonte_texto_dialogo):
    opcoes_dialogo = [
        ("Salvar e sair", "salvar"),
        ("Sair sem salvar", "descartar"),
        ("Cancelar", "cancelar"),
    ]
    selecionado_dialogo = 0
    clock = pygame.time.Clock()

    while True:
        overlay = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        tela.blit(overlay, (0, 0))

        caixa = pygame.Rect(largura_tela // 2 - 330, altura_tela // 2 - 135, 660, 270)
        pygame.draw.rect(tela, (12, 10, 24), caixa, border_radius=10)
        pygame.draw.rect(tela, (0, 255, 204), caixa, width=2, border_radius=10)

        titulo = fonte_titulo_dialogo.render("ALTERACOES NAO SALVAS", True, (255, 230, 120))
        tela.blit(titulo, titulo.get_rect(center=(caixa.centerx, caixa.y + 48)))

        mensagem = fonte_texto_dialogo.render("Voce alterou configuracoes. O que deseja fazer?", True, (220, 220, 230))
        tela.blit(mensagem, mensagem.get_rect(center=(caixa.centerx, caixa.y + 92)))

        mx, my = ui_helpers.obter_pos_mouse_superficie(tela)
        for i, (label, _) in enumerate(opcoes_dialogo):
            botao = pygame.Rect(caixa.x + 90, caixa.y + 125 + i * 42, caixa.w - 180, 34)
            hover = botao.collidepoint(mx, my)
            if hover and selecionado_dialogo != i:
                selecionado_dialogo = i
            cor_borda = (0, 255, 204) if i == selecionado_dialogo else (90, 100, 120)
            cor_texto = (255, 255, 255) if i == selecionado_dialogo else (175, 180, 195)
            pygame.draw.rect(tela, (0, 180, 200, 55) if i == selecionado_dialogo else (20, 18, 32), botao, border_radius=6)
            pygame.draw.rect(tela, cor_borda, botao, width=1, border_radius=6)
            texto = fonte_texto_dialogo.render(label, True, cor_texto)
            tela.blit(texto, texto.get_rect(center=botao.center))

        ui_helpers.desenhar_cursor_personalizado(tela)
        pygame.display.flip()

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                exit()
            if evento.type == pygame.KEYDOWN:
                if evento.key in [pygame.K_UP, pygame.K_w]:
                    selecionado_dialogo = (selecionado_dialogo - 1) % len(opcoes_dialogo)
                    tocar_hover()
                elif evento.key in [pygame.K_DOWN, pygame.K_s]:
                    selecionado_dialogo = (selecionado_dialogo + 1) % len(opcoes_dialogo)
                    tocar_hover()
                elif evento.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    tocar_selecionar()
                    return opcoes_dialogo[selecionado_dialogo][1]
                elif evento.key == pygame.K_ESCAPE:
                    tocar_selecionar()
                    return "cancelar"
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                for i, (_, acao) in enumerate(opcoes_dialogo):
                    botao = pygame.Rect(caixa.x + 90, caixa.y + 125 + i * 42, caixa.w - 180, 34)
                    if botao.collidepoint(mx, my):
                        tocar_selecionar()
                        return acao

        clock.tick(60)


def _desenhar_status_aplicacao(tela, fonte_status, config, config_salva, y_pos):
    if _tem_alteracoes_pendentes(config, config_salva):
        texto_status = "Alteracoes pendentes - use Aplicar Alteracoes para salvar."
        cor_status = (255, 205, 90)
    else:
        texto_status = "Configuracoes aplicadas."
        cor_status = (0, 255, 170)

    texto = fonte_status.render(texto_status, True, cor_status)
    tela.blit(texto, texto.get_rect(center=(largura_tela // 2, y_pos)))


def _quebrar_texto_largura(texto, fonte, largura_max):
    palavras = str(texto).split()
    linhas = []
    linha = ""
    for palavra in palavras:
        teste = palavra if not linha else f"{linha} {palavra}"
        if fonte.size(teste)[0] <= largura_max:
            linha = teste
        else:
            if linha:
                linhas.append(linha)
            linha = palavra
    if linha:
        linhas.append(linha)
    return linhas or [""]


def _desenhar_caixa_descricao(tela, fonte_texto, texto, y_pos, largura=720):
    largura = min(largura, largura_tela - 80)
    linhas = _quebrar_texto_largura(texto, fonte_texto, largura - 32)[:2]
    altura = 34 + (len(linhas) - 1) * 22
    rect_desc = pygame.Rect(largura_tela // 2 - largura // 2, y_pos, largura, altura)
    pygame.draw.rect(tela, (15, 10, 30, 210), rect_desc, border_radius=8)
    pygame.draw.rect(tela, (0, 255, 230, 90), rect_desc, width=1, border_radius=8)
    y_texto = rect_desc.centery - ((len(linhas) - 1) * 11)
    for idx, linha in enumerate(linhas):
        surf = fonte_texto.render(linha, True, (215, 215, 230))
        tela.blit(surf, surf.get_rect(center=(rect_desc.centerx, y_texto + idx * 22)))


def tela_configuracoes_graficas(tela, fonte):
    """Tela de configuracoes graficas."""
    global ultima_troca, exibindo_fundo1, indice_fundo
    try:
        with open("saves/config_graficos.json", "r") as f:
            config = json.load(f)
    except:
        config = {
            "sombras_ativas": "dinamicas",
            "qualidade_grafica": "alta",
            "particulas_ativas": True,
            "efeitos_visuais": True,
            "efeitos_manifestacoes": "alto",
            "fps_limite": 60,
            "tela_cheia": False,
            "sangue_lacerante": "alto"
        }
    config.setdefault("fps_limite", 60)
    config.setdefault("nivel_detalhes", "alto")
    config.setdefault("particulas_ativas", True)
    config.setdefault("efeitos_visuais", True)
    config.setdefault("efeitos_manifestacoes", "alto")
    config.setdefault("tela_cheia", False)
    config.setdefault("sangue_lacerante", "alto")
    config["__aplicar__"] = "aplicar"
    config_salva = json.loads(json.dumps(config))

    opcoes_config = [
        {"nome": "Tela Cheia", "chave": "tela_cheia", "valores": [False, True], "labels": ["Janela", "Tela Cheia"]},
        {"nome": "Sombras", "chave": "sombras_ativas", "valores": ["desativadas", "simples", "dinamicas"], "labels": ["Desativadas", "Simples", "Dinamicas"]},
        {"nome": "Qualidade Grafica", "chave": "qualidade_grafica", "valores": ["alta", "media", "baixa"], "labels": ["Alta", "Media", "Baixa"]},
        {"nome": "Detalhes dos Efeitos", "chave": "nivel_detalhes", "valores": ["alto", "medio", "baixo"], "labels": ["Alto", "Medio", "Baixo"]},
        {"nome": "Particulas", "chave": "particulas_ativas", "valores": [True, False], "labels": ["Ativadas", "Desativadas"]},
        {"nome": "Efeitos Visuais", "chave": "efeitos_visuais", "valores": [True, False], "labels": ["Ativados", "Desativados"]},
        {"nome": "Efeitos Manifestacoes", "chave": "efeitos_manifestacoes", "valores": ["alto", "medio", "baixo", "desativado"], "labels": ["Alto", "Medio", "Baixo", "Desativado"]},
        {"nome": "Limite de FPS", "chave": "fps_limite", "valores": [30, 60, 120, 0], "labels": ["30 FPS", "60 FPS", "120 FPS", "Ilimitado"]},
        {"nome": "Sangue Lacerante", "chave": "sangue_lacerante", "valores": ["alto", "reduzido", "desativado"], "labels": ["Completo", "Reduzido", "Desativado"]},
        {"nome": "Aplicar Alteracoes", "chave": "__aplicar__", "valores": None, "labels": None},
        {"nome": "Voltar", "chave": None, "valores": None, "labels": None}
    ]

    descricoes_valores = {
        "__aplicar__": {
            "aplicar": "Salva e aplica as alteracoes feitas nesta tela."
        },
        "tela_cheia": {
            False: "Modo janela. Mantem barras e habilidades sobre a tela do jogo.",
            True: "Tela cheia. Centraliza o jogo e move HUD para molduras laterais."
        },
        "sombras_ativas": {
            "desativadas": "Desliga sombras. Melhora muito o desempenho em PCs fracos.",
            "simples": "Sombras basicas estaticas. Bom equilibrio de performance.",
            "dinamicas": "Sombras realistas em tempo real. Exige mais da placa de video."
        },
        "qualidade_grafica": {
            "alta": "Texturas e renderizacao maxima. Para placas de video modernas.",
            "media": "Qualidade padrao equilibrada para a maioria dos computadores.",
            "baixa": "Reduz resolucao de efeitos para rodar liso em qualquer maquina."
        },
        "nivel_detalhes": {
            "alto": "Mais fragmentos, brilho e solidificacao detalhada na HUD.",
            "medio": "Equilibrio entre efeitos visuais e desempenho.",
            "baixo": "Efeitos essenciais com menos particulas e brilho."
        },
        "particulas_ativas": {
            True: "Particulas visuais de explosoes e faiscas ligadas.",
            False: "Remove particulas para maior clareza visual e desempenho."
        },
        "efeitos_visuais": {
            True: "Ativa brilhos, distorcoes de tempo e glows premium.",
            False: "Desativa pos-processamento pesado para evitar lentidao."
        },
        "efeitos_manifestacoes": {
            "alto": "Mostra efeitos completos de manifestacoes, como marcas, vinhas e parasitas.",
            "medio": "Reduz quantidade de vinhas, marcas e particulas das manifestacoes.",
            "baixo": "Mantem leitura essencial com poucos efeitos ao redor de inimigos e projeteis.",
            "desativado": "Remove efeitos extras das manifestacoes sem desligar toda a interface."
        },
        "fps_limite": {
            30: "Limita a 30 FPS. Reduz consumo de energia e aquecimento.",
            60: "Padrao recomendado para jogabilidade fluida e estavel.",
            120: "Para monitores de alta taxa de atualizacao (120Hz ou mais).",
            0: "Ilimitado. Roda o mais rapido possivel (uso maximo de hardware)."
        },
        "sangue_lacerante": {
            "alto": "Efeito de sangue completo na passiva Lacerante. Maxima fidelidade.",
            "reduzido": "Efeito de sangue simplificado para economizar desempenho.",
            "desativado": "Remove as gotas e o rastro de sangue da passiva Lacerante."
        }
    }

    selecionado = 0
    modo_interacao = "teclado"
    clock = pygame.time.Clock()
    fonte_titulo_tela = pygame.font.Font(caminho_fonte_titulo, 48)
    fonte_opcao_tela = pygame.font.Font(caminho_fonte_letra1, 24)
    fonte_valor_tela = pygame.font.Font(caminho_fonte_letras, 20)
    popup_aplicar = PopUpAplicar(largura_tela, altura_tela)

    def aplicar_config():
        nonlocal config_salva, tela
        if not _tem_alteracoes_pendentes(config, config_salva):
            return False
        dados_para_salvar = {k: v for k, v in config.items() if not k.startswith("__")}
        with open("saves/config_graficos.json", "w") as f:
            json.dump(dados_para_salvar, f, indent=4)
        tela = configurar_tela(largura_tela, altura_tela)
        config_salva = json.loads(json.dumps(config))
        popup_aplicar.disparar(pygame.time.get_ticks())
        return True

    def tentar_sair():
        if not _tem_alteracoes_pendentes(config, config_salva):
            return True
        acao = _confirmar_saida_alteracoes(tela, fonte_opcao_tela, fonte_valor_tela)
        if acao == "salvar":
            aplicar_config()
            return True
        if acao == "descartar":
            return True
        return False

    while True:
        agora = pygame.time.get_ticks()

        # Atualiza e desenha o fundo dinÃ¢mico
        if exibindo_fundo1:
            tela.blit(fundo_menu1, (0, 0))
            if agora - ultima_troca > tempo_exibicao_fundo1:
                exibindo_fundo1 = False
                ultima_troca = agora
                indice_fundo = 0
        else:
            tela.blit(imagens_fundo[indice_fundo], (0, 0))
            if agora - ultima_troca > tempo_troca_fundo:
                indice_fundo = (indice_fundo + 1) % len(imagens_fundo)
                ultima_troca = agora

        # Camada preta semi-transparente para contraste
        overlay = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        tela.blit(overlay, (0, 0))

        texto_titulo = render_glitch_text_with_fallback("CONFIGURACOES GRAFICAS", fonte_titulo_tela, fonte_fallback_config, (0, 255, 204))
        retangulo_titulo = texto_titulo.get_rect(center=(largura_tela // 2, altura_tela // 8))

        # Sombra
        texto_titulo_sombra = render_glitch_text_with_fallback("CONFIGURACOES GRAFICAS", fonte_titulo_tela, fonte_fallback_config, (15, 5, 25))
        tela.blit(texto_titulo_sombra, (retangulo_titulo.left + 4, retangulo_titulo.top + 4))

        # Contorno
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            texto_titulo_contorno = render_glitch_text_with_fallback("CONFIGURACOES GRAFICAS", fonte_titulo_tela, fonte_fallback_config, contorno_rosa)
            tela.blit(texto_titulo_contorno, (retangulo_titulo.left + dx, retangulo_titulo.top + dy))

        tela.blit(texto_titulo, retangulo_titulo)

        mx, my = ui_helpers.obter_pos_mouse_superficie(tela)
        clicado = False

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif evento.type == pygame.MOUSEMOTION:
                if evento.rel != (0, 0):
                    modo_interacao = "mouse"
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                if evento.button == 1:
                    modo_interacao = "mouse"
                    clicado = True
            elif evento.type == pygame.KEYDOWN:
                modo_interacao = "teclado"
                if evento.key in [pygame.K_UP, pygame.K_w]:
                    selecionado = (selecionado - 1) % len(opcoes_config)
                    tocar_hover()
                elif evento.key in [pygame.K_DOWN, pygame.K_s]:
                    selecionado = (selecionado + 1) % len(opcoes_config)
                    tocar_hover()
                elif evento.key in [pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d]:
                    if opcoes_config[selecionado]["chave"] and opcoes_config[selecionado]["chave"] != "__aplicar__":
                        tocar_hover()
                        chave = opcoes_config[selecionado]["chave"]
                        valores = opcoes_config[selecionado]["valores"]
                        valor_atual = config[chave]
                        indice_atual = valores.index(valor_atual)

                        if evento.key in [pygame.K_RIGHT, pygame.K_d]:
                            novo_indice = (indice_atual + 1) % len(valores)
                        else:
                            novo_indice = (indice_atual - 1) % len(valores)

                        config[chave] = valores[novo_indice]

                elif evento.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    tocar_selecionar()
                    if opcoes_config[selecionado]["chave"] == "__aplicar__":
                        aplicar_config()
                    elif opcoes_config[selecionado]["nome"] == "Voltar" and tentar_sair():
                        return
                elif evento.key == pygame.K_ESCAPE:
                    tocar_selecionar()
                    if tentar_sair():
                        return

        # Desenhar opÃ§Ãµes
        y_inicial = altura_tela // 4
        espacamento = 46

        for i, opcao in enumerate(opcoes_config):
            y_pos = y_inicial + i * espacamento
            rect_bg = pygame.Rect(largura_tela // 4 - 20, y_pos - 8, largura_tela // 2 + 40, 42)

            # DetecÃ§Ã£o de hover e cliques do mouse
            if modo_interacao == "mouse" and rect_bg.collidepoint(mx, my):
                if selecionado != i:
                    selecionado = i
                    tocar_hover()
                if clicado:
                    tocar_selecionar()
                    if opcao["chave"] == "__aplicar__":
                        aplicar_config()
                    elif opcao["nome"] == "Voltar" and tentar_sair():
                        return
                    elif opcao["chave"]:
                        chave = opcao["chave"]
                        valores = opcao["valores"]
                        valor_atual = config[chave]
                        indice_atual = valores.index(valor_atual)

                        # Verificar se o clique foi na seta esquerda ou direita
                        rect_seta_esq = pygame.Rect(largura_tela // 2 + 15, y_pos + 4, 25, 34)
                        rect_seta_dir = pygame.Rect(largura_tela // 2 + 225, y_pos + 4, 25, 34)

                        if rect_seta_esq.collidepoint(mx, my):
                            novo_indice = (indice_atual - 1) % len(valores)
                        elif rect_seta_dir.collidepoint(mx, my):
                            novo_indice = (indice_atual + 1) % len(valores)
                        else:
                            novo_indice = (indice_atual + 1) % len(valores)

                        config[chave] = valores[novo_indice]

            # Caixa glassy para a opÃ§Ã£o selecionada
            if i == selecionado:
                pygame.draw.rect(tela, (0, 180, 200, 65), rect_bg, border_radius=6)
                pygame.draw.rect(tela, (0, 255, 230), rect_bg, width=2, border_radius=6)
                cor_nome = (255, 255, 255)
            else:
                cor_nome = (120, 120, 120)

            # Nome da opÃ§Ã£o
            texto_nome = fonte_opcao_tela.render(opcao["nome"], True, cor_nome)
            tela.blit(texto_nome, (largura_tela // 4, y_pos))

            # Valor atual (se nÃ£o for "Voltar")
            if opcao["chave"] and opcao["chave"] != "__aplicar__":
                valor_atual = config[opcao["chave"]]
                indice_valor = opcao["valores"].index(valor_atual)
                label_valor = opcao["labels"][indice_valor]

                cor_valor = (0, 255, 204) if i == selecionado else (150, 150, 150)
                texto_valor = fonte_valor_tela.render(label_valor, True, cor_valor)
                tela.blit(texto_valor, (largura_tela // 2 + 50, y_pos + 4))

                # Setas de navegaÃ§Ã£o se selecionado
                if i == selecionado:
                    seta_esq = fonte_valor_tela.render("<", True, (255, 255, 255))
                    seta_dir = fonte_valor_tela.render(">", True, (255, 255, 255))
                    tela.blit(seta_esq, (largura_tela // 2 + 20, y_pos + 4))
                    tela.blit(seta_dir, (largura_tela // 2 + 230, y_pos + 4))

        opt_sel = opcoes_config[selecionado]
        if opt_sel["chave"] is None:
            texto_desc_str = "Retornar ao menu de configuracoes anterior."
        else:
            val_sel = config[opt_sel["chave"]]
            texto_desc_str = descricoes_valores[opt_sel["chave"]][val_sel]
        y_desc = min(altura_tela - 128, y_inicial + len(opcoes_config) * espacamento + 10)
        _desenhar_caixa_descricao(tela, fonte_valor_tela, texto_desc_str, y_desc)

        # InstruÃ§Ãµes no rodapÃ©
        instrucoes = [
            "W/S: Navegar | A/D: Alterar valor",
            "ENTER/ESPACO: Confirmar | ESC: Voltar"
        ]

        y_instrucao = altura_tela - 55
        for instrucao in instrucoes:
            texto_inst = fonte_instrucao.render(instrucao, True, (150, 150, 150))
            tela.blit(texto_inst, (largura_tela // 2 - texto_inst.get_width() // 2, y_instrucao))
            y_instrucao += 20

        if popup_aplicar.ativo:
            popup_aplicar.update(agora)
            popup_aplicar.draw(tela)

        ui_helpers.desenhar_cursor_personalizado(tela)
        pygame.display.flip()
        clock.tick(60)


def tela_configuracoes_audio(tela, fonte):
    """Tela de configuracoes de audio."""
    global ultima_troca, exibindo_fundo1, indice_fundo
    # Carregar configuraÃ§Ãµes atuais
    try:
        with open("saves/config_audio.json", "r") as f:
            config = json.load(f)
    except:
        config = {
            "volume_musica": 0.5,
            "volume_efeitos": 0.5,
            "volume_master": 1.0
        }
    config_salva = json.loads(json.dumps(config))

    selecionado = 0
    modo_interacao = "teclado"
    clock = pygame.time.Clock()
    fonte_titulo_tela = pygame.font.Font(caminho_fonte_titulo, 48)
    fonte_opcao_tela = pygame.font.Font(caminho_fonte_letra1, 24)
    fonte_valor_tela = pygame.font.Font(caminho_fonte_letras, 20)
    popup_aplicar = PopUpAplicar(largura_tela, altura_tela)

    opcoes = ["volume_master", "volume_musica", "volume_efeitos", "aplicar", "voltar"]
    labels = ["Volume Master", "Volume Musica", "Volume Efeitos", "Aplicar Alteracoes", "Voltar"]

    descricoes_audio = {
        "volume_master": "Volume geral. Ajusta a musica e os efeitos sonoros proporcionalmente.",
        "volume_musica": "Trilha sonora. Ajusta o volume da musica de fundo e ambiente.",
        "volume_efeitos": "Efeitos sonoros. Ajusta o volume de tiros, explosoes e impactos.",
        "voltar": "Retornar ao menu de configuracoes anterior."
    }
    descricoes_audio["aplicar"] = "Salva e aplica as alteracoes de audio agora."

    def aplicar_config():
        nonlocal config_salva
        if not _tem_alteracoes_pendentes(config, config_salva):
            return False
        with open("saves/config_audio.json", "w") as f:
            json.dump(config, f, indent=4)
        aplicar_volumes_audio(config)
        config_salva = json.loads(json.dumps(config))
        popup_aplicar.disparar(pygame.time.get_ticks())
        return True

    def tentar_sair():
        if not _tem_alteracoes_pendentes(config, config_salva):
            return True
        acao = _confirmar_saida_alteracoes(tela, fonte_opcao_tela, fonte_valor_tela)
        if acao == "salvar":
            aplicar_config()
            return True
        if acao == "descartar":
            pygame.mixer.music.set_volume(config_salva["volume_musica"] * config_salva["volume_master"])
            return True
        return False

    while True:
        agora = pygame.time.get_ticks()

        # Atualiza e desenha o fundo dinÃ¢mico
        if exibindo_fundo1:
            tela.blit(fundo_menu1, (0, 0))
            if agora - ultima_troca > tempo_exibicao_fundo1:
                exibindo_fundo1 = False
                ultima_troca = agora
                indice_fundo = 0
        else:
            tela.blit(imagens_fundo[indice_fundo], (0, 0))
            if agora - ultima_troca > tempo_troca_fundo:
                indice_fundo = (indice_fundo + 1) % len(imagens_fundo)
                ultima_troca = agora

        # Camada preta semi-transparente para contraste
        overlay = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        tela.blit(overlay, (0, 0))

        texto_titulo = render_glitch_text_with_fallback("CONFIGURACOES DE AUDIO", fonte_titulo_tela, fonte_fallback_config, (0, 255, 204))
        retangulo_titulo = texto_titulo.get_rect(center=(largura_tela // 2, altura_tela // 8))

        # Sombra
        texto_titulo_sombra = render_glitch_text_with_fallback("CONFIGURACOES DE AUDIO", fonte_titulo_tela, fonte_fallback_config, (15, 5, 25))
        tela.blit(texto_titulo_sombra, (retangulo_titulo.left + 4, retangulo_titulo.top + 4))

        # Contorno
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            texto_titulo_contorno = render_glitch_text_with_fallback("CONFIGURACOES DE AUDIO", fonte_titulo_tela, fonte_fallback_config, contorno_rosa)
            tela.blit(texto_titulo_contorno, (retangulo_titulo.left + dx, retangulo_titulo.top + dy))

        tela.blit(texto_titulo, retangulo_titulo)

        mx, my = ui_helpers.obter_pos_mouse_superficie(tela)
        clicado = False
        mouse_pressionado = pygame.mouse.get_pressed()[0]

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif evento.type == pygame.MOUSEMOTION:
                if evento.rel != (0, 0):
                    modo_interacao = "mouse"
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                if evento.button == 1:
                    modo_interacao = "mouse"
                    clicado = True
            elif evento.type == pygame.KEYDOWN:
                modo_interacao = "teclado"
                if evento.key in [pygame.K_UP, pygame.K_w]:
                    selecionado = (selecionado - 1) % len(opcoes)
                    tocar_hover()
                elif evento.key in [pygame.K_DOWN, pygame.K_s]:
                    selecionado = (selecionado + 1) % len(opcoes)
                    tocar_hover()
                elif evento.key in [pygame.K_LEFT, pygame.K_a]:
                    if opcoes[selecionado] not in ["voltar", "aplicar"]:
                        tocar_hover()
                        chave = opcoes[selecionado]
                        config[chave] = max(0.0, config[chave] - 0.1)
                        pygame.mixer.music.set_volume(config["volume_musica"] * config["volume_master"])

                elif evento.key in [pygame.K_RIGHT, pygame.K_d]:
                    if opcoes[selecionado] not in ["voltar", "aplicar"]:
                        tocar_hover()
                        chave = opcoes[selecionado]
                        config[chave] = min(1.0, config[chave] + 0.1)
                        pygame.mixer.music.set_volume(config["volume_musica"] * config["volume_master"])

                elif evento.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    tocar_selecionar()
                    if opcoes[selecionado] == "aplicar":
                        aplicar_config()
                    elif opcoes[selecionado] == "voltar" and tentar_sair():
                        return
                elif evento.key == pygame.K_ESCAPE:
                    tocar_selecionar()
                    if tentar_sair():
                        return

        # Desenhar opÃ§Ãµes
        y_inicial = altura_tela // 4 + 40
        espacamento = 65

        for i, opcao in enumerate(opcoes):
            y_pos = y_inicial + i * espacamento
            rect_bg = pygame.Rect(largura_tela // 4 - 20, y_pos - 8, largura_tela // 2 + 40, 48)

            # DetecÃ§Ã£o de hover e cliques do mouse
            if modo_interacao == "mouse" and rect_bg.collidepoint(mx, my):
                if selecionado != i:
                    selecionado = i
                    tocar_hover()
                if clicado:
                    tocar_selecionar()
                    if opcao == "aplicar":
                        aplicar_config()
                    elif opcao == "voltar" and tentar_sair():
                        return

                # Se arrastar ou clicar nos volumes, ajustar dinamicamente
                if mouse_pressionado and opcao not in ["voltar", "aplicar"]:
                    barra_x = largura_tela // 2 - 20
                    barra_largura = 200
                    # Calcula novo volume de forma contÃ­nua
                    novo_val = (mx - barra_x) / barra_largura
                    novo_val = max(0.0, min(1.0, novo_val))
                    novo_val = round(novo_val, 2)
                    if config[opcao] != novo_val:
                        config[opcao] = novo_val
                        pygame.mixer.music.set_volume(config["volume_musica"] * config["volume_master"])

            # Caixa glassy para a opÃ§Ã£o selecionada
            if i == selecionado:
                pygame.draw.rect(tela, (0, 180, 200, 65), rect_bg, border_radius=6)
                pygame.draw.rect(tela, (0, 255, 230), rect_bg, width=2, border_radius=6)
                cor_nome = (255, 255, 255)
            else:
                cor_nome = (120, 120, 120)

            # Nome da opÃ§Ã£o
            texto_nome = fonte_opcao_tela.render(labels[i], True, cor_nome)
            tela.blit(texto_nome, (largura_tela // 4, y_pos))

            # Barra de volume (se nÃ£o for "Voltar")
            if opcao not in ["voltar", "aplicar"]:
                valor = config[opcao]

                # Barra de fundo
                barra_x = largura_tela // 2 - 20
                barra_y = y_pos + 10
                barra_largura = 200
                barra_altura = 16

                pygame.draw.rect(tela, (50, 50, 50), (barra_x, barra_y, barra_largura, barra_altura), border_radius=4)

                # Barra de preenchimento
                cor_barra = (0, 255, 204) if i == selecionado else (100, 200, 180)
                largura_preenchimento = int(barra_largura * valor)
                pygame.draw.rect(tela, cor_barra, (barra_x, barra_y, largura_preenchimento, barra_altura), border_radius=4)

                # Borda
                pygame.draw.rect(tela, (255, 255, 255), (barra_x, barra_y, barra_largura, barra_altura), 1, border_radius=4)

                # Porcentagem
                porcentagem = int(valor * 100)
                texto_porcentagem = fonte_valor_tela.render(f"{porcentagem}%", True, cor_nome)
                tela.blit(texto_porcentagem, (barra_x + barra_largura + 15, y_pos + 5))

                # Setas de navegaÃ§Ã£o se selecionado
                if i == selecionado:
                    seta_esq = fonte_valor_tela.render("<", True, (255, 255, 255))
                    seta_dir = fonte_valor_tela.render(">", True, (255, 255, 255))
                    tela.blit(seta_esq, (barra_x - 25, y_pos + 5))
                    tela.blit(seta_dir, (barra_x + barra_largura + 50, y_pos + 5))

        opt_sel = opcoes[selecionado]
        texto_desc_str = descricoes_audio[opt_sel]
        y_desc = min(altura_tela - 128, y_inicial + len(opcoes) * espacamento + 10)
        _desenhar_caixa_descricao(tela, fonte_valor_tela, texto_desc_str, y_desc)

        # InstruÃ§Ãµes no rodapÃ©
        instrucoes = [
            "W/S: Navegar | A/D: Ajustar volume",
            "ENTER/ESPACO: Confirmar | ESC: Voltar"
        ]

        y_instrucao = altura_tela - 55
        for instrucao in instrucoes:
            texto_inst = fonte_instrucao.render(instrucao, True, (150, 150, 150))
            tela.blit(texto_inst, (largura_tela // 2 - texto_inst.get_width() // 2, y_instrucao))
            y_instrucao += 20

        if popup_aplicar.ativo:
            popup_aplicar.update(agora)
            popup_aplicar.draw(tela)

        ui_helpers.desenhar_cursor_personalizado(tela)
        pygame.display.flip()
        clock.tick(60)


def tela_configuracoes_jogabilidade(tela, fonte):
    """Tela de configuracoes de jogabilidade."""
    global ultima_troca, exibindo_fundo1, indice_fundo

    # Carregar tutorial config
    try:
        with open("saves/tutorial_config.json", "r") as f:
            mostrar_tut = json.load(f).get("mostrar_tutorial", True)
    except:
        mostrar_tut = True

    # Carregar teleporte config
    try:
        with open("saves/config_teleporte.json", "r") as f:
            modo_teleporte = json.load(f).get("modo", "fixo")
    except:
        modo_teleporte = "fixo"

    try:
        import Variaveis
        loja_forcada = Variaveis.loja_forcada_ativa(forcar_recarregar=True)
    except:
        loja_forcada = True

    config = {
        "mostrar_tutorial": mostrar_tut,
        "modo_teleporte": modo_teleporte,
        "loja_forcada": loja_forcada
    }
    config["__aplicar__"] = "aplicar"
    config_salva = json.loads(json.dumps(config))

    opcoes_config = [
        {"nome": "Tutorial", "chave": "mostrar_tutorial", "valores": [True, False], "labels": ["Ativado", "Desativado"]},
        {"nome": "Modo de Teleporte", "chave": "modo_teleporte", "valores": ["fixo", "mouse"], "labels": ["Fixo", "Mouse Target"]},
        {"nome": "Loja Forcada", "chave": "loja_forcada", "valores": [True, False], "labels": ["Ativada", "Desativada"]},
        {"nome": "Aplicar Alteracoes", "chave": "__aplicar__", "valores": None, "labels": None},
        {"nome": "Voltar", "chave": None, "valores": None, "labels": None}
    ]

    descricoes_valores = {
        "mostrar_tutorial": {
            True: "Exibe baloes explicativos e dicas ao longo das fases para iniciantes.",
            False: "Desativa tutoriais de jogabilidade. Recomendado para jogadores experientes."
        },
        "modo_teleporte": {
            "fixo": "Modo Fixo: Teleporta na direcao do movimento. Rapido e instantaneo.",
            "mouse": "Modo Mouse: Segure a tecla para mirar na posicao do cursor e solte para teleportar."
        },
        "loja_forcada": {
            True: "A loja abre sozinha apos aviso quando voce acumula pontos para 5 cartas.",
            False: "A loja nunca abre sozinha; voce decide quando gastar seus pontos."
        }
    }

    descricoes_valores["__aplicar__"] = {"aplicar": "Salva e aplica as alteracoes de jogabilidade."}
    selecionado = 0
    modo_interacao = "teclado"
    clock = pygame.time.Clock()
    fonte_titulo_tela = pygame.font.Font(caminho_fonte_titulo, 48)
    fonte_opcao_tela = pygame.font.Font(caminho_fonte_letra1, 24)
    fonte_valor_tela = pygame.font.Font(caminho_fonte_letras, 20)
    popup_aplicar = PopUpAplicar(largura_tela, altura_tela)

    def aplicar_config():
        nonlocal config_salva
        if not _tem_alteracoes_pendentes(config, config_salva):
            return False
        with open("saves/tutorial_config.json", "w") as f:
            json.dump({"mostrar_tutorial": config["mostrar_tutorial"]}, f)
        with open("saves/config_teleporte.json", "w") as f:
            json.dump({"modo": config["modo_teleporte"]}, f)
        try:
            import Variaveis
            Variaveis.salvar_config_jogabilidade({"loja_forcada": config["loja_forcada"]})
            Variaveis.obter_modo_teleporte(forcar_recarregar=True)
        except Exception:
            pass
        config_salva = json.loads(json.dumps(config))
        popup_aplicar.disparar(pygame.time.get_ticks())
        return True

    def tentar_sair():
        if not _tem_alteracoes_pendentes(config, config_salva):
            return True
        acao = _confirmar_saida_alteracoes(tela, fonte_opcao_tela, fonte_valor_tela)
        if acao == "salvar":
            aplicar_config()
            return True
        if acao == "descartar":
            return True
        return False

    while True:
        agora = pygame.time.get_ticks()

        # Fundo dinÃ¢mico
        if exibindo_fundo1:
            tela.blit(fundo_menu1, (0, 0))
            if agora - ultima_troca > tempo_exibicao_fundo1:
                exibindo_fundo1 = False
                ultima_troca = agora
                indice_fundo = 0
        else:
            tela.blit(imagens_fundo[indice_fundo], (0, 0))
            if agora - ultima_troca > tempo_troca_fundo:
                indice_fundo = (indice_fundo + 1) % len(imagens_fundo)
                ultima_troca = agora

        # Overlay
        overlay = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 185))
        tela.blit(overlay, (0, 0))

        texto_titulo = render_glitch_text_with_fallback("CONFIGURACOES DE JOGABILIDADE", fonte_titulo_tela, fonte_fallback_config, (0, 255, 204))
        retangulo_titulo = texto_titulo.get_rect(center=(largura_tela // 2, altura_tela // 8))

        # Sombra
        texto_titulo_sombra = render_glitch_text_with_fallback("CONFIGURACOES DE JOGABILIDADE", fonte_titulo_tela, fonte_fallback_config, (15, 5, 25))
        tela.blit(texto_titulo_sombra, (retangulo_titulo.left + 4, retangulo_titulo.top + 4))

        # Contorno
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            texto_titulo_contorno = render_glitch_text_with_fallback("CONFIGURACOES DE JOGABILIDADE", fonte_titulo_tela, fonte_fallback_config, contorno_rosa)
            tela.blit(texto_titulo_contorno, (retangulo_titulo.left + dx, retangulo_titulo.top + dy))

        tela.blit(texto_titulo, retangulo_titulo)

        mx, my = ui_helpers.obter_pos_mouse_superficie(tela)
        clicado = False

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif evento.type == pygame.MOUSEMOTION:
                if evento.rel != (0, 0):
                    modo_interacao = "mouse"
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                if evento.button == 1:
                    modo_interacao = "mouse"
                    clicado = True
            elif evento.type == pygame.KEYDOWN:
                modo_interacao = "teclado"
                if evento.key in [pygame.K_UP, pygame.K_w]:
                    selecionado = (selecionado - 1) % len(opcoes_config)
                    tocar_hover()
                elif evento.key in [pygame.K_DOWN, pygame.K_s]:
                    selecionado = (selecionado + 1) % len(opcoes_config)
                    tocar_hover()
                elif evento.key in [pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d]:
                    if opcoes_config[selecionado]["chave"] and opcoes_config[selecionado]["chave"] != "__aplicar__":
                        tocar_hover()
                        chave = opcoes_config[selecionado]["chave"]
                        valores = opcoes_config[selecionado]["valores"]
                        valor_atual = config[chave]
                        indice_atual = valores.index(valor_atual)

                        if evento.key in [pygame.K_RIGHT, pygame.K_d]:
                            novo_indice = (indice_atual + 1) % len(valores)
                        else:
                            novo_indice = (indice_atual - 1) % len(valores)

                        config[chave] = valores[novo_indice]

                elif evento.key in [pygame.K_RETURN, pygame.K_SPACE]:
                    tocar_selecionar()
                    if opcoes_config[selecionado]["chave"] == "__aplicar__":
                        aplicar_config()
                    elif opcoes_config[selecionado]["nome"] == "Voltar" and tentar_sair():
                        return
                elif evento.key == pygame.K_ESCAPE:
                    tocar_selecionar()
                    if tentar_sair():
                        return

        # Desenhar opÃ§Ãµes
        y_inicial = altura_tela // 3 + 20
        espacamento = 70

        for i, opcao in enumerate(opcoes_config):
            y_pos = y_inicial + i * espacamento
            rect_bg = pygame.Rect(largura_tela // 4 - 20, y_pos - 8, largura_tela // 2 + 40, 48)

            # DetecÃ§Ã£o de hover e cliques do mouse
            if modo_interacao == "mouse" and rect_bg.collidepoint(mx, my):
                if selecionado != i:
                    selecionado = i
                    tocar_hover()
                if clicado:
                    tocar_selecionar()
                    if opcao["chave"] == "__aplicar__":
                        aplicar_config()
                    elif opcao["nome"] == "Voltar" and tentar_sair():
                        return
                    elif opcao["chave"]:
                        chave = opcao["chave"]
                        valores = opcao["valores"]
                        valor_atual = config[chave]
                        indice_atual = valores.index(valor_atual)

                        # Verificar se o clique foi na seta esquerda ou direita
                        rect_seta_esq = pygame.Rect(largura_tela // 2 + 15, y_pos + 4, 25, 34)
                        rect_seta_dir = pygame.Rect(largura_tela // 2 + 225, y_pos + 4, 25, 34)

                        if rect_seta_esq.collidepoint(mx, my):
                            novo_indice = (indice_atual - 1) % len(valores)
                        elif rect_seta_dir.collidepoint(mx, my):
                            novo_indice = (indice_atual + 1) % len(valores)
                        else:
                            novo_indice = (indice_atual + 1) % len(valores)

                        config[chave] = valores[novo_indice]


            # Caixa glassy para a opÃ§Ã£o selecionada
            if i == selecionado:
                pygame.draw.rect(tela, (0, 180, 200, 65), rect_bg, border_radius=6)
                pygame.draw.rect(tela, (0, 255, 230), rect_bg, width=2, border_radius=6)
                cor_nome = (255, 255, 255)
            else:
                cor_nome = (120, 120, 120)

            # Nome da opÃ§Ã£o
            texto_nome = fonte_opcao_tela.render(opcao["nome"], True, cor_nome)
            tela.blit(texto_nome, (largura_tela // 4, y_pos))

            # Valor atual
            if opcao["chave"] and opcao["chave"] != "__aplicar__":
                valor_atual = config[opcao["chave"]]
                indice_valor = opcao["valores"].index(valor_atual)
                label_valor = opcao["labels"][indice_valor]

                cor_valor = (0, 255, 204) if i == selecionado else (150, 150, 150)
                texto_valor = fonte_valor_tela.render(label_valor, True, cor_valor)
                tela.blit(texto_valor, (largura_tela // 2 + 50, y_pos + 4))

                if i == selecionado:
                    seta_esq = fonte_valor_tela.render("<", True, (255, 255, 255))
                    seta_dir = fonte_valor_tela.render(">", True, (255, 255, 255))
                    tela.blit(seta_esq, (largura_tela // 2 + 20, y_pos + 4))
                    tela.blit(seta_dir, (largura_tela // 2 + 230, y_pos + 4))

        opt_sel = opcoes_config[selecionado]
        if opt_sel["chave"] is None:
            texto_desc_str = "Retornar ao menu de configuracoes anterior."
        else:
            val_sel = config[opt_sel["chave"]]
            texto_desc_str = descricoes_valores[opt_sel["chave"]][val_sel]
        y_desc = min(altura_tela - 128, y_inicial + len(opcoes_config) * espacamento + 10)
        _desenhar_caixa_descricao(tela, fonte_valor_tela, texto_desc_str, y_desc)

        # InstruÃ§Ãµes no rodapÃ©
        instrucoes = [
            "W/S: Navegar | A/D: Alterar valor",
            "ENTER/ESPACO: Confirmar | ESC: Voltar"
        ]

        y_instrucao = altura_tela - 55
        for instrucao in instrucoes:
            texto_inst = fonte_instrucao.render(instrucao, True, (150, 150, 150))
            tela.blit(texto_inst, (largura_tela // 2 - texto_inst.get_width() // 2, y_instrucao))
            y_instrucao += 20

        if popup_aplicar.ativo:
            popup_aplicar.update(agora)
            popup_aplicar.draw(tela)

        ui_helpers.desenhar_cursor_personalizado(tela)
        pygame.display.flip()
        clock.tick(60)


def aplicar_volumes_audio(config):
    """Aplica as configuraÃ§Ãµes de volume a todos os sons e mÃºsicas"""
    volume_master = config.get("volume_master", 1.0)
    volume_musica = config.get("volume_musica", 0.5)

    # Aplicar volume da mÃºsica
    pygame.mixer.music.set_volume(volume_musica * volume_master)

    # Salvar configuraÃ§Ã£o
    with open("saves/config_audio.json", "w") as f:
        json.dump(config, f, indent=4)


def _dados_catalogo_temporal():
    return {
        "Inimigos": [
            {"nome": "Errante Temporal", "imagem": "Sprites/Inimig1.png", "funcionamento": "Persegue o jogador em linha direta, pressiona espaco e serve como base para o escalonamento das fases.", "historia": "Fragmentos de pessoas e criaturas presos no primeiro pulso da ruptura. Eles nao pensam em vencer, apenas em voltar para uma linha do tempo que ja nao existe."},
            {"nome": "Atirador", "imagem": "Sprites/inimigo_direita2-1.png", "funcionamento": "Mantem distancia e cria projeteis para quebrar rotas seguras. Fica mais perigoso quando o jogador para de se mover.", "historia": "Uma variante que aprendeu a usar a propria instabilidade como municao. Cada disparo e uma pequena tentativa de fixar Geovana no tempo."},
            {"nome": "Kamikaze", "imagem": "Sprites/inimigo_esquerda2-1.png", "funcionamento": "Avanca para explodir perto do jogador, causando dano e efeitos de controle quando alcanca alcance curto.", "historia": "Nasceu de ecos congelados da segunda fase. Sua forma e instavel demais para sobreviver, entao transforma o proprio colapso em arma."},
            {"nome": "Aglomerador", "imagem": "Sprites/Inimig2.png", "funcionamento": "Ao morrer, pode se partir em inimigos menores ou favorecer grupos densos. Exige controle de area.", "historia": "Varias linhas temporais falharam no mesmo ponto e se colaram em um unico corpo. Quando ele cai, as partes ainda tentam continuar."},
            {"nome": "Espreitador", "imagem": "Sprites/Inimig1.png", "funcionamento": "Mesmo corpo-base do Errante Temporal, mas com furtividade: oscila transparencia, pode ficar quase invisivel e usa arrancadas curtas para se aproximar.", "historia": "No livro, ele nao e outra especie: e o proprio errante aprendendo a falhar entre os frames da realidade. A ameaca vem do desaparecimento, nao de uma silhueta nova."},
            {"nome": "Cristalizador", "imagem": "Sprites/Inimig1.png", "funcionamento": "Mesmo corpo-base do Errante Temporal com efeito cristalizador. No jogo, funciona como suporte defensivo: reduz dano em inimigos proximos e vira alvo prioritario.", "historia": "A ruptura endurece o errante por dentro, cobrindo sua forma comum com uma logica de cristal. Ele nao persegue apenas para matar; persegue para fixar a batalha em favor da horda."},
            {"nome": "Projetador", "imagem": "Sprites/Inimig1.png", "funcionamento": "Mesmo corpo-base do Errante Temporal, mas ataca de longe. Ele para em distancia segura, projeta disparos e obriga reposicionamento constante.", "historia": "E um errante que aprendeu a estender o proprio colapso pelo espaco. No livro, sua diferenca nao esta no corpo, mas na capacidade de transformar distancia em pressao."},
            {"nome": "Elite", "imagem": "Sprites/Inimig1.png", "funcionamento": "Mesmo corpo-base do Errante Temporal, so que maior, com vida multiplicada e presenca mais punitiva. No jogo, pune dano baixo e falta de mobilidade.", "historia": "Quando um errante sobrevive tempo demais, ganha peso temporal. A Elite e o mesmo monstro comum, ampliado pela memoria das vezes em que quase venceu."},
            {"nome": "Curater", "imagem": "Sprites/Inimig1.png", "visual": "curater", "funcionamento": "Anomalia de cura liberada mais tarde na primeira fase. Mantem distancia e cura globalmente aliados feridos de outras especies. Ele nao cura a si mesmo nem outros Curaters, entao eliminar essa anomalia corta a sustentacao do grupo.", "historia": "Nasceu quando a areia cosmica aprendeu a preservar seus proprios erros. Tem o mesmo corpo-base do Errante Temporal, mas cogumelos e brotos verdes denunciam a mutacao de suporte que o prende ao campo de batalha."},
        ],
        "Chefes": [
            {"nome": "BOSS 1: Caranguejo do Nulo", "imagem": "Sprites/Boss1.png", "funcionamento": "A Entropia Temporal. No jogo, e o primeiro teste grande de leitura de ataques, teleporte, dano sustentado e controle de invocacoes. Suas janelas de perigo representam bolhas, impacto e pressao de lacaios corrompidos.", "historia": "Localizacao: Dimensao Roxa, castelo em ruinas e deserto roxo. Crustaceo biomecanico colossal fundido a rocha, com bracos desproporcionais, olhos roxos flamejantes e um relogio caotico de bronze no torax. A vitoria abre a fenda dimensional que arranca Geovana para o proximo mundo."},
            {"nome": "BOSS 2: Colosso Pinguim", "imagem": "Sprites/Boss2_1.png", "funcionamento": "O Guardiao do Gelo. No jogo, domina a arena com gelo, avisos de area, lancas/cristais e punicoes de mobilidade. A luta exige deslocamento constante e leitura rapida para evitar empalamento.", "historia": "Localizacao: Deserto Branco e Gelado. Criatura pinguim monstruosa e colossal, com olhos vermelhos cortando a neblina congelante. Sua criocinese transforma o campo em um teste de sobrevivencia pura logo apos a queda pela fenda dimensional."},
            {"nome": "BOSS 3: Pai-Rato", "imagem": "Sprites/Boss3_1.png", "funcionamento": "O Falso Profeta. No jogo, combina pressao de arena, invocacoes/ameacas menores e disparos canalizados, traduzindo as hordas cultistas e os feixes de luz corrompida do livro.", "historia": "Localizacao: Catedral do Ninho, reino dos ratos. Rato humanoide encurvado, inchado, em mantos vermelhos esfarrapados, sentado sobre trono de queijo derretido e velas de gordura. Um olho e um buraco negro queimado. Seu simbolo sagrado distorcido canaliza energia ate ser quebrado pela Ressonancia de Minkowski."},
            {"nome": "BOSS 4: O Capitao", "imagem": "Sprites/Boss4_1.png", "funcionamento": "O Vigia Milenar. No jogo, representa pressao pesada de arena, ataques diretos e sequencias que exigem build madura, defesa, dano continuo e bom reposicionamento.", "historia": "Localizacao: Salao do Trono, Cupula do Poder, quarta fase. Hibrido titanico de sapo e gorila, quatro metros, pele verde-oliva rugosa e armadura espacial preta com placas foscas e ouro. Manipula gravidade pesada, empunha lamina de energia antiga e comanda subordinados nas sombras."},
            {"nome": "BOSS 5: ?", "imagem": None, "funcionamento": "Arquivo bloqueado. O jogo reserva este encontro para punir padroes repetidos, leitura previsivel e abuso de poder acumulado.", "historia": "SUSPENSE. O catalogo registra apenas uma assinatura: UMBRA. O restante permanece oculto para preservar o impacto narrativo da quinta ruptura."},
        ],
        "Fases": [
            {"nome": "Fase 1 - Primeiro Rasgo", "imagem": "Sprites/Fase1.png", "funcionamento": "Apresenta o ciclo principal: mover, atirar, coletar moedas, escolher fragmentos dimensionais e sobreviver ao primeiro boss.", "historia": "O mundo ainda parece reconhecivel, mas a primeira ruptura ja contaminou seus habitantes e suas leis fisicas."},
            {"nome": "Fase 2 - Nevasca de Memorias", "imagem": "Sprites/Fase2.png", "funcionamento": "Introduz gelo, controle de area e inimigos com comportamento mais variado.", "historia": "As memorias rejeitadas congelam antes de desaparecer. A fase e um arquivo vivo de tentativas fracassadas."},
            {"nome": "Fase 3 - Geometria Instavel", "imagem": "Sprites/Fase3.png", "funcionamento": "Aumenta a densidade de projeteis, efeitos e decisoes de posicionamento.", "historia": "A ruptura deixa de ser acidente e vira padrao. Tudo tenta se organizar em formas hostis."},
            {"nome": "Fase 4 - Nucleo Temporal", "imagem": "Sprites/Fase4.png", "funcionamento": "Teste de build madura, escalonamento alto e sobrevivencia sob pressao constante.", "historia": "Aqui o tempo nao flui: ele pulsa. Cada passo empurra Geovana para mais perto do centro da anomalia."},
            {"nome": "Fase 5 - Confronto de Ecos", "imagem": "Sprites/Fase5-1.png", "funcionamento": "Fase de confronto avancado, com sistemas de IA e punicoes para repeticao de padroes.", "historia": "Quando a ruptura entende Geovana, ela cria uma resposta. A quinta fase e menos um lugar e mais um julgamento."},
        ],
        "Anatomia": [
            {"nome": "Disparo Temporal", "imagem": "Sprites/Geo_Disp1.png", "funcionamento": "Ataque primario da personagem. Dispara energia temporal em linha reta, escala com dano, velocidade de ataque, critico, veneno e efeitos dos fragmentos dimensionais.", "historia": "Geovana comprime instantes em projeteis. Cada tiro e uma pequena ordem dada a um futuro instavel."},
            {"nome": "Teleporte", "imagem": "Sprites/Deck/carta_teleporte1.png", "funcionamento": "Habilidade de reposicionamento. Pode operar em modo fixo, seguindo a direcao de movimento, ou em modo de mira pelo mouse conforme configuracao.", "historia": "Nao e velocidade. E uma costura curta entre dois pontos que deveriam estar distantes."},
            {"nome": "Onda de Choque", "imagem": "Sprites/Onda_Boss2.png", "funcionamento": "Segunda habilidade ativa da personagem. Libera uma explosao de area ao redor de Geovana para afastar grupos, abrir espaco e causar dano quando a arena fecha.", "historia": "Um pulso de recusa: por um momento, Geovana empurra a ruptura para fora da propria volta."},
        ],
        "Aureas": [
            {"nome": "Aurea Racional", "imagem": "Sprites/aurea_cientista.png", "funcionamento": "Controle de ritmo. Ficar imovel por 5s gera pontuacao bonus. Teleporte pronto ativa Dilatacao Temporal por 8s: inimigos/projeteis ficam 58% mais lentos, Geovana ganha +35% movimento e atira 28% mais rapido. Depois vem Rebote por 3s, acelerando inimigos/projeteis em 50%.", "historia": "A mente fria calcula trajetorias e enxerga padroes em meio ao caos da ruptura temporal."},
            {"nome": "Aurea Impulsiva", "imagem": "Sprites/aurea_impulsiva.png", "funcionamento": "Agressao continua. A cada 5 abates sem sofrer dano, ativa Frenesi temporario de dano e/ou velocidade. Manter a sequencia renova a pressao; nas fases com sistema completo, renovar com tempo sobrando aumenta o nivel e sofrer hit durante o Frenesi arma Panico.", "historia": "Acao imediata. O instinto reage antes que o proprio tempo possa processar."},
            {"nome": "Aurea Devota", "imagem": "Sprites/aurea_devota.png", "funcionamento": "Sobrevivencia ofensiva. Cria 3 cargas de escudo que anulam impactos. Cada bloqueio cura 10% da vida perdida e da +25% dano por 3s. Ao quebrar a ultima carga, ativa Fe Ardente: +65% dano por 4.5s, com apenas -10% velocidade. Upgrade reduz a recarga.", "historia": "A fe inabalavel manifesta uma barreira divina que desafia a propria causalidade."},
            {"nome": "Aurea Vanguarda", "imagem": "Sprites/aurea_vanguarda.png", "funcionamento": "Area e queimadura. Inimigos proximos ou tocados podem incendiar e sofrer dano por segundo baseado em vida maxima. Nas fases com sistema completo, sofrer hit abre um circulo de fogo por 5s. Cada inimigo queimando aumenta o cooldown do Teleporte em 15%.", "historia": "Liderando o avanco, a pioneira incendeia o solo para que nada a siga no fluxo temporal."},
            {"nome": "Aurea Insana", "imagem": "Sprites/aurea_insana.png", "funcionamento": "Ecos temporais. A cada ciclo liberado, Geovana ganha 4 ecos parados que repetem seus disparos com 1s de atraso e dano reduzido. Se um eco finalizar inimigo, a proxima ativacao ganha +1 eco, ate 5. Depois da aura, o Teleporte sofre +2s de recarga.", "historia": "A insanidade temporal quebra a linha do presente e deixa copias atrasadas atirando no mesmo instante."},
            {"nome": "Aurea Aleatoria", "imagem": "Sprites/aurea_misteriosa.png", "funcionamento": "Seleciona uma das cinco aureas ativas ao confirmar a jornada: Racional, Impulsiva, Devota, Vanguarda ou Insana. A utilidade muda conforme a sorte, exigindo adaptar movimentacao, agressividade, defesa, controle de area ou ecos temporais.", "historia": "O destino e incerto, e o tempo se desdobra em infinitas possibilidades."},
        ],
        "Fragmentos": [
            {"nome": "Speed Boost", "imagem": "Sprites/Deck/Speed_boost1.png", "funcionamento": "Fragmento dimensional que aumenta velocidade de movimento.", "historia": "Um fragmento para quem prefere vencer a ruptura antes que ela feche o cerco."},
            {"nome": "Porcao", "imagem": "Sprites/Deck/carta_por1.png", "funcionamento": "Fragmento vital que recupera vida e pode aumentar vida maxima.", "historia": "Elixir extraido de linhas temporais estaveis, raro o bastante para parecer milagre."},
            {"nome": "Disparo crescente", "imagem": "Sprites/Deck/carta_odio1.png", "funcionamento": "Fragmento ofensivo que aumenta o dano do disparo principal.", "historia": "Cada tiro carrega um pouco mais da raiva acumulada contra a fratura."},
            {"nome": "Tempestade", "imagem": "Sprites/Deck/Carta_tempestade_crescente1.png", "funcionamento": "Fragmento de instabilidade que aumenta chance critica e explosao de dano.", "historia": "Probabilidade violenta, dobrada ate virar clima."},
            {"nome": "Cura", "imagem": "Sprites/Deck/Carta_roubo_vida1.png", "funcionamento": "Fragmento de sifao que permite recuperar vida ao causar dano.", "historia": "A ruptura tira; este fragmento ensina Geovana a tomar de volta."},
            {"nome": "Reviver Temporal", "imagem": "Sprites/Deck/carta_trem1.png", "funcionamento": "Fragmento de retorno apos morte. Funciona como segunda chance limitada e deixa penalidades progressivas.", "historia": "Voltar no tempo nunca e gratis. Cada retorno deixa uma marca que a ruptura aprende a cobrar."},
            {"nome": "Speed Atack", "imagem": "Sprites/Deck/carta_onda.png", "funcionamento": "Fragmento de cadencia que reduz intervalo entre disparos.", "historia": "A cadencia fica tao alta que o tempo parece tropecar entre os tiros."},
            {"nome": "Teleporte", "imagem": "Sprites/Deck/carta_teleporte1.png", "funcionamento": "Fragmento que reduz cooldown do teleporte.", "historia": "Dobre o espaco, corte a perseguicao, sobreviva ao impossivel."},
            {"nome": "Petro", "imagem": "Sprites/Deck/carta_petro1.png", "funcionamento": "Fragmento-companheiro que ativa ou evolui Petro, a sentinela que ataca inimigos proximos.", "historia": "Um pacto simples: Geovana protege o caminho, Petro protege Geovana."},
            {"nome": "Defesa", "imagem": "Sprites/Deck/carta_defesa1.png", "funcionamento": "Fragmento de resistencia que reduz dano recebido.", "historia": "Uma camada de realidade endurecida ao redor do corpo."},
            {"nome": "Sorte", "imagem": "Sprites/Deck/carta_sorte1.png", "funcionamento": "Fragmento probabilistico que aumenta chance de raridade e melhora drops no modo sem loja.", "historia": "Nao muda o destino. Apenas inclina a moeda antes que ela caia."},
            {"nome": "Poison", "imagem": "Sprites/Deck/carta_poison1.png", "funcionamento": "Fragmento toxico que aplica veneno nos ataques e escala dano continuo.", "historia": "Uma toxina que envelhece o alvo por dentro."},
            {"nome": "Coletora", "imagem": "Sprites/Deck/carta_estalo1.png", "funcionamento": "Fragmento de execucao que elimina inimigos enfraquecidos.", "historia": "Quando a vida ja esta por um fio, a Coletora corta o resto."},
            {"nome": "Mercenaria", "imagem": "Sprites/Deck/carta_mercenaria1.png", "funcionamento": "Fragmento de recompensa que aumenta pontuacao por sequencias e abates constantes.", "historia": "Nao luta por honra. Luta por resultado."},
        ],
    }


def _catalogo_aplicar_visual_curater(img):
    base = pygame.Surface(img.get_size(), pygame.SRCALPHA)
    base.blit(img, (0, 0))
    base.fill((190, 255, 205, 255), special_flags=pygame.BLEND_RGBA_MULT)

    w, h = base.get_size()
    centro_x = w // 2
    base_y = h - 12
    for i in range(9):
        fase = i * 0.83
        px = centro_x + int(math.cos(fase) * w * 0.38)
        py = base_y + int(math.sin(i * 1.27) * h * 0.08)
        caule_h = int(h * (0.08 + (i % 3) * 0.025))
        cor_caule = (42, 150, 58, 235)
        cor_chapeu = (108, 238, 128, 245) if i % 2 else (74, 204, 92, 245)
        pygame.draw.line(base, cor_caule, (px, py), (px, py - caule_h), max(2, w // 45))
        pygame.draw.ellipse(base, cor_chapeu, (px - w // 22, py - caule_h - h // 30, w // 13, h // 23))
        pygame.draw.ellipse(base, (210, 255, 216, 230), (px - w // 70, py - caule_h - h // 42, w // 42, h // 55))

    for i in range(5):
        ang = i * (math.pi * 2 / 5) + 0.35
        x1 = centro_x + int(math.cos(ang) * w * 0.18)
        y1 = int(h * 0.52) + int(math.sin(ang) * h * 0.12)
        x2 = centro_x + int(math.cos(ang) * w * 0.32)
        y2 = int(h * 0.52) + int(math.sin(ang) * h * 0.20)
        pygame.draw.line(base, (88, 255, 120, 135), (x1, y1), (x2, y2), max(1, w // 70))
        pygame.draw.circle(base, (170, 255, 190, 170), (x2, y2), max(2, w // 38))

    pygame.draw.circle(base, (80, 230, 105, 120), (centro_x, int(h * 0.55)), int(min(w, h) * 0.43), max(1, w // 70))
    return base


def _catalogo_carregar_imagem(caminho, limite=(190, 190), visual=None):
    if not caminho or not os.path.exists(caminho):
        return None
    try:
        img = pygame.image.load(caminho).convert_alpha()
        w, h = img.get_size()
        escala = min(limite[0] / max(1, w), limite[1] / max(1, h))
        novo_tamanho = (max(1, int(w * escala)), max(1, int(h * escala)))
        img = pygame.transform.smoothscale(img, novo_tamanho)
        if visual == "curater":
            img = _catalogo_aplicar_visual_curater(img)
        return img
    except Exception as e:
        registrar_erro(f"Erro ao carregar imagem do catalogo: {caminho}", e)
        return None


def _catalogo_texto_elipsado(texto, fonte_local, largura_maxima):
    texto = str(texto)
    if fonte_local.size(texto)[0] <= largura_maxima:
        return texto
    sufixo = "..."
    texto_base = texto
    while texto_base and fonte_local.size(texto_base + sufixo)[0] > largura_maxima:
        texto_base = texto_base[:-1]
    return (texto_base.rstrip() + sufixo) if texto_base else sufixo


def _catalogo_texto_wrap(superficie, texto, fonte_local, cor, rect, espacamento=4):
    palavras = texto.split()
    linhas = []
    linha = ""
    for palavra in palavras:
        tentativa = palavra if not linha else f"{linha} {palavra}"
        if fonte_local.size(tentativa)[0] <= rect.width:
            linha = tentativa
        else:
            if linha:
                linhas.append(linha)
            linha = palavra
    if linha:
        linhas.append(linha)

    y = rect.top
    altura_linha = fonte_local.get_height() + espacamento
    for linha in linhas:
        if y + altura_linha > rect.bottom:
            break
        render = fonte_local.render(linha, True, cor)
        superficie.blit(render, (rect.left, y))
        y += altura_linha
    return y


def tela_catalogo_temporal():
    pygame.event.set_grab(False)
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()
    dados = _dados_catalogo_temporal()
    categorias = list(dados.keys())
    categoria_idx = 0
    item_idx = 0
    scroll_lista = 0
    imagens_cache = {}

    fonte_titulo_local = pygame.font.Font(caminho_fonte_titulo, 44)
    fonte_cat = pygame.font.Font(caminho_fonte_letra1, 22)
    fonte_item = pygame.font.Font(caminho_fonte_letra1, 20)
    fonte_nome = pygame.font.Font(caminho_fonte_letra1, 32)
    fonte_texto = pygame.font.Font(caminho_fonte_letra1, 21)
    fonte_pequena = pygame.font.Font(caminho_fonte_letra1, 18)

    def obter_imagem(item):
        caminho = item.get("imagem")
        chave_cache = (caminho, item.get("visual"))
        if chave_cache not in imagens_cache:
            imagens_cache[chave_cache] = _catalogo_carregar_imagem(caminho, visual=item.get("visual"))
        return imagens_cache[chave_cache]

    rodando_catalogo = True
    modo_interacao = "teclado"
    while rodando_catalogo:
        mx, my = ui_helpers.obter_pos_mouse_superficie(tela)
        itens = dados[categorias[categoria_idx]]
        item_idx = max(0, min(item_idx, len(itens) - 1))

        tab_rects = []
        tab_w = 148
        tab_h = 38
        tab_gap = 10
        tab_total_w = len(categorias) * tab_w + (len(categorias) - 1) * tab_gap
        tab_x0 = max(30, (largura_tela - tab_total_w) // 2)
        tab_y = 106
        for i, cat in enumerate(categorias):
            tab_rects.append((i, pygame.Rect(tab_x0 + i * (tab_w + tab_gap), tab_y, tab_w, tab_h)))

        lista_rect = pygame.Rect(60, 170, 330, altura_tela - 255)
        detalhe_rect = pygame.Rect(430, 170, largura_tela - 490, altura_tela - 255)
        btn_voltar = pygame.Rect(60, altura_tela - 60, 140, 36)
        item_h = 46
        visiveis = max(1, lista_rect.height // item_h)
        scroll_lista = max(0, min(scroll_lista, max(0, len(itens) - visiveis)))
        if item_idx < scroll_lista:
            scroll_lista = item_idx
        elif item_idx >= scroll_lista + visiveis:
            scroll_lista = item_idx - visiveis + 1

        item_rects = []
        for slot, idx_real in enumerate(range(scroll_lista, min(len(itens), scroll_lista + visiveis))):
            item_rects.append((idx_real, pygame.Rect(lista_rect.left + 8, lista_rect.top + 8 + slot * item_h, lista_rect.width - 16, item_h - 8)))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEMOTION:
                if event.rel != (0, 0):
                    modo_interacao = "mouse"
            elif event.type == pygame.KEYDOWN:
                modo_interacao = "teclado"
                if event.key == pygame.K_ESCAPE:
                    rodando_catalogo = False
                elif event.key in [pygame.K_a, pygame.K_LEFT]:
                    categoria_idx = (categoria_idx - 1) % len(categorias)
                    item_idx = 0
                    scroll_lista = 0
                    tocar_hover()
                elif event.key in [pygame.K_d, pygame.K_RIGHT]:
                    categoria_idx = (categoria_idx + 1) % len(categorias)
                    item_idx = 0
                    scroll_lista = 0
                    tocar_hover()
                elif event.key in [pygame.K_w, pygame.K_UP]:
                    item_idx = (item_idx - 1) % len(itens)
                    tocar_hover()
                elif event.key in [pygame.K_s, pygame.K_DOWN]:
                    item_idx = (item_idx + 1) % len(itens)
                    tocar_hover()
            elif event.type == pygame.MOUSEWHEEL:
                if lista_rect.collidepoint(mx, my):
                    scroll_lista -= event.y
                    scroll_lista = max(0, min(scroll_lista, max(0, len(itens) - visiveis)))
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                modo_interacao = "mouse"
                pos_clique = ui_helpers.converter_pos_mouse_jogo(event.pos)
                if btn_voltar.collidepoint(pos_clique):
                    tocar_selecionar()
                    rodando_catalogo = False
                for i, rect_tab in tab_rects:
                    if rect_tab.collidepoint(pos_clique):
                        categoria_idx = i
                        item_idx = 0
                        scroll_lista = 0
                        tocar_selecionar()
                        break
                for idx_real, rect_item in item_rects:
                    if rect_item.collidepoint(pos_clique):
                        item_idx = idx_real
                        tocar_selecionar()
                        break

        if modo_interacao == "mouse":
            for idx_real, rect_item in item_rects:
                if rect_item.collidepoint(mx, my) and item_idx != idx_real:
                    item_idx = idx_real
                    tocar_hover()
                    break

        tela.blit(fundo_menu1, (0, 0))
        overlay = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 205))
        tela.blit(overlay, (0, 0))

        titulo = render_glitch_text_with_fallback("CATALOGO TEMPORAL", fonte_titulo_local, fonte_letra1, (0, 255, 204))
        titulo_rect = titulo.get_rect(center=(largura_tela // 2, 58))
        tela.blit(titulo, titulo_rect)

        for i, rect_tab in tab_rects:
            ativo = i == categoria_idx
            hover = modo_interacao == "mouse" and rect_tab.collidepoint(mx, my)
            cor_bg = (0, 150, 170, 115) if ativo else (18, 18, 28, 185)
            cor_borda = (0, 255, 230) if ativo or hover else (90, 90, 120)
            pygame.draw.rect(tela, cor_bg, rect_tab, border_radius=8)
            pygame.draw.rect(tela, cor_borda, rect_tab, width=2 if ativo or hover else 1, border_radius=8)
            txt = fonte_cat.render(categorias[i].upper(), True, (255, 255, 255) if ativo else (190, 200, 215))
            tela.blit(txt, (rect_tab.centerx - txt.get_width() // 2, rect_tab.centery - txt.get_height() // 2))

        pygame.draw.rect(tela, (10, 10, 18, 210), lista_rect, border_radius=10)
        pygame.draw.rect(tela, (0, 255, 230, 120), lista_rect, width=1, border_radius=10)

        for idx_real, rect_item in item_rects:
            ativo = idx_real == item_idx
            hover = modo_interacao == "mouse" and rect_item.collidepoint(mx, my)
            pygame.draw.rect(tela, (0, 180, 200, 95) if ativo else (24, 24, 36, 170), rect_item, border_radius=6)
            pygame.draw.rect(tela, (0, 255, 230) if ativo or hover else (70, 70, 90), rect_item, width=1, border_radius=6)
            txt = fonte_item.render(itens[idx_real]["nome"], True, (255, 255, 255) if ativo else (195, 200, 215))
            tela.blit(txt, (rect_item.left + 12, rect_item.centery - txt.get_height() // 2))

        if len(itens) > visiveis:
            barra_h = max(28, int(lista_rect.height * (visiveis / len(itens))))
            barra_y = lista_rect.top + int((lista_rect.height - barra_h) * (scroll_lista / max(1, len(itens) - visiveis)))
            pygame.draw.rect(tela, (0, 255, 230, 160), (lista_rect.right - 7, barra_y, 4, barra_h), border_radius=3)

        item = itens[item_idx]
        pygame.draw.rect(tela, (12, 12, 20, 220), detalhe_rect, border_radius=12)
        pygame.draw.rect(tela, (0, 255, 230, 130), detalhe_rect, width=1, border_radius=12)

        img = obter_imagem(item)
        img_area = pygame.Rect(detalhe_rect.right - 230, detalhe_rect.top + 32, 190, 190)
        pygame.draw.rect(tela, (20, 20, 30, 180), img_area, border_radius=10)
        pygame.draw.rect(tela, (90, 90, 130), img_area, width=1, border_radius=10)
        if img:
            tela.blit(img, (img_area.centerx - img.get_width() // 2, img_area.centery - img.get_height() // 2))
        else:
            sem_img = fonte_pequena.render("SEM IMAGEM", True, (140, 140, 160))
            tela.blit(sem_img, (img_area.centerx - sem_img.get_width() // 2, img_area.centery - sem_img.get_height() // 2))

        x_texto = detalhe_rect.left + 28
        largura_lateral = max(260, img_area.left - x_texto - 22)
        nome_seguro = _catalogo_texto_elipsado(item["nome"], fonte_nome, largura_lateral)
        nome = fonte_nome.render(nome_seguro, True, (0, 255, 204))
        tela.blit(nome, (x_texto, detalhe_rect.top + 24))

        y_texto = detalhe_rect.top + 82
        lbl_func = fonte_cat.render("FUNCIONAMENTO", True, (255, 255, 255))
        tela.blit(lbl_func, (x_texto, y_texto))
        y_texto += 32
        y_texto = _catalogo_texto_wrap(tela, item["funcionamento"], fonte_texto, (210, 220, 230), pygame.Rect(x_texto, y_texto, largura_lateral, 150))

        y_texto = max(y_texto + 22, img_area.bottom + 18)
        lbl_hist = fonte_cat.render("HISTORIA E CONTEXTO", True, (255, 255, 255))
        tela.blit(lbl_hist, (x_texto, y_texto))
        y_texto += 32
        _catalogo_texto_wrap(tela, item["historia"], fonte_texto, (190, 195, 210), pygame.Rect(x_texto, y_texto, detalhe_rect.width - 56, detalhe_rect.bottom - y_texto - 26))

        hover_voltar = modo_interacao == "mouse" and btn_voltar.collidepoint(mx, my)
        pygame.draw.rect(tela, (18, 18, 28), btn_voltar, border_radius=8)
        pygame.draw.rect(tela, (0, 255, 230) if hover_voltar else (90, 90, 120), btn_voltar, width=2 if hover_voltar else 1, border_radius=8)
        txt_voltar = fonte_item.render("VOLTAR", True, (255, 255, 255))
        tela.blit(txt_voltar, (btn_voltar.centerx - txt_voltar.get_width() // 2, btn_voltar.centery - txt_voltar.get_height() // 2))

        instr = fonte_pequena.render("Mouse: abas e itens | A/D troca categoria | W/S navega | ESC volta", True, (140, 150, 165))
        tela.blit(instr, (largura_tela - instr.get_width() - 30, altura_tela - 48))

        ui_helpers.desenhar_cursor_personalizado(tela)
        pygame.display.flip()
        clock.tick(60)


def executar_menu_principal(game_manager=None):
    """
    Executa o menu principal do jogo

    Args:
        game_manager: InstÃ¢ncia do GameManager para controlar transiÃ§Ãµes de estado

    Returns:
        str: PrÃ³ximo estado ('jogo', 'sair', etc.) ou None se usar game_manager
    """
    inicializar_menu()
    global tela, indice_selecionado, ultima_mudanca_de_opcao, analogo_movido
    global indice_fundo, exibindo_fundo1, ultima_troca

    # Reinicia mÃºsica se nÃ£o estiver tocando
    if not pygame.mixer.music.get_busy():
        pygame.mixer.music.load("Sounds/Menu.mp3")
        config_audio = carregar_config_audio()
        aplicar_volume_musica(config_audio)
        pygame.mixer.music.play(-1)

    clock = pygame.time.Clock()
    rodando = True

    opcao_confirmada = None
    tempo_confirmacao = 0
    particulas_eclosao = []
    modo_interacao = "teclado"

    while rodando:
        agora = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if game_manager:
                    from game_manager import EstadoJogo
                    game_manager.mudar_estado(EstadoJogo.SAIR)
                    return
                else:
                    pygame.mixer.music.stop()
                    pygame.quit()
                    sys.exit()
            elif event.type == pygame.MOUSEMOTION:
                if event.rel != (0, 0):
                    modo_interacao = "mouse"

            if opcao_confirmada is None:
                if event.type == pygame.KEYDOWN:
                    modo_interacao = "teclado"
                    if event.key in [pygame.K_w, pygame.K_UP] and agora - ultima_mudanca_de_opcao >= DELAY_ENTRE_OPCOES:
                        indice_selecionado = (indice_selecionado - 1) % len(opcoes)
                        ultima_mudanca_de_opcao = agora
                        tocar_hover()
                    elif event.key in [pygame.K_s, pygame.K_DOWN] and agora - ultima_mudanca_de_opcao >= DELAY_ENTRE_OPCOES:
                        indice_selecionado = (indice_selecionado + 1) % len(opcoes)
                        ultima_mudanca_de_opcao = agora
                        tocar_hover()
                    elif event.key in [pygame.K_SPACE, pygame.K_RETURN]:
                        opcao_confirmada = indice_selecionado
                        tempo_confirmacao = agora
                        tocar_selecionar()

                        particulas_eclosao = []
                        x_centro = 60 + 320 // 2
                        y_centro = (altura_tela // 2 - 20 + opcao_confirmada * 70) + 50 // 2
                        import random
                        for _ in range(40):
                            particulas_eclosao.append({
                                'x': x_centro + random.uniform(-160, 160),
                                'y': y_centro + random.uniform(-25, 25),
                                'dx': random.uniform(-8, 8),
                                'dy': random.uniform(-8, 8),
                                'cor': random.choice([(0, 255, 230), (255, 0, 128), (255, 255, 255)]),
                                'raio': random.uniform(2, 6),
                                'vida': 1.0
                            })
                    elif event.key == pygame.K_ESCAPE:
                        opcao_confirmada = len(opcoes) - 1
                        tempo_confirmacao = agora
                        tocar_selecionar()

                        particulas_eclosao = []
                        x_centro = 60 + 320 // 2
                        y_centro = (altura_tela // 2 - 20 + opcao_confirmada * 70) + 50 // 2
                        import random
                        for _ in range(40):
                            particulas_eclosao.append({
                                'x': x_centro + random.uniform(-160, 160),
                                'y': y_centro + random.uniform(-25, 25),
                                'dx': random.uniform(-8, 8),
                                'dy': random.uniform(-8, 8),
                                'cor': random.choice([(0, 255, 230), (255, 0, 128), (255, 255, 255)]),
                                'raio': random.uniform(2, 6),
                                'vida': 1.0
                            })
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    modo_interacao = "mouse"
                    pos_clique = ui_helpers.converter_pos_mouse_jogo(event.pos)
                    for i, opcao in enumerate(opcoes):
                        x_botao = 60
                        y_botao = altura_tela // 2 - 20 + i * 70
                        rect_botao = pygame.Rect(x_botao, y_botao, 320, 50)
                        if rect_botao.collidepoint(pos_clique):
                            opcao_confirmada = i
                            tempo_confirmacao = agora
                            tocar_selecionar()

                            particulas_eclosao = []
                            x_centro = 60 + 320 // 2
                            y_centro = y_botao + 50 // 2
                            import random
                            for _ in range(40):
                                particulas_eclosao.append({
                                    'x': x_centro + random.uniform(-160, 160),
                                    'y': y_centro + random.uniform(-25, 25),
                                    'dx': random.uniform(-8, 8),
                                    'dy': random.uniform(-8, 8),
                                    'cor': random.choice([(0, 255, 230), (255, 0, 128), (255, 255, 255)]),
                                    'raio': random.uniform(2, 6),
                                    'vida': 1.0
                                })

                elif event.type == pygame.JOYAXISMOTION and controle is not None:
                    modo_interacao = "teclado"
                    if event.axis == 1 and abs(controle.get_axis(0)) < 0.2:
                        if not analogo_movido:
                            if event.value > 0.5:
                                indice_selecionado = (indice_selecionado + 1) % len(opcoes)
                                analogo_movido = True
                                tocar_hover()
                            elif event.value < -0.5:
                                indice_selecionado = (indice_selecionado - 1) % len(opcoes)
                                analogo_movido = True
                                tocar_hover()
                    elif event.axis == 1 and abs(event.value) < 0.5:
                        analogo_movido = False

                elif event.type == pygame.JOYBUTTONDOWN and controle is not None:
                    modo_interacao = "teclado"
                    if event.button == 0:  # BotÃ£o A
                        opcao_confirmada = indice_selecionado
                        tempo_confirmacao = agora
                        tocar_selecionar()

                        particulas_eclosao = []
                        x_centro = 60 + 320 // 2
                        y_centro = (altura_tela // 2 - 20 + opcao_confirmada * 70) + 50 // 2
                        import random
                        for _ in range(40):
                            particulas_eclosao.append({
                                'x': x_centro + random.uniform(-160, 160),
                                'y': y_centro + random.uniform(-25, 25),
                                'dx': random.uniform(-8, 8),
                                'dy': random.uniform(-8, 8),
                                'cor': random.choice([(0, 255, 230), (255, 0, 128), (255, 255, 255)]),
                                'raio': random.uniform(2, 6),
                                'vida': 1.0
                            })

        # DetecÃ§Ã£o de hover pelo mouse
        mx, my = ui_helpers.obter_pos_mouse_superficie(tela)
        for i, opcao in enumerate(opcoes):
            x_botao = 60
            y_botao = altura_tela // 2 - 20 + i * 70
            rect_botao = pygame.Rect(x_botao, y_botao, 320, 50)
            if modo_interacao == "mouse" and rect_botao.collidepoint(mx, my) and opcao_confirmada is None:
                if indice_selecionado != i:
                    indice_selecionado = i
                    tocar_hover()

        # LÃ³gica de troca de imagem de fundo
        agora = pygame.time.get_ticks()

        if exibindo_fundo1:
            tela.blit(fundo_menu1, (0, 0))
            if agora - ultima_troca > tempo_exibicao_fundo1:
                exibindo_fundo1 = False
                ultima_troca = agora
                indice_fundo = 0
        else:
            tela.blit(imagens_fundo[indice_fundo], (0, 0))
            if agora - ultima_troca > tempo_troca_fundo:
                indice_fundo += 1
                ultima_troca = agora

                if indice_fundo >= len(imagens_fundo):
                    exibindo_fundo1 = True
                    indice_fundo = 0

        # Renderizar opÃ§Ãµes do menu (AAA Premium Sci-Fi)
        for i, opcao in enumerate(opcoes):
            x_botao = 60
            y_botao = altura_tela // 2 - 20 + i * 70
            largura_b = 320
            altura_b = 50

            surf_botao = pygame.Surface((largura_b, altura_b), pygame.SRCALPHA)

            if opcao_confirmada == i:
                decorrido = agora - tempo_confirmacao
                progresso = min(1.0, max(0.0, decorrido / 200.0))
                fator_escala = 1.0 + progresso * 0.4
                nova_largura = int(largura_b * fator_escala)
                nova_altura = int(altura_b * fator_escala)

                surf_eclosao = pygame.Surface((nova_largura, nova_altura), pygame.SRCALPHA)
                alpha_borda = int((1.0 - progresso) * 255)
                pygame.draw.rect(surf_eclosao, (0, 255, 230, alpha_borda), (0, 0, nova_largura, nova_altura), width=3, border_radius=10)

                x_ecl = x_botao - (nova_largura - largura_b) // 2
                y_ecl = y_botao - (nova_altura - altura_b) // 2
                tela.blit(surf_eclosao, (x_ecl, y_ecl))

                # BotÃ£o principal brilha em branco
                pygame.draw.rect(surf_botao, (255, 255, 255, 200), (0, 0, largura_b, altura_b), border_radius=8)
                texto_surf = fonte_letra1.render(opcao, True, (0, 0, 0))
                ret_texto = texto_surf.get_rect(center=(largura_b // 2 + 10, altura_b // 2))
                surf_botao.blit(texto_surf, ret_texto)

            elif i == indice_selecionado:
                import random
                is_glitch_frame = random.random() < 0.15 and opcao_confirmada is None
                glitch_offset_x = random.randint(-3, 3) if is_glitch_frame else 0
                glitch_offset_y = random.randint(-1, 1) if is_glitch_frame else 0

                alpha_bg = random.randint(45, 95) if is_glitch_frame else 65
                pygame.draw.rect(surf_botao, (0, 180, 200, alpha_bg), (0, 0, largura_b, altura_b), border_radius=8)
                pygame.draw.rect(surf_botao, (0, 255, 230), (0, 0, largura_b, altura_b), width=2, border_radius=8)
                pygame.draw.rect(surf_botao, (0, 255, 230), (0, 0, 6, altura_b), border_radius=8)

                if is_glitch_frame:
                    texto_ciano = fonte_letra1.render(opcao, True, (0, 255, 255))
                    texto_rosa = fonte_letra1.render(opcao, True, (255, 0, 128))

                    ret_ciano = texto_ciano.get_rect(center=(largura_b // 2 + 10 + glitch_offset_x, altura_b // 2 + glitch_offset_y))
                    ret_rosa = texto_rosa.get_rect(center=(largura_b // 2 + 10 - glitch_offset_x, altura_b // 2 - glitch_offset_y))

                    surf_botao.blit(texto_ciano, ret_ciano)
                    surf_botao.blit(texto_rosa, ret_rosa)

                    if random.random() < 0.5:
                        y_linha = random.randint(5, altura_b - 5)
                        pygame.draw.line(surf_botao, (255, 255, 255), (5, y_linha), (largura_b - 5, y_linha), 1)
                else:
                    texto_surf = fonte_letra1.render(opcao, True, (255, 255, 255))
                    ret_texto = texto_surf.get_rect(center=(largura_b // 2 + 10, altura_b // 2))
                    surf_botao.blit(texto_surf, ret_texto)
            else:
                pygame.draw.rect(surf_botao, (15, 15, 25, 160), (0, 0, largura_b, altura_b), border_radius=8)
                pygame.draw.rect(surf_botao, (100, 100, 150, 45), (0, 0, largura_b, altura_b), width=1, border_radius=8)

                texto_surf = fonte_letras.render(opcao, True, (200, 200, 220))
                ret_texto = texto_surf.get_rect(center=(largura_b // 2, altura_b // 2))
                surf_botao.blit(texto_surf, ret_texto)

            tela.blit(surf_botao, (x_botao, y_botao))

        # Texto de instruÃ§Ã£o
        texto_instrucao = "Use W ou S para alternar e EspaÃ§o ou Enter para selecionar"



        # RenderizaÃ§Ã£o do tÃ­tulo
        texto_titulo = fonte_titulo.render(titulo_jogo, True, cor_letra)
        retangulo_titulo = texto_titulo.get_rect(center=posicao_titulo)



        # Sombra e Contorno do TÃ­tulo (AAA volumetric effect)
        texto_titulo_sombra = fonte_titulo.render(titulo_jogo, True, (15, 5, 25))
        tela.blit(texto_titulo_sombra, (retangulo_titulo.left + 4, retangulo_titulo.top + 4))

        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            texto_titulo_contorno = fonte_titulo.render(titulo_jogo, True, contorno_rosa)
            tela.blit(texto_titulo_contorno, (retangulo_titulo.left + dx, retangulo_titulo.top + dy))

        tela.blit(texto_titulo, retangulo_titulo)


        # Barra glassy de instruÃ§Ã£o no rodapÃ©
        render_instrucao_aaa = fonte_instrucao.render(texto_instrucao, True, (0, 255, 230))
        largura_instr = render_instrucao_aaa.get_width() + 40
        altura_instr = 40

        surf_instr = pygame.Surface((largura_instr, altura_instr), pygame.SRCALPHA)
        pygame.draw.rect(surf_instr, (10, 10, 15, 200), (0, 0, largura_instr, altura_instr), border_radius=8)
        pygame.draw.rect(surf_instr, (0, 240, 255, 80), (0, 0, largura_instr, altura_instr), width=1, border_radius=8)

        surf_instr.blit(render_instrucao_aaa, (20, (altura_instr - render_instrucao_aaa.get_height()) // 2))
        tela.blit(surf_instr, (largura_tela - largura_instr - 20, altura_tela - altura_instr - 20))

        # Desenhar e atualizar partÃ­culas de eclosÃ£o
        if particulas_eclosao:
            for part in particulas_eclosao[:]:
                part['x'] += part['dx']
                part['y'] += part['dy']
                part['dx'] *= 0.96
                part['dy'] *= 0.96
                part['vida'] -= 0.05
                if part['vida'] <= 0:
                    particulas_eclosao.remove(part)
                    continue

                raio_atual = int(part['raio'] * part['vida'])
                if raio_atual > 0:
                    alpha_part = max(0, min(255, int(part['vida'] * 255)))
                    cor_alpha = part['cor'] + (alpha_part,)
                    surf_part = pygame.Surface((raio_atual * 2, raio_atual * 2), pygame.SRCALPHA)
                    pygame.draw.circle(surf_part, cor_alpha, (raio_atual, raio_atual), raio_atual)
                    tela.blit(surf_part, (int(part['x'] - raio_atual), int(part['y'] - raio_atual)))

        ui_helpers.desenhar_cursor_personalizado(tela)
        pygame.display.flip()
        clock.tick(60)

        # LÃ³gica de confirmaÃ§Ã£o apÃ³s 200ms de eclosÃ£o (TransiÃ§Ãµes de Tela)
        if opcao_confirmada is not None and agora - tempo_confirmacao >= 200:
            escolha = opcao_confirmada
            opcao_confirmada = None
            particulas_eclosao = []

            if escolha == 0:  # Iniciar Jornada
                if not os.path.exists("saves/nome_jogador.json"):
                    try:
                        os.makedirs("saves", exist_ok=True)
                        with open("saves/nome_jogador.json", "w") as f:
                            json.dump({"nome": "Geovana"}, f)
                    except:
                        pass
                if not os.path.exists("saves/tutorial_config.json"):
                    mostrar_tutorial = tela_decisao_tutorial(tela, fonte)
                    with open("saves/tutorial_config.json", "w") as f:
                        json.dump({"mostrar_tutorial": mostrar_tutorial}, f)
                else:
                    with open("saves/tutorial_config.json", "r") as f:
                        mostrar_tutorial = json.load(f)["mostrar_tutorial"]

                estado_jornada = "modo"
                retornar_ao_menu = False
                modo, ip = None, None
                modo_cartas = "loja"

                while True:
                    if estado_jornada == "modo":
                        modo, ip = tela_escolha_modo()
                        if modo is None:
                            retornar_ao_menu = True
                            break
                        else:
                            if modo == "offline":
                                estado_jornada = "dificuldade"
                            else:
                                modo_cartas = "loja"
                                estado_jornada = "aurea"
                    elif estado_jornada == "dificuldade":
                        modo_escolhido = tela_escolha_dificuldade(tela, fonte, mostrar_tutorial)
                        if modo_escolhido is None:
                            estado_jornada = "modo"
                        else:
                            modo_cartas = modo_escolhido
                            estado_jornada = "aurea"
                    elif estado_jornada == "aurea":
                        res_aurea = tela_selecao_aurea(tela, fonte)
                        if res_aurea == "voltar":
                            estado_jornada = "dificuldade" if modo == "offline" else "modo"
                        else:
                            estado_jornada = "manifestacao"
                    elif estado_jornada == "manifestacao":
                        res_manifestacao = tela_manifestacoes(tela, fonte)
                        if res_manifestacao == "voltar":
                            estado_jornada = "aurea"
                        else:
                            break

                if retornar_ao_menu:
                    continue

                pygame.mixer.music.stop()

                # ComeÃ§ar partida limpa ao iniciar a partir do menu
                import Variaveis
                Variaveis.limpar_historico_rewind()
                if os.path.exists("saves/atributos.json"):
                    try:
                        os.remove("saves/atributos.json")
                    except Exception as e:
                        registrar_erro("Erro ao remover atributos antigos ao iniciar jornada", e)

                with open("saves/modo_jogo.json", "w") as f:
                    json.dump({"modo": modo, "ip": ip}, f)
                with open("saves/config_cartas.json", "w") as f:
                    json.dump({"modo_cartas": modo_cartas}, f)

                if game_manager:
                    from game_manager import EstadoJogo
                    game_manager.mudar_estado(
                        EstadoJogo.JOGO_PRINCIPAL,
                        dados={'modo_jogo': modo, 'ip': ip, 'fase': 1}
                    )
                    return
                else:
                    if modo == 'offline':
                        import GAME
                        GAME.main()
                    else:
                        import GAMERE
                        GAMERE.main()
                    return

            elif escolha == 1:  # Catalogo
                tela_catalogo_temporal()
                continue

            elif escolha == 2:  # ConfiguraÃ§Ã£o
                indice_config = 0

                opcao_conf_confirmada = None
                tempo_conf_confirmacao = 0
                particulas_conf_eclosao = []

                config_rodando = True
                while config_rodando:
                    agora_conf = pygame.time.get_ticks()

                    opcoes_config = ["Controles", "Graficos", "Audio", "Jogabilidade", "Voltar"]

                    # Atualiza e desenha o fundo dinÃ¢mico do menu
                    if exibindo_fundo1:
                        tela.blit(fundo_menu1, (0, 0))
                        if agora_conf - ultima_troca > tempo_exibicao_fundo1:
                            exibindo_fundo1 = False
                            ultima_troca = agora_conf
                            indice_fundo = 0
                    else:
                        tela.blit(imagens_fundo[indice_fundo], (0, 0))
                        if agora_conf - ultima_troca > tempo_troca_fundo:
                            indice_fundo = (indice_fundo + 1) % len(imagens_fundo)
                            ultima_troca = agora_conf

                    # Camada preta semi-transparente (glassmorphism/dimming overlay) para contraste
                    overlay = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
                    overlay.fill((0, 0, 0, 185))
                    tela.blit(overlay, (0, 0))

                    texto_config = render_glitch_text_with_fallback("CONFIGURACOES", fonte_config, fonte_fallback_config, (0, 255, 204))
                    retangulo_config = texto_config.get_rect(center=(largura_tela // 2, altura_tela // 6))

                    # Sombra
                    texto_config_sombra = render_glitch_text_with_fallback("CONFIGURACOES", fonte_config, fonte_fallback_config, (15, 5, 25))
                    tela.blit(texto_config_sombra, (retangulo_config.left + 4, retangulo_config.top + 4))

                    # Contorno
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        texto_config_contorno = render_glitch_text_with_fallback("CONFIGURACOES", fonte_config, fonte_fallback_config, contorno_rosa)
                        tela.blit(texto_config_contorno, (retangulo_config.left + dx, retangulo_config.top + dy))

                    tela.blit(texto_config, retangulo_config)

                    for event_config in pygame.event.get():
                        if event_config.type == pygame.QUIT:
                            if game_manager:
                                from game_manager import EstadoJogo
                                game_manager.mudar_estado(EstadoJogo.SAIR)
                                return
                            else:
                                pygame.quit()
                                sys.exit()
                        elif event_config.type == pygame.MOUSEMOTION:
                            if event_config.rel != (0, 0):
                                modo_interacao = "mouse"

                        if opcao_conf_confirmada is None:
                            if event_config.type == pygame.KEYDOWN:
                                modo_interacao = "teclado"
                                if event_config.key in [pygame.K_w, pygame.K_UP]:
                                    indice_config = (indice_config - 1) % len(opcoes_config)
                                elif event_config.key in [pygame.K_s, pygame.K_DOWN]:
                                    indice_config = (indice_config + 1) % len(opcoes_config)
                                elif event_config.key in [pygame.K_SPACE, pygame.K_RETURN]:
                                    opcao_conf_confirmada = indice_config
                                    tempo_conf_confirmacao = agora_conf

                                    particulas_conf_eclosao = []
                                    x_centro = largura_tela // 2
                                    y_centro = int(altura_tela // 4.5 + opcao_conf_confirmada * 65) + 50 // 2
                                    import random
                                    for _ in range(40):
                                        particulas_conf_eclosao.append({
                                            'x': x_centro + random.uniform(-160, 160),
                                            'y': y_centro + random.uniform(-25, 25),
                                            'dx': random.uniform(-8, 8),
                                            'dy': random.uniform(-8, 8),
                                            'cor': random.choice([(0, 255, 230), (255, 0, 128), (255, 255, 255)]),
                                            'raio': random.uniform(2, 6),
                                            'vida': 1.0
                                        })
                                elif event_config.key == pygame.K_ESCAPE:
                                    config_rodando = False
                                    break
                            elif event_config.type == pygame.MOUSEBUTTONDOWN and event_config.button == 1:
                                modo_interacao = "mouse"
                                pos_clique = ui_helpers.converter_pos_mouse_jogo(event_config.pos)
                                for i, opcao in enumerate(opcoes_config):
                                    x_botao = largura_tela // 2 - 160
                                    y_botao = int(altura_tela // 4.5 + i * 65)
                                    rect_botao = pygame.Rect(x_botao, y_botao, 320, 50)
                                    if rect_botao.collidepoint(pos_clique):
                                        opcao_conf_confirmada = i
                                        tempo_conf_confirmacao = agora_conf
                                        tocar_selecionar()

                                        particulas_conf_eclosao = []
                                        x_centro = largura_tela // 2
                                        y_centro = y_botao + 50 // 2
                                        import random
                                        for _ in range(40):
                                            particulas_conf_eclosao.append({
                                                'x': x_centro + random.uniform(-160, 160),
                                                'y': y_centro + random.uniform(-25, 25),
                                                'dx': random.uniform(-8, 8),
                                                'dy': random.uniform(-8, 8),
                                                'cor': random.choice([(0, 255, 230), (255, 0, 128), (255, 255, 255)]),
                                                'raio': random.uniform(2, 6),
                                                'vida': 1.0
                                            })
                                        break

                    # DetecÃ§Ã£o de hover pelo mouse no submenu de configuraÃ§Ãµes
                    mx_conf, my_conf = ui_helpers.obter_pos_mouse_superficie(tela)
                    for i, opcao in enumerate(opcoes_config):
                        x_botao = largura_tela // 2 - 160
                        y_botao = int(altura_tela // 4.5 + i * 65)
                        rect_botao = pygame.Rect(x_botao, y_botao, 320, 50)
                        if modo_interacao == "mouse" and rect_botao.collidepoint(mx_conf, my_conf) and opcao_conf_confirmada is None:
                            if indice_config != i:
                                indice_config = i
                                tocar_hover()

                    if not config_rodando:
                        break

                    # Desenhar botões premium glassy no submenu
                    for i, opcao in enumerate(opcoes_config):
                        x_botao = largura_tela // 2 - 160
                        y_botao = int(altura_tela // 4.5 + i * 65)
                        largura_b = 320
                        altura_b = 50

                        surf_botao = pygame.Surface((largura_b, altura_b), pygame.SRCALPHA)

                        if opcao_conf_confirmada == i:
                            decorrido = agora_conf - tempo_conf_confirmacao
                            progresso = min(1.0, max(0.0, decorrido / 200.0))
                            fator_escala = 1.0 + progresso * 0.4
                            nova_largura = int(largura_b * fator_escala)
                            nova_altura = int(altura_b * fator_escala)

                            surf_eclosao = pygame.Surface((nova_largura, nova_altura), pygame.SRCALPHA)
                            alpha_borda = int((1.0 - progresso) * 255)
                            pygame.draw.rect(surf_eclosao, (0, 255, 230, alpha_borda), (0, 0, nova_largura, nova_altura), width=3, border_radius=10)

                            x_ecl = x_botao - (nova_largura - largura_b) // 2
                            y_ecl = y_botao - (nova_altura - altura_b) // 2
                            tela.blit(surf_eclosao, (x_ecl, y_ecl))

                            # BotÃ£o brilha em branco
                            pygame.draw.rect(surf_botao, (255, 255, 255, 200), (0, 0, largura_b, altura_b), border_radius=8)
                            texto_surf = fonte_letra1.render(opcao, True, (0, 0, 0))
                            ret_texto = texto_surf.get_rect(center=(largura_b // 2, altura_b // 2))
                            surf_botao.blit(texto_surf, ret_texto)

                        elif i == indice_config:
                            import random
                            is_glitch_frame = random.random() < 0.15 and opcao_conf_confirmada is None
                            glitch_offset_x = random.randint(-3, 3) if is_glitch_frame else 0
                            glitch_offset_y = random.randint(-1, 1) if is_glitch_frame else 0

                            alpha_bg = random.randint(45, 95) if is_glitch_frame else 65
                            pygame.draw.rect(surf_botao, (0, 180, 200, alpha_bg), (0, 0, largura_b, altura_b), border_radius=8)
                            pygame.draw.rect(surf_botao, (0, 255, 230), (0, 0, largura_b, altura_b), width=2, border_radius=8)
                            pygame.draw.rect(surf_botao, (0, 255, 230), (0, 0, 6, altura_b), border_radius=8)

                            if is_glitch_frame:
                                texto_ciano = fonte_letra1.render(opcao, True, (0, 255, 255))
                                texto_rosa = fonte_letra1.render(opcao, True, (255, 0, 128))

                                ret_ciano = texto_ciano.get_rect(center=(largura_b // 2 + glitch_offset_x, altura_b // 2 + glitch_offset_y))
                                ret_rosa = texto_rosa.get_rect(center=(largura_b // 2 - glitch_offset_x, altura_b // 2 - glitch_offset_y))

                                surf_botao.blit(texto_ciano, ret_ciano)
                                surf_botao.blit(texto_rosa, ret_rosa)

                                if random.random() < 0.5:
                                    y_linha = random.randint(5, altura_b - 5)
                                    pygame.draw.line(surf_botao, (255, 255, 255), (5, y_linha), (largura_b - 5, y_linha), 1)
                            else:
                                texto_surf = fonte_letra1.render(opcao, True, (255, 255, 255))
                                ret_texto = texto_surf.get_rect(center=(largura_b // 2, altura_b // 2))
                                surf_botao.blit(texto_surf, ret_texto)

                            # Setas indicadoras piscantes
                            seta_esq = fonte_letra1.render("<", True, (0, 255, 230))
                            seta_dir = fonte_letra1.render(">", True, (0, 255, 230))
                            tela.blit(seta_esq, (x_botao - 45, y_botao + (altura_b - seta_esq.get_height()) // 2))
                            tela.blit(seta_dir, (x_botao + largura_b + 20, y_botao + (altura_b - seta_dir.get_height()) // 2))
                        else:
                            pygame.draw.rect(surf_botao, (15, 15, 25, 160), (0, 0, largura_b, altura_b), border_radius=8)
                            pygame.draw.rect(surf_botao, (100, 100, 150, 45), (0, 0, largura_b, altura_b), width=1, border_radius=8)

                            texto_surf = fonte_letras.render(opcao, True, (200, 200, 220))
                            ret_texto = texto_surf.get_rect(center=(largura_b // 2, altura_b // 2))
                            surf_botao.blit(texto_surf, ret_texto)

                        tela.blit(surf_botao, (x_botao, y_botao))

                    # Desenhar e atualizar partÃ­culas de eclosÃ£o do submenu de config
                    if particulas_conf_eclosao:
                        for part in particulas_conf_eclosao[:]:
                            part['x'] += part['dx']
                            part['y'] += part['dy']
                            part['dx'] *= 0.96
                            part['dy'] *= 0.96
                            part['vida'] -= 0.05
                            if part['vida'] <= 0:
                                particulas_conf_eclosao.remove(part)
                                continue

                            raio_atual = int(part['raio'] * part['vida'])
                            if raio_atual > 0:
                                alpha_part = max(0, min(255, int(part['vida'] * 255)))
                                cor_alpha = part['cor'] + (alpha_part,)
                                surf_part = pygame.Surface((raio_atual * 2, raio_atual * 2), pygame.SRCALPHA)
                                pygame.draw.circle(surf_part, cor_alpha, (raio_atual, raio_atual), raio_atual)
                                tela.blit(surf_part, (int(part['x'] - raio_atual), int(part['y'] - raio_atual)))

                    ui_helpers.desenhar_cursor_personalizado(tela)
                    pygame.display.flip()
                    clock.tick(60)

                    # LÃ³gica de confirmaÃ§Ã£o apÃ³s 200ms de eclosÃ£o do submenu
                    if opcao_conf_confirmada is not None and agora_conf - tempo_conf_confirmacao >= 200:
                        escolha_config = opcao_conf_confirmada
                        opcao_conf_confirmada = None
                        particulas_conf_eclosao = []

                        if escolha_config == 0:  # Controles
                            config_teclas = carregar_config_teclas()
                            tela_de_controles(tela, config_teclas, largura_tela, altura_tela)
                            tela = ui_helpers.obter_superficie_palco()
                        elif escolha_config == 1:  # GrÃ¡ficos
                            tela_configuracoes_graficas(tela, fonte)
                            tela = ui_helpers.obter_superficie_palco()
                        elif escolha_config == 2:  # Ãudio
                            tela_configuracoes_audio(tela, fonte)
                            tela = ui_helpers.obter_superficie_palco()
                        elif escolha_config == 3:  # Jogabilidade
                            tela_configuracoes_jogabilidade(tela, fonte)
                            tela = ui_helpers.obter_superficie_palco()
                        elif escolha_config == 4:  # Voltar
                            config_rodando = False

            elif escolha == 3:  # Sair
                if game_manager:
                    from game_manager import EstadoJogo
                    game_manager.mudar_estado(EstadoJogo.SAIR)
                    return
                else:
                    pygame.mixer.music.stop()
                    pygame.quit()
                    sys.exit()


# CÃ³digo principal - mantÃ©m compatibilidade com execuÃ§Ã£o direta
if __name__ == "__main__":
    # Tenta usar o GameManager se disponÃ­vel
    try:
        from game_manager import obter_game_manager, EstadoJogo
        manager = obter_game_manager()
        manager.executar()
    except ImportError:
        # Fallback: executa modo legado
        executar_menu_principal()
