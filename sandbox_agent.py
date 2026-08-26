#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["web3", "python-dotenv", "langgraph", "langchain-anthropic", "e2b"]
# ///
"""
Phase 3 — On-Chain Pre-Flight Sandbox agent.

Same "what will this transaction ACTUALLY do, before I sign it?" question as
`web3/preflight-agent`, but the simulation now runs via a real Anvil fork
inside an isolated, disposable E2B sandbox (full `debug_traceCall` trace)
instead of a plain `eth_call` against a public RPC.

The LLM does not decide whether a transaction is risky — it only narrates
the deterministic verdict from `sandbox_tools.py`.

100% simulation. Nothing is ever signed or sent.

Run: ./sandbox_agent.py
"""

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from web3 import Web3

from sandbox_tools import SANDBOX_TOOLS

load_dotenv()

llm = ChatAnthropic(model="claude-sonnet-4-6", max_tokens=1536)

SYSTEM_PROMPT = """You are a "pre-flight" transaction-safety checker for
Ethereum mainnet. You have ONE tool: preflight_check_via_sandbox(to, data,
value) — it simulates an UNSIGNED transaction on a real, disposable fork of
mainnet running inside an isolated sandbox, and tells you whether it would
succeed or revert, WITHOUT ever signing or broadcasting anything.

Your job: call the tool on the transaction you are given, then explain in
plain language, for someone about to sign this in their wallet, whether it
would succeed or fail and why. Never invent function names, addresses, or
outcomes that were not in the tool output."""

agent = create_react_agent(llm, SANDBOX_TOOLS, prompt=SYSTEM_PROMPT)

# Demo: the REVERT case from Phase 1/2 (WETH.withdraw with 0 balance) — the
# exact kind of thing a pre-flight check exists to catch before signing.
WETH_MAINNET = Web3.to_checksum_address("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2")
WITHDRAW_SELECTOR = "0x2e1a7d4d"
AMOUNT_1_ETH = hex(10**18)[2:].zfill(64)
DEMO_DATA = WITHDRAW_SELECTOR + AMOUNT_1_ETH

DEMO_INSTRUCTION = (
    f"I'm about to sign a transaction. Here are the raw details:\n"
    f"to: {WETH_MAINNET}\n"
    f"data: {DEMO_DATA}\n"
    f"value: 0\n"
    f"Before I sign, tell me what this transaction actually does and whether "
    f"it would succeed."
)


def main() -> None:
    print("Pre-Flight Sandbox Agent\n")
    print(f"Instruction:\n{DEMO_INSTRUCTION}\n")

    result = agent.invoke({"messages": [{"role": "user", "content": DEMO_INSTRUCTION}]})

    summary = result["messages"][-1].content
    print("REPORT\n" + "-" * 50)
    print(summary)


if __name__ == "__main__":
    main()
