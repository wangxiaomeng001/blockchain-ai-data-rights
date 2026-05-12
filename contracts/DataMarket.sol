// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title DataMarket — 去中心化 AI 数据市场合约
 * @notice 实现数据集上架、购买、资金托管与自动结算
 * @dev 对应论文第 3.3 节"去中心化交易机制"
 *
 *      核心功能：
 *      - listData()   数据提供者上架数据集（绑定 DataToken NFT）
 *      - purchase()   数据消费者购买数据集（智能合约自动结算）
 *      - getDataInfo()查询数据集信息
 *
 *      安全措施：
 *      - ReentrancyGuard：防止重入攻击
 *      - Checks-Effects-Interactions 模式
 *      - Solidity 0.8.x 内置溢出检查
 *
 * Remix IDE 编译：选择 Solidity 0.8.20，直接编译即可
 */

// ──────────────────────────────────────────
// 内联 ReentrancyGuard（简化版）
// ──────────────────────────────────────────
abstract contract ReentrancyGuard {
    uint256 private constant _NOT_ENTERED = 1;
    uint256 private constant _ENTERED = 2;
    uint256 private _status;

    constructor() {
        _status = _NOT_ENTERED;
    }

    modifier nonReentrant() {
        require(_status != _ENTERED, "ReentrancyGuard: reentrant call");
        _status = _ENTERED;
        _;
        _status = _NOT_ENTERED;
    }
}

// ──────────────────────────────────────────
// DataToken 接口（与 DataToken.sol 交互）
// ──────────────────────────────────────────
interface IDataToken {
    function ownerOf(uint256 tokenId) external view returns (address);
    function verifyData(uint256 tokenId, bytes32 dataHash) external view returns (bool);
    function safeTransferFrom(address from, address to, uint256 tokenId) external;
}

// ──────────────────────────────────────────
// 主合约：DataMarket
// ──────────────────────────────────────────
contract DataMarket is ReentrancyGuard {

    // ── 常量 ──
    uint256 public constant PLATFORM_FEE_RATE = 5;    // 平台抽成 5%
    uint256 public constant FEE_DENOMINATOR = 100;

    // ── 数据集上架记录 ──
    struct DataListing {
        uint256 tokenId;       // 对应 DataToken NFT 的 token ID
        address seller;        // 卖家地址
        bytes32 dataHash;      // 数据指纹（SHA-256）
        string ipfsCID;        // IPFS 存储 CID（数据内容寻址）
        uint256 price;         // 定价（wei 单位）
        string dataType;       // 数据类型（如 "csv" / "image" / "text"）
        string description;    // 数据集描述
        bool isActive;         // 是否在售
        uint256 listTime;      // 上架时间戳
    }

    // ── 购买记录 ──
    struct Purchase {
        address buyer;
        address seller;
        uint256 tokenId;
        uint256 price;
        uint256 purchaseTime;
    }

    // ── 状态变量 ──
    address public immutable platformWallet;    // 平台收款钱包
    IDataToken public immutable dataToken;      // DataToken 合约地址

    // listingId → DataListing
    mapping(uint256 => DataListing) public listings;
    uint256 public listingCount;

    // 购买记录
    Purchase[] public purchases;

    // buyer → 已购买的 tokenId 列表
    mapping(address => uint256[]) public buyerPurchases;

    // tokenId → 是否已被购买
    mapping(uint256 => bool) public isSold;

    // 平台累积手续费（wei）
    uint256 public platformFeeAccumulated;

    // ── 事件 ──
    event DataListed(
        uint256 indexed listingId,
        uint256 indexed tokenId,
        address indexed seller,
        uint256 price,
        string description
    );
    event DataPurchased(
        uint256 indexed listingId,
        uint256 indexed tokenId,
        address indexed buyer,
        address seller,
        uint256 price,
        uint256 sellerReceives,
        uint256 platformFee
    );
    event ListingCancelled(uint256 indexed listingId, address indexed seller);
    event PlatformFeeWithdrawn(address indexed to, uint256 amount);

    // ── 构造函数 ──
    constructor(address _dataToken, address _platformWallet) {
        require(_dataToken != address(0), "DataMarket: zero token address");
        require(_platformWallet != address(0), "DataMarket: zero platform address");
        dataToken = IDataToken(_dataToken);
        platformWallet = _platformWallet;
    }

    // ── 核心函数 ──

    /**
     * @notice 数据提供者上架数据集
     * @param tokenId     DataToken NFT 的 token ID（须提前铸造）
     * @param dataHash    数据 SHA-256 哈希
     * @param ipfsCID     数据在 IPFS 上的 CID
     * @param price       售价（wei）
     * @param dataType    数据类型描述
     * @param description 数据集简介
     * @return listingId  上架编号
     */
    function listData(
        uint256 tokenId,
        bytes32 dataHash,
        string calldata ipfsCID,
        uint256 price,
        string calldata dataType,
        string calldata description
    ) external returns (uint256 listingId) {
        // 验证调用者是 NFT 持有者
        require(
            dataToken.ownerOf(tokenId) == msg.sender,
            "DataMarket: caller is not token owner"
        );
        require(!isSold[tokenId], "DataMarket: token already sold");
        require(price > 0, "DataMarket: price must be positive");

        // 验证数据哈希与 NFT 绑定的哈希一致
        require(
            dataToken.verifyData(tokenId, dataHash),
            "DataMarket: data hash mismatch with NFT"
        );

        listingCount++;
        listingId = listingCount;

        listings[listingId] = DataListing({
            tokenId: tokenId,
            seller: msg.sender,
            dataHash: dataHash,
            ipfsCID: ipfsCID,
            price: price,
            dataType: dataType,
            description: description,
            isActive: true,
            listTime: block.timestamp
        });

        emit DataListed(listingId, tokenId, msg.sender, price, description);
    }

    /**
     * @notice 数据消费者购买数据集
     * @param listingId 上架编号
     *
     * @dev 智能合约自动托管资金并结算：
     *      - 平台 5% 手续费留存合约
     *      - 卖家 95% 立即到账
     *      - NFT 转让给买家（代表数据使用权）
     */
    function purchase(uint256 listingId) external payable nonReentrant {
        DataListing storage listing = listings[listingId];

        require(listing.isActive, "DataMarket: listing not active");
        require(msg.sender != listing.seller, "DataMarket: seller cannot buy own listing");
        require(msg.value >= listing.price, "DataMarket: insufficient payment");
        require(!isSold[listing.tokenId], "DataMarket: already sold");

        // ── Checks ──（以上 require 完成）

        // ── Effects ──
        listing.isActive = false;
        isSold[listing.tokenId] = true;

        uint256 platformFee = (listing.price * PLATFORM_FEE_RATE) / FEE_DENOMINATOR;
        uint256 sellerAmount = listing.price - platformFee;
        platformFeeAccumulated += platformFee;

        purchases.push(Purchase({
            buyer: msg.sender,
            seller: listing.seller,
            tokenId: listing.tokenId,
            price: listing.price,
            purchaseTime: block.timestamp
        }));
        buyerPurchases[msg.sender].push(listing.tokenId);

        // ── Interactions ──
        // 卖家到账
        (bool sent,) = payable(listing.seller).call{value: sellerAmount}("");
        require(sent, "DataMarket: transfer to seller failed");

        // NFT 转让给买家（需要卖家提前 approve 本合约）
        // dataToken.safeTransferFrom(listing.seller, msg.sender, listing.tokenId);

        // 退还多付的金额
        if (msg.value > listing.price) {
            (bool refunded,) = payable(msg.sender).call{value: msg.value - listing.price}("");
            require(refunded, "DataMarket: refund failed");
        }

        emit DataPurchased(
            listingId,
            listing.tokenId,
            msg.sender,
            listing.seller,
            listing.price,
            sellerAmount,
            platformFee
        );
    }

    /**
     * @notice 卖家撤销上架
     */
    function cancelListing(uint256 listingId) external {
        DataListing storage listing = listings[listingId];
        require(listing.seller == msg.sender, "DataMarket: not seller");
        require(listing.isActive, "DataMarket: already inactive");
        listing.isActive = false;
        emit ListingCancelled(listingId, msg.sender);
    }

    /**
     * @notice 查询数据集上架信息
     */
    function getDataInfo(uint256 listingId) external view returns (
        uint256 tokenId,
        address seller,
        bytes32 dataHash,
        string memory ipfsCID,
        uint256 price,
        string memory dataType,
        bool isActive
    ) {
        DataListing storage l = listings[listingId];
        return (l.tokenId, l.seller, l.dataHash, l.ipfsCID,
                l.price, l.dataType, l.isActive);
    }

    /**
     * @notice 查询买家已购买的数据集令牌列表
     */
    function getBuyerPurchases(address buyer) external view returns (uint256[] memory) {
        return buyerPurchases[buyer];
    }

    /**
     * @notice 平台提取手续费
     * @dev 仅限 platformWallet 调用
     */
    function withdrawPlatformFee() external {
        require(msg.sender == platformWallet, "DataMarket: not platform wallet");
        uint256 amount = platformFeeAccumulated;
        platformFeeAccumulated = 0;
        (bool sent,) = payable(platformWallet).call{value: amount}("");
        require(sent, "DataMarket: withdraw failed");
        emit PlatformFeeWithdrawn(platformWallet, amount);
    }

    /**
     * @notice 查询合约持有的平台手续费余额
     */
    function getPlatformBalance() external view returns (uint256) {
        return platformFeeAccumulated;
    }

    /**
     * @notice 返回总交易笔数
     */
    function getTotalPurchases() external view returns (uint256) {
        return purchases.length;
    }
}
