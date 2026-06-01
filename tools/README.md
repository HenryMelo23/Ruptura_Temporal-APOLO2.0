# Tools

Ferramentas auxiliares que nao fazem parte do loop principal do jogo.

## `tools/ai`

Treinos, telemetria e manutencao da memoria neural:

```powershell
python tools/ai/treino_laser_apolo.py
python tools/ai/grafico_evolucao.py
python tools/ai/painel_neural.py
python tools/ai/reset_memoria_apolo.py
```

## `tools/patches`

Patches historicos de manutencao. Eles localizam a raiz do projeto automaticamente,
mas devem ser usados com cuidado porque alteram arquivos de runtime.
