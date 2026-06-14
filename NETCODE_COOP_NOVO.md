# Netcode Coop Novo

## Diagnostico Atual

- `rede.py` mantinha uma fila unica TCP (`fila_envio`/`fila_recebimento`) para eventos criticos e dados frequentes.
- `multiplayer_coop.py` envia player, mundo, ping, pedido de snapshot e dano pela mesma via logica.
- `GAME.py` a `GAME4.py` chamam a fachada `multiplayer_coop.atualizar`, `sincronizar_mundo`, `desenhar_jogador_remoto`, loja, pause, boss call e barreiras.
- O host ja e autoritativo para inimigos, boss, economia e fases; o client renderiza mundo recebido por `coop_id`.
- O client ja tinha coalescing, descarte por `seq`, interpolacao local e pedido de snapshot quando o mundo envelhece.
- O ponto fraco principal era misturar snapshot descartavel com eventos confiaveis no mesmo canal.

## Arquitetura Alvo

- TCP: eventos criticos e ordenados, como fase, game over, convite de pause/loja/boss e barreiras.
- UDP: dados frequentes e descartaveis, como `player`, `mundo`, `ping/pong`, `snapshot_request` e `dano`.
- `multiplayer_coop.py` permanece como fachada de alto nivel para evitar reescrever as fases.
- `net_protocol.py` centraliza encode/decode, versao, tipos de pacote e compatibilidade com pacotes legados `coop_tipo`.
- `net_transport.py` cria o canal UDP de jogo na porta `5052`, com filas separadas.

## Tipos de Pacote

- TCP confiavel: `fase`, `convite`, `barreira`, `game_over`.
- UDP descartavel: `player`, `mundo`, `ping`, `pong`, `snapshot_request`, `dano`.
- Pacote v2 interno:
  - `protocol`: `RT_COOP`
  - `version`: `2`
  - `type`: tipo logico
  - `seq`: sequencia quando existir
  - `time`: tempo local/host
  - `channel`: `tcp` ou `udp`
  - `payload`: pacote legado usado pela fachada atual

## Responsabilidades

- Host:
  - cria inimigos e `coop_id`;
  - envia snapshots de mundo;
  - aplica dano oficial do client;
  - decide boss, economia, loja, pause, fase e game over.
- Client:
  - envia estado/input atual;
  - envia pedidos de dano;
  - renderiza feedback local;
  - interpola inimigos e player remoto;
  - descarta snapshot antigo.

## Fases de Migracao

1. Protocolo central e UDP paralelo com fallback TCP.
2. Snapshots/player/dano pelo UDP, eventos criticos no TCP.
3. Refinar heartbeat vivo em pause/loja/barreira.
4. Evoluir `player` para input autoritativo.
5. Melhorar validacao de dano e lag compensation.
6. Delta snapshots e compressao opcional.

## Como Testar

1. Abrir host e client em LAN.
2. Ativar overlay F10 nos dois.
3. Verificar `udp p/w/m/d/e/h` no overlay.
4. No client, confirmar que `snapshot idade` fica baixo.
5. Atirar em inimigos pelo client e observar `dano env/rec/apl`.
6. Abrir pause/loja e confirmar que ping/snapshot nao ficam varios segundos parados.

## Constantes Importantes

- `COOP_SYNC_PLAYER_MS = 33`
- `COOP_SYNC_INIMIGOS_MOV_MS = 33`
- `COOP_SYNC_MUNDO_MS = 150`
- `COOP_INTERPOLATION_DELAY_MS = 100`
- `COOP_EXTRAPOLACAO_MAX_MS = 120`
- `UDP_PLAYER_PORT = 5052`
- `UDP_WORLD_PORT = 5053`
- `UDP_ENEMY_MOVE_PORT = 5056`
- `UDP_DAMAGE_PORT = 5054`
- `UDP_EVENT_PORT = 5057`
- `UDP_HEARTBEAT_PORT = 5055`
- `COOP_SNAPSHOT_STALE_REQUEST_MS = 600`

## Limitacoes Atuais

- Input autoritativo completo ainda nao foi migrado; o canal UDP ja esta pronto para isso.
- Dano remoto aplica vida/morte no host, mas recompensas especificas por fase ainda precisam ser refinadas.
- Heartbeat de sessao existe parcialmente via canal dedicado de ping/pong e snapshot request; ainda falta um `SESSION_STATE` confiavel formal.
