"""Install a release asset after checking its GitHub-published SHA-256 digest."""

import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import subprocess
import tarfile
import tempfile
from urllib.request import Request, urlopen
import zipfile


REPOSITORY = "common-repo/common-repo"


def fetch(url, token=""):
    headers = {"User-Agent": "setup-common-repo"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(url, headers=headers), timeout=60) as response:
        return response.read()


def targets(system, machine):
    arch = {"AMD64": "x86_64", "amd64": "x86_64", "arm64": "aarch64"}.get(
        machine, machine
    )
    supported = {
        ("Linux", "x86_64"): ["x86_64-unknown-linux-musl", "x86_64-unknown-linux-gnu"],
        ("Linux", "aarch64"): ["aarch64-unknown-linux-gnu"],
        ("Darwin", "aarch64"): ["aarch64-apple-darwin"],
        ("Windows", "x86_64"): ["x86_64-pc-windows-msvc"],
    }
    if (system, arch) not in supported:
        raise ValueError(f"No prebuilt binary for {system}/{arch}")
    return supported[system, arch]


def install(version, directory, system=None, machine=None, token="", fetcher=fetch):
    system = system or platform.system()
    candidates = targets(system, machine or platform.machine())
    if version != "latest" and not re.fullmatch(r"v?\d+\.\d+\.\d+(?:[-+][\w.-]+)?", version):
        raise ValueError("Expected latest or a release version such as v0.38.4")
    requested = version if version.startswith("v") else f"v{version}"
    endpoint = "latest" if version == "latest" else f"tags/{requested}"
    release = json.loads(fetcher(f"https://api.github.com/repos/{REPOSITORY}/releases/{endpoint}", token))
    tag = release["tag_name"]
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:[-+][\w.-]+)?", tag):
        raise ValueError("Release has an invalid version tag")
    if version != "latest" and tag != requested:
        raise ValueError("Release version does not match the requested version")
    extension = ".zip" if system == "Windows" else ".tar.gz"
    assets = {asset["name"]: asset for asset in release["assets"]}
    asset = next((assets.get(f"common-repo-{tag}-{target}{extension}")
                  for target in candidates if f"common-repo-{tag}-{target}{extension}" in assets), None)
    if asset is None:
        raise ValueError("Release has no asset for this platform")
    digest = asset.get("digest") or ""
    if not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest):
        raise ValueError("Release asset lacks a valid SHA-256 digest; refusing to install")
    # The API token is never sent to the asset host or its redirect targets.
    archive = fetcher(f"https://github.com/{REPOSITORY}/releases/download/{tag}/{asset['name']}")
    if hashlib.sha256(archive).hexdigest() != digest.split(":", 1)[1].lower():
        raise ValueError("Release asset SHA-256 mismatch; refusing to install")
    binary = "common-repo.exe" if system == "Windows" else "common-repo"
    # Read only the binary; never extract archive paths, links or other files.
    if system == "Windows":
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            members = [m for m in bundle.namelist() if PurePosixPath(m).name == binary]
            if len(members) != 1:
                raise ValueError("Expected exactly one common-repo executable")
            payload = bundle.read(members[0])
    else:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
            members = [m for m in bundle.getmembers() if m.isfile() and PurePosixPath(m.name).name == binary]
            if len(members) != 1:
                raise ValueError("Expected exactly one common-repo executable")
            payload = bundle.extractfile(members[0]).read()
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    # Verify everything before replacing a previous install. Copy the alias too
    # so Windows needs no symlink privileges and old symlinks are not followed.
    for name in (binary, "cr.exe" if system == "Windows" else "cr"):
        with tempfile.NamedTemporaryFile(dir=directory, delete=False) as staging:
            staging.write(payload)
        staged = Path(staging.name)
        try:
            staged.chmod(0o755)
            staged.replace(directory / name)
        finally:
            staged.unlink(missing_ok=True)
    return tag


if __name__ == "__main__":
    directory = Path.home() / ".local/bin"
    tag = install(os.environ.get("VERSION") or "latest", directory,
                  token=os.environ.get("GITHUB_TOKEN", ""))
    executable = directory / ("common-repo.exe" if platform.system() == "Windows" else "common-repo")
    version = subprocess.check_output([str(executable), "--version"], text=True).strip().split()[1]
    if version != tag.removeprefix("v"):
        raise ValueError("Installed binary version does not match the requested release")
    if os.environ.get("GITHUB_PATH"):
        with open(os.environ["GITHUB_PATH"], "a", encoding="utf-8") as output:
            output.write(f"{directory}\n")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write(f"version={version}\npath={executable}\n")
    print(f"Installed common-repo {tag} (SHA-256 verified)")
