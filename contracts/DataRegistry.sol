// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title DataRegistry
 * @notice AI 数据确权注册合约（宁波工程学院 · 王孝萌 · 2026 毕业设计）
 * @dev
 *   核心职责：
 *     1. register()   将数据指纹与 IPFS CID 上链登记
 *     2. verify()     比对本地文件哈希与链上记录，判断是否被篡改
 *     3. ownerOf()    查询某个 dataId 的所有者与登记时间
 *   设计原则：
 *     - 时间优先：同一个数据哈希只允许被第一次登记，之后的重复登记会被拒绝
 *     - 记录不可篡改：合约不提供删除/覆盖接口，任何变更需由 owner 通过 deactivate 标记
 *     - 事件驱动：所有状态变更对外发 Event，便于链下索引与审计
 */
contract DataRegistry {

    // ─────────────────────────────
    // 状态定义
    // ─────────────────────────────
    struct DataRecord {
        address owner;       // 数据提供者钱包地址
        bytes32 dataHash;    // 数据 SHA-256 指纹
        string  ipfsCID;     // IPFS 内容标识符
        string  dataType;    // 数据类型 (image/text/tabular ...)
        string  license;     // 授权协议 (MIT/CC-BY/private ...)
        uint256 timestamp;   // 上链时间戳 (block.timestamp)
        bool    isActive;    // 是否处于激活状态
    }

    // dataId ⇒ DataRecord
    mapping(bytes32 => DataRecord) public records;

    // dataHash ⇒ dataId  (全局防重复确权)
    mapping(bytes32 => bytes32)    public hashToId;

    // 全局登记计数，便于外部索引
    uint256 public totalRegistered;

    // ─────────────────────────────
    // 事件
    // ─────────────────────────────
    event DataRegistered(
        bytes32 indexed dataId,
        address indexed owner,
        bytes32 dataHash,
        string  ipfsCID,
        uint256 timestamp
    );

    event DataVerified(
        bytes32 indexed dataId,
        address indexed verifier,
        bool    passed
    );

    event DataDeactivated(
        bytes32 indexed dataId,
        address indexed owner
    );

    // ─────────────────────────────
    // 修饰器
    // ─────────────────────────────
    modifier onlyOwner(bytes32 dataId) {
        require(records[dataId].owner == msg.sender, "DataRegistry: caller is not owner");
        _;
    }

    modifier recordExists(bytes32 dataId) {
        require(records[dataId].timestamp != 0, "DataRegistry: record not found");
        _;
    }

    // ─────────────────────────────
    // 核心接口
    // ─────────────────────────────

    /**
     * @notice 将一份数据登记到链上
     * @param dataId   数据集唯一 ID（推荐由前端 keccak256(dataHash, salt) 生成）
     * @param dataHash 数据 SHA-256 哈希
     * @param cid      IPFS 内容标识符
     * @param dataType 数据类型（image/text/tabular 等）
     * @param license  授权协议字符串
     */
    function register(
        bytes32 dataId,
        bytes32 dataHash,
        string calldata cid,
        string calldata dataType,
        string calldata license
    ) external {
        require(dataId != bytes32(0),     "DataRegistry: dataId cannot be zero");
        require(dataHash != bytes32(0),   "DataRegistry: dataHash cannot be zero");
        require(bytes(cid).length > 0,    "DataRegistry: CID cannot be empty");
        require(records[dataId].timestamp == 0, "DataRegistry: dataId already exists");
        require(hashToId[dataHash] == bytes32(0), "DataRegistry: data already registered");

        records[dataId] = DataRecord({
            owner:     msg.sender,
            dataHash:  dataHash,
            ipfsCID:   cid,
            dataType:  dataType,
            license:   license,
            timestamp: block.timestamp,
            isActive:  true
        });

        hashToId[dataHash] = dataId;
        totalRegistered   += 1;

        emit DataRegistered(dataId, msg.sender, dataHash, cid, block.timestamp);
    }

    /**
     * @notice 校验本地数据指纹与链上记录是否一致
     * @param dataId    数据集 ID
     * @param localHash 本地计算出的 SHA-256 哈希
     * @return passed   true = 一致（未被篡改）， false = 不一致（已被篡改或 ID 不存在）
     */
    function verify(bytes32 dataId, bytes32 localHash)
        external
        returns (bool passed)
    {
        DataRecord memory r = records[dataId];
        passed = (r.timestamp != 0) && r.isActive && (r.dataHash == localHash);
        emit DataVerified(dataId, msg.sender, passed);
    }

    /**
     * @notice 查询某个数据集的所有者与上链时间（view 函数，不消耗 Gas）
     */
    function ownerOf(bytes32 dataId)
        external
        view
        recordExists(dataId)
        returns (address owner, uint256 timestamp)
    {
        DataRecord memory r = records[dataId];
        return (r.owner, r.timestamp);
    }

    /**
     * @notice 根据数据哈希反查 dataId（用于防重复登记预检）
     */
    function lookupByHash(bytes32 dataHash) external view returns (bytes32) {
        return hashToId[dataHash];
    }

    /**
     * @notice 所有者将自己的数据标记为已下架
     * @dev    不删除记录，仅将 isActive 置为 false，保留历史可追溯
     */
    function deactivate(bytes32 dataId)
        external
        recordExists(dataId)
        onlyOwner(dataId)
    {
        require(records[dataId].isActive, "DataRegistry: already inactive");
        records[dataId].isActive = false;
        emit DataDeactivated(dataId, msg.sender);
    }
}
