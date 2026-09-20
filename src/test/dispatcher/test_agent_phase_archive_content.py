"""Content-authoritative archive stability at the packaging boundary."""
import json
import os
from types import SimpleNamespace
import zipfile

import pytest
from agent_phase import archive, archive_snapshot


@pytest.mark.parametrize("change", ["touch", "rewrite", "replace", "bytes", "mode", "add", "remove", "symlink"])
def test_selected_state_stability(tmp_path, monkeypatch, change):
    source = tmp_path / "run"
    source.mkdir()
    for name in archive_snapshot.CORE:
        (source / name).write_bytes(b"{}")
    state = source / "state.json"
    initial_mode = state.stat().st_mode
    real = zipfile.ZipFile.testzip
    def during_packaging(bundle):
        result = real(bundle)
        if change == "touch":
            info = state.stat()
            os.utime(state, ns=(info.st_atime_ns, info.st_mtime_ns + 1000000))
        elif change == "rewrite":
            state.write_bytes(b"{}")
        elif change == "replace":
            replacement = source / "replacement"
            replacement.write_bytes(b"{}")
            replacement.chmod(initial_mode)
            replacement.replace(state)
        elif change == "bytes":
            state.write_bytes(b"[]")
        elif change == "mode":
            state.chmod(0o400)
        elif change == "add":
            (source / "added").write_bytes(b"x")
        elif change == "remove":
            state.unlink()
        elif change == "symlink":
            state.unlink()
            state.symlink_to(tmp_path / "never-read")
        return result
    monkeypatch.setattr(zipfile.ZipFile, "testzip", during_packaging)
    directory = SimpleNamespace(path=source, leaf="run", archive_path=tmp_path / "run.zip",
                                archive_temporary_path=tmp_path / "run.tmp")
    categories = {"bytes": "content_changed", "mode": "mode_or_type_changed",
                  "add": "membership_changed", "remove": "membership_changed",
                  "symlink": "mode_or_type_changed"}
    if change in categories:
        with pytest.raises(archive.ArchiveError) as caught:
            archive.create(directory)
        assert caught.value.code == "RUN_ARCHIVE_CHANGED"
        assert caught.value.verification[-1]["category"] == categories[change]
        assert not directory.archive_path.exists()
    else:
        archive.create(directory)
        receipt = json.loads(archive.receipt_path(directory.archive_path).read_bytes())
        changes = receipt["verification"]
        assert changes == [{"category": "metadata_only_changed", "path": "state.json",
                            "same_content_replacement": change == "replace"}]
        assert receipt["selected_bytes"] == 8
