# Development Rules

## Package Management
- Use `uv` as the Python package manager
- Install dependencies: `uv sync`
- Run commands: `uv run <command>`
- Add new dependencies: `uv add <package>`

## Code Quality
- Format all `.py` files with `black` before committing
- Check type errors: `pyright --outputjson`
- Parse errors using array slicing to get first 5 errors
- Never use `type: ignore` - always fix the actual type issues

## Development Workflow
- Ultra-think: Consider all edge cases and implications
- Write comprehensive docstrings for all public methods
- Use type hints for all function parameters and return values