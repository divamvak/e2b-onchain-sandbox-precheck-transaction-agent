"""
Phase 3 — the tool: `preflight_check_via_sandbox`.

Wraps the full Phase-2 sandbox lifecycle (open -> run `preflight_check.py`
inside it -> read its JSON verdict -> kill the sandbox) as a single
`@tool` a LangGraph agent can call on any candidate transaction it's given.
Same "agent decides WHEN to call it, deterministic code decides everything
about HOW it runs and what counts as risky" pattern as `web3/preflight-agent`.

A fresh sandbox is opened and killed on every call (not a long-lived one
reused across calls) — same guarantee as `e2b_run.py`: no state persists
between checks, nothing lingers if something goes wrong mid-call.

SAFETY: 100% simulation, same as `web3/preflight-agent`. Nothing is ever
signed or sent — this runs `debug_traceCall` against a disposable Anvil
fork inside a disposable E2B sandbox.
"""

import json
import os

from dotenv import load_dotenv
from e2b import Sandbox
from langchain_core.tools import tool
from web3 import Web3

from build_template import TEMPLATE_NAME

load_dotenv()

FORK_RPC_URL = os.getenv("FORK_RPC_URL", "https://ethereum-rpc.publicnode.com")
FORK_BLOCK_NUMBER = os.getenv("FORK_BLOCK_NUMBER") or ""


@tool
def preflight_check_via_sandbox(to: str, data: str, value: int = 0) -> str:
    """Pre-flight check an UNSIGNED transaction by simulating it on a real,
    disposable fork of Ethereum mainnet, running inside an isolated E2B
    sandbox.

    Unlike a plain `eth_call` against a public RPC, this uses
    `debug_traceCall` against our own local Anvil fork (spun up fresh
    inside the sandbox) — giving a full execution trace, not just a
    success/revert flag. The sandbox is destroyed immediately after, so
    nothing about this call persists anywhere.

    Args:
        to: The contract address the transaction would call.
        data: The transaction's calldata (hex string, e.g. '0xd0e30db0').
        value: ETH to send with the call, in wei. Usually 0 for contract
            calls like approve/transfer/deposit-with-args.

    Returns:
        The simulation verdict (would succeed or would revert, and why),
        plus the block number the fork was taken from.
    """
    if not Web3.is_address(to):
        return f"Invalid 'to' address: {to!r}"
    to = Web3.to_checksum_address(to)

    sandbox = Sandbox.create(template=TEMPLATE_NAME, timeout=120)
    try:
        # `data` is attacker/agent-controlled calldata — pass it via `envs=`
        # (not shell-interpolated into `cmd`) so it can never be read as
        # shell syntax inside the sandbox.
        result = sandbox.commands.run(
            "python3 preflight_check.py",
            envs={
                "TX_TO": to,
                "TX_DATA": data,
                "TX_VALUE_WEI": str(value),
                "FORK_RPC_URL": FORK_RPC_URL,
                "FORK_BLOCK_NUMBER": FORK_BLOCK_NUMBER,
            },
            cwd="/home/user",
            timeout=90,
        )
    finally:
        sandbox.kill()

    if result.exit_code != 0 and not result.stdout.strip():
        return f"Sandbox run failed (exit {result.exit_code}): {result.stderr}"

    try:
        verdict = json.loads(result.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return f"Could not parse sandbox output as JSON.\nstdout: {result.stdout}\nstderr: {result.stderr}"

    if verdict["verdict"] == "ERROR":
        return f"Simulation error (not a revert, likely a bad input or RPC issue): {verdict['detail']}"

    return (
        f"Forked mainnet at block {verdict['block_number']} (chain_id={verdict['chain_id']}).\n"
        f"VERDICT: would {verdict['verdict']} — {verdict['detail']}."
    )


SANDBOX_TOOLS = [preflight_check_via_sandbox]
