# Contributing to MemPalace Evolve

We love your input! We want to make contributing to MemPalace Evolve as easy and transparent as possible.

## Development Process

1. Fork the repo and create your branch from `master`.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Issue a pull request!

## Code Style

This project uses [ruff](https://github.com/astral-sh/ruff) for code formatting and linting.

```bash
pip install -e ".[dev]"
ruff check src/
```

## Testing

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v
```

## Pull Request Process

1. Update the `README.md` with details of changes if needed.
2. Update the `docs/` with any new features or API changes.
3. The PR will be merged once you have the sign-off of at least one maintainer.

## Any contributions you make will be under the MIT Software License

When you submit code changes, your submissions are understood to be under the same [MIT License](LICENSE) that covers the project.

## Report bugs using GitHub Issues

We use GitHub Issues to track public bugs. Report a bug by [opening a new issue](https://github.com/a2328275243/mempalace-evolve/issues/new).

## Write bug reports with detail, background, and sample code

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce (be specific: what Python version, what OS)
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

## License

By contributing, you agree that your contributions will be licensed under its MIT License.
