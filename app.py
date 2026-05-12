"""
app.py — 基于 Streamlit 的数据确权系统原型前端
后端：真实 EVM（py-evm + Solidity 0.8.20 字节码 + web3.py 调用）
这不是"仿真"—— 合约真的被编译、真的被部署、register/verify/ownerOf 都是真实 EVM 调用。

启动：
    cd wang-yan-project-code
    streamlit run app.py
"""

from __future__ import annotations

import hashlib
import time
from datetime import datetime

import streamlit as st

from evm_backend import EVMBackend, Role, bytes32_of


ROLE_LABELS = {Role.Provider: "数据提供者 (Provider)",
               Role.Consumer: "数据消费者 (Consumer)",
               Role.Both:     "双身份 (Both)"}


# ──────────────────────────────────────────
# 全局后端（Streamlit session_state 持久化）
# ──────────────────────────────────────────
def _bootstrap():
    if "be" not in st.session_state:
        with st.spinner("🔧 正在编译 IdentityRegistry + DataRegistry 并部署到本地 EVM ..."):
            be = EVMBackend()
            be.deploy_all()
            # 预置 3 条身份样例
            be.register_identity("ACME AI Lab", Role.Provider,
                                 b"auth-acme-lab-2026", sender=be.accounts[1])
            be.register_identity("MediData Corp", Role.Provider,
                                 b"auth-medidata-2026", sender=be.accounts[2])
            be.register_identity("IndusBoost Inc.", Role.Both,
                                 b"auth-indusboost-2026", sender=be.accounts[3])
            # 预置 3 条数据样例
            be.register(data=b"mnist-train-subset-10k",
                        data_type="image", license="CC-BY-4.0",
                        sender=be.accounts[1])
            be.register(data=b"medical-text-corpus-v2",
                        data_type="text",  license="private",
                        sender=be.accounts[2])
            be.register(data=b"industrial-sensor-logs-2025q1",
                        data_type="tabular", license="MIT",
                        sender=be.accounts[3])
        st.session_state.be = be
        st.session_state.account_idx = 1  # 默认 Alice


ACCOUNT_NAMES = ["部署者", "0xAlice", "0xBob", "0xCarol", "0xDan",
                 "0xEve", "0xFrank", "0xGrace", "0xHenry", "0xIrene"]


def _acct_label(idx: int, address: str) -> str:
    name = ACCOUNT_NAMES[idx] if idx < len(ACCOUNT_NAMES) else f"acct#{idx}"
    return f"{name}  ({address[:6]}...{address[-4:]})"


# ──────────────────────────────────────────
# 主入口
# ──────────────────────────────────────────
def main():
    st.set_page_config(
        page_title="AI 数据确权系统 · 真实 EVM",
        page_icon="🔗",
        layout="wide",
    )
    _bootstrap()
    be: EVMBackend = st.session_state.be

    # ── 侧栏 ──
    st.sidebar.title("🔗 AI 数据确权系统")
    st.sidebar.caption("基于区块链的分布式 AI 数据确权 · **真实 EVM 后端**")
    st.sidebar.divider()

    idx = st.sidebar.selectbox(
        "当前身份（本地 EVM 账户）",
        options=list(range(len(be.accounts))),
        format_func=lambda i: _acct_label(i, be.accounts[i]),
        index=st.session_state.account_idx,
    )
    st.session_state.account_idx = idx

    stats = be.chain_stats()
    st.sidebar.markdown("**合约地址**")
    st.sidebar.code(f"DataRegistry     {stats['contract'][:10]}…{stats['contract'][-4:]}\n"
                    f"IdentityRegistry {stats['identity_contract'][:10]}…{stats['identity_contract'][-4:]}",
                    language="text")
    c1, c2 = st.sidebar.columns(2)
    c1.metric("区块", stats["block_number"])
    c2.metric("已登记", len(be.list_all()))
    c1.metric("数据 Gas", f"{stats['deploy_gas']:,}")
    c2.metric("身份 Gas", f"{stats['identity_deploy_gas']:,}")
    st.sidebar.divider()
    st.sidebar.caption("编译器：Solidity 0.8.20\nEVM：py-evm（本地真实执行）\nWeb3：web3.py 7.x")
    st.sidebar.divider()
    st.sidebar.caption("宁波工程学院 · AI221 · 王孝萌\n指导教师：王艳")

    # ── 主区：Tab ──
    tab0, tab1, tab2, tab3, tab4 = st.tabs([
        "👤 身份登记",
        "📤 数据登记",
        "🔍 完整性验证",
        "🔎 所有权查询",
        "📚 链上浏览",
    ])

    with tab0: _tab_identity(be, idx)
    with tab1: _tab_register(be, idx)
    with tab2: _tab_verify(be, idx)
    with tab3: _tab_owner(be)
    with tab4: _tab_browser(be)


# ──────────────────────────────────────────
# Tab 0 · 身份登记（新增，对应 IdentityRegistry 合约）
# ──────────────────────────────────────────
def _tab_identity(be: EVMBackend, idx: int):
    st.header("身份登记")
    st.caption("参与者须先向 IdentityRegistry 合约完成链上实名登记，随后方可调用 DataRegistry 登记数据。")

    # 当前账户的身份状态
    current_addr = be.accounts[idx]
    identity = be.get_identity(current_addr)
    if identity and identity.get("isActive"):
        st.success(f"✅ 当前账户已登记身份：**{identity['orgName']}**"
                   f" · 角色：{ROLE_LABELS.get(identity['role'], '未知')}")
        c1, c2, c3 = st.columns(3)
        c1.metric("钱包", current_addr[:6] + "…" + current_addr[-4:])
        c2.metric("登记时间", datetime.fromtimestamp(identity["registeredAt"]).strftime("%Y-%m-%d %H:%M"))
        c3.metric("状态", "🟢 激活" if identity["isActive"] else "⚪ 已注销")
        st.code(f"wallet:    {identity['wallet']}\n"
                f"orgName:   {identity['orgName']}\n"
                f"role:      {ROLE_LABELS.get(identity['role'])}\n"
                f"authHash:  {identity['authHash']}",
                language="text")
        return

    st.info("当前账户尚未登记身份，请填写以下信息完成登记。")
    org_name = st.text_input("机构 / 个人实名",
                             placeholder="例：某某 AI 研究院 · 某某实验室")
    role_label = st.selectbox("角色", list(ROLE_LABELS.values()))
    role_val = {v: k for k, v in ROLE_LABELS.items()}[role_label]

    auth_material = st.text_area(
        "身份凭证材料（原文不上链，仅上链 SHA-256 哈希）",
        height=100,
        placeholder="例：机构编号、工商注册信息、实名认证文件摘要等（此处演示用任意文本）",
    )

    if auth_material:
        import hashlib
        preview = hashlib.sha256(auth_material.encode()).hexdigest()
        st.code(f"authHash 预计算\n0x{preview}", language="text")

    if st.button("🪪 向 IdentityRegistry 登记", type="primary",
                 disabled=(not org_name or not auth_material)):
        try:
            with st.spinner("调用 IdentityRegistry.register() ..."):
                r = be.register_identity(
                    org_name=org_name,
                    role=role_val,
                    auth_material=auth_material.encode("utf-8"),
                    sender=current_addr,
                )
            st.success(f"✅ 身份登记成功！ Gas 使用 {r['gasUsed']:,}")
            st.json(r)
        except Exception as e:
            msg = str(e)
            if "already registered" in msg or "already used" in msg:
                st.error("此身份凭证或钱包已被登记过")
            else:
                st.error(f"登记失败：{type(e).__name__} · {msg}")

    # 展示链上所有已登记身份
    st.divider()
    st.subheader("链上所有已登记身份")
    ids = be.list_identities()
    if not ids:
        st.info("暂无身份记录。")
    else:
        rows = []
        for it in ids:
            rows.append({
                "钱包":    it["wallet"][:6] + "…" + it["wallet"][-4:],
                "机构":    it["orgName"],
                "角色":    ROLE_LABELS.get(it["role"], "-"),
                "区块":    it["blockNumber"],
                "时间":    datetime.fromtimestamp(it["timestamp"]).strftime("%m-%d %H:%M:%S"),
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)


# ──────────────────────────────────────────
# Tab 1 · 数据登记
# ──────────────────────────────────────────
def _tab_register(be: EVMBackend, idx: int):
    st.header("数据登记")
    st.caption("上传文件或粘贴文本，前端先计算 SHA-256，后端将数据指纹、CID、元数据写入真实 EVM 合约。")

    mode = st.radio("数据来源", ["📎 上传文件", "📝 粘贴文本"], horizontal=True)
    data_bytes = None
    if mode == "📎 上传文件":
        up = st.file_uploader("选择要登记的数据文件", type=None)
        if up is not None:
            data_bytes = up.read()
            st.info(f"文件：**{up.name}** · 大小：**{len(data_bytes)} bytes**")
    else:
        text = st.text_area("粘贴要登记的文本", height=150,
                            placeholder="例：2026 Q1 工业传感器采集数据 ...")
        if text:
            data_bytes = text.encode("utf-8")
            st.info(f"文本长度：**{len(data_bytes)} bytes**")

    c1, c2 = st.columns(2)
    with c1:
        dtype = st.selectbox("数据类型", ["image", "text", "tabular", "audio", "video", "other"])
    with c2:
        lic   = st.selectbox("授权协议", ["CC-BY-4.0", "MIT", "Apache-2.0", "private", "custom"])

    if data_bytes:
        preview = hashlib.sha256(data_bytes).hexdigest()
        st.code(f"SHA-256 预计算\n0x{preview}", language="text")

    if st.button("🚀 提交至区块链", type="primary", disabled=(data_bytes is None)):
        try:
            with st.spinner("广播交易并等待出块 ..."):
                rec = be.register(data=data_bytes, data_type=dtype, license=lic,
                                  sender=be.accounts[idx])
            st.success(f"✅ 登记成功  ／ Gas 使用：{rec['gasUsed']:,}")
            st.json({
                "dataId":    rec["dataId"],
                "dataHash":  rec["dataHash"],
                "ipfsCID":   rec["ipfsCID"],
                "owner":     rec["owner"],
                "blockNumber": rec["blockNumber"],
                "timestamp": rec["timestamp"],
                "txHash":    rec["txHash"],
            })
        except Exception as e:
            st.error(f"交易被拒：{type(e).__name__} · {e}")


# ──────────────────────────────────────────
# Tab 2 · 完整性验证
# ──────────────────────────────────────────
def _tab_verify(be: EVMBackend, idx: int):
    st.header("完整性验证")
    st.caption("输入 dataId 与本地文件，合约会比对哈希并触发 DataVerified 事件。")

    data_id = st.text_input("数据集 ID（dataId，0x...）", key="verify_id",
                            placeholder="0xfa08d3af4fb4dc2407c352fab...")

    mode = st.radio("本地数据", ["📎 上传文件", "📝 粘贴文本"], horizontal=True, key="verify_mode")
    local_bytes = None
    if mode == "📎 上传文件":
        up = st.file_uploader("选择本地文件校验", type=None, key="verify_upload")
        if up is not None:
            local_bytes = up.read()
    else:
        t = st.text_area("粘贴本地文本", height=120, key="verify_text")
        if t:
            local_bytes = t.encode("utf-8")

    if st.button("🔍 校验完整性", disabled=(not data_id or local_bytes is None)):
        try:
            with st.spinner("发送 verify() 交易..."):
                r = be.verify(data_id.strip(), local_bytes, verifier=be.accounts[idx])
            if r["passed"]:
                st.success(f"✅ 校验通过：链上记录与本地数据完全一致。Gas = {r['gasUsed']:,}")
            else:
                st.error(f"❌ 校验失败：哈希不一致。Gas = {r['gasUsed']:,}")
                local_h = "0x" + bytes32_of(local_bytes).hex()
                o = be.owner_of(data_id.strip())
                if o is None:
                    st.warning("链上不存在此 dataId，请确认输入。")
                else:
                    st.code(f"本地 SHA-256:\n{local_h}", language="text")
            st.json({"txHash": r["txHash"], "blockNumber": r["blockNumber"]})
        except Exception as e:
            st.error(f"调用失败：{e}")


# ──────────────────────────────────────────
# Tab 3 · 所有权查询
# ──────────────────────────────────────────
def _tab_owner(be: EVMBackend):
    st.header("所有权查询")
    st.caption("给定 dataId 查询其链上所有者与上链时间（view 调用，不消耗 Gas）。")

    data_id = st.text_input("数据集 ID（dataId）", key="owner_id")

    if st.button("👤 查询所有权", disabled=(not data_id)):
        o = be.owner_of(data_id.strip())
        if o is None:
            st.error("未找到该 dataId 对应的链上记录。")
        else:
            addr, ts = o
            st.success("查询成功")
            c1, c2 = st.columns(2)
            c1.metric("所有者钱包", addr[:6] + "…" + addr[-4:])
            c2.metric("登记时间", datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S"))
            st.code(addr, language="text")


# ──────────────────────────────────────────
# Tab 4 · 链上浏览
# ──────────────────────────────────────────
def _tab_browser(be: EVMBackend):
    st.header("链上浏览")
    st.caption("从 DataRegistered 事件日志还原所有登记记录，与区块链浏览器等价。")

    records = be.list_all()
    if not records:
        st.info("链上暂无登记记录。")
        return

    rows = []
    for r in records:
        rows.append({
            "dataId":   r["dataId"][:10] + "…" + r["dataId"][-6:],
            "owner":    r["owner"][:8] + "…" + r["owner"][-4:],
            "CID":      r["ipfsCID"][:16] + "…",
            "block #":  r["blockNumber"],
            "txHash":   r["txHash"][:10] + "…" + r["txHash"][-6:],
            "时间":     datetime.fromtimestamp(r["timestamp"]).strftime("%m-%d %H:%M:%S"),
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)

    with st.expander("🔎 原始事件详情（JSON）"):
        st.json(records)


if __name__ == "__main__":
    main()
