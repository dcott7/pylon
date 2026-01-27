# Bears vs 49ers Example

This example demonstrates how to use Pylon to simulate NFL games between the Chicago Bears and San Francisco 49ers.

## Quick Start

```bash
cd examples/bears_49ers
python -m main
```

## What It Does

The example performs:

1. **Single Game Simulation**: Runs one game simulation with default settings
2. **Multi-Rep Simulation**: Runs 10 replications with different random seeds and persists results to a SQLite database

## Data Loading

The example loads team data from the example database (`data/football.db`):
- Team rosters (players with positions)
- Offensive formations and play calls
- Team identifiers

The `teams.py` module provides the team loading logic that queries the database and constructs `Team` domain objects with full rosters and playbooks.

## Output

After running, the example generates:

- **pylon.log**: Detailed log of simulation execution
- **pylon_sim.db**: SQLite database with:
  - Dimension tables: Teams, Athletes, Formations, Personnel, Plays, Playbooks
  - Fact tables: Experiments, Games (one per replication)
  - All relationships preserved for analysis
- **simulation_results.json**: Aggregate results and statistics

## Module Structure

- **main.py**: Entry point demonstrating single and multi-rep simulation
- **teams.py**: Loads Team objects from the example database
- **athletes.py**: Queries athletes/roster data and maps positions
- **plays.py**: Loads formations and play calls from the database

## Analyzing Results

Query the generated `pylon_sim.db` to analyze:

```sql
-- Find the experiment
SELECT * FROM experiments WHERE name LIKE '%Bears vs 49ers%';

-- Get all game results for an experiment
SELECT * FROM games WHERE experiment_id = '<experiment_id>';

-- Aggregate results
SELECT 
  home_team_id,
  COUNT(*) as total_games,
  SUM(CASE WHEN winner_id = home_team_id THEN 1 ELSE 0 END) as wins,
  AVG(home_score) as avg_home_score,
  AVG(away_score) as avg_away_score
FROM games
GROUP BY home_team_id;
```

## Customization

Modify `main.py` to:
- Change number of replications: `num_reps=100`
- Use different random seed: `base_seed=12345`
- Add custom user models via `user_models` parameter
- Override league rules: `rules=CustomRules()`
- Skip database persistence: `db_manager=None`
