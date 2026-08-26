"""
Phase 2 — open a sandbox from our custom template, run the Phase-1
Anvil-fork script INSIDE it, print the result, tear down.

This is the sandbox lifecycle in full: open (Sandbox.create) -> execute
(commands.run) -> read result (stdout) -> teardown (sandbox.kill()).
Everything from Phase 1 (fork, debug_traceCall, verdicts) is unchanged —
it just now runs on E2B's infrastructure instead of this machine.

Usage: .venv/bin/python e2b_run.py
"""

import os

from dotenv import load_dotenv
from e2b import Sandbox

from build_template import TEMPLATE_NAME

load_dotenv()

FORK_RPC_URL = os.getenv("FORK_RPC_URL", "https://ethereum-rpc.publicnode.com")


def main() -> None:
    print(f"opening sandbox from template '{TEMPLATE_NAME}'...")
    sandbox = Sandbox.create(template=TEMPLATE_NAME, timeout=120)
    print(f"sandbox open: {sandbox.sandbox_id}")

    try:
        result = sandbox.commands.run(
            f"FORK_RPC_URL={FORK_RPC_URL} python3 anvil_fork.py",
            cwd="/home/user",
            timeout=90,
        )
        print("\n--- stdout from inside the sandbox ---")
        print(result.stdout)
        if result.stderr:
            print("--- stderr ---")
            print(result.stderr)
        print(f"exit code: {result.exit_code}")
    finally:
        sandbox.kill()
        print("\nsandbox killed — no trace of it left.")


if __name__ == "__main__":
    main()
