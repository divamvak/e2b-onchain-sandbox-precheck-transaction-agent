"""
Phase 2 — E2B sandbox template definition.

Defines a custom E2B image: Debian/Python base + Foundry (for `anvil`) +
our Phase-1 script (`anvil_fork.py`). Built once (`build_template.py`),
versioned, reused by every sandbox we open afterwards.

NOTE (2026-08-25): E2B's current template API is this Python `Template()`
builder — the Dockerfile + e2b.toml approach from the original theory
write-up has been superseded. Confirmed live against docs.e2b.dev before
writing this; same underlying idea (build once, versioned image), different
syntax.
"""

from e2b import Template

# Foundry installs its binaries under ~/.foundry/bin. We reference that path
# explicitly everywhere (instead of relying on `export PATH=...` persisting
# across build steps, which — like Dockerfile RUN instructions — it does not).
FOUNDRY_BIN = "/home/user/.foundry/bin"
FULL_PATH = f"{FOUNDRY_BIN}:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

template = (
    Template()
    .from_python_image("3.12")
    .apt_install(["curl", "ca-certificates", "tar", "gzip"])
    # Same 2-step install as we did locally: (1) get foundryup, (2) run it
    # to actually fetch forge/cast/anvil/chisel.
    .run_cmd("curl -L https://foundry.paradigm.xyz | bash")
    .run_cmd(f"{FOUNDRY_BIN}/foundryup")
    .pip_install(["web3", "python-dotenv"])
    .set_envs({"PATH": FULL_PATH})
    .set_workdir("/home/user")
    .copy("anvil_lifecycle.py", "/home/user/anvil_lifecycle.py")
    .copy("anvil_fork.py", "/home/user/anvil_fork.py")
    .copy("preflight_check.py", "/home/user/preflight_check.py")
)
