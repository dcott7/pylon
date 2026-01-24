# `domain/` — Core Football Domain Models

The `domain/` folder contains the fundamental football concepts used throughout the simulation. These classes are intentionally simple, immutable, and free of simulation logic. They define **what** exists in the football world, not **how** the simulation behaves.

This folder is the foundation for:
- roster construction
- formation and personnel validation
- playbook design
- league rule definitions
- model inputs and outputs

If you're building new models, adding new rules, or extending the simulation, this is where the core vocabulary lives.

## 🏈 Athlete & Position System (`athlete.py`)
### Athlete
A simple domain object representing a player on a team roster.

Each athlete has:
- `uid` — unique identifier
- `first_name`, `last_name`
- `position` — an `AthletePositionEnum` value

Athletes are selected by user models to participate in plays.

### AthletePositionEnum
A comprehensive enumeration of football positions, including:
- specific positions (QB, LT, CB, FS, etc.)
- generic grouping positions (SKILL, OLINE, DB, EDGE, etc.)
- special teams positions (K, P, LS, KR)

These grouping positions enable flexible personnel logic.

### PositionTree
A hierarchical structure describing parent/child relationships between positions.

This enables:
- formation validation
- personnel grouping (11, 12, 21, nickel, dime, etc.)
- fallback logic (e.g., WR → SKILL → OFFENSE)
- model queries like “is WR a SKILL player?”

This tree is central to how the simulation understands football roles.

## 🧩 Team (`team.py`)
The `Team` domain object represents a football team and contains:
- team identity (name, uid)
- offensive and defensive playbooks
- roster of `Athlete` objects

Teams do **not** contain simulation logic. They simply hold the data needed by the engine and models.

## 📐 Formations, Personnel, Play Calls, and Playbooks (`plays.py`)
This module defines the structural components of football strategy.

### Formation
Describes how players are aligned on the field.
- Formations can be **abstract** (parents) or **concrete** (subformations).
- Concrete formations must define exactly 11 positions.
- Formations are independent of personnel packages.

Examples:
- Shotgun
- Trips Right
- Bunch Left

### PersonnelPackage
Describes *who* is on the field, not *where* they line up.

Examples:
- 11 personnel (1 RB, 1 TE, 3 WR)
- 12 personnel (1 RB, 2 TE, 2 WR)
- Nickel (5 DBs)

Personnel packages are used by selection models to choose athletes.

### PlayCall
A template for a play that can be executed during a game.

A PlayCall includes:
- name
- play type (run, pass, punt, FG, etc.)
- formation
- personnel package
- offensive or defensive side
- optional tags and description

PlayCalls are validated at creation time to ensure:
- formation positions match the play side
- personnel package can satisfy formation requirements

### Playbook
A collection of PlayCalls.

Playbooks support:
- lookup by tag
- lookup by play type
- iteration and selection by user models

## 🏛️ League Rules (`rules/`)
The `rules/` folder defines the **rulebook** for a football league.

### LeagueRules (abstract base class)
Defines the interface for league‑specific behavior:
- how games start
- how halves start
- when drives end
- when games end
- how scoring works
- what transitions (kickoffs, extra points) should occur

**LeagueRules should only *decide*, not mutate.** GameStateUpdater applies the decisions.

Concrete implementations (e.g., NFLRules, NCAARules) override these methods.

### KickoffSetup / ExtraPointSetup
Simple configuration objects describing special transitions.

These are returned by LeagueRules and consumed by GameStateUpdater.

## 🧠 How These Domain Models Fit Together
Athlete → Team → Playbook → PlayCall → Formation/Personnel → LeagueRules

These domain objects are used by:
- the GameEngine
- user‑defined models
- the state machine (GameState, DriveRecord, PlayRecord)

## 🤝 Contributing
If you want to extend the domain layer:
- Add new positions → update `AthletePositionEnum` and `PositionTree`
- Add new formations → create new `Formation` objects
- Add new personnel packages → define new `PersonnelPackage` instances
- Add new play types → extend `PlayTypeEnum`
- Add new league rules → subclass `LeagueRules`

All domain objects should remain:
- simple
- immutable
- free of simulation logic

This keeps the architecture clean and predictable.