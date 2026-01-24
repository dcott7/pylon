# **Pylon — A Modular, Model‑Driven American Football Simulation**


If you enjoy helping shape a project from the ground up — especially one focused on football analytics, modeling, and operations research — this is a great time to get involved.

Pylon is a fully modular, decision‑agnostic American football simulation engine designed for **operations research**, **analytics**, and **experimentation**.  
Unlike traditional football sims, Pylon does **not** decide anything on its own.  
Every decision — from playcalling to player selection to yardage gained — is made by **models** supplied by the user or by the default model library.

Pylon’s job is simple:

> **Simulate the consequences of decisions, not make them.**

This makes Pylon ideal for:

- evaluating playcalling strategies  
- testing 4th‑down decision models  
- simulating personnel packages  
- running Monte Carlo experiments  
- training reinforcement learning agents  
- comparing coaching philosophies  
- exploring “what‑if” scenarios  

Pylon is built to be **transparent**, **extensible**, and **research‑friendly**.

---

## ⭐ Why Pylon Exists

Most football simulations mix *decision logic* with *game mechanics*, making it impossible to isolate the effect of a strategy.  
Pylon takes the opposite approach:

### **The simulation engine never chooses anything.**

Instead:

- The engine asks models what to do  
- Models return decisions  
- The engine applies those decisions to the game state  
- Snapshots and records are created for analysis  
- The engine moves to the next event  

This separation mirrors how operations research models are built:

- **State transition function** (Pylon)  
- **Decision function** (user‑supplied models)  

This architecture allows researchers to:

- swap out a single model (e.g., playcalling)  
- keep everything else constant  
- measure the impact cleanly  

Pylon is a *laboratory* for football strategy.

---

## ⭐ Core Principles

### **1. Decision‑Agnostic Simulation**
Pylon never decides:

- which play to call  
- which players take the field  
- how many yards a play gains  
- whether a pass is complete  
- how long a play takes  
- whether a kick is good  

All of these come from models.

### **2. User‑Defined or Default Models**
Every decision point is backed by a model:

- Offensive playcall model  
- Defensive playcall model  
- Player assignment models  
- Yardage models  
- Clock runoff models  
- Timeout models  
- Coin toss model  
- Kick/receive choice model  
- Special teams models  

Users can:

- use the default models  
- override specific models  
- replace the entire model registry  
- plug in ML models, heuristics, or rule‑based logic  

### **3. Snapshot‑Driven Architecture**
Every play, drive, and game produces:

- a **Snapshot** (immutable state at a moment in time)  
- an **ExecutionData** (raw model outputs)  
- a **Record** (finalized, validated, replayable event)  

This makes Pylon:

- fully replayable  
- fully auditable  
- ideal for analytics pipelines  

### **4. League‑Agnostic Rules**
LeagueRules defines:

- quarter length  
- scoring values  
- kickoff rules  
- drive‑ending conditions  
- overtime rules  

The engine applies decisions returned by LeagueRules, but LeagueRules never mutates state directly.

---

## ⭐ High‑Level Architecture

```
User Models  →  ModelRegistry  →  GameEngine
                                   │
                                   ▼
                           GameStateUpdater
                                   │
                                   ▼
    ┌──────────────┬──────────────┬──────────────┐
    │ PlayRecord    │ DriveRecord  │ GameRecord   │
    └──────────────┴──────────────┴──────────────┘
```

### **GameEngine**
Orchestrates the simulation loop.

### **GameState**
Live, authoritative state (clock, scoreboard, possession).

### **GameStateUpdater**
Applies model outputs and rule decisions to mutate state.

### **LeagueRules**
Decides what *should* happen (kickoffs, extra points, drive endings).

### **ModelRegistry**
Stores all decision models.

### **Records & Snapshots**
Immutable, replayable history of the simulation.

---

## ⭐ Example: How a Play Is Simulated

1. Engine asks the offensive playcall model for a play  
2. Engine asks player‑assignment models who is on the field  
3. Engine asks yardage models for outcomes  
4. Engine asks clock models for time elapsed  
5. Engine builds a PlayExecutionData  
6. GameStateUpdater applies the results  
7. A PlayRecord is finalized and added to the DriveRecord  
8. LeagueRules decides if the drive should end  

The engine itself never chooses anything.

---

## ⭐ Running Experiments

Because Pylon is model‑driven, you can:

### **Swap out the offensive playcaller**
```python
models.register_model(MyAggressivePlaycaller(), override=True)
```

### **Run 1,000 simulated games**
```python
for _ in range(10000):
    engine = PylonEngine(home, away, models=my_models)
    engine.run()
```

### **Test a reinforcement learning agent**
Your RL agent becomes the playcall model.

### **Compare strategies**
- baseline vs. aggressive 4th‑down  
- run‑heavy vs. pass‑heavy  
- man vs. zone defensive models  
- different personnel usage  

Pylon is built for this.

---

## ⭐ Installation

TBD

---

## ⭐ Contributing

Pylon is designed to be a community‑driven project.  
We welcome contributions in:

- model development  
- league rule implementations  
- documentation  
- analytics tooling  
- testing  
- performance improvements  

---

## ⭐ Roadmap

- Full NFLRules implementation  
- NCAA and CFL rule sets  
- Penalty engine  
- Weather models  
- Reinforcement learning examples  
- Visualization tools  
- Play‑by‑play export formats  
- Real‑world data integration  

---

## ⭐ License

MIT

# Disclaimer
Pylon is currently under active construction.
Major components are being refactored, and several systems are incomplete or temporarily unstable.
The architecture is solidifying, but the simulation is not yet fully functional.