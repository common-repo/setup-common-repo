# setup-common-repo

GitHub Action to install the
[common-repo](https://github.com/common-repo/common-repo) binary.

## Usage

```yaml
steps:
  - uses: common-repo/setup-common-repo@v1
  - run: common-repo validate
```

### Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `version` | No | `latest` | Version to install (e.g., `v0.28.1`) or `latest` |

### Outputs

| Output | Description |
|--------|-------------|
| `version` | The installed version of common-repo |
| `path` | Path to the installed binary |

### Pin to a specific version

```yaml
steps:
  - uses: common-repo/setup-common-repo@v1
    with:
      version: v0.28.1
```

### Installation and integrity

Requires Python 3.9+ on the runner (included on GitHub-hosted runners).
The action downloads the selected release asset and verifies its SHA-256 digest
against GitHub's release metadata before installing or executing it. It does
not execute an installer from another branch. A missing digest, checksum
mismatch, unsupported platform or missing release asset fails the action.
Use an exact version and pin the action SHA for repeatable installation;
`latest` intentionally follows the newest release. GitHub's release publisher
and metadata remain the trust source; this is not signature verification.

Supported platforms: Linux x86_64/aarch64, macOS arm64, Windows x86_64.
The `cr` alias is installed alongside the binary. Older releases without a
GitHub-published SHA-256 digest cannot be installed.

Run offline regression tests with `python3 -m unittest discover -s tests -v`.
CI also installs both `latest` and a pinned release on each supported runner OS.

## License

AGPL-3.0
