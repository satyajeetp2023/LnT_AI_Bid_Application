import hashlib
import tempfile
from pathlib import Path

from app.storage.base import LocalSecureStorage


def main():
    payload=b"release-readiness-storage-persistence-check"
    expected=hashlib.sha256(payload).hexdigest()
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp)/"documents"
        first=LocalSecureStorage(root)
        relative=first.save(101,"evidence.txt",payload)
        assert relative=="101/evidence.txt"
        assert (root/relative).exists()

        # Recreate the provider to simulate an application process restart.
        second=LocalSecureStorage(root)
        restored=second.read(relative)
        assert hashlib.sha256(restored).hexdigest()==expected

        try:
            second.read("../outside.txt")
        except ValueError:
            pass
        else:
            raise AssertionError("path traversal must be rejected")

    print("storage durability and traversal smoke passed")


if __name__=="__main__":
    main()
