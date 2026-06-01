# Estrutura do Projeto

Este projeto ainda usa imports Python planos e caminhos de assets relativos a raiz
(`Sprites/...`, `Sounds/...`, `Texto/...`, `Video/...`). Por isso, a organizacao foi
feita de forma incremental: os arquivos de runtime continuam na raiz para preservar
compatibilidade, enquanto documentacao, scripts e ferramentas auxiliares foram
separados por responsabilidade.

## Pastas Principais

```text
.
|-- Ruptura_Temporal.py        # entrada principal do jogo
|-- GAME*.py                   # fases e modos jogaveis
|-- *_manager.py, *_helpers.py # sistemas compartilhados do runtime
|-- Sprites/                   # imagens e sprites usados pelo jogo
|-- Sounds/                    # musicas e efeitos sonoros
|-- Texto/                     # fontes
|-- Video/                     # videos
|-- saves/                     # memoria local, configuracoes e dados persistentes
|-- docs/                      # documentacao tecnica e narrativa
|-- scripts/                   # scripts de build e empacotamento
|-- tools/                     # ferramentas de IA, manutencao e patches
|-- tests/                     # testes e experimentos verificaveis
```

## Convencoes

- Mantenha arquivos executados pelo jogo na raiz enquanto os imports estiverem no
  formato atual (`import GAME`, `from Variaveis import *`).
- Coloque novos documentos em `docs/`.
- Coloque scripts de empacotamento em `scripts/`.
- Coloque utilitarios de treino, telemetria e manutencao em `tools/`.
- Coloque testes automatizados em `tests/`.
- Evite commitar builds gerados em `dist/` ou cache Python.

## Proxima Evolucao Recomendada

Quando houver tempo para uma migracao maior, o caminho natural e criar um pacote
em `src/ruptura_temporal/`, centralizar carregamento de assets em um helper unico
e trocar imports planos por imports de pacote. Essa etapa exige atualizar chamadas
de subprocess e todos os paths de asset, entao ficou fora desta organizacao segura.
