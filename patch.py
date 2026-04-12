import re

with open('GAME5.py', 'r', encoding='utf-8') as f:
    c = f.read()

c = re.sub(
    r'if\s+apolo\.estado_anterior\s+in\s+apolo\.q_table:\s*\n\s*apolo\.q_table\[apolo\.estado_anterior\]\[apolo\.acao_anterior\]\s*([-+]=)\s*([\d\.]+)',
    r'apolo.aplicar_recompensa_direta(\1\2)',
    c
)

rep103 = """        pesos_reais = {}
        import torch
        if memoria_umbra.ultimo_estado_tensor is not None:
            with torch.no_grad():
                memoria_umbra.q_network.eval()
                q_vals = memoria_umbra.q_network(memoria_umbra.ultimo_estado_tensor)[0]
                for i, acn in enumerate(memoria_umbra.acoes_base):
                    pesos_reais[acn] = round(float(q_vals[i]), 3)
        else:"""

c = re.sub(r'if estado_ativo and estado_ativo in memoria_umbra\.q_table:\s*\n\s*pesos_reais = memoria_umbra\.q_table\[estado_ativo\]', rep103, c)

rep1408 = '                mapa_neural = {"DQN": "Ativo"}'
c = re.sub(r'estados_relevantes = list\(memoria_umbra\.q_table\.keys\(\)\)\[:\]\s*\n\s*mapa_neural = \{est: memoria_umbra\.q_table\[est\] for est in estados_relevantes if isinstance\(memoria_umbra\.q_table\[est\], dict\)\}', rep1408, c)

c = c.replace('estado_ativo = memoria_umbra.ultimo_estado', 'estado_ativo = "DQN_TENSOR"')

with open('GAME5.py', 'w', encoding='utf-8') as f:
    f.write(c)

with open('treino_acelerado_v3_percepcao_expandida.py', 'r', encoding='utf-8') as f:
    c2 = f.read()

c2 = re.sub(
    r'if\s+self\.apolo\.estado_anterior\s+in\s+self\.apolo\.q_table:\s*\n\s*self\.apolo\.q_table\[self\.apolo\.estado_anterior\]\[self\.apolo\.acao_anterior\]\s*([-+]=)\s*([\d\.]+)',
    r'self.apolo.aplicar_recompensa_direta(\1\2)',
    c2
)

c2 = c2.replace('len(self.umbra.q_table)', '0')
c2 = c2.replace('len(self.apolo.q_table)', '0')

with open('treino_acelerado_v3_percepcao_expandida.py', 'w', encoding='utf-8') as f:
    f.write(c2)
