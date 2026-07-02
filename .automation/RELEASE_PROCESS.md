# Release Process

## Version Bumping

This project follows Semantic Versioning:

- MAJOR (1.x.x): Breaking API changes
- MINOR (x.1.x): New features, backward compatible
- PATCH (x.x.1): Bug fixes and minor improvements

## Release Steps

1. Ensure all tests pass: python -m pytest tests/ -v
2. Update version in src/mempalace_evolve/__init__.py
3. Update CHANGELOG.md
4. Commit with message: chore: release vX.Y.Z
5. Tag: git tag vX.Y.Z
6. Push: git push origin master --tags
7. GitHub Release will be auto-created by CI
