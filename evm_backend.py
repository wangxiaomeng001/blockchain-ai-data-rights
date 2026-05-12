"""
evm_backend.py — 真实 EVM 后端
用 py-solc-x 编译 DataRegistry.sol 为真实字节码，
然后用 eth-tester + py-evm 在本地内存中跑一个真实 EVM，
用 web3.py 进行标准以太坊交互（eth_sendTransaction、事件订阅、Gas 消耗等）。

这不是"仿真"——它是一个完整的以太坊执行环境，
Solidity 合约在里面真实地编译、部署、调用、抛出 revert，
和部署到 Sepolia 主网的唯一区别只是"网络范围"。
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from solcx import compile_source, install_solc, set_solc_version
from web3 import Web3, EthereumTesterProvider
from eth_utils import to_bytes, to_hex


HERE = Path(__file__).parent
CONTRACT_PATH       = HERE / "contracts" / "DataRegistry.sol"
IDENTITY_SOL_PATH   = HERE / "contracts" / "IdentityRegistry.sol"


# ──────────────────────────────────────────
# 角色枚举（与 IdentityRegistry.sol 的 enum Role 对齐）
# ──────────────────────────────────────────
class Role:
    Undefined = 0
    Provider  = 1
    Consumer  = 2
    Both      = 3


# ──────────────────────────────────────────
# 工具
# ──────────────────────────────────────────
def _ensure_solc(version: str = "0.8.20"):
    try:
        set_solc_version(version)
    except Exception:
        install_solc(version)
        set_solc_version(version)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def bytes32_of(data: bytes) -> bytes:
    """压缩任意数据到 bytes32（用于 dataId / dataHash 字段）"""
    return hashlib.sha256(data).digest()  # 32 bytes


def mock_cid(data_hash: bytes | str) -> str:
    if isinstance(data_hash, bytes):
        data_hash = data_hash.hex()
    return "Qm" + hashlib.sha256(("cid-" + data_hash).encode()).hexdigest()[:44]


# ──────────────────────────────────────────
# 核心后端
# ──────────────────────────────────────────
@dataclass
class DeployInfo:
    contract_address: str
    deployer: str
    tx_hash: str
    gas_used: int
    abi: list


class EVMBackend:
    """
    在本地内存 EVM 中部署并交互 DataRegistry 合约。

    使用方式：
        be = EVMBackend()
        be.deploy()          # 编译 + 部署
        rec = be.register(data=b"hello", data_type="text", license="MIT")
        assert be.verify(rec["dataId"], b"hello")
    """

    def __init__(self):
        _ensure_solc("0.8.20")
        self.w3 = Web3(EthereumTesterProvider())
        self.accounts = self.w3.eth.accounts
        self.w3.eth.default_account = self.accounts[0]
        # DataRegistry
        self.contract = None
        self.deploy_info: Optional[DeployInfo] = None
        self.abi: list = []
        self.bytecode: str = ""
        # IdentityRegistry
        self.identity_contract = None
        self.identity_deploy_info: Optional[DeployInfo] = None
        self.identity_abi: list = []
        self.identity_bytecode: str = ""

    # ── 编译 ──
    def compile(self) -> Tuple[str, list]:
        source = CONTRACT_PATH.read_text()
        compiled = compile_source(source,
                                  output_values=["abi", "bin"],
                                  solc_version="0.8.20")
        # 取第一个 (唯一) 合约
        _, info = next(iter(compiled.items()))
        self.abi = info["abi"]
        self.bytecode = info["bin"]
        return self.bytecode, self.abi

    # ── 部署 DataRegistry ──
    def deploy(self) -> DeployInfo:
        if not self.bytecode:
            self.compile()
        Contract = self.w3.eth.contract(abi=self.abi, bytecode=self.bytecode)
        deployer = self.accounts[0]
        tx_hash = Contract.constructor().transact({"from": deployer})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        self.contract = self.w3.eth.contract(address=receipt.contractAddress,
                                             abi=self.abi)
        self.deploy_info = DeployInfo(
            contract_address=receipt.contractAddress,
            deployer=deployer,
            tx_hash=to_hex(tx_hash),
            gas_used=receipt.gasUsed,
            abi=self.abi,
        )
        return self.deploy_info

    # ── 编译 IdentityRegistry ──
    def compile_identity(self) -> Tuple[str, list]:
        source = IDENTITY_SOL_PATH.read_text()
        compiled = compile_source(source,
                                  output_values=["abi", "bin"],
                                  solc_version="0.8.20")
        _, info = next(iter(compiled.items()))
        self.identity_abi = info["abi"]
        self.identity_bytecode = info["bin"]
        return self.identity_bytecode, self.identity_abi

    # ── 部署 IdentityRegistry ──
    def deploy_identity(self) -> DeployInfo:
        if not self.identity_bytecode:
            self.compile_identity()
        Contract = self.w3.eth.contract(abi=self.identity_abi,
                                        bytecode=self.identity_bytecode)
        deployer = self.accounts[0]
        tx_hash = Contract.constructor().transact({"from": deployer})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        self.identity_contract = self.w3.eth.contract(
            address=receipt.contractAddress, abi=self.identity_abi)
        self.identity_deploy_info = DeployInfo(
            contract_address=receipt.contractAddress,
            deployer=deployer,
            tx_hash=to_hex(tx_hash),
            gas_used=receipt.gasUsed,
            abi=self.identity_abi,
        )
        return self.identity_deploy_info

    # ── 一键部署两个合约 ──
    def deploy_all(self) -> Dict:
        self.compile()
        self.compile_identity()
        self.deploy_identity()
        self.deploy()
        return {
            "identity": self.identity_deploy_info,
            "data":     self.deploy_info,
        }

    # ── IdentityRegistry 接口 ──
    def register_identity(self, org_name: str, role: int, auth_material: bytes,
                          sender: Optional[str] = None) -> Dict:
        assert self.identity_contract, "deploy_identity() first"
        sender = sender or self.accounts[0]
        auth_hash = bytes32_of(auth_material)
        tx_hash = self.identity_contract.functions.register(
            org_name, role, auth_hash
        ).transact({"from": sender})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        ev = self.identity_contract.events.IdentityRegistered().process_receipt(receipt)
        return {
            "wallet":    sender,
            "orgName":   org_name,
            "role":      role,
            "authHash":  to_hex(auth_hash),
            "gasUsed":   receipt.gasUsed,
            "txHash":    to_hex(tx_hash),
            "blockNumber": receipt.blockNumber,
            "event":     dict(ev[0].args) if ev else None,
        }

    def is_identity_active(self, wallet: str) -> bool:
        assert self.identity_contract, "deploy_identity() first"
        return self.identity_contract.functions.isActive(wallet).call()

    def get_identity(self, wallet: str) -> Dict:
        assert self.identity_contract, "deploy_identity() first"
        try:
            data = self.identity_contract.functions.getIdentity(wallet).call()
            return {
                "wallet":       data[0],
                "orgName":      data[1],
                "role":         data[2],
                "authHash":     to_hex(data[3]),
                "registeredAt": data[4],
                "updatedAt":    data[5],
                "isActive":     data[6],
            }
        except Exception:
            return {}

    def deactivate_identity(self, wallet: Optional[str] = None) -> Dict:
        assert self.identity_contract, "deploy_identity() first"
        wallet = wallet or self.accounts[0]
        tx_hash = self.identity_contract.functions.deactivate().transact({"from": wallet})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return {
            "wallet":  wallet,
            "gasUsed": receipt.gasUsed,
            "txHash":  to_hex(tx_hash),
        }

    def list_identities(self) -> List[Dict]:
        """扫描 IdentityRegistered 事件返回所有已登记身份"""
        assert self.identity_contract, "deploy_identity() first"
        logs = self.identity_contract.events.IdentityRegistered().get_logs(from_block=0)
        out = []
        for lg in logs:
            args = lg.args
            out.append({
                "wallet":    args["wallet"],
                "orgName":   args["orgName"],
                "role":      args["role"],
                "timestamp": args["timestamp"],
                "blockNumber": lg.blockNumber,
                "txHash":    to_hex(lg.transactionHash),
            })
        return out

    # ── register ──
    def register(
        self,
        data: bytes,
        data_type: str = "unknown",
        license: str = "private",
        sender: Optional[str] = None,
    ) -> Dict:
        assert self.contract, "deploy() first"
        sender = sender or self.accounts[0]

        data_hash = bytes32_of(data)                          # bytes32
        # data_id 由 sender + data_hash + nonce 派生（使用区块号做 nonce）
        salt = f"{sender}|{self.w3.eth.block_number}".encode()
        data_id = hashlib.sha256(salt + data_hash).digest()   # bytes32
        cid = mock_cid(data_hash)

        tx_hash = self.contract.functions.register(
            data_id, data_hash, cid, data_type, license
        ).transact({"from": sender})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        # 解析 DataRegistered 事件
        ev = self.contract.events.DataRegistered().process_receipt(receipt)
        return {
            "dataId":    to_hex(data_id),
            "dataHash":  to_hex(data_hash),
            "ipfsCID":   cid,
            "owner":     sender,
            "txHash":    to_hex(tx_hash),
            "gasUsed":   receipt.gasUsed,
            "blockNumber": receipt.blockNumber,
            "event":     dict(ev[0].args) if ev else None,
            "timestamp": self.w3.eth.get_block(receipt.blockNumber).timestamp,
        }

    # ── verify ──
    def verify(self, data_id_hex: str, local_bytes: bytes,
               verifier: Optional[str] = None) -> Dict:
        assert self.contract, "deploy() first"
        verifier = verifier or self.accounts[0]
        data_id = to_bytes(hexstr=data_id_hex)
        local_hash = bytes32_of(local_bytes)

        tx_hash = self.contract.functions.verify(data_id, local_hash) \
                       .transact({"from": verifier})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        ev = self.contract.events.DataVerified().process_receipt(receipt)
        passed = bool(ev[0].args["passed"]) if ev else False

        return {
            "dataId":  data_id_hex,
            "passed":  passed,
            "gasUsed": receipt.gasUsed,
            "txHash":  to_hex(tx_hash),
            "blockNumber": receipt.blockNumber,
        }

    # ── ownerOf ──
    def owner_of(self, data_id_hex: str) -> Optional[Tuple[str, int]]:
        assert self.contract, "deploy() first"
        try:
            data_id = to_bytes(hexstr=data_id_hex)
            owner, ts = self.contract.functions.ownerOf(data_id).call()
            return owner, ts
        except Exception:
            return None

    # ── 查询所有记录（扫事件） ──
    def list_all(self) -> List[Dict]:
        assert self.contract, "deploy() first"
        logs = self.contract.events.DataRegistered().get_logs(from_block=0)
        records = []
        for lg in logs:
            args = lg.args
            records.append({
                "dataId":    to_hex(args["dataId"]),
                "owner":     args["owner"],
                "dataHash":  to_hex(args["dataHash"]),
                "ipfsCID":   args["ipfsCID"],
                "timestamp": args["timestamp"],
                "blockNumber": lg.blockNumber,
                "txHash":    to_hex(lg.transactionHash),
            })
        return records

    # ── 链统计 ──
    def chain_stats(self) -> Dict:
        block = self.w3.eth.get_block("latest")
        return {
            "block_number": block.number,
            "chain_id":     self.w3.eth.chain_id,
            "accounts":     len(self.accounts),
            "gas_limit":    block.gasLimit,
            "contract":     self.deploy_info.contract_address if self.deploy_info else None,
            "deployer":     self.deploy_info.deployer if self.deploy_info else None,
            "deploy_gas":   self.deploy_info.gas_used if self.deploy_info else None,
            "identity_contract":   self.identity_deploy_info.contract_address if self.identity_deploy_info else None,
            "identity_deploy_gas": self.identity_deploy_info.gas_used if self.identity_deploy_info else None,
        }


# ──────────────────────────────────────────
# CLI 演示（答辩前可以跑一次验证）
# ──────────────────────────────────────────
def _demo():
    print("=" * 64)
    print("  真实 EVM 后端演示（本地 py-evm + Solidity 0.8.20）")
    print("=" * 64)

    be = EVMBackend()
    print("[1/5] 编译 DataRegistry.sol ...")
    be.compile()
    print(f"      字节码长度 = {len(be.bytecode)} hex chars")
    print(f"      ABI 函数 = {[f['name'] for f in be.abi if f['type']=='function']}")

    print("\n[2/5] 部署合约到本地 EVM ...")
    info = be.deploy()
    print(f"      合约地址 = {info.contract_address}")
    print(f"      部署者   = {info.deployer}")
    print(f"      Gas Used = {info.gas_used:,}")
    print(f"      TxHash   = {info.tx_hash}")

    print("\n[3/5] 登记数据 ...")
    r1 = be.register(data=b"mnist-train-subset-10k",
                     data_type="image", license="CC-BY-4.0",
                     sender=be.accounts[1])
    print(f"      dataId   = {r1['dataId']}")
    print(f"      owner    = {r1['owner']}")
    print(f"      ipfsCID  = {r1['ipfsCID']}")
    print(f"      gasUsed  = {r1['gasUsed']:,}")
    print(f"      txHash   = {r1['txHash']}")

    print("\n[4/5] 完整性校验 ...")
    v1 = be.verify(r1["dataId"], b"mnist-train-subset-10k")
    print(f"      同原始数据 → passed = {v1['passed']}  gas={v1['gasUsed']:,}")
    v2 = be.verify(r1["dataId"], b"mnist-train-subset-10k-TAMPERED")
    print(f"      1 字节篡改 → passed = {v2['passed']}  gas={v2['gasUsed']:,}")

    print("\n[5/5] 所有权查询 & 链上扫事件 ...")
    o = be.owner_of(r1["dataId"])
    print(f"      ownerOf → {o}")
    all_recs = be.list_all()
    print(f"      事件扫描得到 {len(all_recs)} 条登记记录")

    print("\n" + "=" * 64)
    print("  链统计：", json.dumps(be.chain_stats(), indent=2, default=str))
    print("=" * 64)


if __name__ == "__main__":
    _demo()
