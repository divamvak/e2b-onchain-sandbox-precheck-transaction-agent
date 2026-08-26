#!/usr/bin/env python3
"""
Phase 3 — runs INSIDE the E2B sandbox. Checks exactly ONE candidate
transaction (to/data/value), supplied by the caller via env vars — unlike
`anvil_fork.py`'s two hardcoded demo cases, this is the script the agent
tool actually drives with whatever transaction it's given.

Prints a SINGLE line of JSON to stdout and nothing else. The host-side tool
(`sandbox_tools.py`) parses that line — JSON instead of the prose format
`anvil_fork.py` uses, because a tool return value needs a reliable parse,
not something to eyeball.

Env vars:
  FORK_RPC_URL    - real RPC to fork chain state from (required)
  FORK_BLOCK_NUMBER - optional, pin to a specific block
  TX_TO           - contract address the candidate tx would call (required)
  TX_DATA         - candidate tx calldata, hex string (required)
  TX_VALUE_WEI    - ETH sent with the call, in wei (optional, default "0")
  TX_FROM         - address to simulate as (optional, defaults to Anvil's
                     pre-funded dev account — same one anvil_fork.py uses)
"""

import json
import os
import sys

from web3 import Web3

from anvil_lifecycle import ANVIL_RPC_URL, start_anvil, wait_until_ready

DEV_ACCOUNT = Web3.to_checksum_address("0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266")


def main() -> None:
    fork_rpc_url = os.environ["FORK_RPC_URL"]
    fork_block_number = os.environ.get("FORK_BLOCK_NUMBER") or None
    to = Web3.to_checksum_address(os.environ["TX_TO"])
    data = os.environ["TX_DATA"]
    value_wei = int(os.environ.get("TX_VALUE_WEI", "0"))
    from_address = Web3.to_checksum_address(os.environ.get("TX_FROM") or DEV_ACCOUNT)

    proc = start_anvil(fork_rpc_url, fork_block_number)
    w3 = Web3(Web3.HTTPProvider(ANVIL_RPC_URL))
    wait_until_ready(w3, proc)

    candidate_tx = {
        "from": from_address,
        "to": to,
        "data": data,
        "value": hex(value_wei),
    }

    result = {
        "candidate_tx": candidate_tx,
        "block_number": w3.eth.block_number,
        "chain_id": w3.eth.chain_id,
    }

    try:
        trace = w3.manager.request_blocking(
            "debug_traceCall", [candidate_tx, "latest", {"tracer": "callTracer"}]
        )
        trace = dict(trace)
        result["trace"] = trace
        if "error" in trace:
            result["verdict"] = "REVERT"
            result["detail"] = trace["error"]
        else:
            result["verdict"] = "SUCCEED"
            result["detail"] = f"gas used: {int(trace['gasUsed'], 16)}"
    except Exception as e:
        result["verdict"] = "ERROR"
        result["detail"] = f"simulation could not run: {e}"

    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({"verdict": "ERROR", "detail": f"script failed: {e}"}))
        sys.exit(1)
