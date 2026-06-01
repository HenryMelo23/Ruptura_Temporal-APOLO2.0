<div align="center">

# ⏳ Ruptura Temporal

### *A 2D Action Game Powered by Deep Reinforcement Learning*

![Python](https://img.shields.io/badge/Python-3.14+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)
![Pygame](https://img.shields.io/badge/Pygame-2.x-00CC44?style=for-the-badge&logo=python&logoColor=white)
![Deep Learning](https://img.shields.io/badge/Deep_Learning-DQN-FF6F00?style=for-the-badge&logo=tensorflow&logoColor=white)
![License](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-EF9421?style=for-the-badge&logo=creativecommons&logoColor=white)
![Status](https://img.shields.io/badge/Status-Beta-yellow?style=for-the-badge)

<br/>

**An open-source action-survival game featuring adaptive AI agents trained with Deep Q-Networks (DQN).**  
**Experience real-time combat against neural network-powered bosses that learn and adapt to your playstyle.**

<br/>

[📥 Download](https://github.com/HenryMelo23/Ruptura_Temporal/releases/tag/v0.0.1) · [🐛 Report Bug](https://github.com/HenryMelo23/Ruptura_Temporal/issues) · [💡 Request Feature](https://github.com/HenryMelo23/Ruptura_Temporal/issues) · [📖 Documentation](https://github.com/HenryMelo23/Ruptura_Temporal/wiki)

</div>

---

## 📖 Table of Contents

- [🎯 Project Overview](#-project-overview)
- [🧠 AI Architecture: From Tabular Q-Learning to Deep Q-Networks](#-ai-architecture-from-tabular-q-learning-to-deep-q-networks)
  - [The Problem: Curse of Dimensionality](#the-problem-curse-of-dimensionality)
  - [The Solution: Deep Q-Learning (DQN)](#the-solution-deep-q-learning-dqn)
  - [Agent Architecture](#agent-architecture)
- [🛠️ Tech Stack](#️-tech-stack)
- [📸 Visual Showcase](#-visual-showcase)
- [✨ Game Features](#-game-features)
- [🔮 Áureas System (Character Passives)](#-áureas-system-character-passives)
- [🌐 LAN Multiplayer Architecture](#-lan-multiplayer-architecture)
- [📁 Project Structure](#-project-structure)
- [🚀 Installation & Setup](#-installation--setup)
- [🎮 Training the AI](#-training-the-ai)
- [🎹 Controls](#-controls)
- [🗺️ Roadmap](#️-roadmap)
- [🤝 Contributing](#-contributing)
- [📜 License](#-license)
- [📬 Contact](#-contact)

---

## 🎯 Project Overview

**Ruptura Temporal** is a 2D top-down action-survival game that showcases the practical application of **Deep Reinforcement Learning** in real-time game AI. Originally developed as a personal project, it has evolved into a comprehensive open-source demonstration of modern AI techniques in game development.

### What Makes This Project Unique?

- **🧠 Adaptive AI Opponents**: Boss enemies powered by Deep Q-Networks that learn and adapt to player behavior across multiple game sessions
- **🔬 Real-Time Learning**: Neural networks train during gameplay, creating dynamic and unpredictable combat encounters
- **📊 Persistent Memory**: AI agents retain learned strategies through PyTorch tensor weights (`.pt` files), evolving with each battle
- **🎮 Production-Ready Implementation**: Fully integrated DQN agents in a playable game environment, not just a research prototype

### Technical Highlights

This project demonstrates:
- Migration from discrete state-space Q-Learning to continuous function approximation with neural networks
- Asymmetric agent architectures optimized for different strategic objectives
- Real-time inference and training without compromising game performance
- Bayesian statistical tracking for predictive behavior modeling

---

## 🧠 AI Architecture: From Tabular Q-Learning to Deep Q-Networks

### The Problem: Curse of Dimensionality

The initial implementation used **Tabular Q-Learning**, where the agent maintained a discrete lookup table (JSON dictionary) mapping each unique game state to action values. This approach faced critical limitations:

**Dimensional Explosion:**
```
State Space = Positions × Velocities × Health States × Enemy Configurations × ...
            ≈ 1000 × 100 × 50 × 200 × ... → 10^9+ states
```

**Perceptual Aliasing:**
- Discrete binning of continuous variables (position, distance, velocity) caused information loss
- Similar situations were treated as completely different states
- No generalization: the agent couldn't apply learned strategies to novel scenarios

**Memory Constraints:**
- JSON files grew exponentially with state space coverage
- Sparse exploration: most states never visited during training
- Static knowledge: no interpolation between known states

### The Solution: Deep Q-Learning (DQN)

The transition to **Deep Q-Networks** solved these fundamental issues through **function approximation**:

```python
# Old: Discrete lookup
Q(state) = q_table[discretize(state)]  # ❌ Rigid, non-generalizable

# New: Continuous approximation
Q(state) = neural_network(state_tensor)  # ✅ Smooth, generalizable
```

**Key Advantages:**

| Aspect | Tabular Q-Learning | Deep Q-Learning (DQN) |
|:---|:---:|:---:|
| **State Representation** | Discrete bins (JSON dict) | Continuous tensors (PyTorch) |
| **Generalization** | None (exact match only) | High (interpolates unseen states) |
| **Memory Footprint** | O(|S| × |A|) - exponential | O(network parameters) - fixed |
| **Novel Situations** | Random action | Informed inference |
| **Training Data** | Requires visiting every state | Learns from similar states |
| **Geometric Processing** | Aliased/quantized | Raw continuous values |

**Mathematical Foundation:**

The Bellman equation remains the same, but the Q-function is now approximated by a neural network:

```
Q(s, a; θ) ≈ Q*(s, a)

Loss = MSE(Q(s, a; θ), r + γ · max Q(s', a'; θ))
              ↑                    ↑
         Current estimate    Target (Bellman)
```

Where `θ` represents the neural network weights optimized via backpropagation.

### Agent Architecture

The game features two asymmetric DQN agents with distinct strategic objectives:

#### 🎮 **Apolo** (Player Agent)

**Objective:** Survival and evasion under constant threat

**Network Architecture:**
```
Input Layer:  23 features (normalized continuous values)
   ↓
Hidden Layer: 128 neurons (LeakyReLU activation)
   ↓
Hidden Layer: 64 neurons (LeakyReLU activation)
   ↓
Output Layer: 5 actions (Q-values for each action)
```

**Input Features (23):**
- **Spatial:** Player position (x, y), boss position (x, y)
- **Health:** Player HP %, boss HP %
- **Threat Assessment:** Distance to nearest projectile, projectile velocity vector (x, y)
- **Cooldowns:** Teleport availability (binary)
- **Environmental Hazards:** 7 trap states (vortex, prison, thorns, laser, discharge, borders, miasma)
- **Dynamics:** Player velocity, number of energy spheres, boss velocity
- **Laser Threat:** Laser active flag, laser direction vector (x, y)

**Output Actions (5):**
1. Move Up
2. Move Down
3. Move Left
4. Move Right
5. Dash/Teleport

**Reward Function:**
```python
reward = 0.5  # Base survival reward per frame

# Damage dynamics
if player_took_damage:
    reward -= 50
if boss_took_damage:
    reward += 30
if player_healed:
    reward += 100

# Positional awareness
if near_map_borders:
    reward -= 2
if optimal_distance_from_boss (300-600 units):
    reward += 1
elif too_close (< 200 units):
    reward -= 3

# Laser evasion
if laser_active and player_took_damage:
    reward -= 150
if laser_active and player_survived:
    reward += 20
```

**Training Configuration:**
- **Optimizer:** Adam (lr=0.001)
- **Loss Function:** MSE (Mean Squared Error)
- **Discount Factor (γ):** 0.95
- **Exploration Rate (ε):** 0.20 (20% random actions)
- **Memory Persistence:** `saves/apolo_memoria_dqn.pt`

---

#### 👾 **Umbra** (Boss Agent)

**Objective:** Tactical dominance and player elimination

**Network Architecture:**
```
Input Layer:  18 features (normalized continuous values)
   ↓
Hidden Layer: 128 neurons (LeakyReLU activation)
   ↓
Hidden Layer: 64 neurons (LeakyReLU activation)
   ↓
Output Layer: 22 actions (Q-values for each action)
```

**Input Features (18):**
- **Health Percentage:** Boss HP % (survival priority)
- **Distance to Player:** Euclidean distance (tactical positioning)
- **Under Fire:** Binary flag (player actively shooting)
- **Player Velocity:** Movement vector (x, y) for prediction
- **Relative Position:** Direction vector to player (x, y)
- **Active Traps:** 8 binary flags (current hazards deployed)
- **Dimensional Phase:** Current map/dimension identifier
- **Threat Vector:** Incoming projectile direction (x, y)

**Output Actions (22):**

*Movement Strategies (4):*
1. FLEE (maximize distance)
2. INTERCEPT (cut off player path)
3. ORBIT (circular strafe)
4. SURROUND (close distance)

*Offensive Abilities (1):*
5. ATTACK (directed projectile)

*Defensive Abilities (2):*
6. SIPHON (healing stasis at map center)
7. TELEPORT (tactical repositioning)

*Dimensional Transmutation (7):*
8. TRANSMUTE_VORTEX (Dimension 1: temporal vortex)
9. TRANSMUTE_GRAVITY (Dimension 2: gravity well)
10. TRANSMUTE_NECROSIS (Dimension 3: necrotic zone)
11. TRANSMUTE_RESONANCE (Dimension 4: sonic resonance)
12. TRANSMUTE_HEMORRHAGE (Dimension 6: bleeding thorns)
13. TRANSMUTE_FRICTION (Dimension 7: laser overcharge)
14. TRANSMUTE_TRAIL (Dimension 9: toxic borders)

*Dimension-Specific Hazards (7):*
15. VORTEX (pull player to center)
16. PRISON (cryogenic trap)
17. MIASMA (toxic cloud)
18. ELECTRIC_DISCHARGE (cone attack)
19. THORN_PATH (geometric spike patterns)
20. LASER_OVERCHARGE (sweeping beam)
21. RAT_PLAGUE (border damage)
22. NONE (idle/cooldown)

**Bayesian Bias System:**

Umbra maintains a statistical model of player movement tendencies:

```python
# Tracks directional preferences over time
tendencies = {
    "TOTAL": 0,
    "LEFT": 0, "RIGHT": 0,
    "UP": 0, "DOWN": 0
}

# Calculates predictive bias
bias_x = (tendencies["RIGHT"] - tendencies["LEFT"]) / max(1, tendencies["TOTAL"])
bias_y = (tendencies["DOWN"] - tendencies["UP"]) / max(1, tendencies["TOTAL"])

# Used for predictive aiming and trap placement
predicted_position = player_pos + (player_velocity + bias_vector) * time_horizon
```

This allows Umbra to develop "intuition" about player behavior patterns, leading projectiles and placing traps where the player is likely to move.

**Training Configuration:**
- **Optimizer:** Adam (lr=0.001)
- **Loss Function:** MSE
- **Discount Factor (γ):** 0.95
- **Exploration Rate (ε):** 0.20
- **Memory Persistence:** `saves/memoria_umbra_dqn.pt` (neural weights) + `saves/tendencias_umbra.json` (Bayesian stats)

---

### Training Mechanics

Both agents employ **online learning** during gameplay:

1. **State Observation:** Raw game state → normalized feature tensor
2. **Action Selection:** ε-greedy policy (80% exploitation, 20% exploration)
3. **Environment Interaction:** Execute action, observe reward and next state
4. **Q-Value Update:** Backpropagation using temporal difference error
5. **Weight Persistence:** Save updated network parameters to `.pt` files

**Key Implementation Details:**

```python
# Feature normalization example
feat_position_x = player_x / map_width  # [0, 1]
feat_health = current_hp / max_hp       # [0, 1]
feat_distance = distance / 2000.0       # Scaled to reasonable range

# Epsilon-greedy action selection
if random.random() < exploration_rate:
    action = random.choice(available_actions)  # Explore
else:
    with torch.no_grad():
        q_values = q_network(state_tensor)
        action = torch.argmax(q_values).item()  # Exploit

# Temporal difference learning
current_q = q_network(state)[action]
target_q = reward + gamma * torch.max(q_network(next_state))
loss = mse_loss(current_q, target_q)
loss.backward()
optimizer.step()
```

**Why LeakyReLU?**

Standard ReLU can cause "dying neurons" (always outputting zero). LeakyReLU allows small negative gradients, ensuring all neurons remain active during training:

```python
LeakyReLU(x) = max(0.01x, x)
```

This is critical for continuous learning in dynamic game environments where state distributions shift over time.

---

## 🛠️ Tech Stack

### Core Technologies

| Technology | Purpose | Version |
|:---|:---|:---:|
| **Python** | Primary language | 3.14+ |
| **PyTorch** | Deep learning framework, tensor operations, neural network training | 2.0+ |
| **Pygame** | Game engine (rendering, input, audio, game loop) | 2.x |
| **NumPy** | Numerical computations (implicit via PyTorch) | Latest |

### AI/ML Components

| Component | Implementation |
|:---|:---|
| **Neural Network Architecture** | `torch.nn.Sequential` with Linear layers |
| **Activation Function** | `LeakyReLU` (negative slope = 0.01) |
| **Optimizer** | `torch.optim.Adam` (adaptive learning rate) |
| **Loss Function** | `torch.nn.MSELoss` (mean squared error) |
| **Device Management** | CUDA-enabled (GPU acceleration when available) |
| **Weight Persistence** | `torch.save()` / `torch.load()` for `.pt` files |

### Networking (LAN Mode)

| Technology | Purpose |
|:---|:---|
| **TCP Sockets** | Reliable state synchronization |
| **UDP Broadcast** | Host discovery on local network |
| **Threading** | Non-blocking send/receive operations |
| **JSON Serialization** | Packet encoding/decoding |

### Data Management

| Format | Usage |
|:---|:---|
| **`.pt` (PyTorch)** | Neural network weights (DQN agents) |
| **`.json`** | Configuration, saves, Bayesian statistics |
| **`.png`** | Sprites and visual assets |
| **`.mp3/.wav`** | Audio files |

---

## 📸 Visual Showcase

<div align="center">

### 🏠 Main Menu
<img src="Sprites/Git/Menu_intro.png" alt="Main Menu" width="600" />

<br/><br/>

### 🌊 Phase 1 — Ruined Beach
<img src="Sprites/Git/Fase1_git.png" alt="Phase 1 - Beach" width="600" />

<br/><br/>

### ❄️ Phase 2 — Frozen Kingdom
<img src="Sprites/Git/Fase2_git.png" alt="Phase 2 - Ice" width="600" />

<br/><br/>

### 🐀 Phase 3 — Cultist Rat Dimension
<img src="Sprites/Git/Fase3_git.png" alt="Phase 3 - Rats" width="600" />

<br/><br/>

### 🐸 Phase 4 — Scientist Frog World
<img src="Sprites/Git/Fase4_git.png" alt="Phase 4 - Frogs" width="600" />

<br/><br/>

### 🔥 Phase 5 — Final Boss Arena (In Development)
> The fifth and final phase is under development. This will feature the ultimate boss encounter with full DQN capabilities.

</div>

---

## ✨ Game Features

### 🎯 Gameplay
- **5 thematic phases** — each with unique environments, enemies, and bosses
- **Combat system** with melee attacks and projectiles
- **Dash/Teleport** mechanic for dodging enemy attacks
- **Card Shop (Deck)** — upgrade system with random rolls and strategic purchases
- **Scoring system** — eliminate enemies to earn points and improve your character
- **Epic bosses** with varied attack patterns and behavioral phases
- **DQN-powered boss AI** — Umbra learns and adapts to player strategies across sessions

### 🧙 Áureas System (Character Passives)
- **4 distinct Áureas** — Rational, Impulsive, Vanguard, and Devout
- Each Áurea modifies playstyle with automatic bonuses
- Áurea evolution/upgrade system with cross-session persistence

### 🌐 LAN Multiplayer (Cooperative)
- **Host & Join** — create or connect to sessions directly from menu
- **Automatic discovery via UDP Broadcast** on local network
- **Real-time synchronization** of positions, actions, enemies, and game state
- **Ping monitoring** for latency tracking
- **Cooperative revive** — players can die and revive after cooldown

### 🛠️ Additional Features
- **Integrated tutorial** — step-by-step control instructions
- **Gamepad/Joystick support** — play with Xbox or similar controllers
- **Key configuration** — customize keyboard controls
- **Save system** — save and load character attributes
- **Sound effects and music** — thematic soundtrack per phase
- **Game Over screen** with retry options

---

## 🔮 Áureas System (Character Passives)

Each player can choose an **Áurea** before starting a match. Áureas define the character's passive ability, directly influencing playstyle.

<div align="center">
<img src="Sprites/Git/Aurea.png" alt="Áureas System" width="600" />
</div>

<br/>

<table align="center">
<tr>
<td align="center" width="50%">

### 🧠 Rational Áurea

<img src="Sprites/aurea_cientista.png" alt="Rational Áurea" width="300" />

*"Patience is the most powerful weapon."*

Ideal for **strategic and patient** players.
- Increases score when player remains stationary for several seconds
- After 5 seconds idle, gains +3 points (scales with level)
- Green visual effect indicates gain

</td>
<td align="center" width="50%">

### 🔥 Impulsive Áurea

<img src="Sprites/aurea_impulsiva.png" alt="Impulsive Áurea" width="300" />

*"Fury is the fuel of victory."*

For players with **aggressive and dynamic** style.
- Temporary buff after 5 consecutive eliminations without taking damage
- Random bonus: increased damage or speed
- Taking damage resets counter

</td>
</tr>
<tr>
<td align="center" width="50%">

### ⚔️ Vanguard Áurea

<img src="Sprites/aurea_vanguarda.png" alt="Vanguard Áurea" width="300" />

*"Pain is also a weapon."*

For those who play on the **front line**.
- When taking direct damage, ignites nearby enemies
- Creates danger zone for melee enemies
- Ideal for direct confrontations

</td>
<td align="center" width="50%">

### 🛡️ Devout Áurea

<img src="Sprites/aurea_devota.png" alt="Devout Áurea" width="300" />

*"Faith is shield."*

For players who value **resistance and defense**.
- Temporary shield that absorbs next hit
- Automatic regeneration after fixed interval
- Resists consecutive attacks without losing health

</td>
</tr>
</table>

---

## 🌐 LAN Multiplayer Architecture

The Beta version introduces a networking layer based on **TCP sockets** and **JSON serialization**, enabling direct communication between two game instances.

The architecture follows a **client-server model**, where the Host maintains game state and sends real-time updates to the client.

```
┌──────────────┐         TCP/5050          ┌──────────────┐
│   HOST       │◄────────────────────────►│   CLIENT     │
│              │   JSON serialization      │              │
│  Thread TX ──┼──────────────────────────►│── Thread RX  │
│  Thread RX ──┼◄──────────────────────────│── Thread TX  │
│              │                           │              │
│  Game Loop   │   UDP Broadcast (LAN)     │  Game Loop   │
│  State Sync  │◄─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ │  Discovery   │
└──────────────┘                           └──────────────┘
```

**Key Features:**
- 🔄 Real-time synchronization of positions, actions, and enemies
- 📡 Automatic host discovery via **UDP Broadcast**
- 🧵 **Independent threads** for send/receive (non-blocking game loop)
- 📊 Real-time latency monitoring (ping)
- 🔐 Packet integrity with JSON delimiters
- 🎮 Mode selection (Host / Join / Offline) integrated into main menu

<div align="center">
<img src="Sprites/Git/Escolha.png" alt="Mode selection screen" width="500" />

> Create a session (Host Game) or connect to an existing match (Join Game) directly from the menu.
</div>

---

## 📁 Project Structure

```
Ruptura_Temporal-APOLO2.0/
├── Ruptura_Temporal.py       # main entry point / menu
├── GAME*.py                  # playable phases and modes
├── game_manager.py           # state transitions between screens
├── Variaveis.py              # global gameplay state and shared constants
├── habilidade_boss.py        # Umbra DQN and boss behavior
├── apolo_brain.py            # Apolo neural agent
├── *_helpers.py, utils.py    # shared runtime helpers
├── Sprites/                  # images, backgrounds, cards and UI sprites
├── Sounds/                   # music and sound effects
├── Texto/                    # fonts
├── Video/                    # video assets
├── saves/                    # local saves, config and neural memories
├── docs/                     # technical docs and lore notes
│   ├── STRUCTURE.md
│   └── lore/
├── scripts/                  # build and packaging automation
│   ├── build_dist.py
│   └── build_player.py
├── tools/                    # AI, telemetry and maintenance tools
│   ├── ai/
│   └── patches/
├── tests/                    # tests and small verification scripts
└── dist/                     # generated builds (ignored by git)
```

> The runtime files remain in the project root for now because the game still uses
> flat imports and root-relative asset paths such as `Sprites/...` and `Sounds/...`.
> See [`docs/STRUCTURE.md`](docs/STRUCTURE.md) for the migration plan.

### Key Files for AI Development

| File | Purpose |
|:---|:---|
| `habilidade_boss.py` | Complete DQN implementation for Umbra boss |
| `GAME5.py` | Apolo DQN agent implementation and training loop |
| `saves/*.pt` | PyTorch tensor weights (persistent neural network memory) |
| `saves/tendencias_umbra.json` | Bayesian statistical model of player behavior |
| `saves/historico_batalhas.json` | Training metrics and battle outcomes |
| `tools/ai/` | Training, telemetry and neural-memory maintenance scripts |

---

## 🚀 Installation & Setup

### 📦 For Players (No Python Required)

Download the pre-built executable:

> **[📥 Download — Ruptura Temporal v0.0.1](https://github.com/HenryMelo23/Ruptura_Temporal/releases/tag/v0.0.1)**

### 🐍 For Developers

**Prerequisites:**
- Python 3.14+ (recommended for latest PyTorch compatibility)
- pip (package manager)
- CUDA-capable GPU (optional, for accelerated training)

**Installation:**

```bash
# 1. Clone the repository
git clone https://github.com/HenryMelo23/Ruptura_Temporal.git
cd Ruptura_Temporal

# 2. Install dependencies
pip install pygame torch torchvision pyperclip requests

# For CUDA support (GPU acceleration):
# pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# 3. Run the game
python Ruptura_Temporal.py
```

**Verify PyTorch Installation:**

```python
import torch
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"Device: {torch.device('cuda' if torch.cuda.is_available() else 'cpu')}")
```

---

## 🎮 Training the AI

The DQN agents train automatically during gameplay. Here's how to observe and influence the learning process:

### Observing Training

**Real-Time Telemetry Dashboard:**

The game includes a Flask-based telemetry server that exposes AI decision-making in real-time:

```bash
# The server starts automatically when you run GAME5.py
# Access the dashboard at: http://localhost:5000/dados
```

Auxiliary AI tools now live in `tools/ai`:

```bash
python tools/ai/grafico_evolucao.py
python tools/ai/painel_neural.py
python tools/ai/treino_laser_apolo.py
```

**Telemetry Data:**
```json
{
  "estado_atual": "DQN_TENSOR",
  "decisao_ativa": ["INTERCEPTAR", "ATAQUE"],
  "bias_bayesiano": [0.23, -0.15],
  "rede_completa": {
    "DQN_TENSOR": {
      "FUGIR": 0.234,
      "INTERCEPTAR": 0.891,
      "ORBITAR": 0.456,
      "ATAQUE": 0.723,
      ...
    }
  }
}
```

### Training Configuration

**Modify Exploration Rate:**

```python
# In habilidade_boss.py or GAME5.py
self.exploracao = 0.20  # 20% random actions (default)
# Increase for more exploration: 0.30 (30%)
# Decrease for more exploitation: 0.10 (10%)
```

**Adjust Learning Rate:**

```python
# In agent initialization
self.optimizer = optim.Adam(self.q_network.parameters(), lr=0.001)
# Faster learning: lr=0.01
# More stable learning: lr=0.0001
```

**Reset Training:**

```bash
# Delete weight files to start fresh
rm saves/apolo_memoria_dqn.pt
rm saves/memoria_umbra_dqn.pt
rm saves/tendencias_umbra.json
rm saves/historico_batalhas.json
```

### Training Metrics

After each battle, metrics are saved to `saves/historico_batalhas.json`:

```json
{
  "geracao": 42,
  "duracao": 127.5,
  "vencedor": "Apolo",
  "hp_restante": 450,
  "exploracao_umbra": 0.20,
  "habilidade_dominante": "INTERCEPTAR",
  "precisao_bayesiana": 67.3
}
```

**Key Metrics:**
- **geracao**: Battle number (training iteration)
- **duracao**: Battle duration in seconds
- **vencedor**: Winner (Apolo or Umbra)
- **hp_restante**: Remaining HP of winner
- **exploracao_umbra**: Umbra's exploration rate
- **habilidade_dominante**: Most-used ability by Umbra
- **precisao_bayesiana**: Bayesian prediction accuracy (%)

---

## 🎹 Controls

### ⌨️ Keyboard + Mouse

| Action | Key |
|:---|:---:|
| Move | `W` `A` `S` `D` |
| Attack | `Left Mouse Button` |
| Dash / Teleport | `SHIFT` |
| Open Card Shop | `Q` |
| Purchase in Shop | `E` |
| Summon Boss | `R` |
| Pause / Back | `ESC` |

### 🎮 Gamepad Controller

| Action | Button |
|:---|:---:|
| Move | `Left Analog Stick` |
| Attack | `X` |
| Teleport | `A` |
| Open Shop | `Y` |
| Back | `RB` |

> Keyboard controls can be customized in the **Configuration** menu.

---

## 🗺️ Roadmap

### Completed ✅
- [x] Phase 1 — Ruined Beach
- [x] Phase 2 — Frozen Kingdom
- [x] Phase 3 — Cultist Rat Dimension
- [x] Phase 4 — Scientist Frog World
- [x] Áureas System (4 passives)
- [x] Card Shop / Upgrades
- [x] LAN Cooperative Mode (Host & Join)
- [x] Automatic UDP discovery
- [x] Interactive tutorial
- [x] Gamepad support
- [x] **DQN-based adaptive AI** (Umbra & Apolo)
- [x] **PyTorch neural network integration**
- [x] **Bayesian player behavior prediction**
- [x] **Real-time telemetry dashboard**

### In Progress 🚧
- [ ] Phase 5 — Final Boss Arena (full DQN showcase)
- [ ] Difficulty balancing (Phase 2)
- [ ] Network stability improvements
- [ ] Additional Áureas and cards

### Future Enhancements 🔮
- [ ] Experience Replay Buffer (improve training stability)
- [ ] Target Network (reduce Q-value overestimation)
- [ ] Prioritized Experience Replay
- [ ] Dueling DQN architecture
- [ ] Multi-agent cooperative DQN (player + companion)
- [ ] Curriculum learning (progressive difficulty)
- [ ] Transfer learning between phases
- [ ] Visualization tools for neural network activations

---

## 🤝 Contributing

Contributions are what make the open-source community an amazing place to learn and create. Any contributions are **greatly appreciated**!

### How to Contribute

1. **Fork** the project
2. Create your **Feature Branch** (`git checkout -b feature/AmazingFeature`)
3. **Commit** your changes (`git commit -m 'Add AmazingFeature'`)
4. **Push** to the branch (`git push origin feature/AmazingFeature`)
5. Open a **Pull Request**

### 💡 Contribution Ideas

**AI/ML Improvements:**
- 🧠 Implement Experience Replay Buffer
- 🎯 Add Target Network for stable training
- 📊 Create visualization tools for Q-values
- 🔬 Experiment with different network architectures
- 📈 Implement training metrics dashboard

**Game Development:**
- 🐛 Report bugs and issues
- 🎨 Create new sprites or improve existing ones
- ⚖️ Suggest balance adjustments
- 🌐 Test LAN mode on different networks
- 📝 Improve documentation

**Research & Analysis:**
- 📊 Analyze training convergence patterns
- 🔍 Study emergent behaviors in AI agents
- 📉 Profile performance bottlenecks
- 🧪 Design controlled experiments for AI evaluation

---

## 📜 License

Distributed under the **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International** license.

| Permission | Status |
|:---|:---:|
| Personal and educational use | ✅ Allowed |
| Modification and redistribution | ✅ With attribution and same license |
| Commercial use | ❌ Prohibited without authorization |

See [LICENSE.txt](LICENSE.txt) for more information.

---

## 🎓 Academic Context

This project was developed as part of coursework at **Universidade de Brasília (UnB)**:

- **Computer Networks Course**: LAN multiplayer implementation demonstrating TCP/UDP socket programming
- **Artificial Intelligence**: Practical application of Deep Reinforcement Learning in game AI
- **Software Engineering**: Full-stack game development with modular architecture

The project serves as both an educational resource and a technical demonstration of modern AI techniques in interactive systems.

---

## 📚 Further Reading

### Deep Reinforcement Learning Resources

- **[Playing Atari with Deep Reinforcement Learning](https://arxiv.org/abs/1312.5602)** — Original DQN paper by DeepMind
- **[Human-level control through deep reinforcement learning](https://www.nature.com/articles/nature14236)** — Nature publication on DQN
- **[PyTorch DQN Tutorial](https://pytorch.org/tutorials/intermediate/reinforcement_q_learning.html)** — Official PyTorch RL tutorial
- **[Spinning Up in Deep RL](https://spinningup.openai.com/)** — OpenAI's educational resource

### Project Documentation

- **[LOGICA_IA_UMBRA_E_APOLO_DQN_FUNDACIONAL.md](LOGICA_IA_UMBRA_E_APOLO_DQN_FUNDACIONAL.md)** — Comprehensive AI architecture documentation (Portuguese)
- **[Wiki](https://github.com/HenryMelo23/Ruptura_Temporal/wiki)** — Additional guides and tutorials

---

## 💜 Acknowledgments

Special thanks to:

- **Universidade de Brasília (UnB)** for providing the academic environment that enabled this project
- The **PyTorch** and **Pygame** communities for excellent documentation and support
- **DeepMind** for pioneering DQN research that inspired this implementation
- Everyone who has played, tested, and provided feedback on the game

This project started as a personal gift but grew into a comprehensive demonstration of AI in games. I hope it inspires and educates those interested in game development and machine learning.

---

## 📬 Contact

<div align="center">

[![Instagram](https://img.shields.io/badge/Instagram-@henri__meelo-E4405F?style=for-the-badge&logo=instagram&logoColor=white)](https://www.instagram.com/henri_meelo/)
[![YouTube](https://img.shields.io/badge/YouTube-HMeloI-FF0000?style=for-the-badge&logo=youtube&logoColor=white)](https://www.youtube.com/@HMeloI)
[![GitHub](https://img.shields.io/badge/GitHub-HenryMelo23-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/HenryMelo23)

**Project Link:** [https://github.com/HenryMelo23/Ruptura_Temporal](https://github.com/HenryMelo23/Ruptura_Temporal)

</div>

---

<div align="center">

### 🧠 Built with Neural Networks. Powered by PyTorch. Inspired by DeepMind.

**Ruptura Temporal** — Where Deep Reinforcement Learning meets real-time gameplay.

`Current Version: Beta (Offline + LAN + DQN)`

</div>




