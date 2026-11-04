# Release operations

[Project documentation](README.md) · [Development](development.md)

All development uses main. `project.version` in pyproject.toml is the only version
input; uv.lock, package metadata and tags derive from it. A user-authorized version
increase requests publication. Ordinary main changes run CI without a new release.
Only canonical X.Y.Z versions are supported: patch for fixes/packaging, minor for
features and incompatible changes while the project is 0.x. No CI version-writing
bot, release branches or generated development versions are used.

## Make a release

```sh
uv version --bump patch --no-sync
# Include pyproject.toml and uv.lock with the intended changes, then push main.
```

[main.yml](../../.github/workflows/main.yml) checks macOS/Python 3.12: both renderers,
pandas, zero skipped tests, Ruff, strict mypy, executable docs and local links. It
builds wheel/sdist, checks metadata/assets and README rendering, and installs the
wheel in fresh core-only and full-extra environments outside the source tree.
Linux jobs publish already verified files; they do not establish Linux PDF support.

After checks, a version without a tag becomes a candidate if it exceeds previous
release versions. A tag belonging to another commit means CI-only for the same
version; a lower version fails. A tag at this exact commit permits recovery.
Selection is not based on the previous-commit diff, so batched pushes and fixes to
an untagged failed candidate can still release. Existing v0.2.0 stays git-only.

The workflow serializes main push runs and does not cancel an active run. Manual
PyPI recovery uses a separate concurrency group so it cannot displace a pending
version bump; simultaneous identical PyPI uploads are handled by uv. GitHub may
replace a pending run with a newer push: a superseded, unreserved intermediate
version is not guaranteed publication. A version is reserved once tagged.

## Artifact identity and publication

The workflow builds once, removes only uv’s generated dist/.gitignore, and writes release.json containing version, full commit
SHA and SHA-256 checksums for exactly one wheel and one sdist. A retained Actions
artifact lets a full rerun reuse the original bytes. An annotated vX.Y.Z tag points
to that tested SHA; it is never moved. A draft GitHub Release receives the assets,
with existing files compared rather than replaced. The draft becomes public only
when all three assets are present. The README badge tracks the public Release.

PyPI downloads the completed GitHub Release, checks its manifest and that the tag
belongs to main history, and uploads only its wheel/sdist using uv Trusted Publishing.
It does not build anything. Existing identical PyPI files are accepted on retry;
different bytes fail. Publishing to GitHub and PyPI is not an atomic transaction.
GitHub release assets remain the durable recovery copy after Actions artifacts expire.

## One-time PyPI setup

The default gate is off until the owner configures PyPI. GitHub releases work
independently and explicitly report that PyPI upload is disabled.

1. Sign in to a PyPI account with 2FA. Open [account Publishing](https://pypi.org/manage/account/publishing/).
2. Add a pending GitHub Trusted Publisher with these exact fields:

   | Field | Value |
   | --- | --- |
   | PyPI project name | cardreport |
   | Owner | arch7tect |
   | Repository | cardreport |
   | Workflow name | main.yml |
   | Environment name | pypi |

   A pending publisher does not reserve the package name. If PyPI rejects the name,
   resolve ownership/name before enabling uploads; never publish under an unrelated name.
3. GitHub needs an environment named pypi restricted to the main branch, without a
   per-release reviewer requirement. The workflow grants id-token: write only to
   the PyPI job. No PyPI API token or password is stored in the repository.
4. After the owner confirms setup, set the repository Actions variable
   `PYPI_PUBLISH_ENABLED=true`. Before that it is false/unset.
5. Publish an already verified release with the manual workflow below, or let the
   next version bump publish automatically. Verify the installed package/version
   from PyPI after the first upload. Only then update the README/quickstart to say
   PyPI is available and add its version badge.

The owner only needs to configure PyPI and confirm completion. GitHub environment,
variable and workflow setup can be performed with existing repository administration
access. See [PyPI's pending-publisher guide](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/).

## Retry or publish to PyPI after setup

- Before tagging: fix the source and push; the unreleased version can still be used.
- After tagging: use **Re-run failed jobs** on the original run. A full rerun also
  reuses its retained Actions artifact; it never silently rebuilds a reserved version.
- An interrupted GitHub upload leaves a draft. Retry uploads only missing files and
  verifies existing bytes. A failed upload can leave an incomplete draft asset;
  after verifying that the release is still a draft and the complete original bundle
  is retained, the maintainer may explicitly delete that exact incomplete asset and
  retry its upload. Never delete/replace published assets, or rebuild a reserved
  version to make checks pass. The automation itself never deletes assets.
- After GitHub succeeded but PyPI failed/was disabled: run **CI and release → Run
  workflow**, select main, and set pypi_tag to the existing version, e.g. v0.2.1:

  ```sh
  gh workflow run main.yml --repo arch7tect/cardreport --ref main -f pypi_tag=v0.2.1
  ```

  This path only publishes a completed GitHub Release. The PyPI setup gate still
  applies. It does not create a new tag/release or build a new distribution.
- If the original Actions artifact expired before the GitHub draft was completed,
  stop: do not rebuild or replace files under that reserved version. Recover the
  exact original bundle from a verified copy or release a new version. A completed
  GitHub Release can always supply the PyPI recovery path above.
- A released code defect requires a higher version. Rollback means consumers pin
  an older release; yanking a PyPI version is a separate explicit maintainer action.

GitHub permissions are separated: verification reads source/artifacts; the GitHub
release job writes release assets/tags; the PyPI job reads assets and obtains OIDC
credentials. Actions and uv are pinned. Update their pins deliberately and rerun checks.
Release notes are generated from GitHub history; version intent is never inferred
from commit-subject conventions. See [uv publishing behavior](https://docs.astral.sh/uv/guides/package/).


The version badge updates automatically. While PyPI setup is pending, the README
contains a pinned wheel URL as a reproducible installation example; update this
example on release if needed. Once PyPI is live, replace it with the unversioned
registry install command and retain uv.lock in consuming applications.
