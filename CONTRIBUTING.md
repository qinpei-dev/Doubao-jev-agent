# Contributing

Contributions are welcome, especially new skills, MCP examples, and documentation improvements.

## Add a skill

1. Create a skill class in `src/skills/` that inherits from `BaseSkill` in `src/skills/base.py`. Define its `name`, `description`, and `execute(input)` method.
2. Register an instance in `create_default_registry()` in `src/skills/registry.py`.
3. Add a runnable example under `examples/` and describe how to run it.
4. Add tests under `tests/` for the new skill and its routing or execution behavior.

Run the suite before opening a pull request:

```bash
python -m pytest
```
