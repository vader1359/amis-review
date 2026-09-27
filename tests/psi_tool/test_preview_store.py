"""Local saved selections remain explicit, role bound, and integrity checked."""

import json
import stat

import pytest
from web.preview_store import SourceStore, StoreError

from psi_tool.online_pipeline import SourceSnapshot


def snapshot(content=b"test", filename="test.xlsx"):
    return SourceSnapshot.from_bytes(filename, content)


def test_restart_and_private_permissions(tmp_path):
    root = tmp_path / "private"
    store = SourceStore(root)
    metadata = store.save_many({"purchase": snapshot()})
    restarted = SourceStore(root)
    assert restarted.list() == metadata
    assert restarted.resolve("purchase", metadata["purchase"]["id"]) == snapshot()
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    assert all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in root.iterdir())


def test_replacement_rejects_old_id_and_bounds_files(tmp_path):
    store = SourceStore(tmp_path)
    old = store.save_many({"target": snapshot()})["target"]["id"]
    fresh = store.save_many({"target": snapshot(b"new")})
    with pytest.raises(StoreError, match="SAVED_SOURCE_NOT_FOUND"):
        store.resolve("target", old)
    assert store.resolve("target", fresh["target"]["id"]).content == b"new"
    assert len(list(tmp_path.glob("*.xlsx"))) == 1
    store.clear("target")
    assert store.list() == {} and list(tmp_path.glob("*.xlsx")) == []


def test_role_binding_unknown_refs_and_traversal(tmp_path):
    store = SourceStore(tmp_path)
    saved = store.save_many({"purchase": snapshot()})["purchase"]
    for role, identifier in [
        ("target", saved["id"]),
        ("purchase", "../outside"),
        ("purchase", "f" * 32),
    ]:
        with pytest.raises(StoreError, match="SAVED_SOURCE_NOT_FOUND"):
            store.resolve(role, identifier)
    with pytest.raises(StoreError, match="SAVED_SOURCE_ROLE_INVALID"):
        store.save_many({"crm": snapshot()})
    with pytest.raises(StoreError, match="SAVED_SOURCE_ROLE_INVALID"):
        store.resolve("crm", saved["id"])


def test_corruption_and_symlinks_are_rejected(tmp_path):
    store = SourceStore(tmp_path)
    saved = store.save_many({"target": snapshot()})["target"]
    blob = tmp_path / (saved["sha256"] + ".xlsx")
    blob.write_bytes(b"wrong")
    with pytest.raises(StoreError, match="SAVED_SOURCE_INTEGRITY_FAILED"):
        store.resolve("target", saved["id"])
    blob.unlink()
    outside = tmp_path / "outside"
    outside.write_bytes(b"test")
    blob.symlink_to(outside)
    with pytest.raises(StoreError, match="SAVED_SOURCE_INTEGRITY_FAILED"):
        store.resolve("target", saved["id"])


def test_metadata_cannot_supply_paths(tmp_path):
    store = SourceStore(tmp_path)
    saved = store.save_many({"target": snapshot()})
    saved["target"]["sha256"] = "../../secret"
    (tmp_path / "active.json").write_text(json.dumps(saved))
    with pytest.raises(StoreError, match="SOURCE_STORE_INVALID"):
        store.list()


def test_same_blob_reused_by_two_roles_survives_clear(tmp_path):
    store = SourceStore(tmp_path)
    metadata = store.save_many({"purchase": snapshot(), "target": snapshot()})
    store.clear("purchase")
    assert store.resolve("target", metadata["target"]["id"]) == snapshot()


def test_save_missing_seeds_only_absent_roles(tmp_path):
    store = SourceStore(tmp_path)
    initial = store.save_many({"purchase": snapshot()})["purchase"]
    current = store.save_missing(
        {"purchase": snapshot(b"replacement"), "target": snapshot(b"target")}
    )
    assert current["purchase"] == initial
    assert store.resolve("purchase", initial["id"]) == snapshot()
    assert store.resolve("target", current["target"]["id"]).content == b"target"
    assert len(list(tmp_path.glob("*.xlsx"))) == 2
