"""
Phase 2 — build the custom E2B template defined in `e2b_template.py`.

Run this ONCE (and again only when `e2b_template.py` or `anvil_fork.py`
changes) — it uploads the build context and builds the image on E2B's
infrastructure. Needs E2B_API_KEY in `.env`.

Usage: .venv/bin/python build_template.py
"""

from dotenv import load_dotenv
from e2b import Template, default_build_logger

from e2b_template import template

load_dotenv()

TEMPLATE_NAME = "sandbox-anvil-fork"

if __name__ == "__main__":
    Template.build(
        template,
        TEMPLATE_NAME,
        cpu_count=1,
        memory_mb=1024,
        # Hit a flaky cached "resize-disk" step twice in a row (E2B-side,
        # not our template) — skip_cache reliably avoids it. Build is fast
        # (~1 min) either way, so no real cost to always skipping.
        skip_cache=True,
        on_build_logs=default_build_logger(),
    )
    print(f"\nBuilt template '{TEMPLATE_NAME}'. Now run: .venv/bin/python e2b_run.py")
