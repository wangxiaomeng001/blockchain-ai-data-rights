"""
区块链核心数据结构模块
实现 Block、Transaction、Blockchain 三个类
用纯 Python + hashlib 模拟区块链，不依赖任何外部区块链库
"""

import hashlib
import time
import json
import random
from typing import List, Optional, Dict, Any


# ──────────────────────────────────────────
# 1. 交易类
# ──────────────────────────────────────────
class Transaction:
    """
    代表一笔数据交易记录
    包含：卖方、买方、数据集 ID、价格、时间戳、签名（模拟）
    """

    def __init__(self, seller: str, buyer: str, dataset_id: str,
                 price: float, data_hash: str):
        self.seller = seller          # 卖方地址（模拟以太坊地址）
        self.buyer = buyer            # 买方地址
        self.dataset_id = dataset_id  # 数据集 ID
        self.price = price            # 成交价格（单位：ETH 模拟代币）
        self.data_hash = data_hash    # 数据文件的 SHA-256 哈希
        self.timestamp = time.time()  # 交易时间戳
        self.tx_id = self._compute_tx_id()  # 交易 ID
        self.signature = self._mock_sign()  # 模拟数字签名

    def _compute_tx_id(self) -> str:
        """计算交易唯一 ID"""
        raw = f"{self.seller}{self.buyer}{self.dataset_id}{self.price}{self.timestamp}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _mock_sign(self) -> str:
        """
        模拟 ECDSA 签名
        真实场景中需要卖方用私钥对交易内容签名
        这里用 SHA-256(tx_id + seller) 代替
        """
        raw = f"{self.tx_id}{self.seller}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典（用于区块打包）"""
        return {
            "tx_id": self.tx_id,
            "seller": self.seller,
            "buyer": self.buyer,
            "dataset_id": self.dataset_id,
            "price": self.price,
            "data_hash": self.data_hash,
            "timestamp": self.timestamp,
            "signature": self.signature,
        }


# ──────────────────────────────────────────
# 2. 区块类
# ──────────────────────────────────────────
class Block:
    """
    区块链中的单个区块
    包含：区块索引、时间戳、前区块哈希、交易列表、Nonce、区块哈希
    """

    def __init__(self, index: int, previous_hash: str,
                 transactions: List[Transaction], validator: str = ""):
        self.index = index                         # 区块高度
        self.timestamp = time.time()               # 出块时间戳
        self.previous_hash = previous_hash         # 前一区块哈希
        self.transactions = transactions           # 本块包含的交易列表
        self.validator = validator                 # 出块验证者（PoS 模拟）
        self.nonce = 0                             # 随机数（PoS 中不做 PoW，仅保留字段）
        self.merkle_root = self._compute_merkle()  # 交易 Merkle 根
        self.hash = self._compute_hash()           # 区块哈希

    def _compute_merkle(self) -> str:
        """
        计算 Merkle 树根哈希
        叶子节点 = 每笔交易的 tx_id
        逐层两两哈希合并，最终得到 Merkle 根
        """
        if not self.transactions:
            return hashlib.sha256(b"empty").hexdigest()

        # 叶子节点
        hashes = [hashlib.sha256(tx.tx_id.encode()).hexdigest()
                  for tx in self.transactions]

        # 逐层向上合并
        while len(hashes) > 1:
            if len(hashes) % 2 == 1:
                hashes.append(hashes[-1])  # 奇数时复制最后一个
            next_level = []
            for i in range(0, len(hashes), 2):
                combined = hashes[i] + hashes[i + 1]
                next_level.append(hashlib.sha256(combined.encode()).hexdigest())
            hashes = next_level

        return hashes[0]

    def _compute_hash(self) -> str:
        """计算区块哈希，覆盖 index / timestamp / previous_hash / merkle_root / validator"""
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "merkle_root": self.merkle_root,
            "validator": self.validator,
            "nonce": self.nonce,
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def __repr__(self) -> str:
        return (f"Block(#{self.index}, txs={len(self.transactions)}, "
                f"hash={self.hash[:8]}..., validator={self.validator})")


# ──────────────────────────────────────────
# 3. 区块链类
# ──────────────────────────────────────────
class Blockchain:
    """
    模拟区块链主体
    包含：创世区块、区块追加、交易验证、链完整性校验
    共识机制：简化 PoS（按权益随机选出验证者）
    """

    def __init__(self):
        self.chain: List[Block] = []
        self.pending_transactions: List[Transaction] = []
        self.validators: Dict[str, float] = {}  # 节点地址 → 权益值

        # 创世区块
        genesis = Block(index=0, previous_hash="0" * 64,
                        transactions=[], validator="genesis")
        self.chain.append(genesis)

    def register_validator(self, address: str, stake: float):
        """注册一个 PoS 验证节点"""
        self.validators[address] = stake

    def _select_validator(self) -> str:
        """
        简化 PoS 选主：按权益比例加权随机抽取
        权益越大，被选中概率越高
        """
        if not self.validators:
            return "default_validator"
        addresses = list(self.validators.keys())
        stakes = [self.validators[a] for a in addresses]
        total = sum(stakes)
        probs = [s / total for s in stakes]
        return random.choices(addresses, weights=probs, k=1)[0]

    def add_transaction(self, tx: Transaction):
        """将交易加入待打包队列"""
        self.pending_transactions.append(tx)

    def mine_block(self, max_tx: int = 50) -> Block:
        """
        打包一批待处理交易，生成新区块
        max_tx：每块最多打包多少笔交易
        """
        # 取出本轮要打包的交易
        batch = self.pending_transactions[:max_tx]
        self.pending_transactions = self.pending_transactions[max_tx:]

        validator = self._select_validator()
        last_block = self.chain[-1]
        new_block = Block(
            index=len(self.chain),
            previous_hash=last_block.hash,
            transactions=batch,
            validator=validator,
        )
        self.chain.append(new_block)
        return new_block

    def is_chain_valid(self) -> bool:
        """校验整条链的哈希完整性"""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            # 当前区块哈希是否正确
            if current.hash != current._compute_hash():
                return False
            # 前向指针是否正确
            if current.previous_hash != previous.hash:
                return False
        return True

    def get_transaction(self, tx_id: str) -> Optional[Transaction]:
        """按 tx_id 查询链上已确认交易"""
        for block in self.chain:
            for tx in block.transactions:
                if tx.tx_id == tx_id:
                    return tx
        return None

    @property
    def height(self) -> int:
        return len(self.chain) - 1  # 不含创世块

    def __repr__(self) -> str:
        return f"Blockchain(height={self.height}, blocks={len(self.chain)})"
