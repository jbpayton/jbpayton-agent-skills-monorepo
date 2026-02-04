---
name: doc-templates
description: Documentation templates for software projects. Use when writing READMEs, PR descriptions, changelogs, API docs, or code comments. Provides copy-paste templates for common documentation needs.
license: Unlicense
metadata:
  author: jbpayton
  version: "0.1"
  parent: github.com/comet-ml/opik (documentation skill)
---

# Documentation Templates

Ready-to-use templates for common documentation tasks.

## When to Use

- Starting a new project README
- Writing a PR description
- Creating changelog entries
- Documenting an API
- Adding code comments

---

## README Template

```markdown
# Project Name

Brief one-line description.

## Installation

\`\`\`bash
pip install project-name
# or
npm install project-name
\`\`\`

## Quick Start

\`\`\`python
from project import something
result = something.do_thing()
\`\`\`

## Features

- Feature one
- Feature two
- Feature three

## Documentation

See [docs/](docs/) for full documentation.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
```

---

## PR Description Template

```markdown
## Summary
- What this PR does (bullet points)
- Why it's needed

## Changes
- `file.py` - Added X functionality
- `test_file.py` - Added tests for X

## Test Plan
- [ ] Unit tests pass
- [ ] Manual testing done
- [ ] Edge cases covered

## Screenshots (if UI change)
Before | After
-------|------
img    | img

## Related Issues
- Resolves #123
- Related to #456
```

---

## Changelog Entry Template

```markdown
## [VERSION] - YYYY-MM-DD

### Added
- New feature X (#123)
- Support for Y

### Changed
- Improved performance of Z
- Updated dependency A to v2.0

### Fixed
- Bug where X didn't work (#456)
- Memory leak in Y

### Removed
- Deprecated function Z

### Security
- Fixed vulnerability in X (CVE-XXXX-XXXX)

### Breaking Changes
- Renamed `old_func` to `new_func`
- Minimum Python version now 3.10
```

---

## API Documentation Template

```markdown
## `function_name(param1, param2, **kwargs)`

Brief description of what the function does.

### Parameters

| Name | Type | Default | Description |
|------|------|---------|-------------|
| param1 | str | required | What param1 does |
| param2 | int | 10 | What param2 does |
| **kwargs | dict | {} | Additional options |

### Returns

`ReturnType` - Description of return value

### Raises

- `ValueError` - When param1 is invalid
- `ConnectionError` - When server unreachable

### Example

\`\`\`python
result = function_name("hello", param2=5)
print(result)  # Output: ...
\`\`\`

### Notes

- Important behavior to know
- Edge cases handled
```

---

## Code Comment Templates

### Function/Method

```python
def function_name(param1: str, param2: int = 10) -> ReturnType:
    """Brief one-line summary.

    Longer description if needed. Explain the why,
    not just the what.

    Args:
        param1: What this parameter does.
        param2: What this parameter does. Defaults to 10.

    Returns:
        Description of what's returned.

    Raises:
        ValueError: When param1 is invalid.

    Example:
        >>> result = function_name("hello")
        >>> print(result)
        ...
    """
```

### Class

```python
class ClassName:
    """Brief one-line summary.

    Longer description explaining purpose and usage.

    Attributes:
        attr1: Description of attr1.
        attr2: Description of attr2.

    Example:
        >>> obj = ClassName(value)
        >>> obj.do_something()
    """
```

### Module

```python
"""Module brief description.

This module provides X functionality for Y purpose.

Example usage:
    from module import thing
    thing.do_stuff()

Typical usage patterns and important notes.
"""
```

---

## Style Guide

1. **User perspective** - Write from the user's viewpoint, not implementation details
2. **Concise** - Get to the point quickly
3. **Examples** - Show, don't just tell
4. **Consistent** - Use the same format throughout
5. **Scannable** - Use headers, bullets, tables

## When NOT to Document

- Self-explanatory code (`x = x + 1`)
- Implementation details that may change
- Temporary/debugging code
