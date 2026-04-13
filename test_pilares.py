"""Teste dos 3 pilares do treino_paralelo_gpu_dqn.py"""
import ast, os, math

# -- Sintaxe --
src = open('treino_paralelo_gpu_dqn.py', 'r', encoding='utf-8').read()
ast.parse(src)
print(f"Sintaxe OK - {len(src.splitlines())} linhas")

# -- Imports headless --
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame
pygame.init()
pygame.display.set_mode((1, 1), flags=pygame.NOFRAME)

from treino_paralelo_gpu_dqn import (
    Rato, spawnar_ratos, processar_ratos,
    ApoloSim, UmbraSim,
    obter_estado_apolo_cpu, calcular_reward_apolo, calcular_reward_umbra,
    _acoes_umbra_disponiveis,
    COOLDOWN_RATOS_MS, TEMPO_VIDA_RATO_MS,
    DANO_RATO, CURA_UMBRA_POR_RATO,
    EXPERIENCIAS_POR_ENVIO, APOLO_INPUT_SIZE,
    EPSILON_INICIO, EPSILON_FIM, NUM_WORKERS,
    _criar_estado_ia,
)

print()
print("=== PILAR 1: Mecanica dos Ratos ===")

# Spawn base
agora = 0
ratos = spawnar_ratos(agora, ratos_extras=0)
print(f"  Spawn base (0 extras): {len(ratos)} ratos (esperado 4)")
assert len(ratos) == 4

# Spawn com extras
ratos2 = spawnar_ratos(agora, ratos_extras=3)
print(f"  Spawn com 3 extras: {len(ratos2)} ratos (esperado 7)")
assert len(ratos2) == 7

# Movimento
apolo = ApoloSim()
umbra = UmbraSim()
r0 = ratos[0]
ox, oy = r0.fx, r0.fy
r0.atualizar(apolo, agora + 100)
dist = math.hypot(r0.fx - ox, r0.fy - oy)
print(f"  Rato moveu {dist:.2f}px (esperado > 0)")
assert dist > 0

# Expiracao
ratos_exp = spawnar_ratos(0, 0)
acum = [0]
agora_exp = TEMPO_VIDA_RATO_MS + 100
res = processar_ratos(agora_exp, ratos_exp, apolo, umbra, acum)
print(f"  Expiracao 5s: {res['expirados']} expirados, {res['hits']} hits, restantes: {len(ratos_exp)}")
assert res['expirados'] == 4 and len(ratos_exp) == 0

# Colisao e acumulador
apolo2 = ApoloSim()
acum2 = [0]
umbra_danif = UmbraSim()
umbra_danif.vida = 30_000.0   # Reduz vida para que a cura seja visivel
rato_col = Rato(apolo2.fx, apolo2.fy, 0)   # Spawn em cima do Apolo
v_umbra_antes = umbra_danif.vida
res2 = processar_ratos(50, [rato_col], apolo2, umbra_danif, acum2)
print(f"  Colisao: hits={res2['hits']} acum={acum2[0]} cura_umbra={umbra_danif.vida - v_umbra_antes:.0f}")
assert res2['hits'] == 1 and acum2[0] == 1
assert umbra_danif.vida > v_umbra_antes, f"Esperado cura, vida {umbra_danif.vida} <= {v_umbra_antes}"

# Estado com ratos (41 features)
ratos3 = spawnar_ratos(0, 0)
estado_ia = _criar_estado_ia()
s = obter_estado_apolo_cpu(apolo, umbra, [], [], estado_ia, ratos3)
print(f"  Estado Apolo c/ ratos: {len(s)} features (esperado 41)")
assert len(s) == 41
print(f"  f[30]=qtd_ratos={s[30]:.3f}  f[31]=dist_rato={s[31]:.3f}")
assert s[30] > 0, "qtd_ratos deveria ser > 0"

# Rewards dos ratos
r_a_hit = calcular_reward_apolo(apolo, umbra, [], [], estado_ia,
                                 apolo.vida, umbra.vida, False, False, False,
                                 hits_ratos=2)
r_a_base = calcular_reward_apolo(apolo, umbra, [], [], estado_ia,
                                  apolo.vida, umbra.vida, False, False, False,
                                  hits_ratos=0)
r_a_esq = calcular_reward_apolo(apolo, umbra, [], [], estado_ia,
                                  apolo.vida, umbra.vida, False, False, False,
                                  expirados_ratos=3, hits_ratos=0)
print(f"  Reward Apolo: hit2={r_a_hit:.1f}  base={r_a_base:.1f}  esquiva3={r_a_esq:.1f}")
assert r_a_hit < r_a_base, "Penalidade por rato nao aplicada"
assert r_a_esq > r_a_base, "Bonus esquiva nao aplicado"

r_u_hit = calcular_reward_umbra(False, 'NENHUMA', False, False, hits_ratos=2)
r_u0    = calcular_reward_umbra(False, 'NENHUMA', False, False, hits_ratos=0)
print(f"  Reward Umbra: hits=2={r_u_hit:.1f}  hits=0={r_u0:.1f}")
assert r_u_hit > r_u0, "Reward Umbra por rato nao aplicado"

# PRAGA_RATOS no cooldown
acoes_pos = _acoes_umbra_disponiveis(COOLDOWN_RATOS_MS + 1, {'ratos': 0})
acoes_pre = _acoes_umbra_disponiveis(1000, {'ratos': 0})
print(f"  PRAGA_RATOS disponivel apos 15s: {'PRAGA_RATOS' in acoes_pos}")
print(f"  PRAGA_RATOS indisponivel antes: {'PRAGA_RATOS' not in acoes_pre}")
assert 'PRAGA_RATOS' in acoes_pos
assert 'PRAGA_RATOS' not in acoes_pre

print()
print("=== PILAR 2: IPC Batch Size ===")
print(f"  EXPERIENCIAS_POR_ENVIO = {EXPERIENCIAS_POR_ENVIO} (esperado 128)")
assert EXPERIENCIAS_POR_ENVIO == 128

print()
print("=== PILAR 3: Epsilon por Worker ===")
def epsilon_para_worker(wid, n):
    frac = wid / (n - 1) if n > 1 else 0
    return round(EPSILON_FIM + frac * (EPSILON_INICIO - EPSILON_FIM), 4)

epsilons = [epsilon_para_worker(w, NUM_WORKERS) for w in range(NUM_WORKERS)]
print(f"  Epsilons: {[f'{e:.2f}' for e in epsilons]}")
assert epsilons[0] == EPSILON_FIM, f"W0 esperado {EPSILON_FIM}, obtido {epsilons[0]}"
assert epsilons[-1] == EPSILON_INICIO, f"W{NUM_WORKERS-1} esperado {EPSILON_INICIO}"
assert sorted(epsilons) == epsilons, "Epsilons nao sao crescentes"
print(f"  W0 (greedy): {epsilons[0]:.2f}  W{NUM_WORKERS-1} (exploratorio): {epsilons[-1]:.2f}")

print()
print("TODOS OS TESTES PASSARAM - Script pronto para o Burn-in Test de 12h!")
