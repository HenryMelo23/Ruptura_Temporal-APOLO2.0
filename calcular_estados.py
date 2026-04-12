# Calculando espaço de estados atual do Apolo
componentes_apolo = {
    'quadrante_boss': 5,  # C/L/O/S/N
    'distancia': 4,  # MUITO_PERTO/PERTO/MEDIO/LONGE
    'vida_apolo': 4,  # CRITICA/BAIXA/MEDIA/ALTA
    'vida_boss': 4,
    'perigo': 3,  # NENHUM/PROJETIL/MULTIPLOS
    'dir_perigo': 5,  # LIVRE/L/O/S/N
    'cd_teleporte': 2,
    'armadilha': 2,
    'pos_mapa': 5,  # CENTRO/BORDA_L/BORDA_O/BORDA_S/BORDA_N
    'velocidade': 3  # PARADO/NORMAL/DASH
}

total_apolo = 1
for k, v in componentes_apolo.items():
    total_apolo *= v
    print(f'{k}: {v}')

print(f'\nTotal estados Apolo ATUAL: {total_apolo:,}')

# Calculando Umbra
print('\n--- Umbra ---')
componentes_umbra = {
    'fase_mapa': 5,
    'vida': 2,  # crit/estavel
    'distancia': 2,  # perto/longe
    'fogo': 2,  # perigo/calmo
    'movimento': 2  # linear/erratico
}

total_umbra = 1
for k, v in componentes_umbra.items():
    total_umbra *= v
    print(f'{k}: {v}')

print(f'\nTotal estados Umbra ATUAL: {total_umbra:,}')

# EXPANSÃO PARA 70K ESTADOS
print('\n' + '='*60)
print('EXPANSÃO PARA DEEP Q-LEARNING (70K+ ESTADOS)')
print('='*60)

# Apolo expandido
componentes_apolo_deep = {
    'pos_x_grid': 20,  # Divide mapa em grid 20x20
    'pos_y_grid': 20,
    'boss_x_grid': 20,
    'boss_y_grid': 20,
    'vida_apolo': 10,  # 10 níveis de vida
    'vida_boss': 10,
    'num_projeteis': 5,  # 0, 1-2, 3-5, 6-10, 10+
    'projetil_mais_proximo': 8,  # 8 direções
    'cd_teleporte': 2,
    'cd_disparo': 2,
    'armadilha_tipo': 8,  # 7 tipos + nenhuma
    'velocidade': 4,
    'tempo_combate': 5  # early/mid/late/critical/endgame
}

total_apolo_deep = 1
for k, v in componentes_apolo_deep.items():
    total_apolo_deep *= v

print(f'\nApolo Deep Q-Learning: {total_apolo_deep:,} estados')

# Umbra expandida
componentes_umbra_deep = {
    'pos_x_grid': 15,
    'pos_y_grid': 15,
    'player_x_grid': 15,
    'player_y_grid': 15,
    'vida_umbra': 10,
    'vida_player': 10,
    'player_velocidade': 4,
    'player_direcao': 8,
    'habilidade_cd': 3,
    'fase_mapa': 5,
    'tempo_combate': 5
}

total_umbra_deep = 1
for k, v in componentes_umbra_deep.items():
    total_umbra_deep *= v

print(f'Umbra Deep Q-Learning: {total_umbra_deep:,} estados')

print(f'\n🎯 Equilíbrio de Nash estimado: 5.000-15.000 gerações')
print(f'📊 Com replay buffer e target network: 2.000-8.000 gerações')
