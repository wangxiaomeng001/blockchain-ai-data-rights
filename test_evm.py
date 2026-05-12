"""
test_evm.py — 两个智能合约的真实 EVM 端到端测试
运行：
    python3.12 test_evm.py

覆盖：
  IdentityRegistry (6 项)
  DataRegistry    (8 项)
  ——————————————
  共 14 项
"""

import sys
from evm_backend import EVMBackend, Role, bytes32_of


_PASS, _FAIL = [], []


def check(cond, name):
    if cond:
        _PASS.append(name); print("  ✅", name)
    else:
        _FAIL.append(name); print("  ❌", name)


def run():
    print("=" * 70)
    print("  [SETUP] 编译 + 部署 IdentityRegistry + DataRegistry")
    print("=" * 70)
    be = EVMBackend()
    info = be.deploy_all()

    # ─── IdentityRegistry tests ───────────────────
    id_info = info["identity"]
    data_info = info["data"]
    check(id_info.contract_address.startswith("0x"), "identity: address valid")
    check(id_info.gas_used > 400_000, f"identity deploy gas {id_info.gas_used:,} in realistic range")
    check(data_info.contract_address.startswith("0x"), "data: address valid")
    check(data_info.gas_used > 500_000, f"data deploy gas {data_info.gas_used:,} in realistic range")

    print("\n[TEST 1] IdentityRegistry.register() 登记身份")
    r_id = be.register_identity(
        org_name="ACME AI Lab",
        role=Role.Provider,
        auth_material=b"auth-credential-acme-lab-2026",
        sender=be.accounts[1],
    )
    check(r_id["event"] is not None, "identity register: event emitted")
    check(50_000 < r_id["gasUsed"] < 400_000,
          f"identity register gas {r_id['gasUsed']:,} within [50k, 400k]")

    print("\n[TEST 2] IdentityRegistry.isActive() 身份激活查询")
    ok = be.is_identity_active(be.accounts[1])
    check(ok is True, "identity isActive: true after register")
    ok2 = be.is_identity_active(be.accounts[9])
    check(ok2 is False, "identity isActive: false for unregistered")

    print("\n[TEST 3] IdentityRegistry.getIdentity() 身份详情")
    id_obj = be.get_identity(be.accounts[1])
    check(id_obj.get("orgName") == "ACME AI Lab", "identity getIdentity: orgName correct")
    check(id_obj.get("role") == Role.Provider,   "identity getIdentity: role = Provider")
    check(id_obj.get("isActive") is True,        "identity getIdentity: active flag")

    print("\n[TEST 4] IdentityRegistry 重复登记应被 revert")
    try:
        be.register_identity(
            org_name="Duplicate Co",
            role=Role.Provider,
            auth_material=b"auth-credential-acme-lab-2026",  # 同 hash
            sender=be.accounts[2],
        )
        check(False, "identity dup: second registration should revert")
    except Exception:
        check(True, "identity dup: second registration reverted")

    print("\n[TEST 5] IdentityRegistry 多账户独立登记")
    r2 = be.register_identity(
        org_name="DataBoost Co",
        role=Role.Consumer,
        auth_material=b"auth-credential-databoost-2026",
        sender=be.accounts[2],
    )
    check(r2["wallet"] == be.accounts[2], "identity multi-account: different owner")
    all_ids = be.list_identities()
    check(len(all_ids) == 2, f"identity list_identities: {len(all_ids)} records (expected 2)")

    # ─── DataRegistry tests ───────────────────
    print("\n" + "=" * 70)
    print("  DataRegistry tests")
    print("=" * 70)

    print("\n[TEST 6] DataRegistry.register() 数据登记")
    r1 = be.register(b"dataset-mnist-subset", "image", "CC-BY-4.0",
                     sender=be.accounts[1])
    check(r1["event"] is not None, "data register: event emitted")
    check(r1["owner"] == be.accounts[1], "data register: owner matches sender")
    check(100_000 < r1["gasUsed"] < 500_000,
          f"data register gas {r1['gasUsed']:,} within [100k, 500k]")

    print("\n[TEST 7] DataRegistry.verify() 一致性校验（正确）")
    v1 = be.verify(r1["dataId"], b"dataset-mnist-subset")
    check(v1["passed"] is True, "verify: identical bytes pass")

    print("\n[TEST 8] DataRegistry.verify() 一致性校验（篡改）")
    v2 = be.verify(r1["dataId"], b"dataset-mnist-subset-tampered")
    check(v2["passed"] is False, "verify: 1 byte modified detected")

    print("\n[TEST 9] DataRegistry 重复数据登记应被 revert")
    try:
        be.register(b"dataset-mnist-subset", "image", "MIT", sender=be.accounts[2])
        check(False, "data dup: second registration should revert")
    except Exception:
        check(True, "data dup: second registration reverted")

    print("\n[TEST 10] DataRegistry.ownerOf()")
    o = be.owner_of(r1["dataId"])
    check(o is not None and o[0] == be.accounts[1], "ownerOf: returns correct owner")

    print("\n[TEST 11] DataRegistry.list_all()（扫事件）")
    be.register(b"dataset-2", "text", "MIT", sender=be.accounts[2])
    be.register(b"dataset-3", "tabular", "private", sender=be.accounts[2])
    all_ = be.list_all()
    check(len(all_) == 3, f"list_all: {len(all_)} records (expected 3)")

    # ─── 汇总 ───
    print("\n" + "=" * 70)
    print(f"  PASSED: {len(_PASS)}   FAILED: {len(_FAIL)}")
    print("=" * 70)

    # 打印关键 Gas 数据（会回写到论文）
    print("\n★ Gas 实测数据（用于论文表 4-2）：")
    print(f"  IdentityRegistry deploy:   {id_info.gas_used:>10,}")
    print(f"  IdentityRegistry register: {r_id['gasUsed']:>10,}")
    print(f"  DataRegistry     deploy:   {data_info.gas_used:>10,}")
    print(f"  DataRegistry     register: {r1['gasUsed']:>10,}")
    print(f"  DataRegistry     verify:   {v1['gasUsed']:>10,}")

    if _FAIL:
        for n in _FAIL: print("  ❌", n)
        sys.exit(1)


if __name__ == "__main__":
    run()
