// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IdentityRegistry
 * @notice AI 数据市场的身份登记合约（宁波工程学院 · 王孝萌 · 2026 毕业设计）
 * @dev
 *   职责：在 DataRegistry 之前为参与者（数据提供者 / 数据消费者）提供一个
 *        实名 / 机构化身份登记层。DataRegistry 在执行 register() 时可以先调用
 *        本合约校验调用者是否已登记为激活身份，从而避免匿名账户随意确权。
 *
 *   设计原则：
 *     1. 每个钱包地址最多对应一条身份记录
 *     2. 身份材料的原文不上链，只登记其 SHA-256 哈希（authHash），保护隐私
 *     3. authHash 在全局唯一，防止同一份身份材料被多个钱包重复注册
 *     4. 持有人可随时更新机构名/角色，或将自己的身份注销（软删除）
 */
contract IdentityRegistry {

    // ─────────────────────────────
    // 身份角色枚举
    // ─────────────────────────────
    enum Role { Undefined, Provider, Consumer, Both }

    // ─────────────────────────────
    // 数据结构
    // ─────────────────────────────
    struct Identity {
        address wallet;        // 钱包地址
        string  orgName;       // 机构 / 组织名（可为个人实名）
        Role    role;          // 提供者 / 消费者 / 双身份
        bytes32 authHash;      // 身份凭证材料 SHA-256 哈希
        uint256 registeredAt;  // 首次登记时间戳
        uint256 updatedAt;     // 最近更新时间戳
        bool    isActive;      // 是否处于激活状态
    }

    mapping(address => Identity) public identities;
    mapping(bytes32 => address)  public authHashToWallet;  // 防重复注册
    uint256 public totalIdentities;

    // ─────────────────────────────
    // 事件
    // ─────────────────────────────
    event IdentityRegistered(address indexed wallet, string orgName, Role role, uint256 timestamp);
    event IdentityUpdated(address indexed wallet, string orgName, Role role, uint256 timestamp);
    event IdentityDeactivated(address indexed wallet, uint256 timestamp);

    // ─────────────────────────────
    // 修饰器
    // ─────────────────────────────
    modifier onlyActive() {
        require(identities[msg.sender].isActive, "IdentityRegistry: not active");
        _;
    }

    // ─────────────────────────────
    // 核心接口
    // ─────────────────────────────

    /**
     * @notice 登记新的身份
     * @param orgName   机构 / 个人实名
     * @param role      角色（Provider / Consumer / Both）
     * @param authHash  身份凭证材料的 SHA-256 哈希
     */
    function register(string calldata orgName, Role role, bytes32 authHash) external {
        require(bytes(orgName).length > 0,                  "IdentityRegistry: orgName empty");
        require(role != Role.Undefined,                      "IdentityRegistry: invalid role");
        require(authHash != bytes32(0),                      "IdentityRegistry: authHash empty");
        require(identities[msg.sender].registeredAt == 0,    "IdentityRegistry: already registered");
        require(authHashToWallet[authHash] == address(0),    "IdentityRegistry: authHash already used");

        identities[msg.sender] = Identity({
            wallet: msg.sender,
            orgName: orgName,
            role: role,
            authHash: authHash,
            registeredAt: block.timestamp,
            updatedAt: block.timestamp,
            isActive: true
        });

        authHashToWallet[authHash] = msg.sender;
        totalIdentities += 1;
        emit IdentityRegistered(msg.sender, orgName, role, block.timestamp);
    }

    /**
     * @notice 更新自己的机构名与角色
     */
    function update(string calldata orgName, Role role) external onlyActive {
        require(bytes(orgName).length > 0,  "IdentityRegistry: orgName empty");
        require(role != Role.Undefined,     "IdentityRegistry: invalid role");

        Identity storage id = identities[msg.sender];
        id.orgName = orgName;
        id.role = role;
        id.updatedAt = block.timestamp;

        emit IdentityUpdated(msg.sender, orgName, role, block.timestamp);
    }

    /**
     * @notice 注销自己的身份（软删除）
     */
    function deactivate() external onlyActive {
        identities[msg.sender].isActive = false;
        identities[msg.sender].updatedAt = block.timestamp;
        emit IdentityDeactivated(msg.sender, block.timestamp);
    }

    /**
     * @notice 查询某个钱包的身份记录
     */
    function getIdentity(address wallet) external view returns (Identity memory) {
        return identities[wallet];
    }

    /**
     * @notice 判断某个钱包是否为激活的合法身份（供 DataRegistry 调用）
     * @dev    DataRegistry.register() 内部可调用此方法做前置校验
     */
    function isActive(address wallet) external view returns (bool) {
        return identities[wallet].isActive;
    }

    /**
     * @notice 判断身份是否满足指定角色（例如要求必须是 Provider）
     */
    function hasRole(address wallet, Role required) external view returns (bool) {
        Identity memory id = identities[wallet];
        if (!id.isActive) return false;
        if (required == Role.Both) return id.role == Role.Both;
        return id.role == required || id.role == Role.Both;
    }

    /**
     * @notice 根据身份凭证哈希反查钱包地址（用于身份凭证防重）
     */
    function lookupByAuthHash(bytes32 authHash) external view returns (address) {
        return authHashToWallet[authHash];
    }
}
