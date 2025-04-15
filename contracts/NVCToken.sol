// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title IERC20
 * @dev Interface for the ERC20 standard
 */
interface IERC20 {
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function allowance(address owner, address spender) external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
    
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
}

/**
 * @title NVCToken
 * @dev Implementation of the NVC Token
 */
contract NVCToken is IERC20 {
    string public name = "NVC Banking Token";
    string public symbol = "NVC";
    uint8 public decimals = 18;
    uint256 private _totalSupply;
    
    address public owner;
    
    mapping(address => uint256) private _balances;
    mapping(address => mapping(address => uint256)) private _allowances;
    
    // List of addresses that are frozen
    mapping(address => bool) private _frozen;
    
    // Events
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event AddressFreeze(address indexed target, bool frozen);
    event Mint(address indexed to, uint256 amount);
    event Burn(address indexed from, uint256 amount);
    
    // Modifiers
    modifier onlyOwner() {
        require(msg.sender == owner, "NVCToken: caller is not the owner");
        _;
    }
    
    modifier notFrozen(address account) {
        require(!_frozen[account], "NVCToken: account is frozen");
        _;
    }
    
    /**
     * @dev Constructor
     * @param initialSupply Initial token supply
     * @param initialOwner Address of the initial owner
     */
    constructor(uint256 initialSupply, address initialOwner) {
        require(initialOwner != address(0), "NVCToken: invalid owner address");
        
        _totalSupply = initialSupply * 10 ** decimals;
        _balances[initialOwner] = _totalSupply;
        owner = initialOwner;
        
        emit Transfer(address(0), initialOwner, _totalSupply);
    }
    
    /**
     * @dev Returns the total token supply
     * @return Total supply
     */
    function totalSupply() public view override returns (uint256) {
        return _totalSupply;
    }
    
    /**
     * @dev Returns the balance of an account
     * @param account Address of the account
     * @return Balance
     */
    function balanceOf(address account) public view override returns (uint256) {
        return _balances[account];
    }
    
    /**
     * @dev Transfers tokens to a specified address
     * @param recipient Address to transfer to
     * @param amount Amount to transfer
     * @return success Whether transfer was successful
     */
    function transfer(address recipient, uint256 amount) public override notFrozen(msg.sender) notFrozen(recipient) returns (bool) {
        _transfer(msg.sender, recipient, amount);
        return true;
    }
    
    /**
     * @dev Returns the allowance granted to a spender by an owner
     * @param _owner Owner address
     * @param spender Spender address
     * @return Allowance amount
     */
    function allowance(address _owner, address spender) public view override returns (uint256) {
        return _allowances[_owner][spender];
    }
    
    /**
     * @dev Approves an address to spend a specified amount of tokens
     * @param spender Address to approve
     * @param amount Amount to approve
     * @return success Whether approval was successful
     */
    function approve(address spender, uint256 amount) public override notFrozen(msg.sender) notFrozen(spender) returns (bool) {
        _approve(msg.sender, spender, amount);
        return true;
    }
    
    /**
     * @dev Transfers tokens from one address to another
     * @param sender Address to transfer from
     * @param recipient Address to transfer to
     * @param amount Amount to transfer
     * @return success Whether transfer was successful
     */
    function transferFrom(address sender, address recipient, uint256 amount) public override notFrozen(sender) notFrozen(recipient) notFrozen(msg.sender) returns (bool) {
        _transfer(sender, recipient, amount);
        
        uint256 currentAllowance = _allowances[sender][msg.sender];
        require(currentAllowance >= amount, "NVCToken: transfer amount exceeds allowance");
        unchecked {
            _approve(sender, msg.sender, currentAllowance - amount);
        }
        
        return true;
    }
    
    /**
     * @dev Increases the allowance of a spender
     * @param spender Address of the spender
     * @param addedValue Value to add to allowance
     * @return success Whether operation was successful
     */
    function increaseAllowance(address spender, uint256 addedValue) public notFrozen(msg.sender) notFrozen(spender) returns (bool) {
        _approve(msg.sender, spender, _allowances[msg.sender][spender] + addedValue);
        return true;
    }
    
    /**
     * @dev Decreases the allowance of a spender
     * @param spender Address of the spender
     * @param subtractedValue Value to subtract from allowance
     * @return success Whether operation was successful
     */
    function decreaseAllowance(address spender, uint256 subtractedValue) public notFrozen(msg.sender) notFrozen(spender) returns (bool) {
        uint256 currentAllowance = _allowances[msg.sender][spender];
        require(currentAllowance >= subtractedValue, "NVCToken: decreased allowance below zero");
        unchecked {
            _approve(msg.sender, spender, currentAllowance - subtractedValue);
        }
        
        return true;
    }
    
    /**
     * @dev Mints new tokens
     * @param to Address to mint tokens to
     * @param amount Amount to mint
     */
    function mint(address to, uint256 amount) public onlyOwner notFrozen(to) {
        require(to != address(0), "NVCToken: mint to the zero address");
        
        _totalSupply += amount;
        _balances[to] += amount;
        emit Transfer(address(0), to, amount);
        emit Mint(to, amount);
    }
    
    /**
     * @dev Burns tokens
     * @param from Address to burn tokens from
     * @param amount Amount to burn
     */
    function burn(address from, uint256 amount) public onlyOwner {
        require(from != address(0), "NVCToken: burn from the zero address");
        
        uint256 accountBalance = _balances[from];
        require(accountBalance >= amount, "NVCToken: burn amount exceeds balance");
        unchecked {
            _balances[from] = accountBalance - amount;
        }
        _totalSupply -= amount;
        
        emit Transfer(from, address(0), amount);
        emit Burn(from, amount);
    }
    
    /**
     * @dev Freezes or unfreezes an account
     * @param account Address to freeze/unfreeze
     * @param freeze Whether to freeze (true) or unfreeze (false)
     */
    function freezeAccount(address account, bool freeze) public onlyOwner {
        require(account != address(0), "NVCToken: freeze zero address");
        require(account != owner, "NVCToken: cannot freeze owner");
        
        _frozen[account] = freeze;
        emit AddressFreeze(account, freeze);
    }
    
    /**
     * @dev Checks if an account is frozen
     * @param account Address to check
     * @return Whether account is frozen
     */
    function isFrozen(address account) public view returns (bool) {
        return _frozen[account];
    }
    
    /**
     * @dev Transfers ownership of the contract
     * @param newOwner Address of the new owner
     */
    function transferOwnership(address newOwner) public onlyOwner {
        require(newOwner != address(0), "NVCToken: new owner is the zero address");
        require(newOwner != owner, "NVCToken: new owner is the current owner");
        
        address oldOwner = owner;
        owner = newOwner;
        emit OwnershipTransferred(oldOwner, newOwner);
    }
    
    /**
     * @dev Internal function to transfer tokens
     * @param sender Sender address
     * @param recipient Recipient address
     * @param amount Amount to transfer
     */
    function _transfer(address sender, address recipient, uint256 amount) internal {
        require(sender != address(0), "NVCToken: transfer from the zero address");
        require(recipient != address(0), "NVCToken: transfer to the zero address");
        
        uint256 senderBalance = _balances[sender];
        require(senderBalance >= amount, "NVCToken: transfer amount exceeds balance");
        unchecked {
            _balances[sender] = senderBalance - amount;
        }
        _balances[recipient] += amount;
        
        emit Transfer(sender, recipient, amount);
    }
    
    /**
     * @dev Internal function to approve spending of tokens
     * @param _owner Owner address
     * @param spender Spender address
     * @param amount Amount to approve
     */
    function _approve(address _owner, address spender, uint256 amount) internal {
        require(_owner != address(0), "NVCToken: approve from the zero address");
        require(spender != address(0), "NVCToken: approve to the zero address");
        
        _allowances[_owner][spender] = amount;
        emit Approval(_owner, spender, amount);
    }
}