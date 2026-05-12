"""
基于区块链的分布式 AI 数据确权系统 · 实验主程序
宁波工程学院 AI221 毕业设计 · 王孝萌 · 指导教师：王艳

运行：
    python3.12 main.py

产出：
    outputs/throughput-vs-nodes.png
    outputs/latency-distribution.png
    outputs/rights-verification-time.png
    outputs/gas-cost-estimate.txt

本文件调用 registry_sim（纯 Python 仿真）与 evm_backend（本地真实 EVM），
前者用于吞吐量、延迟、完整性等大规模实验，后者用于合约 Gas 实测。
"""

import random
import time

import numpy as np

random.seed(42)
np.random.seed(42)

from registry_sim import (
    exp1_rights_throughput,
    exp2_scalability,
    exp3_integrity,
    estimate_gas,
)
from plots import (
    plot_throughput_vs_nodes,
    plot_latency_distribution,
    plot_rights_verification_time,
    write_gas_cost_estimate,
)


def hr(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def main():
    t_start = time.perf_counter()

    hr("基于区块链的分布式 AI 数据确权系统 · 实验主程序")

    # ── 实验 1 ────────────────────────────
    hr("实验 1 — 确权登记吞吐实验")
    print("配置：10 个数据提供者 × 每人 12 份数据集 = 120 份数据；10 个验证节点")
    r1 = exp1_rights_throughput(n_owners=10, datasets_per_owner=12, n_validators=10)
    print(f"  ✓ 成功登记：{r1['n_total']} 份")
    print(f"  ✓ 出块数  ：{r1['blocks_produced']}")
    print(f"  ✓ 链完整性：{'通过' if r1['chain_valid'] else '失败'}")
    print(f"  ✓ 平均 register 延迟：{r1['stats']['avg_register_ms']:.1f} ms")
    print(f"  ✓ 平均 verify 延迟  ：{r1['stats']['avg_verify_ms']:.1f} ms")
    print(f"  ✓ 等效 TPS         ：{r1['tps']:.2f}")

    # ── 实验 2 ────────────────────────────
    hr("实验 2 — 可扩展性实验（不同验证节点规模）")
    node_counts = [5, 10, 20, 50, 100, 200, 500]
    print(f"节点规模梯度：{node_counts}")
    r2 = exp2_scalability(node_counts=node_counts, registrations_each=200)
    print("\n  节点数 |   TPS   |  avg 延迟(ms)  |  出块")
    print("  " + "-" * 48)
    for r in r2:
        avg = sum(r["latencies"]) / len(r["latencies"])
        print(f"  {r['total_nodes']:>5}  |  {r['tps']:>5.2f}  |   {avg:>6.1f}      |  {r['blocks_produced']}")

    # ── 实验 3 ────────────────────────────
    hr("实验 3 — 数据完整性验证")
    r3 = exp3_integrity(n_samples=100)
    print(f"  样本数           ：{r3['n_samples']}")
    print(f"  篡改检测         ：{r3['tamper_detected']}/{r3['n_samples']}")
    print(f"  检测率           ：{r3['detection_rate']:.0%}")
    print(f"  平均 verify 耗时 ：{r3['avg_verify_ok_ms']:.3f} ms")

    # ── Gas 实测 ───────────────────────────
    hr("Gas 实测（本地真实 EVM · DataRegistry.sol）")
    gas = estimate_gas()
    for op, info in gas.items():
        if op == "ownerOf":
            print(f"  {op:<12} {info['gas']:>10}  (view · off-chain · 不消耗 gas)")
        else:
            print(f"  {op:<12} {info['gas']:>10}  ≈ {info['eth']:.6f} ETH  ≈ ${info['usd']}")

    # ── 聚合画图数据 ────────────────────────
    all_reg_lat = r1["register_latencies"][:]
    for r in r2:
        all_reg_lat.extend(r["latencies"])

    verify_cdf_lat = r3["verify_ok_latencies"][:]

    hr("生成实验图表")
    # 图一：scalability 的 TPS 曲线
    plot_throughput_vs_nodes(r2)
    # 图二：register 延迟分布
    plot_latency_distribution(all_reg_lat)
    # 图三：verify 延迟 CDF
    plot_rights_verification_time(verify_cdf_lat)

    # ── 把 Gas 转成 plots.py 期望的格式 ─────
    gas_for_plot = {
        "DataRegistry.deploy()":   {"gas": gas["deploy"]["gas"],    "cost_eth": gas["deploy"]["eth"],   "cost_usd": gas["deploy"]["usd"],   "description": "合约部署上链（一次性）"},
        "DataRegistry.register()": {"gas": gas["register"]["gas"],  "cost_eth": gas["register"]["eth"], "cost_usd": gas["register"]["usd"], "description": "数据集链上确权登记（含事件发射）"},
        "DataRegistry.verify()":   {"gas": gas["verify"]["gas"],    "cost_eth": gas["verify"]["eth"],   "cost_usd": gas["verify"]["usd"],   "description": "数据完整性校验（含事件发射）"},
        "DataRegistry.ownerOf()":  {"gas": 0,                        "cost_eth": 0,                       "cost_usd": 0,                       "description": "所有权查询（view 调用，off-chain 不消耗 gas）"},
    }
    write_gas_cost_estimate(gas_for_plot)

    # ── 摘要 ─────────────────────────────
    elapsed = time.perf_counter() - t_start
    hr("实验完成 · 摘要报告")
    all_reg = np.array(all_reg_lat)
    print(f"  总登记操作数     ：{r1['n_total'] + sum(r['n_registrations'] for r in r2)} 次")
    print(f"  总验证操作数     ：{len(r1['verify_latencies']) + len(verify_cdf_lat)} 次")
    print(f"  共完成仿真事件   ：{r1['n_total'] + sum(r['n_registrations'] for r in r2) + len(r1['verify_latencies']) + len(verify_cdf_lat)} 条")
    print(f"  Register 延迟 P50：{np.percentile(all_reg, 50):.1f} ms")
    print(f"  Register 延迟 P95：{np.percentile(all_reg, 95):.1f} ms")
    print(f"  可扩展性 TPS 范围：{min(r['tps'] for r in r2):.2f} ~ {max(r['tps'] for r in r2):.2f}")
    print(f"  完整性检测率     ：{r3['detection_rate']:.0%}（{r3['tamper_detected']}/{r3['n_samples']}）")
    print(f"  Gas · 部署       ：{gas['deploy']['gas']:,}")
    print(f"  Gas · register   ：{gas['register']['gas']:,}")
    print(f"  Gas · verify     ：{gas['verify']['gas']:,}")
    print(f"  本次总用时       ：{elapsed:.2f} 秒")
    print()


if __name__ == "__main__":
    main()
