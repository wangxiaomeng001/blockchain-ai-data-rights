"""
test_registry.py — 数据确权服务的功能与安全性测试
运行：
    cd wang-yan-project-code
    pytest test_registry.py -v
或：
    python test_registry.py   （内置轻量 runner，不依赖 pytest）
"""

from __future__ import annotations

import sys
import traceback

from blockchain import Blockchain
from registry import RegistryService, sha256_bytes, sha256_file


# ──────────────────────────────────────────
# 工具：轻量 runner（不装 pytest 也能跑）
# ──────────────────────────────────────────
_PASSED = []
_FAILED = []


def _check(cond: bool, name: str):
    if cond:
        _PASSED.append(name)
        print(f"  ✅ {name}")
    else:
        _FAILED.append(name)
        print(f"  ❌ {name}")


def _run(test_fn):
    name = test_fn.__name__
    print(f"\n[TEST] {name}")
    try:
        test_fn()
    except AssertionError as e:
        _FAILED.append(name)
        print(f"  ❌ {name} — assertion failed: {e}")
    except Exception:
        _FAILED.append(name)
        print(f"  ❌ {name} — unexpected error:")
        traceback.print_exc()


# ──────────────────────────────────────────
# 1. 基础功能
# ──────────────────────────────────────────
def test_register_and_owner_of():
    svc = RegistryService()
    rec = svc.register(owner="0xAlice", data_bytes=b"dataset-A",
                       data_type="text", license="MIT")
    _check(rec.owner == "0xAlice", "register: owner recorded")
    _check(rec.data_hash == sha256_bytes(b"dataset-A"), "register: sha256 indicator correct")
    _check(rec.ipfs_cid.startswith("Qm"), "register: mock CID has Qm prefix")

    owner, ts = svc.owner_of(rec.data_id)
    _check(owner == "0xAlice", "owner_of: returns correct owner")
    _check(ts > 0, "owner_of: timestamp positive")


def test_verify_integrity_pass():
    svc = RegistryService()
    rec = svc.register(owner="0xAlice", data_bytes=b"model-weights-v1")
    passed = svc.verify(rec.data_id, b"model-weights-v1")
    _check(passed is True, "verify: identical bytes pass")


def test_verify_integrity_fail():
    svc = RegistryService()
    rec = svc.register(owner="0xAlice", data_bytes=b"model-weights-v1")

    # 改动任意一字节
    passed = svc.verify(rec.data_id, b"model-weights-v2")
    _check(passed is False, "verify: modified 1 byte detected")


def test_duplicate_registration_rejected():
    svc = RegistryService()
    svc.register(owner="0xAlice", data_bytes=b"same-data")
    try:
        svc.register(owner="0xBob", data_bytes=b"same-data")
        _check(False, "duplicate: second registration should raise")
    except ValueError:
        _check(True, "duplicate: second registration raises ValueError")


def test_verify_unknown_dataid():
    svc = RegistryService()
    passed = svc.verify("nonexistent_id_123", b"whatever")
    _check(passed is False, "verify: unknown dataId returns False")


# ──────────────────────────────────────────
# 2. 权限
# ──────────────────────────────────────────
def test_deactivate_by_owner_ok():
    svc = RegistryService()
    rec = svc.register(owner="0xAlice", data_bytes=b"to-deactivate")
    ok = svc.deactivate(rec.data_id, caller="0xAlice")
    _check(ok, "deactivate: owner can deactivate")
    _check(svc.records[rec.data_id].is_active is False, "deactivate: isActive flipped")


def test_deactivate_by_other_rejected():
    svc = RegistryService()
    rec = svc.register(owner="0xAlice", data_bytes=b"protected")
    try:
        svc.deactivate(rec.data_id, caller="0xMallory")
        _check(False, "deactivate: non-owner should raise")
    except PermissionError:
        _check(True, "deactivate: non-owner raises PermissionError")


# ──────────────────────────────────────────
# 3. 链完整性
# ──────────────────────────────────────────
def test_chain_integrity_after_registrations():
    svc = RegistryService()
    for i in range(20):
        svc.register(owner=f"0xUser{i%3}", data_bytes=f"data-{i}".encode())
    svc.mine()
    svc.mine()
    _check(svc.chain.is_chain_valid(), "chain: still valid after 20 registrations")
    _check(svc.chain.height >= 1, "chain: height increased")


# ──────────────────────────────────────────
# 4. 雪崩效应（一字节变动 → 哈希完全不同）
# ──────────────────────────────────────────
def test_sha256_avalanche():
    h1 = sha256_bytes(b"A" * 1024)
    h2 = sha256_bytes(b"A" * 1023 + b"B")
    # 统计两个 hex 字符串不同字符的比例
    diff = sum(1 for a, b in zip(h1, h2) if a != b) / len(h1)
    _check(diff > 0.4, f"sha256: avalanche ratio {diff:.2%} (>40%)")


# ──────────────────────────────────────────
# 5. list / stats
# ──────────────────────────────────────────
def test_list_by_owner():
    svc = RegistryService()
    svc.register(owner="0xA", data_bytes=b"a1")
    svc.register(owner="0xA", data_bytes=b"a2")
    svc.register(owner="0xB", data_bytes=b"b1")
    _check(len(svc.list_by_owner("0xA")) == 2, "list_by_owner: Alice has 2")
    _check(len(svc.list_by_owner("0xB")) == 1, "list_by_owner: Bob has 1")
    _check(svc.stats()["total_registered"] == 3, "stats: total correct")


# ──────────────────────────────────────────
# main
# ──────────────────────────────────────────
def main():
    tests = [
        test_register_and_owner_of,
        test_verify_integrity_pass,
        test_verify_integrity_fail,
        test_duplicate_registration_rejected,
        test_verify_unknown_dataid,
        test_deactivate_by_owner_ok,
        test_deactivate_by_other_rejected,
        test_chain_integrity_after_registrations,
        test_sha256_avalanche,
        test_list_by_owner,
    ]
    for t in tests:
        _run(t)

    print("\n" + "=" * 60)
    print(f"  PASSED: {len(_PASSED)}   FAILED: {len(_FAILED)}")
    print("=" * 60)
    if _FAILED:
        print("\nFailed tests:")
        for n in _FAILED:
            print("  -", n)
        sys.exit(1)


if __name__ == "__main__":
    main()
