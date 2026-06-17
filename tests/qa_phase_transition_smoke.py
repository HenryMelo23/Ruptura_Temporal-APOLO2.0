import json
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


FULL_ATTRS = {
    "velocidade_personagem": 4.8,
    "intervalo_disparo": 180,
    "dano_person_hit": 450,
    "chance_critico": 0.35,
    "roubo_de_vida": 0.15,
    "quantidade_roubo_vida": 0.12,
    "vida_petro": 800,
    "vida_maxima_personagem": 2400,
    "vida_maxima_petro": 900,
    "vida_atual_personagem": 2100,
    "nivel_Petro": 18,
    "existencia_petro": True,
    "existencia_trembo": True,
    "dano_petro": 80,
    "resistencia_personagem": 35,
    "resistencia_petro": 20,
    "dano_inimigo_longe": 75,
    "dano_inimigo_perto": 95,
    "Poison_Active": True,
    "Ultimo_Estalo": True,
    "Executa_inimigo": 0.12,
    "Mercenaria_Active": False,
    "Valor_Bonus": 1.0,
    "tempo_cooldown_dash": 900,
    "petro_evolucao": 2,
    "Dano_Veneno_Acumulado": 0.04,
    "Tempo_cura": 1800,
    "porcentagem_cura": 0.08,
    "moedas_totais": 120,
    "Chance_Sorte": 0.25,
    "cartas_compradas": {
        "Speed Boost": 4,
        "Disparo crescente": 5,
        "Tempestade": 2,
        "Roubo de vida": 2,
        "Poison": 1,
    },
    "largura_disparo": 46,
    "altura_disparo": 46,
}


PARTIAL_OLD_ATTRS = {
    key: FULL_ATTRS[key]
    for key in [
        "velocidade_personagem",
        "intervalo_disparo",
        "dano_person_hit",
        "chance_critico",
        "vida_maxima_personagem",
        "vida_atual_personagem",
        "tempo_cooldown_dash",
    ]
}


PHASE_MODULES = ["GAME", "GAME2", "GAME3", "GAME4", "GAME5", "GAME6"]


CHILD = r"""
import importlib
import json
import os
import sys
import threading
import time
import traceback

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

attrs = json.loads(os.environ["QA_ATTRS_JSON"])
module_name = os.environ["QA_PHASE_MODULE"]

import Caminhos

with open("saves/atributos.json", "w", encoding="utf-8") as f:
    json.dump(attrs, f)
with open("saves/aurea_selecionada.json", "w", encoding="utf-8") as f:
    json.dump({"aurea": "Racional"}, f)
with open("saves/manifestacao_selecionada.json", "w", encoding="utf-8") as f:
    json.dump({"manifestacao_ativa": "eletrica"}, f)
with open("saves/config_cartas.json", "w", encoding="utf-8") as f:
    json.dump({"modo_cartas": "loja"}, f)
with open("saves/tutorial_config.json", "w", encoding="utf-8") as f:
    json.dump({"mostrar_tutorial": False}, f)

import pygame

pygame.init()
try:
    mod = importlib.import_module(module_name)
except BaseException:
    traceback.print_exc(file=sys.__stderr__)
    raise

class SmokeManager:
    def __init__(self):
        self.estado = None
        self.dados = None

    def mudar_estado(self, estado, dados=None):
        self.estado = estado
        self.dados = dados


def stop_soon():
    time.sleep(float(os.environ.get("QA_SECONDS", "0.65")))
    pygame.event.post(pygame.event.Event(pygame.QUIT))


threading.Thread(target=stop_soon, daemon=True).start()
try:
    mod.executar_jogo(SmokeManager())
except SystemExit as exc:
    code = exc.code if isinstance(exc.code, int) else 0
    if code not in (0, None):
        raise
except BaseException:
    traceback.print_exc(file=sys.__stderr__)
    raise
sys.__stdout__.write(f"{module_name} ok\n")
"""


def run_case(module_name, attrs, label):
    with tempfile.TemporaryDirectory(prefix=f"ruptura_qa_{module_name}_{label}_") as home:
        env = os.environ.copy()
        env["USERPROFILE"] = home
        env["HOME"] = home
        env["SDL_VIDEODRIVER"] = "dummy"
        env["SDL_AUDIODRIVER"] = "dummy"
        env["QA_PHASE_MODULE"] = module_name
        env["QA_ATTRS_JSON"] = json.dumps(attrs)
        env["QA_SECONDS"] = "0.65"
        result = subprocess.run(
            [sys.executable, "-c", CHILD],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=45,
        )
        if result.returncode != 0:
            raise AssertionError(
                textwrap.dedent(
                    f"""
                    Smoke failed: {module_name} / {label}
                    returncode={result.returncode}
                    STDOUT:
                    {result.stdout}
                    STDERR:
                    {result.stderr}
                    """
                ).strip()
            )
        print(result.stdout.strip())


def main():
    for module_name in PHASE_MODULES:
        run_case(module_name, FULL_ATTRS, "full")
    for module_name in PHASE_MODULES[1:]:
        run_case(module_name, PARTIAL_OLD_ATTRS, "partial_old")


if __name__ == "__main__":
    main()
