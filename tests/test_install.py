import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
import zipfile


spec = importlib.util.spec_from_file_location("installer", Path(__file__).parents[1] / "script/install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def fixture(self, target="x86_64-unknown-linux-musl", windows=False):
        stream = io.BytesIO()
        payload = b"verified executable fixture"
        binary = "common-repo.exe" if windows else "common-repo"
        if windows:
            with zipfile.ZipFile(stream, "w") as bundle:
                bundle.writestr(f"bin/{binary}", payload)
        else:
            with tarfile.open(fileobj=stream, mode="w:gz") as bundle:
                member = tarfile.TarInfo(f"bin/{binary}")
                member.size = len(payload)
                bundle.addfile(member, io.BytesIO(payload))
                other = tarfile.TarInfo("../../never-extract-this")
                other.size = 6
                bundle.addfile(other, io.BytesIO(b"unsafe"))
        archive = stream.getvalue()
        asset = {
            "name": f"common-repo-v0.38.4-{target}" + (".zip" if windows else ".tar.gz"),
            "digest": "sha256:" + hashlib.sha256(archive).hexdigest(),
        }
        release = {"tag_name": "v0.38.4", "assets": [asset]}
        requests = []

        def fetch(url, token=""):
            requests.append((url, token))
            return json.dumps(release).encode() if "api.github.com" in url else archive

        return payload, asset, release, requests, fetch

    def test_latest_checks_digest_installs_alias_and_scopes_token(self):
        payload, _, _, requests, fetch = self.fixture()
        with tempfile.TemporaryDirectory() as directory:
            installer.install("latest", directory, "Linux", "x86_64", "test-token", fetch)
            self.assertEqual((Path(directory) / "common-repo").read_bytes(), payload)
            self.assertEqual((Path(directory) / "cr").read_bytes(), payload)
            if os.name != "nt":
                self.assertTrue((Path(directory) / "common-repo").stat().st_mode & 0o100)
            self.assertEqual(len(list(Path(directory).iterdir())), 2)
        self.assertTrue(requests[0][0].endswith("/releases/latest"))
        self.assertEqual([token for _, token in requests], ["test-token", ""])
        self.assertFalse(any("install.sh" in url for url, _ in requests))

    def test_platforms_and_exact_version(self):
        for system, machine, target in [
            ("Linux", "arm64", "aarch64-unknown-linux-gnu"),
            ("Darwin", "arm64", "aarch64-apple-darwin"),
            ("Windows", "AMD64", "x86_64-pc-windows-msvc"),
        ]:
            with self.subTest(system=system):
                payload, _, _, requests, fetch = self.fixture(target, system == "Windows")
                with tempfile.TemporaryDirectory() as directory:
                    installer.install("0.38.4", directory, system, machine, fetcher=fetch)
                    name = "common-repo.exe" if system == "Windows" else "common-repo"
                    self.assertEqual((Path(directory) / name).read_bytes(), payload)
                self.assertTrue(requests[0][0].endswith("/releases/tags/v0.38.4"))

    def test_missing_or_mismatched_digest_keeps_old_install(self):
        for digest in [None, "sha256:invalid", "sha256:" + "0" * 64]:
            with self.subTest(digest=digest):
                _, asset, _, _, fetch = self.fixture()
                asset["digest"] = digest
                with tempfile.TemporaryDirectory() as directory:
                    binary = Path(directory) / "common-repo"
                    binary.write_bytes(b"old install")
                    with self.assertRaisesRegex(ValueError, "digest|mismatch"):
                        installer.install("v0.38.4", directory, "Linux", "x86_64", fetcher=fetch)
                    self.assertEqual(binary.read_bytes(), b"old install")

    def test_rejects_wrong_release_missing_platform_and_invalid_input(self):
        for kind in ["tag", "asset", "input", "platform"]:
            with self.subTest(kind=kind):
                _, _, release, _, fetch = self.fixture()
                if kind == "tag":
                    release["tag_name"] = "v0.38.3"
                if kind == "asset":
                    release["assets"] = []
                with tempfile.TemporaryDirectory() as directory:
                    with self.assertRaises(ValueError):
                        installer.install("../main" if kind == "input" else "v0.38.4",
                                          directory, "Darwin" if kind == "platform" else "Linux",
                                          "x86_64", fetcher=fetch)
                    self.assertEqual(list(Path(directory).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
