#!/usr/bin/env python3
"""
Phase 1 — local Anvil fork.

Proves the core mechanism the whole project rests on: a local Anvil node,
forked from real chain state, exposes `debug_traceCall` — the RPC method the
free public RPC in `web3/preflight-agent` refused with `-32601 method does
not exist`. That's the exact limitation this project removes.

Flow:
  1. Launch `anvil --fork-url <FORK_RPC_URL>` as a subprocess — our own,
     local, disposable Ethereum node.
  2. Wait until it's accepting RPC calls.
  3. Run TWO candidate transactions against real mainnet WETH, using one of
     Anvil's pre-funded default dev accounts as `from`. No private key
     involved anywhere — `debug_traceCall` simulates a call, it never signs
     or sends anything:
       a. SUCCESS CASE — WETH.deposit(): wrap 1 ETH into WETH. Should succeed.
       b. REVERT CASE  — WETH.withdraw(): try to unwrap 1 WETH from an
          account that never deposited any (balance 0 on this fresh fork).
          Should revert — this is the case a real pre-flight check exists
          to catch, *before* the user signs anything.
  4. Teardown: kill the anvil subprocess.

SAFETY: 100% local simulation. No private key, no real transaction ever sent.
"""

import os

from dotenv import load_dotenv
from web3 import Web3

from anvil_lifecycle import ANVIL_RPC_URL, start_anvil, wait_until_ready

load_dotenv()

FORK_RPC_URL = os.getenv("FORK_RPC_URL", "https://ethereum-rpc.publicnode.com")
FORK_BLOCK_NUMBER = os.getenv("FORK_BLOCK_NUMBER") or None

# Anvil's first default dev account (from its well-known test mnemonic).
# Pre-funded with 10000 ETH on every anvil instance, fork or not — that's
# why no private key is needed anywhere in this script.
DEV_ACCOUNT = Web3.to_checksum_address("0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266")

# Real mainnet WETH contract — a real target, but nothing is ever sent to it.
WETH_ADDRESS = Web3.to_checksum_address("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2")
DEPOSIT_SELECTOR = "0xd0e30db0"  # keccak256("deposit()")[:4] — WETH's wrap function
WITHDRAW_SELECTOR = "0x2e1a7d4d"  # keccak256("withdraw(uint256)")[:4] — WETH's unwrap function


def encode_uint256(value: int) -> str:
    """ABI-encode a single uint256 arg: 32 bytes, left-padded, big-endian, no '0x'."""
    return hex(value)[2:].zfill(64)


def preflight_check(w3: Web3, label: str, candidate_tx: dict) -> None:
    """Run debug_traceCall on a candidate tx and print a plain verdict.

    This is the exact shape the future agent tool will wrap: build tx,
    trace it, decide "would this revert?" — *before* anything is signed.
    """
    print(f"\n--- {label} ---")
    print("candidate transaction (never signed, never sent):")
    print(candidate_tx)

    trace = w3.manager.request_blocking(
        "debug_traceCall", [candidate_tx, "latest", {"tracer": "callTracer"}]
    )
    print("debug_traceCall result:")
    print(trace)

    if "error" in trace:
        print(f"VERDICT: would REVERT ({trace['error']}) — do not sign this.")
    else:
        print(f"VERDICT: would SUCCEED (gas used: {int(trace['gasUsed'], 16)}).")


def main() -> None:
    proc = start_anvil(FORK_RPC_URL, FORK_BLOCK_NUMBER)
    w3 = Web3(Web3.HTTPProvider(ANVIL_RPC_URL))
    wait_until_ready(w3, proc)

    print(f"anvil forked at block {w3.eth.block_number}, chain_id={w3.eth.chain_id}")
    balance = w3.from_wei(w3.eth.get_balance(DEV_ACCOUNT), "ether")
    print(f"{DEV_ACCOUNT} balance: {balance} ETH (pre-funded by anvil)")

    deposit_tx = {
        "from": DEV_ACCOUNT,
        "to": WETH_ADDRESS,
        "data": DEPOSIT_SELECTOR,
        "value": hex(w3.to_wei(1, "ether")),
    }
    preflight_check(w3, "SUCCESS CASE: WETH.deposit(1 ETH)", deposit_tx)

    # This account never called deposit() above for real (debug_traceCall
    # never commits state) — so its WETH balance on this fork is still 0.
    withdraw_tx = {
        "from": DEV_ACCOUNT,
        "to": WETH_ADDRESS,
        "data": WITHDRAW_SELECTOR + encode_uint256(w3.to_wei(1, "ether")),
        "value": "0x0",
    }
    preflight_check(w3, "REVERT CASE: WETH.withdraw(1 WETH) with 0 balance", withdraw_tx)


if __name__ == "__main__":
    main()
