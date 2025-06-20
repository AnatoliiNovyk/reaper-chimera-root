# [Homebrew 4] - Chimera Project
# Module: laundry.py
# Purpose: To automatically launder funds by swapping them through a DEX.

import time
from web3 import Web3

# --- CONFIGURATION ---
# We will use Polygon for this example due to low fees.
RPC_URL = "https://polygon-rpc.com/"

# The wallet with "dirty" funds (must have a private key and some native currency like MATIC).
SOURCE_WALLET = {
    "address": "0xd2bE94A469F2fDA038F1E9aB722F38D2C3251Fb7",
    "private_key": "0x6d19ba9a8853b6cd524862a75e539b2c6030877f0449a7f91926a429c25386b6"
}

# Your clean, final destination wallet.
CLEAN_WALLET_ADDRESS = "0xC83f11E0C3D4Cee59931bB3b280b64E1e8F508C1"

# DEX and Token addresses on Polygon
QUICKSWAP_ROUTER_ADDRESS = "0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff"
WMATIC_ADDRESS = "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270" # Wrapped MATIC
USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174" # USD Coin

# --- ABIs ---
# Minimal ABI for Uniswap V2-style Router
ROUTER_ABI = '[{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"payable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactETHForTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"payable","type":"function"}]'
ERC20_ABI = '[{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},{"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"success","type":"bool"}],"type":"function"}]'


def main():
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        print("[CHIMERA] FATAL: Could not connect to the network.")
        return

    print(f"[CHIMERA] Connected to network with Chain ID: {w3.eth.chain_id}")
    
    source_address = SOURCE_WALLET['address']
    private_key = SOURCE_WALLET['private_key']
    
    router_contract = w3.eth.contract(address=QUICKSWAP_ROUTER_ADDRESS, abi=ROUTER_ABI)
    usdc_contract = w3.eth.contract(address=USDC_ADDRESS, abi=ERC20_ABI)
    
    # --- Step 1: Swap native currency (MATIC) for USDC ---
    print("\n--- STEP 1: Swapping MATIC for USDC ---")
    
    balance_matic = w3.eth.get_balance(source_address)
    # Leave a small amount for gas fees
    amount_to_swap = balance_matic - w3.to_wei(0.1, 'ether')
    
    if amount_to_swap <= 0:
        print("[CHIMERA] Insufficient MATIC balance to perform swap.")
        return

    print(f"Swapping {w3.from_wei(amount_to_swap, 'ether')} MATIC...")
    
    nonce = w3.eth.get_transaction_count(source_address)
    deadline = int(time.time()) + 600 # 10 minute deadline

    tx_swap_matic = router_contract.functions.swapExactETHForTokens(
        0, # amountOutMin
        [WMATIC_ADDRESS, USDC_ADDRESS],
        source_address,
        deadline
    ).build_transaction({
        'from': source_address,
        'value': amount_to_swap,
        'gas': 300000,
        'gasPrice': w3.eth.gas_price,
        'nonce': nonce,
    })

    signed_tx = w3.eth.account.sign_transaction(tx_swap_matic, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Swap transaction sent. Hash: {tx_hash.hex()}. Waiting for confirmation...")
    
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print("STEP 1 COMPLETE: MATIC successfully swapped for USDC.")

    # --- Step 2: Approve the router to spend our new USDC ---
    print("\n--- STEP 2: Approving router to spend USDC ---")
    
    usdc_balance = usdc_contract.functions.balanceOf(source_address).call()
    if usdc_balance <= 0:
        print("[CHIMERA] No USDC to approve. Something went wrong.")
        return
        
    nonce = w3.eth.get_transaction_count(source_address)

    tx_approve = usdc_contract.functions.approve(
        QUICKSWAP_ROUTER_ADDRESS,
        usdc_balance # Approve the full balance
    ).build_transaction({
        'from': source_address,
        'gas': 100000,
        'gasPrice': w3.eth.gas_price,
        'nonce': nonce,
    })
    
    signed_tx_approve = w3.eth.account.sign_transaction(tx_approve, private_key)
    tx_hash_approve = w3.eth.send_raw_transaction(signed_tx_approve.rawTransaction)
    print(f"Approve transaction sent. Hash: {tx_hash_approve.hex()}. Waiting for confirmation...")
    
    w3.eth.wait_for_transaction_receipt(tx_hash_approve)
    print("STEP 2 COMPLETE: Router approved to spend USDC.")
    
    # --- Step 3: Swap USDC back to WMATIC and send to clean wallet ---
    print("\n--- STEP 3: Swapping USDC for WMATIC and sending to clean wallet ---")
    
    nonce = w3.eth.get_transaction_count(source_address)
    
    tx_swap_usdc = router_contract.functions.swapExactTokensForTokens(
        usdc_balance,
        0, # amountOutMin
        [USDC_ADDRESS, WMATIC_ADDRESS],
        CLEAN_WALLET_ADDRESS, # Send the final tokens directly to the clean wallet
        deadline
    ).build_transaction({
        'from': source_address,
        'gas': 300000,
        'gasPrice': w3.eth.gas_price,
        'nonce': nonce,
    })
    
    signed_tx_swap_usdc = w3.eth.account.sign_transaction(tx_swap_usdc, private_key)
    tx_hash_swap_usdc = w3.eth.send_raw_transaction(signed_tx_swap_usdc.rawTransaction)
    print(f"Final swap transaction sent. Hash: {tx_hash_swap_usdc.hex()}. Waiting for confirmation...")
    
    w3.eth.wait_for_transaction_receipt(tx_hash_swap_usdc)
    print("STEP 3 COMPLETE: Funds have been laundered and sent to the clean wallet.")
    print("\n[CHIMERA] LAUNDRY CYCLE COMPLETE.")


if __name__ == '__main__':
    main()
