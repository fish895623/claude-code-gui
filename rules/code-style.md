# Code Style Rules

## Python Style
- Follow PEP 8 with Black formatting
- Use descriptive variable names
- Prefer f-strings for string formatting
- Group imports: standard library, third-party, local

## Type Hints
- Always use type hints for function signatures
- Use Optional[T] for nullable types
- Import types from typing module
- Use dataclasses for data structures

## Comments and Docstrings
- Write docstrings for all public methods
- Use triple quotes for docstrings
- Keep inline comments minimal and meaningful
- Update comments when code changes

## Error Messages
- Make error messages user-friendly
- Include context about what went wrong
- Suggest fixes when possible
- Log technical details separately

## Constants
- Define UI constants at module level
- Use UPPER_CASE for constant names
- Group related constants together