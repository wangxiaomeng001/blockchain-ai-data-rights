"""
数据市场与确权模块
实现 DataRecord（数据确权）、DataMarket（撮合市场）、RightsNFT（NFT 确权令牌）
"""

import hashlib
import time
import random
from typing import Dict, List, Optional, Tuple
from blockchain import Blockchain, Transaction


# ──────────────────────────────────────────
# 1. 数据集确权记录
# ──────────────────────────────────────────
class DataRecord:
    """
    链上数据集注册记录
    对应论文第 3.2 节"数据确权机制"
    """

    def __init__(self, owner: str, dataset_id: str, description: str,
                 size_mb: float, price: float, data_type: str = "csv"):
        self.owner = owner                          # 数据拥有者地址
        self.dataset_id = dataset_id                # 数据集唯一 ID
        self.description = description              # 数据集描述
        self.size_mb = size_mb                      # 数据大小（MB）
        self.price = price                          # 定价（ETH 模拟）
        self.data_type = data_type                  # 数据类型
        self.data_hash = self._compute_data_hash()  # SHA-256 数据指纹
        self.ipfs_cid = self._mock_ipfs_cid()       # 模拟 IPFS CID
        self.register_time = time.time()            # 确权时间戳
        self.is_active = True                       # 是否在售

    def _compute_data_hash(self) -> str:
        """
        计算数据哈希指纹
        真实场景中是对实际文件内容做 SHA-256
        这里用数据集元数据模拟
        """
        raw = f"{self.owner}{self.dataset_id}{self.description}{self.size_mb}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def _mock_ipfs_cid(self) -> str:
        """
        模拟 IPFS CID（内容标识符）
        真实 IPFS CID 以 Qm 开头（v0），或 bafy... 开头（v1）
        """
        raw = f"ipfs:{self.data_hash}"
        short = hashlib.sha256(raw.encode()).hexdigest()[:44]
        return f"Qm{short}"

    def __repr__(self) -> str:
        return (f"DataRecord(id={self.dataset_id}, owner={self.owner[:8]}..., "
                f"price={self.price:.3f} ETH, size={self.size_mb:.1f}MB)")


# ──────────────────────────────────────────
# 2. RightsNFT — 数据权益 NFT
# ──────────────────────────────────────────
class RightsNFT:
    """
    数据确权 NFT
    对应 Solidity 合约 DataToken（ERC-721）
    mint：铸造权益令牌 → 对应链上 ownerOf / tokenURI
    transfer：权益转让 → 对应链上 safeTransferFrom
    verify：验证持有权 → 对应链上 ownerOf 查询
    """

    def __init__(self):
        # token_id → {"owner": str, "dataset_id": str, "mint_time": float}
        self._registry: Dict[int, Dict] = {}
        self._next_token_id = 1
        # dataset_id → token_id 反查
        self._dataset_to_token: Dict[str, int] = {}

    def mint(self, owner: str, dataset_id: str, data_hash: str) -> int:
        """
        铸造新 NFT，绑定数据集确权记录
        返回 token_id
        """
        if dataset_id in self._dataset_to_token:
            raise ValueError(f"数据集 {dataset_id} 已经完成确权，token_id="
                             f"{self._dataset_to_token[dataset_id]}")
        token_id = self._next_token_id
        self._registry[token_id] = {
            "owner": owner,
            "dataset_id": dataset_id,
            "data_hash": data_hash,
            "mint_time": time.time(),
            "transfer_history": [owner],
        }
        self._dataset_to_token[dataset_id] = token_id
        self._next_token_id += 1
        return token_id

    def transfer(self, token_id: int, from_addr: str, to_addr: str) -> bool:
        """
        转让 NFT（对应 safeTransferFrom）
        返回 True 表示成功
        """
        if token_id not in self._registry:
            return False
        record = self._registry[token_id]
        if record["owner"] != from_addr:
            return False
        record["owner"] = to_addr
        record["transfer_history"].append(to_addr)
        return True

    def verify(self, token_id: int, claimed_owner: str) -> bool:
        """验证某地址是否持有指定 token 的所有权"""
        if token_id not in self._registry:
            return False
        return self._registry[token_id]["owner"] == claimed_owner

    def get_token(self, dataset_id: str) -> Optional[Dict]:
        """通过数据集 ID 查询 NFT 信息"""
        token_id = self._dataset_to_token.get(dataset_id)
        if token_id is None:
            return None
        return self._registry[token_id]

    @property
    def total_supply(self) -> int:
        return len(self._registry)


# ──────────────────────────────────────────
# 3. 数据市场主体
# ──────────────────────────────────────────
class DataMarket:
    """
    去中心化 AI 数据市场
    对应论文第 3.3 节"去中心化交易机制"

    功能：
    - register_data：数据提供者上架数据集（同时铸造 NFT）
    - list_datasets：浏览市场中的数据集
    - purchase：购买数据集（自动撮合，智能合约模拟）
    - get_stats：市场统计
    """

    # 平台抽成比例（5%）
    PLATFORM_FEE_RATE = 0.05

    def __init__(self, blockchain: Blockchain, nft: RightsNFT):
        self.blockchain = blockchain    # 挂载区块链
        self.nft = nft                  # NFT 合约

        # 链上数据集注册表 {dataset_id → DataRecord}
        self.datasets: Dict[str, DataRecord] = {}

        # 已完成交易记录列表
        self.completed_transactions: List[Transaction] = []

        # 平台资金池（5% 手续费累计）
        self.platform_fund: float = 0.0

        # 各节点余额模拟
        self.balances: Dict[str, float] = {}

        # 延迟统计（毫秒）
        self.latencies: List[float] = []

        # 确权时间统计（毫秒）
        self.rights_verification_times: List[float] = []

    def _get_balance(self, address: str) -> float:
        return self.balances.get(address, 0.0)

    def _topup(self, address: str, amount: float):
        """向账户充值（模拟）"""
        self.balances[address] = self._get_balance(address) + amount

    def register_data(self, owner: str, dataset_id: str, description: str,
                      size_mb: float, price: float,
                      data_type: str = "csv") -> Tuple[DataRecord, int]:
        """
        数据提供者注册/上架数据集
        同时完成确权（铸造 NFT）并记录链上确权时间
        返回 (DataRecord, token_id)
        """
        if dataset_id in self.datasets:
            raise ValueError(f"数据集 {dataset_id} 已注册")

        t_start = time.perf_counter()

        # 创建数据记录
        record = DataRecord(owner, dataset_id, description, size_mb,
                            price, data_type)
        self.datasets[dataset_id] = record

        # 铸造 NFT 确权
        token_id = self.nft.mint(owner, dataset_id, record.data_hash)

        t_end = time.perf_counter()
        elapsed_ms = (t_end - t_start) * 1000

        # 记录确权时间（用于 rights_verification_time 图）
        self.rights_verification_times.append(elapsed_ms)

        return record, token_id

    def list_datasets(self, active_only: bool = True) -> List[DataRecord]:
        """列出市场上所有可购买的数据集"""
        if active_only:
            return [r for r in self.datasets.values() if r.is_active]
        return list(self.datasets.values())

    def purchase(self, buyer: str, dataset_id: str) -> Optional[Transaction]:
        """
        执行数据购买
        模拟智能合约逻辑：
        1. 验证数据集存在且在售
        2. 验证买方余额充足
        3. 扣款 → 平台手续费 → 卖方到账
        4. 生成链上交易，加入待打包队列
        5. 记录延迟
        """
        t_start = time.perf_counter()

        if dataset_id not in self.datasets:
            return None

        record = self.datasets[dataset_id]
        if not record.is_active:
            return None

        seller = record.owner
        price = record.price

        # 确保买家有足够余额（不足则自动充值，模拟 faucet）
        if self._get_balance(buyer) < price:
            self._topup(buyer, price * 2)  # 模拟测试网水龙头补币

        # 从买方扣款
        self.balances[buyer] -= price

        # 收益分配：平台 5%，卖方 95%
        platform_cut = price * self.PLATFORM_FEE_RATE
        seller_cut = price - platform_cut
        self.platform_fund += platform_cut
        self.balances[seller] = self._get_balance(seller) + seller_cut

        # 创建链上交易
        tx = Transaction(
            seller=seller,
            buyer=buyer,
            dataset_id=dataset_id,
            price=price,
            data_hash=record.data_hash,
        )
        self.blockchain.add_transaction(tx)
        self.completed_transactions.append(tx)

        t_end = time.perf_counter()

        # 加入延迟统计（模拟链上确认延迟：基础网络延迟 + 随机抖动）
        # 真实以太坊 Sepolia 约 12-15 秒，这里模拟单位为毫秒
        network_latency_ms = (t_end - t_start) * 1000 + random.gauss(120, 30)
        self.latencies.append(max(10, network_latency_ms))  # 最低 10ms

        return tx

    def get_stats(self) -> Dict:
        """返回市场运行统计信息"""
        return {
            "total_datasets": len(self.datasets),
            "active_datasets": sum(1 for r in self.datasets.values() if r.is_active),
            "total_transactions": len(self.completed_transactions),
            "total_volume": sum(tx.price for tx in self.completed_transactions),
            "platform_fund": self.platform_fund,
            "avg_latency_ms": (sum(self.latencies) / len(self.latencies)
                               if self.latencies else 0),
            "nft_total_supply": self.nft.total_supply,
        }
