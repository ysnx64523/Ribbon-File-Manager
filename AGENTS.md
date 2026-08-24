# AGENTS.md — development conventions

These are the project's coding standards. Follow them for every change. They are
lightly enforced and reviewed, not auto-formatted.

## Stack

- Python 3.14 (developed/tested), 3.8+ compatible. GTK3 (3.24) via PyGObject.
- UI built with GtkBuilder (`resources/ui/*.glade`); strings through gettext `_()`.
- No GPL code allowed (Apache-2.0 project; GTK/PyGObject are LGPL — fine).

## Code style rules

### 1. Prefer `@dataclass` — no `dict[str, Any]`

Use a typed `@dataclass(frozen=True)` for any structured data you pass around.
Do **not** use `dict[str, Any]` / `Mapping[str, Any]` / loose dicts to carry
state:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class MountInfo:
    name: str
    path: Optional[str]
    volume: object
```

If a mapping is genuinely needed, type it precisely (e.g.
`dict[str, str]`), never `Any`.

### 2. Full type annotations — no bare `Any`

Every function must annotate its parameters and return type.

- If a value is **constrained** to a small set of types, use `Union[...]`
  — do **not** use `Any`.
- If an argument is **optional**, it must be `Optional[T]` (equivalently
  `T | None`), not an untyped default with `= None`.

```python
from typing import Optional, Union

def resolve(path: str, *, follow: bool = True) -> Optional[str]: ...

def format_size(size: Union[int, float]) -> str: ...
```

`Any` is only acceptable where the type truly cannot be expressed (rare). If you
wrote `Any`, add a comment explaining why.

### 3. Full Google-style docstrings

Every public (and most private) function/class/method must have a docstring that
documents:

- **what** it does,
- **Args**: each parameter, with types,
- **Returns**: the return type and meaning,
- **Raises**: every exception it can raise, with the trigger condition.

```python
def chmod(path: str, mode: int) -> tuple[bool, str]:
    """Change file permissions, escalating via pkexec when needed.

    Args:
        path: Absolute filesystem path to change.
        mode: New octal mode (e.g. ``0o755``), 0..0o777.

    Returns:
        Tuple of ``(ok, message)``; ``message`` is translated and safe to show.

    Raises:
        OSError: If the path cannot be statted.
        ValueError: If ``mode`` is outside the valid range.
    """
```

## Verification

Before finishing a change:

```sh
python -m unittest discover -s tests -v     # tests
flake8 src tests                            # lint (see .flake8)
python tools/gen_po.py                      # refresh catalogs after new strings
python tools/gen_index.py                   # refresh the code index (INDEX.md)
```

Add `# noqa` only with a concrete reason; prefer fixing the underlying issue.
