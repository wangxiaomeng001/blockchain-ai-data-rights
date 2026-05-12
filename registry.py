"""
registry.py — 数据确权业务逻辑层
对齐 contracts/DataRegistry.sol 的接口设计，但在 Python 仿真环境中执行。
提供：
  - RegistryService.register()
  - RegistryService.verify()
  - RegistryService.owner_of()
  - RegistryService.list_all()
  - sha256_file() / sha256_bytes()  文件指纹工具
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

from blockchain import Blockchain, Transaction


# ──────────────────────────────────────────
# 哈希工具
# ──────────────────────────────────────────
def sha256_bytes(data: bytes) -> str:
    """对字节内容计算 SHA-256 指纹"""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str, chunk_size: int = 65536) -> str:
    """流式计算文件 SHA-256，适合大文件不占内存"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def mock_cid(data_hash: str) -> str:
    """基于数据哈希生成一个与 IPFS CID 等价的模拟 CID (Qm... 前缀)"""
    # IPFS CID v0 形如 Qm + 44 字符 base58；此处仿真只保证可识别
    digest = hashlib.sha256(("cid-" + data_hash).encode()).hexdigest()
    return "Qm" + digest[:44]


# ──────────────────────────────────────────
# 数据记录
# ──────────────────────────────────────────
@dataclass
class DataRecord:
    data_id: str
    owner: str
    data_hash: str
    ipfs_cid: str
    data_type: str
    license: str
    timestamp: float
    is_active: bool = True

    def to_dict(self) -> Dict:
        return asdict(self)


# ──────────────────────────────────────────
# 注册中心服务
# ──────────────────────────────────────────
class RegistryService:
    """
    数据确权服务，对齐 DataRegistry.sol 的三个核心方法。

    使用方式：
        chain = Blockchain()
        svc   = RegistryService(chain)
        rec   = svc.register(owner="0xAlice", data_bytes=b"hello", data_type="text", license="MIT")
        ok    = svc.verify(rec.data_id, b"hello")          # True
        ok    = svc.verify(rec.data_id, b"hello-changed")  # False
    """

    def __init__(self, chain: Optional[Blockchain] = None):
        self.chain = chain or Blockchain()
        self.records: Dict[str, DataRecord]  = {}   # data_id -> record
        self.hash_to_id: Dict[str, str]      = {}   # data_hash -> data_id
        self.events: List[Dict]              = []   # 链上事件日志（仿真）

    # ── register ──────────────────────────
    def register(
        self,
        owner: str,
        data_bytes: bytes,
        data_type: str = "unknown",
        license: str = "private",
        data_id: Optional[str] = None,
    ) -> DataRecord:
        data_hash = sha256_bytes(data_bytes)

        if data_hash in self.hash_to_id:
            raise ValueError(
                f"data already registered as {self.hash_to_id[data_hash]}"
            )

        # 若未提供 data_id，则用 keccak-like 派生（这里用 SHA-256 简化）
        if data_id is None:
            salt = f"{owner}|{time.time_ns()}"
            data_id = hashlib.sha256((data_hash + salt).encode()).hexdigest()[:32]

        if data_id in self.records:
            raise ValueError(f"dataId {data_id} already exists")

        rec = DataRecord(
            data_id=data_id,
            owner=owner,
            data_hash=data_hash,
            ipfs_cid=mock_cid(data_hash),
            data_type=data_type,
            license=license,
            timestamp=time.time(),
            is_active=True,
        )

        self.records[data_id] = rec
        self.hash_to_id[data_hash] = data_id

        # 把确权记录打包成一笔"交易"上链（buyer 置空，模拟"登记"语义）
        tx = Transaction(
            seller=owner,
            buyer="0x0000000000000000000000000000000000000000",
            dataset_id=data_id,
            price=0.0,
            data_hash=data_hash,
        )
        self.chain.add_transaction(tx)

        # 追加事件日志
        self.events.append({
            "type": "DataRegistered",
            "data_id": data_id,
            "owner": owner,
            "data_hash": data_hash,
            "ipfs_cid": rec.ipfs_cid,
            "timestamp": rec.timestamp,
        })
        return rec

    # ── verify ────────────────────────────
    def verify(self, data_id: str, local_bytes: bytes, verifier: str = "0xGuest") -> bool:
        rec = self.records.get(data_id)
        if rec is None or not rec.is_active:
            self.events.append({
                "type": "DataVerified",
                "data_id": data_id, "verifier": verifier, "passed": False, "reason": "record_missing",
            })
            return False

        local_hash = sha256_bytes(local_bytes)
        passed = (local_hash == rec.data_hash)
        self.events.append({
            "type": "DataVerified",
            "data_id": data_id,
            "verifier": verifier,
            "passed": passed,
            "local_hash": local_hash,
            "chain_hash": rec.data_hash,
        })
        return passed

    # ── owner_of ─────────────────────────
    def owner_of(self, data_id: str) -> Optional[Tuple[str, float]]:
        rec = self.records.get(data_id)
        if rec is None:
            return None
        return rec.owner, rec.timestamp

    # ── deactivate ───────────────────────
    def deactivate(self, data_id: str, caller: str) -> bool:
        rec = self.records.get(data_id)
        if rec is None:
            return False
        if rec.owner != caller:
            raise PermissionError("caller is not owner")
        rec.is_active = False
        self.events.append({
            "type": "DataDeactivated",
            "data_id": data_id, "owner": caller,
        })
        return True

    # ── utilities ────────────────────────
    def list_all(self) -> List[DataRecord]:
        return list(self.records.values())

    def list_by_owner(self, owner: str) -> List[DataRecord]:
        return [r for r in self.records.values() if r.owner == owner]

    def mine(self):
        """把 pending 交易打包成区块"""
        if self.chain.pending_transactions:
            return self.chain.mine_block()
        return None

    def stats(self) -> Dict:
        return {
            "total_registered": len(self.records),
            "active": sum(1 for r in self.records.values() if r.is_active),
            "chain_height": self.chain.height,
            "chain_valid": self.chain.is_chain_valid(),
            "events": len(self.events),
        }


# ──────────────────────────────────────────
# CLI demo
# ──────────────────────────────────────────
def _cli_demo():
    svc = RegistryService()
    svc.chain.register_validator("validator_a", 10)
    svc.chain.register_validator("validator_b", 20)

    r1 = svc.register(owner="0xAlice", data_bytes=b"iris-dataset-v1",
                      data_type="tabular", license="CC-BY-4.0")
    print("[+] registered", r1.data_id, "cid=", r1.ipfs_cid)

    ok = svc.verify(r1.data_id, b"iris-dataset-v1")
    print("[+] verify original:", ok)

    bad = svc.verify(r1.data_id, b"iris-dataset-v1-tampered")
    print("[+] verify tampered:", bad)

    who = svc.owner_of(r1.data_id)
    print("[+] owner_of:", who)

    svc.mine()
    print("[+] chain stats:", json.dumps(svc.stats(), indent=2))


if __name__ == "__main__":
    _cli_demo()
