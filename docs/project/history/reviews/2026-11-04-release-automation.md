# Release automation review

Date: 2026-11-04. Target: 0.2.1. The owner authorized main-only rolling releases on
version increases, GitHub Releases plus PyPI, a latest-release README badge, docs,
Claude review and push. PyPI account setup is still required before enabling uploads.

## Delivery

The [release guide](../../releases.md) defines the implemented contract and setup.
A pinned workflow verifies the exact commit on macOS/Python3.12, builds and checks
wheel/sdist, and creates an annotated tag and GitHub Release with a checksummed
manifest. Retained run artifacts prevent rebuilding on a full retry. Partial GitHub
uploads stay drafts; assets are compared, never replaced by automation. PyPI uses
OIDC and the exact completed GitHub assets. A manual dispatch recovers or initially
publishes an existing release after account setup. Package version lives only in
pyproject.toml; uv.lock is derived. No runtime/rendering implementation changed.

GitHub's pypi environment is configured for main only. PYPI_PUBLISH_ENABLED=false
until owner confirmation. GitHub Release publication works while the PyPI job is
disabled, and the job summary reports this state. No token was requested or stored.
README contains the latest-release badge and a reproducible wheel installation URL;
PyPI install availability is not claimed prematurely. User/project documentation and
contributor authorization rules match the workflow.

## Reviews and fixes

The prior restricted Claude design review supported the scheme. Two further
restricted implementation reviews completed with exit0. The first identified:

- uv creates dist/.gitignore: remove only that generated file before the exact-file
  freeze check. A real uv build/freeze/verify smoke confirms the correction.
- Manual PyPI recovery must not displace a pending main bump: separate concurrency
  groups, no cancellation of active runs.
- Incomplete draft assets can require explicit maintainer recovery; document the
  exact scope and retained-original requirement. Published assets remain immutable.
- Temporary wheel paths in installation commands are not reproducible: replace them
  with the versioned GitHub Release wheel URL in README/quickstart.
- Document no-skips and strict metadata checks alongside local verification commands.

The focused review found no remaining concrete blocker. It inspected the workflow,
release script and related installation/recovery docs, and ran no commands. Hosted
CI and PyPI authentication were not independently exercised by the reviewer.

## Local verification

- Full suite:173 passed with zero skips before three additional recovery tests;
  focused release suite after those additions:21 passed.
- Ruff lint/format, strict mypy (30 files), actionlint and git diff checks passed.
- All36 executable Python documentation blocks and local Markdown targets passed;
  absolute README links to this repository are now checked against local files.
- Real uv build -> generated-file cleanup -> manifest freeze -> verify passed.
- Wheel/sdist assets, metadata, private-path exclusion and installed-wheel smoke
  passed, with core-only and all-extra environments and both reference PDF engines.
- Twine6.2.0 rejected the build backend's metadata2.5; pinned Twine7.0.0 passed both
  distributions. This is a tooling compatibility fix, not a relaxed check.

The first hosted run occurs after this commit is pushed; its job results and Release
assets provide the publication evidence. No hosted success or actual PyPI upload is
claimed by this pre-push review. PyPI setup/recovery instructions specify the remaining
owner action. No new Linux/Windows rendering support is claimed.


Before the first successful push, the owner created the pending PyPI publisher and
confirmed its details (environment field Any). The GitHub pypi environment remains
main-only; the publication gate was enabled. README/quickstart now use PyPI as the
primary install route, with both version badges and a pinned GitHub wheel alternative.
Their remote availability must be verified with the first actual publication.
GitHub rejected the initial push because the CLI OAuth grant lacked workflow scope;
no remote commit/tag/release was created by that rejected push. Access refresh was
requested from the owner; no credential values were requested or stored.


## Hosted publication outcome

After the owner refreshed GitHub CLI workflow access, commits 6764d45 and 5767581
were pushed. [Run 41816443293](https://github.com/arch7tect/cardreport/actions/runs/41816443293)
completed successfully: verification, GitHub Release and PyPI jobs all passed.
It ran176 tests with zero skips, strict mypy30files, Ruff,205 local links and36
executable docs blocks; installed-wheel core-only and full-extra smoke checks passed.

The workflow reserved v0.2.1 at `57675819ec2e193c2da14686f6778e1eb8ff22c6`,
created the [public GitHub Release](https://github.com/arch7tect/cardreport/releases/tag/v0.2.1)
and published [cardreport0.2.1 on PyPI](https://pypi.org/project/cardreport/0.2.1/).
Post-publication checks downloaded the GitHub bundle, verified its manifest/tag,
compared both wheel/sdist SHA-256 values to PyPI metadata, and installed the package
from PyPI in isolation to render HTML. All passed. README badges point to the public GitHub Release and PyPI; badge
caches can lag publication. PYPI_PUBLISH_ENABLED is true; initial account setup no longer blocks publishing.
Published artifacts remain unchanged by subsequent documentation commits.
