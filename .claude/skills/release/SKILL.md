---
name: release
description: Bump the version and publish aladhan-mcp to PyPI. Usage: /release <patch|minor|major|X.Y.Z>
disable-model-invocation: true
---

Release `aladhan-mcp` as version bump `$ARGUMENTS` (default: patch).

1. Make sure you're on `main` with a clean working tree and up to date with `origin`. Stop if any of these is false.
2. Run `/verify`. Stop if anything fails.
3. Compute the new version from `version` in `pyproject.toml` and update it there. Show the old and new versions.
4. Commit with the message `Bump version to X.Y.Z`.
5. Build: `rm -rf dist && uv build`. Check that `dist/` contains exactly one sdist and one wheel for X.Y.Z.
6. **Ask for confirmation before publishing**, then run `uv publish`. The token comes from `UV_PUBLISH_TOKEN`; if it's unset, ask me rather than looking for credentials.
7. Create an annotated tag with `git tag -a vX.Y.Z -m "vX.Y.Z"` (`--follow-tags` skips lightweight tags), then push the commit and tag: `git push origin main --follow-tags`.
8. Report the PyPI URL: https://pypi.org/project/aladhan-mcp/X.Y.Z/
