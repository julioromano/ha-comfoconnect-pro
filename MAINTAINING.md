# Maintaining and releasing

[julioromano/ha-comfoconnect-pro on GitHub](https://github.com/julioromano/ha-comfoconnect-pro) is the source of truth for code, issues, pull requests and releases. Merge changes on GitHub after review and successful checks. See [CONTRIBUTING.md](CONTRIBUTING.md) for development and review expectations.

## Repository settings

Keep the repository public, enable issues and Actions, set its description to "Home Assistant integration for Zehnder ComfoConnect PRO Modbus TCP" and add the topics `home-assistant`, `hacs`, `zehnder`, `comfoconnect-pro` and `modbus`. Keep HACS validation enabled without ignores; repository settings are part of validation.

Protect `main` with required pull requests and the checks **Lint, types and unit coverage**, **Simulated Modbus TCP**, **Home Assistant metadata** and **HACS repository validation**. Prevent force pushes and deletion of `main`.

## Development

Use GitHub as `origin`. Create feature branches from the latest `origin/main`, push them to GitHub and open pull requests against `main`. Merge accepted pull requests on GitHub once the checks pass, then update local `main` with `git pull --ff-only origin main`.

## Releases

1. Update `version` in both `pyproject.toml` and `custom_components/comfoconnect_pro/manifest.json`. Keep `hacs.json` and `MIN_HA_VERSION` synchronized if the minimum Home Assistant version changes. Describe user-visible changes in the release notes.
2. Merge the version update through a GitHub pull request and wait for CI and HACS validation to pass on the resulting `main` commit.
3. From a clean checkout of that tested commit, create an annotated tag matching the version and publish that tag to GitHub. For the initial `0.1.0` release:

   ```sh
   git tag -a v0.1.0 -m "v0.1.0"
   git push origin refs/tags/v0.1.0:refs/tags/v0.1.0
   ```

4. Create a GitHub Release from the existing tag, documenting changes, the minimum Home Assistant version, supported device and known limitations. The ComfoAir Q 600 is at the moment the only supported device and has been tested with a physical ComfoConnect PRO gateway. Tags and released versions are immutable; ship corrections as a new patch version.
5. Verify installation or upgrade through HACS using the released version. Use the standard repository layout; no custom ZIP asset or `zip_release` setting is needed.

HACS uses [GitHub Releases for release-based versioning](https://hacs.xyz/docs/publish/start/#versions); pushing a tag alone does not publish a release. Distribute through HACS custom repositories initially. Consider default-directory submission after gaining experience maintaining public releases.

## Ongoing maintenance

Handle bugs and feature requests on GitHub, and link fixes to the relevant issues. Review Home Assistant compatibility and dependency updates through focused changes, run the full checks and publish fixes as patch releases. Preserve the existing unit coverage gate and separate TCP integration tests.

The HACS workflow runs on GitHub on pushes, pull requests, weekly and on manual dispatch, with read-only permissions and PR comments disabled. Its action reference uses the latest stable release available when added; review upstream action releases during dependency maintenance.
