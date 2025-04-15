// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title MultiSigWallet
 * @dev Multi-signature wallet for secure high-value transactions
 */
contract MultiSigWallet {
    address[] public owners;
    uint256 public requiredConfirmations;
    uint256 public transactionCount;
    
    struct Transaction {
        address destination;
        uint256 value;
        bytes data;
        bool executed;
        uint256 confirmations;
    }
    
    // Mapping from transaction ID to Transaction
    mapping(uint256 => Transaction) public transactions;
    
    // Mapping from transaction ID to owner address to confirmation status
    mapping(uint256 => mapping(address => bool)) public confirmations;
    
    // Mapping of owner address to bool (is owner)
    mapping(address => bool) public isOwner;
    
    // Events
    event Deposit(address indexed sender, uint256 value);
    event Submission(uint256 indexed transactionId);
    event Confirmation(address indexed sender, uint256 indexed transactionId);
    event Execution(uint256 indexed transactionId);
    event ExecutionFailure(uint256 indexed transactionId);
    event OwnerAddition(address indexed owner);
    event OwnerRemoval(address indexed owner);
    event RequirementChange(uint256 required);
    
    // Modifiers
    modifier onlyOwner() {
        require(isOwner[msg.sender], "MultiSigWallet: caller is not an owner");
        _;
    }
    
    modifier transactionExists(uint256 transactionId) {
        require(transactions[transactionId].destination != address(0), "MultiSigWallet: transaction does not exist");
        _;
    }
    
    modifier notConfirmed(uint256 transactionId) {
        require(!confirmations[transactionId][msg.sender], "MultiSigWallet: transaction already confirmed");
        _;
    }
    
    modifier notExecuted(uint256 transactionId) {
        require(!transactions[transactionId].executed, "MultiSigWallet: transaction already executed");
        _;
    }
    
    /**
     * @dev Constructor sets initial owners and required confirmations
     * @param _owners Array of owner addresses
     * @param _requiredConfirmations Number of required confirmations for a transaction
     */
    constructor(address[] memory _owners, uint256 _requiredConfirmations) {
        require(_owners.length > 0, "MultiSigWallet: owners required");
        require(_requiredConfirmations > 0 && _requiredConfirmations <= _owners.length, "MultiSigWallet: invalid required confirmations");
        
        for (uint256 i = 0; i < _owners.length; i++) {
            address owner = _owners[i];
            
            require(owner != address(0), "MultiSigWallet: null owner");
            require(!isOwner[owner], "MultiSigWallet: duplicate owner");
            
            isOwner[owner] = true;
            owners.push(owner);
        }
        
        requiredConfirmations = _requiredConfirmations;
    }
    
    /**
     * @dev Receive function to accept Ether deposits
     */
    receive() external payable {
        if (msg.value > 0) {
            emit Deposit(msg.sender, msg.value);
        }
    }
    
    /**
     * @dev Submit a new transaction
     * @param destination Transaction target address
     * @param value Transaction value in wei
     * @param data Transaction data payload
     * @return transactionId Returns transaction ID
     */
    function submitTransaction(address destination, uint256 value, bytes memory data) public onlyOwner returns (uint256) {
        uint256 transactionId = transactionCount;
        
        transactions[transactionId] = Transaction({
            destination: destination,
            value: value,
            data: data,
            executed: false,
            confirmations: 0
        });
        
        transactionCount += 1;
        emit Submission(transactionId);
        
        confirmTransaction(transactionId);
        return transactionId;
    }
    
    /**
     * @dev Confirm a transaction
     * @param transactionId Transaction ID
     */
    function confirmTransaction(uint256 transactionId) 
        public
        onlyOwner
        transactionExists(transactionId)
        notConfirmed(transactionId)
        notExecuted(transactionId)
    {
        confirmations[transactionId][msg.sender] = true;
        transactions[transactionId].confirmations += 1;
        emit Confirmation(msg.sender, transactionId);
        
        executeTransaction(transactionId);
    }
    
    /**
     * @dev Revoke a confirmation for a transaction
     * @param transactionId Transaction ID
     */
    function revokeConfirmation(uint256 transactionId)
        public
        onlyOwner
        transactionExists(transactionId)
        notExecuted(transactionId)
    {
        require(confirmations[transactionId][msg.sender], "MultiSigWallet: transaction not confirmed");
        
        confirmations[transactionId][msg.sender] = false;
        transactions[transactionId].confirmations -= 1;
    }
    
    /**
     * @dev Execute a confirmed transaction
     * @param transactionId Transaction ID
     */
    function executeTransaction(uint256 transactionId)
        public
        onlyOwner
        transactionExists(transactionId)
        notExecuted(transactionId)
    {
        if (transactions[transactionId].confirmations >= requiredConfirmations) {
            Transaction storage transaction = transactions[transactionId];
            
            transaction.executed = true;
            
            (bool success, ) = transaction.destination.call{value: transaction.value}(transaction.data);
            if (success) {
                emit Execution(transactionId);
            } else {
                emit ExecutionFailure(transactionId);
                transaction.executed = false;
            }
        }
    }
    
    /**
     * @dev Add a new owner
     * @param owner Address of new owner
     */
    function addOwner(address owner)
        public
        onlyOwner
    {
        require(owner != address(0), "MultiSigWallet: null owner");
        require(!isOwner[owner], "MultiSigWallet: owner exists");
        require(owners.length < 10, "MultiSigWallet: max owners reached");
        
        isOwner[owner] = true;
        owners.push(owner);
        emit OwnerAddition(owner);
    }
    
    /**
     * @dev Remove an owner
     * @param owner Address of owner to remove
     */
    function removeOwner(address owner)
        public
        onlyOwner
    {
        require(isOwner[owner], "MultiSigWallet: not owner");
        require(owners.length > requiredConfirmations, "MultiSigWallet: cannot remove owner below required confirmations");
        
        isOwner[owner] = false;
        
        for (uint256 i = 0; i < owners.length; i++) {
            if (owners[i] == owner) {
                owners[i] = owners[owners.length - 1];
                owners.pop();
                break;
            }
        }
        
        if (requiredConfirmations > owners.length) {
            changeRequirement(owners.length);
        }
        
        emit OwnerRemoval(owner);
    }
    
    /**
     * @dev Replace an owner with a new owner
     * @param owner Address of owner to replace
     * @param newOwner Address of new owner
     */
    function replaceOwner(address owner, address newOwner)
        public
        onlyOwner
    {
        require(owner != newOwner, "MultiSigWallet: invalid replacement");
        require(isOwner[owner], "MultiSigWallet: not owner");
        require(!isOwner[newOwner], "MultiSigWallet: duplicate owner");
        
        for (uint256 i = 0; i < owners.length; i++) {
            if (owners[i] == owner) {
                owners[i] = newOwner;
                break;
            }
        }
        
        isOwner[owner] = false;
        isOwner[newOwner] = true;
        
        emit OwnerRemoval(owner);
        emit OwnerAddition(newOwner);
    }
    
    /**
     * @dev Change requirement to a new value
     * @param _requiredConfirmations Number of required confirmations
     */
    function changeRequirement(uint256 _requiredConfirmations)
        public
        onlyOwner
    {
        require(_requiredConfirmations > 0, "MultiSigWallet: confirmations must be positive");
        require(_requiredConfirmations <= owners.length, "MultiSigWallet: confirmations exceeds owners");
        
        requiredConfirmations = _requiredConfirmations;
        emit RequirementChange(_requiredConfirmations);
    }
    
    /**
     * @dev Get number of confirmations for a transaction
     * @param transactionId Transaction ID
     * @return Number of confirmations
     */
    function getConfirmationCount(uint256 transactionId)
        public
        view
        returns (uint256)
    {
        return transactions[transactionId].confirmations;
    }
    
    /**
     * @dev Get transaction count
     * @param pending Include pending transactions
     * @param executed Include executed transactions
     * @return count Transaction count
     */
    function getTransactionCount(bool pending, bool executed)
        public
        view
        returns (uint256 count)
    {
        for (uint256 i = 0; i < transactionCount; i++) {
            if ((pending && !transactions[i].executed) || (executed && transactions[i].executed)) {
                count += 1;
            }
        }
    }
    
    /**
     * @dev Get list of owners
     * @return List of owner addresses
     */
    function getOwners()
        public
        view
        returns (address[] memory)
    {
        return owners;
    }
    
    /**
     * @dev Get list of transaction IDs in defined range
     * @param from Index start position
     * @param to Index end position
     * @param pending Include pending transactions
     * @param executed Include executed transactions
     * @return _transactionIds Returns array of transaction IDs
     */
    function getTransactionIds(uint256 from, uint256 to, bool pending, bool executed)
        public
        view
        returns (uint256[] memory _transactionIds)
    {
        uint256[] memory transactionIdsTemp = new uint256[](transactionCount);
        uint256 count = 0;
        uint256 i;
        
        for (i = 0; i < transactionCount; i++) {
            if ((pending && !transactions[i].executed) || (executed && transactions[i].executed)) {
                transactionIdsTemp[count] = i;
                count += 1;
            }
        }
        
        _transactionIds = new uint256[](to - from);
        for (i = from; i < to; i++) {
            _transactionIds[i - from] = transactionIdsTemp[i];
        }
    }
    
    /**
     * @dev Get wallet balance
     * @return Wallet balance
     */
    function getBalance() public view returns (uint256) {
        return address(this).balance;
    }
}