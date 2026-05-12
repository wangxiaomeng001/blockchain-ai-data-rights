"""
实验仿真模块
运行多组仿真实验，收集吞吐量、延迟、确权时间等数据
供 main.py 调用，再交给 plots.py 出图
"""

import random
import time
import hashlib
from typing import List, Dict, Tuple

from blockchain import Blockchain, Transaction
from market import DataMarket, RightsNFT


# ──────────────────────────────────────────
# 工具函数：生成模拟地址
# ──────────────────────────────────────────
def _addr(name: str) -> str:
    """生成模拟以太坊地址（格式：0x + 40 位十六进制）"""
    h = hashlib.sha256(name.encode()).hexdigest()
    return "0x" + h[:40]


def _dataset_id(seller: str, idx: int) -> str:
    """生成数据集 ID"""
    return f"DS_{seller[:6]}_{idx:04d}"


# ──────────────────────────────────────────
# 实验1：固定节点数，跑 N 笔交易，统计吞吐量
# ──────────────────────────────────────────
def run_throughput_experiment(
    n_sellers: int = 10,
    n_buyers: int = 20,
    n_transactions: int = 500,
    tx_per_block: int = 50,
) -> Dict:
    """
    吞吐量实验
    n_sellers：数据提供方数量
    n_buyers：数据消费方数量
    n_transactions：模拟交易总量
    tx_per_block：每块最多打包交易数
    返回统计字典
    """
    bc = Blockchain()
    nft = RightsNFT()

    # 注册 PoS 验证节点（模拟 5 个矿工节点）
    for i in range(5):
        validator = _addr(f"validator_{i}")
        stake = random.uniform(10, 100)  # 随机权益
        bc.register_validator(validator, stake)

    market = DataMarket(bc, nft)

    # 生成卖家、买家地址
    sellers = [_addr(f"seller_{i}") for i in range(n_sellers)]
    buyers = [_addr(f"buyer_{i}") for i in range(n_buyers)]

    # 每个卖家预注册若干数据集
    datasets = []
    for s_idx, seller in enumerate(sellers):
        n_datasets = random.randint(5, 20)
        for d_idx in range(n_datasets):
            ds_id = _dataset_id(f"s{s_idx}", d_idx)
            size_mb = random.uniform(10, 2000)
            price = random.uniform(0.001, 0.1)
            market.register_data(seller, ds_id, f"AI训练数据集{s_idx}-{d_idx}",
                                 size_mb, price, data_type="csv")
            datasets.append(ds_id)

    # 执行模拟交易
    t_start = time.perf_counter()
    successful_txs = 0
    for _ in range(n_transactions):
        buyer = random.choice(buyers)
        ds_id = random.choice(datasets)
        tx = market.purchase(buyer, ds_id)
        if tx:
            successful_txs += 1

    # 把所有待打包交易写进区块
    while bc.pending_transactions:
        bc.mine_block(max_tx=tx_per_block)

    t_end = time.perf_counter()
    elapsed_sec = t_end - t_start

    tps = successful_txs / elapsed_sec if elapsed_sec > 0 else 0

    return {
        "n_sellers": n_sellers,
        "n_buyers": n_buyers,
        "n_transactions": n_transactions,
        "successful_txs": successful_txs,
        "elapsed_sec": elapsed_sec,
        "tps": tps,
        "blocks_produced": bc.height,
        "chain_valid": bc.is_chain_valid(),
        "latencies": market.latencies[:],
        "rights_times": market.rights_verification_times[:],
        "stats": market.get_stats(),
    }


# ──────────────────────────────────────────
# 实验2：不同节点规模下的吞吐量对比
# ──────────────────────────────────────────
def run_scalability_experiment(
    node_counts: List[int] = None,
    transactions_each: int = 300,
) -> List[Dict]:
    """
    可扩展性实验
    对不同节点数量（n_sellers + n_buyers）分别运行实验
    记录吞吐量 TPS 随节点数变化的趋势
    """
    if node_counts is None:
        # 对应论文第 4.3 节实验，节点规模梯度
        node_counts = [5, 10, 20, 50, 100, 200, 500]

    results = []
    for n_nodes in node_counts:
        n_sellers = max(3, n_nodes // 3)
        n_buyers = n_nodes - n_sellers

        print(f"  → 节点数 {n_nodes}（卖家 {n_sellers}，买家 {n_buyers}）"
              f"，交易量 {transactions_each}...")

        result = run_throughput_experiment(
            n_sellers=n_sellers,
            n_buyers=n_buyers,
            n_transactions=transactions_each,
        )
        result["total_nodes"] = n_nodes
        results.append(result)

    return results


# ──────────────────────────────────────────
# 实验3：数据完整性验证
# ──────────────────────────────────────────
def run_integrity_experiment() -> Dict:
    """
    验证数据完整性保护机制
    对应论文实验3：改动 1 字节后哈希是否变化
    """
    import hashlib

    # 原始数据（模拟 1GB CSV 训练集的哈希）
    original_content = "feature1,feature2,label\n" + "0.5,0.3,1\n" * 10000
    original_hash = hashlib.sha256(original_content.encode()).hexdigest()

    # 篡改 1 字节
    tampered_content = original_content[:-1] + "X"
    tampered_hash = hashlib.sha256(tampered_content.encode()).hexdigest()

    detected = (original_hash != tampered_hash)

    # 模拟 SHA-256 计算时间（1GB 数据实测约 2.3s，这里按比例模拟）
    t_start = time.perf_counter()
    _ = hashlib.sha256(original_content.encode()).hexdigest()
    t_end = time.perf_counter()

    return {
        "original_hash": original_hash,
        "tampered_hash": tampered_hash,
        "tamper_detected": detected,
        "hash_compute_ms": (t_end - t_start) * 1000,
    }


# ──────────────────────────────────────────
# Gas 费用估算（对应 Solidity 合约）
# ──────────────────────────────────────────
def estimate_gas_costs() -> Dict:
    """
    估算 Solidity 合约各操作的 Gas 消耗
    数据来源：Remix IDE + Ethereum Yellow Paper 标准值
    """
    # 基础 Gas 价格（Sepolia 测试网 2024 年均值，单位 Gwei）
    gas_price_gwei = 20.0
    eth_price_usd = 3000  # 参考价格（仅用于成本估算）

    operations = {
        "DataRegistry.register()": {
            "gas": 150_000,
            "description": "数据集链上确权注册（写入 mapping + Event）",
        },
        "DataRegistry.verify()": {
            "gas": 25_000,
            "description": "数据完整性校验（读操作，消耗较少）",
        },
        "DataMarket.listData()": {
            "gas": 80_000,
            "description": "数据集上架（写入市场 listing）",
        },
        "DataMarket.purchase()": {
            "gas": 200_000,
            "description": "购买交易（资金托管 + 释放 + 授权 Event）",
        },
        "DataToken.mint()": {
            "gas": 120_000,
            "description": "铸造确权 NFT（ERC-721 mint）",
        },
        "DataToken.safeTransferFrom()": {
            "gas": 65_000,
            "description": "NFT 所有权转让",
        },
    }

    result = {}
    for op, info in operations.items():
        gas = info["gas"]
        cost_eth = gas * gas_price_gwei * 1e-9  # gas × gwei → ETH
        cost_usd = cost_eth * eth_price_usd
        result[op] = {
            "gas": gas,
            "gas_price_gwei": gas_price_gwei,
            "cost_eth": cost_eth,
            "cost_usd": cost_usd,
            "description": info["description"],
        }

    return result
