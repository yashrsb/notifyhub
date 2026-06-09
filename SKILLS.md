Python Project Skills & Coding Standards
Core Principles
Write clean, maintainable, production-grade code.
Prioritize readability over cleverness.
Follow SOLID principles.
Keep functions small and focused.
Avoid premature optimization.
Prefer composition over inheritance.
Follow "Explicit is better than implicit."
Python Standards
Version
Use Python 3.12+
Use type hints everywhere.
Use dataclasses or Pydantic models when appropriate.

Example:

def get_user(user_id: str) -> User:
    ...
Formatting

Use:

black
isort
ruff

Rules:

Maximum line length: 100
Use double quotes
No unused imports
No wildcard imports

Forbidden:

from x import *