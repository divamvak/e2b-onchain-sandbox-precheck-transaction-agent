# Project: sandbox — On-Chain Pre-Flight Sandbox v2 (learning)

Εκπαιδευτικό project για **sandbox execution** — το θεμελιώδες skill του να τρέχεις
LLM/agent-initiated κώδικα με ασφάλεια, απομονωμένα από το πραγματικό σύστημα.

> Το on-chain κομμάτι (Anvil, forking, tx simulation) είναι το **πρόσχημα**, όχι το μάθημα.
> Το πραγματικό μάθημα: sandbox lifecycle (open → execute → read → teardown), πώς
> ενσωματώνεται sandbox call ως tool μέσα σε agent loop, resource/timeout/error handling.
> Ισχύουν επίσης το ενδιάμεσο `../../CLAUDE.md` και το global `~/.claude/CLAUDE.md`.

## 🎯 Φάσεις

| Φάση | Τι | Κόστος | Status |
|------|-----|--------|--------|
| Φ1 | **Τοπικό** Anvil fork (`anvil --fork-url ...`) + `debug_traceCall` πάνω σε candidate tx (success + revert case), μηδενικό E2B ακόμα | 🟢 μηδενικό | ✅ (`anvil_fork.py`) |
| Φ2 | Τύλιξε το Φ1 σε custom **E2B template** + sandbox lifecycle μέσω SDK | 🟡 δωρεάν tier ($100 credit, χωρίς κάρτα) | ✅ live-verified end-to-end (`e2b_run.py`) |
| Φ3 | Sandbox call ως **LangGraph tool** μέσα σε agent (agent αποφασίζει πότε να preflight-check μια tx) | 🟡 | ✅ live-verified end-to-end (`sandbox_tools.py` + `sandbox_agent.py`) |

> **Διόρθωση (2026-08-25):** το αρχικό θεωρητικό doc έλεγε "custom Dockerfile + `e2b.toml`".
> Ελέγχθηκε ζωντανά στα docs.e2b.dev πριν γραφτεί ο κώδικας: αυτό έχει αντικατασταθεί από
> το Python **`Template()` builder** (`e2b_template.py`) — ίδια ιδέα (build once, versioned
> image), διαφορετικό syntax. `Template.build(...)` σε `build_template.py` κάνει το build,
> όχι CLI. Δες `e2b_template.py` / `build_template.py` / `e2b_run.py`.

**Bugs βρέθηκαν/διορθώθηκαν στη Φ2 (live, 2026-08-25):**
- Base image τρέχει build steps ως user `user`, όχι `root` — Foundry πάει σε
  `/home/user/.foundry/bin`, όχι `/root/...`.
- Το `PATH` από `.set_envs()` (image-level, σαν Dockerfile `ENV`) δεν φτάνει αξιόπιστα
  στο δικό μας `subprocess.Popen` μέσα από `commands.run()`. Fix στο `anvil_fork.py`:
  `resolve_anvil_bin()` — `shutil.which()` πρώτα, αλλιώς ρητό `~/.foundry/bin/anvil`,
  ΚΑΘΟΛΟΥ βασισμένο σε PATH. Δουλεύει ίδιο script και τοπικά και στο sandbox.
- Flaky E2B-side infra bug: cached `resize-disk` build step απέτυχε 2/2 φορές
  ("internal error"). Fix: `skip_cache=True` μόνιμα στο `build_template.py` (build
  ούτως ή άλλως γρήγορο, ~1 λεπτό).

**Συμφωνημένη στρατηγική:** χτίσε/debug το Anvil-fork κομμάτι πρώτα τοπικά (γρήγορη
επανάληψη, μηδενικό κόστος), μόνο μετά τύλιξέ το σε πραγματικό E2B sandbox call.

**Φ3 (25 Αυγ) — αρχεία και σχεδιαστικές αποφάσεις:**
- `anvil_lifecycle.py` — εξήχθη από το `anvil_fork.py` (start/wait/resolve-bin λογική,
  ~40 γραμμές) ώστε να μοιράζεται με το νέο `preflight_check.py` — πραγματική
  επανάληψη πολύπλοκης λογικής, όχι πρόωρο abstraction.
- `preflight_check.py` — τρέχει ΜΕΣΑ στο sandbox, παίρνει ΜΙΑ αυθαίρετη candidate tx
  (`TX_TO`/`TX_DATA`/`TX_VALUE_WEI`/προαιρετικό `TX_FROM` μέσω env vars, όχι πια
  hardcoded όπως το `anvil_fork.py`), τυπώνει **JSON** στο stdout (όχι prose) — το
  tool στο host πρέπει να παρσάρει αξιόπιστα, όχι να "διαβάσει" ελεύθερο κείμενο.
- `e2b_template.py` ενημερώθηκε να κάνει copy και τα δύο νέα αρχεία μέσα στο image
  (χρειάστηκε rebuild με `build_template.py` πριν δουλέψει — το template είναι
  versioned snapshot, όχι live sync).
- `sandbox_tools.py` — `@tool preflight_check_via_sandbox(to, data, value=0)`. Ίδιο
  "agent αποφασίζει ΠΟΤΕ, deterministic κώδικας αποφασίζει ΠΩΣ" pattern με το
  `web3/preflight-agent`. Ανοίγει/κλείνει sandbox σε ΚΑΘΕ tool call (όχι μακρόβιο) —
  ίδια εγγύηση καθαρού teardown με το `e2b_run.py`.
- `sandbox_agent.py` — `create_react_agent`, demo το REVERT σενάριο (WETH.withdraw
  χωρίς balance). Πρόσθηκε `langgraph`/`langchain-anthropic` στο `pyproject.toml`
  (unpinned `>=`, ίδιο pattern με τα υπόλοιπα uv-script agents στο workspace) —
  `uv sync` έφερε `langgraph 1.2.11`, `langchain-anthropic 1.6.1`.
- **Tool-level tests (χωρίς LLM, πριν το agent-level run):** SUCCESS case (WETH
  deposit) ✅, REVERT case (WETH withdraw χωρίς balance) ✅ — και τα δύο μέσα από
  πραγματικό sandbox call.
- **Live agent-level test:** ο LLM σωστά αφηγήθηκε το REVERT verdict βασισμένο ΜΟΝΟ
  στο πραγματικό tool output (σωστό reasoning για το "γιατί" — ανεπαρκές WETH
  balance — χωρίς hallucination). Deprecation warning (`create_react_agent`) ξανά
  σημειώθηκε, καμία ενέργεια (ίδιο ήδη-γνωστό θέμα με τα άλλα projects).
- Χρειάστηκε νέο κλειδί στο `.env`: `ANTHROPIC_API_KEY` (δεν υπήρχε πριν, μόνο
  `FORK_RPC_URL`/`FORK_BLOCK_NUMBER`/`E2B_API_KEY`).

**Status:** Φ1+Φ2+Φ3 όλα live-verified end-to-end. Project ολοκληρωμένο σε επίπεδο
βασικής λειτουργικότητας. Ανοιχτό (καμία απόφαση ακόμα): GitHub push;

## 🔗 Σχέση με άλλα projects

- `../web3/preflight-agent/` — ήδη υπάρχον read-only preflight agent (intent decoding +
  `eth_call`). Είχε μπλοκάρει ακριβώς επειδή το δωρεάν public RPC **δεν** υποστηρίζει
  `debug_traceCall` (`-32601`) — αυτό ακριβώς λύνει το τοπικό Anvil fork εδώ (δικός μας
  node, άρα πλήρη debug namespace).
- Anvil/forking/on-chain domain logic ήδη γνωστά από εκεί — δεν είναι το νέο μάθημα εδώ.

## 🔐 Ασφάλεια

- **100% read-only / simulation.** Καμία πραγματική υπογραφή, κανένα πραγματικό private
  key, καμία πραγματική tx. Ό,τι τρέχει, τρέχει πάνω σε τοπικό fork (Φ1) ή sandbox (Φ2+).
- **Ποτέ hardcoded secrets.** `.env` (gitignored) για `FORK_RPC_URL` κ.λπ.
- Πριν από `git push`: security review + ερώτηση Co-Authored-By (global CLAUDE.md).

## ⚙️ Πρακτικά

- `.venv/bin/python` μέσα στο project (δικό του venv, `uv sync`).
- Anvil/Foundry: όχι ακόμα εγκατεστημένο στο μηχάνημα (ελέγχθηκε 2026-08-25) — πρώτο
  practical βήμα της Φ1 είναι η εγκατάσταση (`curl -L https://foundry.paradigm.xyz | bash`
  → `foundryup`).
