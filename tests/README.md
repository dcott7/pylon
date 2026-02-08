# Pylon Tests

Comprehensive test suite for the Pylon football simulation engine.

## Test Organization

The test suite is organized into layers matching the codebase architecture:

- **test_domain.py** - Domain layer: Team, Athlete, Playbook classes (10 tests)
- **test_state.py** - State layer: GameState, GameClock, Scoreboard, PossessionState (16 tests)
- **test_engine.py** - Engine layer: GameEngine, RNG, specialized engines (9 tests)
- **test_engines.py** - Drive and Play engines: DriveEngine, PlayEngine (18 tests)
- **test_domain_rules.py** - Domain rules: Formation, Personnel, PlayCall validation (30 tests)
- **test_database.py** - Database layer: Schema, repositories, persistence (11 tests)
- **test_integration.py** - Integration tests: Full simulation workflow (8 tests)
- **test_typed_model.py** - Model framework: TypedModel validation (5 tests)

## Running Tests

### Run all tests
```bash
uv run pytest tests/ -v
```

### Run specific test file
```bash
uv run pytest tests/test_domain.py -v
```

### Run specific test class
```bash
uv run pytest tests/test_domain.py::TestAthlete -v
```

### Run specific test
```bash
uv run pytest tests/test_domain.py::TestAthlete::test_create_athlete -v
```

### Run with coverage
```bash
uv run pytest tests/ --cov=src/pylon --cov-report=html
```

## Test Status

Currently **103 tests passing** across all layers. All tests are passing and API requirements are properly implemented:

✅ PlayCall requires formation and personnel_package parameters
✅ Database uses sqlite:// URL format  
✅ All state methods working correctly
✅ GameClock.time_remaining returns total game time remaining
✅ Engine integration tests validate drive and play execution
✅ Domain rules validation for formations, personnel, and play calls

## Test Coverage

The test suite covers:

✅ **Domain Models** (10 tests)
- Team and Athlete creation
- Roster management  
- Position filtering
- Formation and PersonnelPackage creation
- PlayCall creation (offensive, defensive, run plays)

✅ **State Management** (16 tests)
- GameState creation and lifecycle
- Scoreboard scoring methods
- GameClock quarter progression
- PossessionState tracking

✅ **Engine Components** (9 tests)
- RNG determinism with seeds
- GameEngine initialization and drive execution
- NFL rules constants
- Specialized engines (pass, run, punt, kickoff, etc.)

✅ **Engine & Records** (18 tests)
- DriveRecord state capture and end result enums
- PlayRecord scoring type tracking
- DriveEngine and PlayEngine instantiation
- Game state time and possession management
- Scoreboard and roster verification

✅ **Domain Rules** (30 tests)
- Formation validation (offensive/defensive, 11-player constraint)
- Formation hierarchy (parent/subformation)
- Personnel package constraints
- PlayCall validation with formation and personnel
- NFL rules enforcement (10-yard first down, 4 downs max, field dimensions)
- Team roster and position filtering
- Rule constraints and requirements

✅ **Database** (11 tests)
- Repository pattern and persistence
- ORM conversion for all dimension types
- Batch operations
- Formation and Play persistence
- Proper handling of shared dimensions

✅ **Integration** (8+ tests)
- SimulationRunner workflow  
- Database persistence across games
- Deterministic replay with seeds
- Full end-to-end game simulation

✅ **Model Framework** (5 tests)
- TypedModel validation and type checking
- Invalid return type rejection
- Abstract class enforcement

## Adding New Tests

Follow the existing patterns in test files:

1. Use pytest fixtures for common setup (like `db_manager`)
2. Create helper functions for complex object creation
3. Group related tests in classes
4. Use descriptive test names starting with `test_`
5. Include docstrings explaining what each test verifies

## Future Improvements

- Add tests for model execution and model registry
- Add tests for all edge cases in play execution
- Add tests for injury/fatigue mechanics if implemented
- Increase coverage of specific game scenarios (goal line, red zone, etc.)
- Add performance/benchmark tests
- Add tests for replay and video capture features
