// SPDX-License-Identifier: MIT
pragma solidity ^0.8.10;

// Интерфейсы для взаимодействия с протоколами
interface IPool {
    function flashLoanSimple(address receiverAddress, address asset, uint256 amount, bytes calldata params, uint16 referralCode) external;
}

interface IERC20 {
    function approve(address spender, uint256 amount) external returns (bool);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

interface IUniswapV2Router {
    function swapExactTokensForTokens(uint amountIn, uint amountOutMin, address[] calldata path, address to, uint deadline) external returns (uint[] memory amounts);
}

contract AttackBlade {
    address public owner;
    address public constant AAVE_POOL = 0x794a61358D6845594F94dc1DB02A252b5b4814aD; // Aave V3 Pool на Polygon
    
    // Адреса токенов и роутеров на Polygon
    address public constant DAI = 0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063;
    address public constant WETH = 0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619;
    address public constant SUSHI_ROUTER = 0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506;

    constructor() {
        owner = msg.sender;
    }

    // Эта функция будет вызвана Aave после выдачи кредита
    function executeOperation(address asset, uint256 amount, uint256 premium, address initiator, bytes calldata params) external returns (bool) {
        require(msg.sender == AAVE_POOL, "Caller must be Aave V3 Pool");
        
        // --- Шаг 1: Арбитражная сделка ---
        uint256 amountToSwap = IERC20(asset).balanceOf(address(this));
        
        IERC20(asset).approve(SUSHI_ROUTER, amountToSwap);
        
        address[] memory pathDaiToWeth = new address[](2);
        pathDaiToWeth[0] = asset;
        pathDaiToWeth[1] = WETH;
        
        IUniswapV2Router(SUSHI_ROUTER).swapExactTokensForTokens(amountToSwap, 0, pathDaiToWeth, address(this), block.timestamp);
        
        uint256 wethBalance = IERC20(WETH).balanceOf(address(this));
        
        IERC20(WETH).approve(SUSHI_ROUTER, wethBalance);
        
        address[] memory pathWethToDai = new address[](2);
        pathWethToDai[0] = WETH;
        pathWethToDai[1] = asset;

        IUniswapV2Router(SUSHI_ROUTER).swapExactTokensForTokens(wethBalance, 0, pathWethToDai, address(this), block.timestamp);
        
        // --- Шаг 2: Возврат кредита и изъятие прибыли ---
        uint256 totalDebt = amount + premium;
        IERC20(asset).approve(AAVE_POOL, totalDebt);
        
        uint256 finalDaiBalance = IERC20(asset).balanceOf(address(this));
        if (finalDaiBalance > totalDebt) {
            uint256 profit = finalDaiBalance - totalDebt;
            IERC20(asset).transfer(owner, profit);
        }
        
        return true;
    }
    
    // --- Функция-триггер для начала атаки ---
    function startAttack(address loanToken, uint256 loanAmount) external {
        require(msg.sender == owner, "Only owner can start the attack");
        IPool(AAVE_POOL).flashLoanSimple(address(this), loanToken, loanAmount, bytes(""), 0);
    }
    
    function withdraw(address tokenAddress) external {
        require(msg.sender == owner);
        uint256 balance = IERC20(tokenAddress).balanceOf(address(this));
        IERC20(tokenAddress).transfer(owner, balance);
    }

    receive() external payable {}
}
