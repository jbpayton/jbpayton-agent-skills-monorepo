---
name: ascii-banner
description: Generate ASCII art text banners. Use when you want to make output stand out, create headers, or add visual flair to terminal output.
license: Unlicense
metadata:
  author: jbpayton
  version: "0.1"
---

# ASCII Banner

Generate eye-catching ASCII art text banners.

## When to Use

- Make important output stand out
- Create section headers in terminal output
- Add visual flair to scripts or logs
- Generate banners for README files

## Usage

```bash
python scripts/banner.py "Hello World"
python scripts/banner.py "SUCCESS" --style block
python scripts/banner.py "ERROR" --style shadow
```

## Examples

**Input:**
```bash
python scripts/banner.py "Hi"
```

**Output:**
```
 _   _   _
| | | | (_)
| |_| |  _
|  _  | | |
|_| |_| |_|
```

**Input:**
```bash
python scripts/banner.py "OK" --style block
```

**Output:**
```
 â–ˆâ–ˆâ–ˆâ–ˆ  â–ˆ   â–ˆ
â–ˆ    â–ˆ â–ˆ  â–ˆ
â–ˆ    â–ˆ â–ˆâ–ˆâ–ˆ
â–ˆ    â–ˆ â–ˆ  â–ˆ
 â–ˆâ–ˆâ–ˆâ–ˆ  â–ˆ   â–ˆ
```

## Options

| Flag | Effect |
|------|--------|
| `--style` | Banner style: `standard` (default), `block`, `shadow` |
| `--width` | Max width before wrapping (default: 80) |

## Requirements

- Python 3.8+
- No external dependencies

## Notes

- Supports uppercase letters, numbers, and basic punctuation
- Unknown characters are rendered as spaces
- Output is always uppercase for consistency
