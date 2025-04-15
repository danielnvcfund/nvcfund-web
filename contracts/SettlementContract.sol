// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title SettlementContract
 * @dev Smart contract for secure settlements between financial institutions
 */
contract SettlementContract {
    address public owner;
    uint256 public settlementCounter;
    uint256 public feePercentage; // Fee in basis points (1/100 of a percent)
    address public feeCollector;
    
    // Settlement statuses
    enum SettlementStatus { Pending, Completed, Cancelled, Disputed, Resolved }
    
    // Settlement structure
    struct Settlement {
        uint256 id;
        string transactionId; // Reference to platform transaction ID
        address from;
        address to;
        uint256 amount;
        uint256 fee;
        uint256 timestamp;
        SettlementStatus status;
        string metadata; // Additional settlement data in JSON format
    }
    
    // Mapping from settlement ID to Settlement
    mapping(uint256 => Settlement) public settlements;
    
    // Mapping from platform transaction ID to settlement ID
    mapping(string => uint256) public transactionToSettlement;
    
    // Mapping of addresses to their settlement IDs
    mapping(address => uint256[]) public accountSettlements;
    
    // Events
    event SettlementCreated(uint256 indexed id, string transactionId, address indexed from, address indexed to, uint256 amount);
    event SettlementCompleted(uint256 indexed id, string transactionId);
    event SettlementCancelled(uint256 indexed id, string transactionId);
    event SettlementDisputed(uint256 indexed id, string transactionId, string reason);
    event SettlementResolved(uint256 indexed id, string transactionId);
    event FeeCollected(uint256 indexed settlementId, uint256 feeAmount);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event FeePercentageChanged(uint256 oldFeePercentage, uint256 newFeePercentage);
    event FeeCollectorChanged(address oldFeeCollector, address newFeeCollector);
    
    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "SettlementContract: caller is not the owner");
        _;
    }
    
    modifier settlementExists(uint256 settlementId) {
        require(settlements[settlementId].id == settlementId, "SettlementContract: settlement does not exist");
        _;
    }
    
    modifier onlyParticipant(uint256 settlementId) {
        require(
            settlements[settlementId].from == msg.sender || settlements[settlementId].to == msg.sender,
            "SettlementContract: caller is not a participant in this settlement"
        );
        _;
    }
    
    /**
     * @dev Constructor sets the owner, fee percentage, and fee collector
     * @param _feePercentage Fee percentage in basis points (1 basis point = 0.01%)
     * @param _feeCollector Address that collects fees
     */
    constructor(uint256 _feePercentage, address _feeCollector) {
        owner = msg.sender;
        feePercentage = _feePercentage;
        feeCollector = _feeCollector;
        settlementCounter = 0;
    }
    
    /**
     * @dev Create a new settlement
     * @param transactionId Platform transaction ID
     * @param to Recipient address
     * @param metadata Additional settlement data
     * @return settlementId The ID of the created settlement
     */
    function createSettlement(string memory transactionId, address to, string memory metadata) external payable returns (uint256) {
        require(msg.value > 0, "SettlementContract: amount must be greater than 0");
        require(to != address(0), "SettlementContract: recipient cannot be zero address");
        require(bytes(transactionId).length > 0, "SettlementContract: transactionId cannot be empty");
        require(transactionToSettlement[transactionId] == 0, "SettlementContract: transaction already has a settlement");
        
        // Calculate fee
        uint256 fee = (msg.value * feePercentage) / 10000;
        uint256 amountAfterFee = msg.value - fee;
        
        // Increment settlement counter
        settlementCounter++;
        
        // Create settlement
        Settlement memory newSettlement = Settlement({
            id: settlementCounter,
            transactionId: transactionId,
            from: msg.sender,
            to: to,
            amount: amountAfterFee,
            fee: fee,
            timestamp: block.timestamp,
            status: SettlementStatus.Pending,
            metadata: metadata
        });
        
        // Store settlement
        settlements[settlementCounter] = newSettlement;
        transactionToSettlement[transactionId] = settlementCounter;
        
        // Add to account settlements
        accountSettlements[msg.sender].push(settlementCounter);
        accountSettlements[to].push(settlementCounter);
        
        // Emit event
        emit SettlementCreated(settlementCounter, transactionId, msg.sender, to, amountAfterFee);
        
        return settlementCounter;
    }
    
    /**
     * @dev Complete a settlement
     * @param settlementId ID of the settlement to complete
     */
    function completeSettlement(uint256 settlementId) external onlyOwner settlementExists(settlementId) {
        Settlement storage settlement = settlements[settlementId];
        
        require(settlement.status == SettlementStatus.Pending, "SettlementContract: settlement is not pending");
        
        // Update status
        settlement.status = SettlementStatus.Completed;
        
        // Transfer amount to recipient
        (bool success, ) = settlement.to.call{value: settlement.amount}("");
        require(success, "SettlementContract: transfer to recipient failed");
        
        // Transfer fee to fee collector
        if (settlement.fee > 0) {
            (bool feeSuccess, ) = feeCollector.call{value: settlement.fee}("");
            require(feeSuccess, "SettlementContract: fee transfer failed");
            emit FeeCollected(settlementId, settlement.fee);
        }
        
        // Emit event
        emit SettlementCompleted(settlementId, settlement.transactionId);
    }
    
    /**
     * @dev Cancel a settlement
     * @param settlementId ID of the settlement to cancel
     */
    function cancelSettlement(uint256 settlementId) external settlementExists(settlementId) {
        Settlement storage settlement = settlements[settlementId];
        
        require(settlement.status == SettlementStatus.Pending, "SettlementContract: settlement is not pending");
        require(msg.sender == settlement.from || msg.sender == owner, "SettlementContract: not authorized to cancel");
        
        // Update status
        settlement.status = SettlementStatus.Cancelled;
        
        // Return funds to sender
        uint256 totalAmount = settlement.amount + settlement.fee;
        (bool success, ) = settlement.from.call{value: totalAmount}("");
        require(success, "SettlementContract: refund failed");
        
        // Emit event
        emit SettlementCancelled(settlementId, settlement.transactionId);
    }
    
    /**
     * @dev Dispute a settlement
     * @param settlementId ID of the settlement to dispute
     * @param reason Reason for the dispute
     */
    function disputeSettlement(uint256 settlementId, string memory reason) external settlementExists(settlementId) onlyParticipant(settlementId) {
        Settlement storage settlement = settlements[settlementId];
        
        require(settlement.status == SettlementStatus.Pending, "SettlementContract: settlement is not pending");
        
        // Update status
        settlement.status = SettlementStatus.Disputed;
        
        // Emit event
        emit SettlementDisputed(settlementId, settlement.transactionId, reason);
    }
    
    /**
     * @dev Resolve a disputed settlement
     * @param settlementId ID of the settlement to resolve
     * @param completeSettlement Whether to complete the settlement (true) or cancel it (false)
     */
    function resolveDispute(uint256 settlementId, bool completeSettlement) external onlyOwner settlementExists(settlementId) {
        Settlement storage settlement = settlements[settlementId];
        
        require(settlement.status == SettlementStatus.Disputed, "SettlementContract: settlement is not disputed");
        
        if (completeSettlement) {
            // Complete the settlement
            settlement.status = SettlementStatus.Completed;
            
            // Transfer amount to recipient
            (bool success, ) = settlement.to.call{value: settlement.amount}("");
            require(success, "SettlementContract: transfer to recipient failed");
            
            // Transfer fee to fee collector
            if (settlement.fee > 0) {
                (bool feeSuccess, ) = feeCollector.call{value: settlement.fee}("");
                require(feeSuccess, "SettlementContract: fee transfer failed");
                emit FeeCollected(settlementId, settlement.fee);
            }
            
            emit SettlementCompleted(settlementId, settlement.transactionId);
        } else {
            // Cancel the settlement
            settlement.status = SettlementStatus.Cancelled;
            
            // Return funds to sender
            uint256 totalAmount = settlement.amount + settlement.fee;
            (bool success, ) = settlement.from.call{value: totalAmount}("");
            require(success, "SettlementContract: refund failed");
            
            emit SettlementCancelled(settlementId, settlement.transactionId);
        }
        
        // Mark as resolved
        settlement.status = SettlementStatus.Resolved;
        emit SettlementResolved(settlementId, settlement.transactionId);
    }
    
    /**
     * @dev Get settlement by ID
     * @param settlementId ID of the settlement
     * @return Settlement data
     */
    function getSettlement(uint256 settlementId) external view settlementExists(settlementId) returns (
        uint256 id,
        string memory transactionId,
        address from,
        address to,
        uint256 amount,
        uint256 fee,
        uint256 timestamp,
        SettlementStatus status,
        string memory metadata
    ) {
        Settlement memory settlement = settlements[settlementId];
        return (
            settlement.id,
            settlement.transactionId,
            settlement.from,
            settlement.to,
            settlement.amount,
            settlement.fee,
            settlement.timestamp,
            settlement.status,
            settlement.metadata
        );
    }
    
    /**
     * @dev Get settlement ID by transaction ID
     * @param transactionId Platform transaction ID
     * @return Settlement ID
     */
    function getSettlementIdByTransactionId(string memory transactionId) external view returns (uint256) {
        uint256 settlementId = transactionToSettlement[transactionId];
        require(settlementId != 0, "SettlementContract: settlement not found for transaction ID");
        return settlementId;
    }
    
    /**
     * @dev Get all settlements for an account
     * @param account Address of the account
     * @return Array of settlement IDs
     */
    function getAccountSettlements(address account) external view returns (uint256[] memory) {
        return accountSettlements[account];
    }
    
    /**
     * @dev Set fee percentage
     * @param _feePercentage New fee percentage in basis points
     */
    function setFeePercentage(uint256 _feePercentage) external onlyOwner {
        require(_feePercentage <= 1000, "SettlementContract: fee percentage cannot exceed 10%");
        uint256 oldFeePercentage = feePercentage;
        feePercentage = _feePercentage;
        emit FeePercentageChanged(oldFeePercentage, _feePercentage);
    }
    
    /**
     * @dev Set fee collector address
     * @param _feeCollector New fee collector address
     */
    function setFeeCollector(address _feeCollector) external onlyOwner {
        require(_feeCollector != address(0), "SettlementContract: fee collector cannot be zero address");
        address oldFeeCollector = feeCollector;
        feeCollector = _feeCollector;
        emit FeeCollectorChanged(oldFeeCollector, _feeCollector);
    }
    
    /**
     * @dev Transfer ownership of the contract
     * @param newOwner Address of the new owner
     */
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "SettlementContract: new owner cannot be zero address");
        address oldOwner = owner;
        owner = newOwner;
        emit OwnershipTransferred(oldOwner, newOwner);
    }
    
    /**
     * @dev Get contract balance
     * @return Contract balance
     */
    function getContractBalance() external view returns (uint256) {
        return address(this).balance;
    }
    
    /**
     * @dev Withdraw funds in case of emergency
     * @param amount Amount to withdraw
     */
    function emergencyWithdraw(uint256 amount) external onlyOwner {
        require(amount <= address(this).balance, "SettlementContract: insufficient balance");
        (bool success, ) = owner.call{value: amount}("");
        require(success, "SettlementContract: withdrawal failed");
    }
}