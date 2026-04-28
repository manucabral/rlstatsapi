# Contributing

Thanks for contributing.

## Quick setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
# source .venv/bin/activate

pip install -e .
```
## Code style and checks
Run formatting and linting before opening a PR:

```bash
python -m black .
python -m pylint src examples
```


## Pull requests
Please include:

- A short summary of what changed
- Why the change is needed
- Any manual verification steps
- Keep pull requests focused and small when possible.

## Security
If you find a vulnerability, follow the process in SECURITY.md.
