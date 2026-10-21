<!-- Managed by scripts/agents-blueprint. -->
<!-- Reapply with: scripts/agents-blueprint apply --repo <path> --blueprint <id> -->

<!-- BEGIN GENERATED -->
<!-- blueprint: backend-python -->

## Repository Baseline
- Keep changes scoped and reviewable.
- Prefer existing project conventions over introducing new patterns.
- Avoid adding dependencies unless necessary for the requested outcome.

## Change Workflow
- Run targeted checks relevant to changed files.
- Update tests when behavior changes.
- Call out follow-up work explicitly if not completed in this change.

## Testing Approach
- Prefer TDD whenever feasible: start by writing a failing test that defines the intended behavior, then implement to make it pass.
- Treat tests as executable documentation: prioritize clear, behavior-focused test cases that describe intended and allowed use cases first.
- If strict TDD is not practical (for example, legacy code or urgent fixes), add characterization or regression tests as early as possible and note the constraint.

## Coverage Expectations
- Always collect and publish coverage from unit tests in CI.
- Enforce a minimum unit-test coverage threshold (or ratcheting baseline) for merges.
- Integration-test coverage may be collected for visibility, but should not block merges by default.
- End-to-end tests should be evaluated by critical user-journey coverage, not line-percentage thresholds.

## Documentation Expectations
- Document behavior changes that affect teammates or users.
- Keep architecture and setup notes current when conventions change.

## Python Backend Defaults
- Prefer modern Python typing for new modules.
- Keep modules small and explicit at API boundaries.
- Favor established project tooling for formatting and linting.

## Preferred Tooling For New Projects
- Use the latest Python `3.14.x` release for new projects.
- Use `uv` for package and project management.
- Use `ruff` for formatting and linting.
- Use `basedpyright` for static type checking, using its `recommended` setting.
- Use `pytest` for running tests.
- Use a single `pyproject.toml` file for project configuration, including `ruff` settings.

## Testing Expectations
- Prefer pytest for unit and integration tests.
- Add tests for edge cases and error handling paths.
- Include regression tests for production issues.
<!-- END GENERATED -->

## Local Notes (Manual)

- Add repository-specific notes here. This section is preserved across re-apply operations.
