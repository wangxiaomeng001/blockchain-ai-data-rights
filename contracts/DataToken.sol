// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// 引入 OpenZeppelin ERC-721 标准合约
// 真实部署时使用：import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
// 下方为内联简化版本，可在 Remix IDE 直接编译（无需安装依赖）

/**
 * @title DataToken — 数据权益 NFT 合约
 * @notice 基于 ERC-721 标准实现数据集确权令牌
 * @dev 对应论文第 3.2 节"数据确权机制"
 *      每个数据集铸造唯一 NFT，令牌 ID 与链上数据指纹绑定
 *
 * Remix IDE 使用说明：
 *   1. 打开 https://remix.ethereum.org
 *   2. 新建文件 DataToken.sol，粘贴本代码
 *   3. 选择 Compiler 0.8.20，点击 Compile
 *   4. 部署到 JavaScript VM（无需 gas / 钱包）
 */

// ──────────────────────────────────────────
// 内联 Ownable（简化版）
// ──────────────────────────────────────────
abstract contract Ownable {
    address private _owner;

    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    constructor(address initialOwner) {
        _owner = initialOwner;
        emit OwnershipTransferred(address(0), initialOwner);
    }

    modifier onlyOwner() {
        require(msg.sender == _owner, "Ownable: caller is not the owner");
        _;
    }

    function owner() public view returns (address) {
        return _owner;
    }
}

// ──────────────────────────────────────────
// 主合约：DataToken（ERC-721 确权令牌）
// ──────────────────────────────────────────
contract DataToken is Ownable {
    // ── 状态变量 ──
    string public name = "AI Data Rights Token";  // 代币名称
    string public symbol = "ADRT";                // 代币符号

    uint256 private _tokenIdCounter;              // Token ID 自增计数器

    // tokenId → 所有者地址
    mapping(uint256 => address) private _owners;

    // 所有者地址 → 持有代币数量
    mapping(address => uint256) private _balances;

    // tokenId → 已授权的操作者地址
    mapping(uint256 => address) private _tokenApprovals;

    // 所有者 → 全局授权操作者 → 是否授权
    mapping(address => mapping(address => bool)) private _operatorApprovals;

    // tokenId → 数据集元数据 URI（通常是 IPFS 地址）
    mapping(uint256 => string) private _tokenURIs;

    // tokenId → 数据哈希（SHA-256，32字节）
    mapping(uint256 => bytes32) public dataHashes;

    // 数据哈希 → tokenId（防止同一数据重复确权）
    mapping(bytes32 => uint256) private _hashToTokenId;

    // ── 事件 ──
    event Transfer(address indexed from, address indexed to, uint256 indexed tokenId);
    event Approval(address indexed owner, address indexed approved, uint256 indexed tokenId);
    event ApprovalForAll(address indexed owner, address indexed operator, bool approved);
    event DataMinted(uint256 indexed tokenId, address indexed owner,
                     bytes32 dataHash, string tokenURI);
    event DataTransferred(uint256 indexed tokenId, address indexed from,
                          address indexed to, uint256 timestamp);

    // ── 构造函数 ──
    constructor() Ownable(msg.sender) {}

    // ── 标准 ERC-721 查询接口 ──

    /**
     * @notice 查询某地址持有的 NFT 数量
     */
    function balanceOf(address owner_) public view returns (uint256) {
        require(owner_ != address(0), "ERC721: balance query for zero address");
        return _balances[owner_];
    }

    /**
     * @notice 查询某 tokenId 的所有者地址
     */
    function ownerOf(uint256 tokenId) public view returns (address) {
        address owner_ = _owners[tokenId];
        require(owner_ != address(0), "ERC721: owner query for nonexistent token");
        return owner_;
    }

    /**
     * @notice 返回 Token 元数据 URI（通常是 ipfs://CID）
     */
    function tokenURI(uint256 tokenId) public view returns (string memory) {
        require(_owners[tokenId] != address(0), "ERC721: URI query for nonexistent token");
        return _tokenURIs[tokenId];
    }

    // ── 核心业务函数 ──

    /**
     * @notice 铸造新的数据确权 NFT
     * @param to        令牌接收者（数据集所有者）
     * @param dataHash  数据文件 SHA-256 哈希（32 字节）
     * @param uri       元数据 URI（IPFS CID 或 HTTP URI）
     * @return tokenId  新铸造的令牌 ID
     *
     * @dev 同一数据哈希不可重复铸造，防止一数据多权
     */
    function mint(
        address to,
        bytes32 dataHash,
        string calldata uri
    ) external onlyOwner returns (uint256) {
        require(to != address(0), "DataToken: mint to zero address");
        require(_hashToTokenId[dataHash] == 0, "DataToken: data already registered");

        _tokenIdCounter++;
        uint256 tokenId = _tokenIdCounter;

        // 建立双向映射
        _owners[tokenId] = to;
        _balances[to]++;
        _tokenURIs[tokenId] = uri;
        dataHashes[tokenId] = dataHash;
        _hashToTokenId[dataHash] = tokenId;

        emit Transfer(address(0), to, tokenId);
        emit DataMinted(tokenId, to, dataHash, uri);

        return tokenId;
    }

    /**
     * @notice 转让 NFT 所有权（即数据集权益转让）
     * @param from    原所有者
     * @param to      新所有者
     * @param tokenId 令牌 ID
     */
    function safeTransferFrom(
        address from,
        address to,
        uint256 tokenId
    ) external {
        require(to != address(0), "DataToken: transfer to zero address");
        require(_owners[tokenId] == from, "DataToken: transfer of token that is not own");
        require(
            msg.sender == from ||
            _tokenApprovals[tokenId] == msg.sender ||
            _operatorApprovals[from][msg.sender],
            "DataToken: caller is not owner nor approved"
        );

        _balances[from]--;
        _balances[to]++;
        _owners[tokenId] = to;

        emit Transfer(from, to, tokenId);
        emit DataTransferred(tokenId, from, to, block.timestamp);
    }

    /**
     * @notice 验证数据完整性
     * @param tokenId   令牌 ID
     * @param dataHash  待验证的数据哈希
     * @return          true = 数据未被篡改
     */
    function verifyData(uint256 tokenId, bytes32 dataHash) external view returns (bool) {
        return dataHashes[tokenId] == dataHash;
    }

    /**
     * @notice 通过数据哈希查询令牌 ID
     * @dev 0 表示该哈希未注册
     */
    function getTokenByHash(bytes32 dataHash) external view returns (uint256) {
        return _hashToTokenId[dataHash];
    }

    /**
     * @notice 查询当前已铸造的 NFT 总量
     */
    function totalSupply() external view returns (uint256) {
        return _tokenIdCounter;
    }

    // ── 授权函数 ──

    function approve(address to, uint256 tokenId) external {
        address owner_ = _owners[tokenId];
        require(msg.sender == owner_ || _operatorApprovals[owner_][msg.sender],
                "DataToken: approve caller is not owner");
        _tokenApprovals[tokenId] = to;
        emit Approval(owner_, to, tokenId);
    }

    function setApprovalForAll(address operator, bool approved) external {
        _operatorApprovals[msg.sender][operator] = approved;
        emit ApprovalForAll(msg.sender, operator, approved);
    }

    function getApproved(uint256 tokenId) external view returns (address) {
        return _tokenApprovals[tokenId];
    }

    function isApprovedForAll(address owner_, address operator) external view returns (bool) {
        return _operatorApprovals[owner_][operator];
    }
}
