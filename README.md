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

## License

AGPL-3.0
