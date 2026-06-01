# Scripts

Scripts de automacao do projeto.

## Build

```powershell
python scripts/build_dist.py
```

Esse comando gera a distribuicao em `dist/Ruptura_Temporal_APOLO2.0`.

## Player Manual

```powershell
python scripts/build_player.py
```

Gera `GAME5_PLAYER.py` a partir de `GAME5.py`, removendo partes automaticas para o
modo de controle manual.
