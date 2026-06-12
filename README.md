# parthivrmenon.github.io

Build the assets for my Github Pages website.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Build

```bash
python build.py
```

Output is written to the `docs/` directory, which is the source for GitHub Pages (`main` branch → `/docs`).
