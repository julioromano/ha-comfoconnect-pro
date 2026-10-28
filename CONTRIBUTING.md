# Contributing

Use [GitHub issues](https://github.com/julioromano/ha-comfoconnect-pro/issues) for bug reports and feature requests, and open pull requests against GitHub `main`.

For bug reports, include the Home Assistant version, integration version, actual ventilation model, selected model, installed accessories, unit and PRO firmware versions, steps to reproduce and expected versus observed behavior. Attach integration diagnostics when useful, after reviewing them for private information. For protocol or firmware changes, include results from the [hardware regression checklist](README.md#hardware-regression-checklist).

Q350, Q450, Q600, Flex 250 and Flex 350 use the shared manufacturer map. Physical validation currently covers Q600 only; identify simulated results as such. See the [register reference](docs/register-map.md) for source revisions, model restrictions and the unresolved Classic documentation. New capability exclusions or model additions need authoritative manufacturer evidence and behavior tests. Keep model definitions in the central `models.py` registry, enforce exclusions in entity creation, reads and writes, and update the register reference and both English string files together. Preserve existing Q600 and common entity identities and test model reconfiguration cleanup.

Keep changes focused, update documentation for user-visible changes and add regression tests for behavior changes. Run the checks in [Development](README.md#development) before requesting review. Changes must pass linting, typing, unit tests with at least 95% statement/branch coverage, simulated TCP tests, hassfest and HACS validation.

Maintainers review pull requests for correctness, Home Assistant compatibility and test coverage, then merge accepted changes on GitHub after the checks pass. See [MAINTAINING.md](MAINTAINING.md) for the development and release workflow.
