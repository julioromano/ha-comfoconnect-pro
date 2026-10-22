# Contributing

Use [GitHub issues](https://github.com/julioromano/ha-comfoconnect-pro/issues) for bug reports and feature requests, and open pull requests against GitHub `main`.

For bug reports, include the Home Assistant version, integration version, Q600 and PRO firmware versions, steps to reproduce and expected versus observed behavior. Attach integration diagnostics when useful, after reviewing them for private information. The integration is experimental; physical hardware results are especially useful for the [hardware acceptance checklist](README.md#hardware-acceptance-checklist).

Keep changes focused, update documentation for user-visible changes and add regression tests for behavior changes. Run the checks in [Development](README.md#development) before requesting review. Changes must pass linting, typing, unit tests with at least 95% statement/branch coverage, simulated TCP tests, hassfest and HACS validation.

Maintainers review pull requests for correctness, Home Assistant compatibility and test coverage, then merge accepted changes on GitHub after the checks pass. See [MAINTAINING.md](MAINTAINING.md) for the development and release workflow.
