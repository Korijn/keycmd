# Contributing

keycmd is developed on [GitHub](https://github.com/Korijn/keycmd). Issues and pull requests are welcome.

This project uses [uv](https://docs.astral.sh/uv/) for dependency management, [ruff](https://docs.astral.sh/ruff/) for linting and formatting, and [ty](https://docs.astral.sh/ty/) for type checking.

## Getting set up

```bash
# create the virtual environment and install all dependencies
uv sync

# install the git hooks that run the checks below on every commit
uv run pre-commit install
```

## The checks

```bash
uv run ruff check --fix
uv run ruff format
uv run ty check
uv run pytest tests
```

CI runs all four, so the pre-commit hooks are the cheapest place to find out about them.

## Conventions

The `keycmd` package is fully annotated and ships a [PEP 561](https://peps.python.org/pep-0561/) `py.typed` marker, so the types are available to anything that imports it. Ruff's `ANN` rules keep it that way; the test suite is exempt. `ty` is configured for the oldest supported Python, so it catches typing features that are newer than `requires-python` allows.

### Startup time is a feature

keycmd sits in front of every command a user runs through it, so its own startup is latency the user pays each time. A handful of imports cost more than everything else in the package together, and none of them is needed on every run:

* `keyring` (and the backend it goes on to discover) — only once a credential is looked up
* `pprint` — only under `--verbose`
* `subprocess` — only on the Windows path, which cannot replace its own process

Those are imported inside the function that needs them, which keeps `import keycmd.cli` at roughly a third of what it would otherwise cost, and there is a test that fails if one of them wanders back up to module level. Reach for a lazy import when adding a dependency that most runs will not touch, and leave the rest at the top of the file where they belong.

## The documentation

This site is built with [MkDocs](https://www.mkdocs.org/) and [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/), from the markdown files under `docs/`.

```bash
# install the docs dependencies
uv sync --group docs

# serve the site locally, with live reload, on http://127.0.0.1:8000
uv run mkdocs serve

# build it into site/
uv run mkdocs build
```

Every push to `master` builds the site and deploys it to GitHub Pages.

The nav lives in `mkdocs.yml`; a new page has to be added there to show up. The README is deliberately short and points here, so new prose belongs on this site rather than in the README.
