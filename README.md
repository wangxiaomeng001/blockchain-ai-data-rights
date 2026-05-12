# 基于区块链的分布式 AI 数据确权系统

宁波工程学院 机器人学院 AI221 毕业设计代码仓库
指导教师：王艳  学生：王孝萌  学号：22480010119

---

## 项目简介

本项目面向 AI 训练数据场景，设计并实现了一套基于区块链的分布式数据确权系统。整体策略为"链上索引 + 链下加密存储"：链上保存数据指纹、IPFS CID 与元数据，原始数据加密后托管在分布式存储层。

系统由四个部分组成：

1. **Solidity 智能合约**（`contracts/DataRegistry.sol`）— 确权核心合约
2. **Python 区块链仿真**（`blockchain.py` / `registry.py` / `simulation.py`）— 离线运行、无需真链
3. **Streamlit 前端原型**（`app.py`）— 4 个页面：登记 / 验证 / 查询 / 链上浏览
4. **测试**（`test_registry.py`）— 18 个单元/功能测试，覆盖确权主流程与安全边界

---

## 目录结构

```
wang-yan-project-code/
├── app.py                   # Streamlit 前端（数据登记/验证/查询/浏览）
├── registry.py              # 确权业务服务层（对齐 DataRegistry.sol 接口）
├── blockchain.py            # 区块链核心（Block / Transaction / Blockchain）
├── simulation.py            # 性能仿真（吞吐量/延迟/完整性/Gas 估算）
├── plots.py                 # matplotlib 实验图生成
├── market.py                # 遗留：数据市场扩展模块（本版减量后未纳入主线）
├── main.py                  # 仿真实验主入口 → 产出 4 张论文图
├── test_registry.py         # 确权服务测试（轻量 runner 或 pytest）
├── requirements.txt         # 依赖清单
├── contracts/
│   ├── DataRegistry.sol     # ★ 核心确权合约（论文第 4.2 节）
│   ├── DataToken.sol        # 遗留：NFT 方案（本版未启用）
│   └── DataMarket.sol       # 遗留：交易合约（本版未启用）
└── outputs/
    ├── throughput-vs-nodes.png          # 图 4-5
    ├── latency-distribution.png         # 图 4-6
    ├── rights-verification-time.png     # 图 4-7
    ├── gas-cost-estimate.txt            # 表 4-2 原始数据
    ├── frontend-register.png            # 图 4-1 前端登记页
    ├── frontend-verify.png              # 图 4-2 前端验证页
    ├── frontend-owner.png               # 图 4-3 所有权查询页
    └── frontend-browser.png             # 图 4-4 链上浏览页
```

---

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 跑性能仿真（产出 3 张实验图）
```bash
python main.py
```

### 3. 跑测试（18 个 case）
```bash
python test_registry.py
```

### 4. 启动前端
```bash
streamlit run app.py
```
浏览器会自动打开 http://localhost:8501

---

## Solidity 合约编译（Remix）

合约不需要真实部署，只需在 Remix IDE 完成编译验证：

1. 打开 https://remix.ethereum.org
2. 新建文件 `DataRegistry.sol`，粘贴 `contracts/DataRegistry.sol` 全部内容
3. Compiler 选 `0.8.20`，点 **Compile**，应无警告无错误
4. 在 **Deploy & Run** 面板选择 `Remix VM`，部署后可在本地 EVM 中调用 `register / verify / ownerOf`
5. 点击各函数旁的 `Gas estimate` 图标即可获得 Gas 估算（论文表 4-2 数据来源）

---

## 测试结果（参考）

```
============================================================
  PASSED: 18   FAILED: 0
============================================================

  ✅ register: owner recorded
  ✅ register: sha256 indicator correct
  ✅ register: mock CID has Qm prefix
  ✅ owner_of: returns correct owner
  ✅ verify: identical bytes pass
  ✅ verify: modified 1 byte detected
  ✅ duplicate: second registration raises ValueError
  ✅ deactivate: owner can deactivate
  ✅ deactivate: non-owner raises PermissionError
  ✅ chain: still valid after 20 registrations
  ✅ sha256: avalanche ratio 92.19% (>40%)
  ✅ list_by_owner: Alice has 2 / Bob has 1
  ... 等共 18 项
```

---

## 论文对应关系

| 论文位置 | 对应代码 |
|---------|---------|
| 第 3.3 节 数据确权机制 | `registry.py::RegistryService.register` |
| 第 3.4 节 数据验证机制 | `registry.py::RegistryService.verify` |
| 第 4.2 节 智能合约实现 | `contracts/DataRegistry.sol` |
| 第 4.3.1 节 Python 仿真 | `blockchain.py` + `registry.py` + `simulation.py` |
| 第 4.3.2 节 Streamlit 前端 | `app.py` + 4 张前端截图 |
| 第 4.4 节 实验验证 | `main.py` + 3 张实验图 |
| 表 4-2 Gas 估算 | `outputs/gas-cost-estimate.txt` |

---

## 技术说明

- **区块链仿真**：用 Python 字典 + hashlib 实现 Block/Chain，不依赖 web3.py
- **共识机制**：简化 PoS（按权益加权随机选主）
- **IPFS**：用 SHA-256 前缀模拟 CID，不连接真实网络
- **签名**：用 SHA-256(tx_id + sender) 模拟 ECDSA
- **链上部署**：本版未部署至 Sepolia 等公网，合约在 Remix IDE 中完成编译验证

---

*本代码仅用于毕业设计实验仿真，不构成生产级部署方案。*
