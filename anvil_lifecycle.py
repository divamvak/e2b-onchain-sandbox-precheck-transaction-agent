"""
Shared Anvil process lifecycle — used by both `anvil_fork.py` (Phase 1 demo,
two hardcoded cases) and `preflight_check.py` (Phase 3, one arbitrary tx from
an agent tool call). Extracted because both need the identical "start anvil,
wait until it accepts RPC calls, find the binary without relying on PATH"
logic, not because of speculative future reuse.
"""

import atexit
import os
import shutil
import subprocess
import time

from web3 import Web3

ANVIL_PORT = 8545
ANVIL_RPC_URL = f"http://127.0.0.1:{ANVIL_PORT}"


def resolve_anvil_bin() -> str:
    """Find the anvil binary without depending on PATH.

    PATH set at the container-image level (E2B template `set_envs`) does
    not reliably reach `subprocess.Popen` inside a `commands.run()` process
    — confirmed live (worked locally via PATH, `FileNotFoundError` inside
    the E2B sandbox). Checking `~/.foundry/bin` directly sidesteps that
    entirely and works in both places.
    """
    found = shutil.which("anvil")
    if found:
        return found
    candidate = os.path.expanduser("~/.foundry/bin/anvil")
    if os.path.exists(candidate):
        return candidate
    raise RuntimeError("anvil binary not found on PATH or in ~/.foundry/bin")


def start_anvil(fork_rpc_url: str, fork_block_number: str | None = None) -> subprocess.Popen:
    cmd = [resolve_anvil_bin(), "--fork-url", fork_rpc_url, "--port", str(ANVIL_PORT)]
    if fork_block_number:
        cmd += ["--fork-block-number", fork_block_number]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    atexit.register(proc.terminate)
    return proc


def wait_until_ready(w3: Web3, proc: subprocess.Popen, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("anvil exited early — check fork_rpc_url / that anvil is installed")
        if w3.is_connected():
            return
        time.sleep(0.2)
    raise TimeoutError(f"anvil did not come up within {timeout}s")
