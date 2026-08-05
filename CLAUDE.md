# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**Algo** is a Portuguese-language algorithmic pseudocode language (compiles to
Python) for teaching programming. **Alguem** ("someone") is an LLM-based
Socratic tutor bundled with it — it helps students without ever solving the
exercise or writing code for them. Both are used two ways that **share the
exact same compiler, unmodified**: a local CLI (`algo_lang/`) and a multi-user
web service (`online/`, FastAPI).

The whole project — code, comments, docstrings, commit messages, tests,
identifiers — is written in **Portuguese**. Match that when editing existing
files; don't switch to English identifiers or comments in Portuguese modules.

Three largely independent sub-projects, each with its own README with far
more detail than this file:
- `algo_lang/` — the compiler/CLI. No dependency on `alguem/` or `online/`.
- `alguem/` — the LLM tutor (see `alguem/README.md`). Only touches
  `algo_lang` by reading `lexer.PALAVRAS_CHAVE` (never writes to it).
- `online/` — the FastAPI web service (see `online/README.md`). Imports
  `algo_lang` and `alguem` but never modifies them.

## Commands

No linter/formatter is configured — match existing style by hand.

```bash
# Compiler test suite (334 tests) — must run from tests/, not repo root
cd tests && python3 -m pytest
python3 -m pytest tests/test_estruturas.py -v      # single file
python3 -m pytest tests/test_estruturas.py -k nome_do_teste  # single test

# Alguem (tutor) test suite (173 tests) — from repo root
python3 -m pytest alguem/tests/ -v

# Online (web service) test suite (83 tests)
cd online && python3 -m pytest -v

# Run the CLI/console locally (creates a venv on first run, no manual activation needed)
./algo.sh          # Linux/macOS
algo.bat           # Windows
```

Tests marked `slow` (in `tests/`) actually build a real venv via `algo.sh` —
skip with `-m "not slow"` for a quick loop.

The `online/` service needs two env vars to boot (it refuses to start
without them): `ONLINE_CHAVE_CIFRAGEM` (Fernet key, encrypts stored LLM
credentials) and `ONLINE_CHAVE_SESSAO` (session cookie signing key). Generate
via `python3 -c "from cifragem import gerar_chave_nova; print(gerar_chave_nova())"`
and `python3 -c "import secrets; print(secrets.token_hex(32))"`.

## Compiler pipeline (`algo_lang/compilador/`)

Straight-line pipeline, each stage its own file:

```
lexer.py (tokenizar) → parser.py (parse/parse_biblioteca, recursive-descent)
  → ast_nodes.py (No subclasses) → semantics.py (verificar — type checking)
  → codegen.py (gerar_python) → runnable Python
```

- `codegen.py` generates "normal" Python, with helper functions for safety.
- `codegen_minimo.py` is a separate, more direct code path for `compila
  --minimo`: skips type checking, maps `afirmar`→`assert`, `math.raiz`→
  `math.sqrt`, etc. directly — a type error only surfaces when the generated
  `.py` actually runs, as a native Python error.
- `algo_lang/tools/tracer.py` adds step-by-step execution tracing (used by
  `executa --debug`/`--json`) by running the real generated Python under
  `sys.settrace()` — the compiler itself has no notion of debugging; codegen
  only emits code plus a line map (`gerar_python_com_mapa`).
- `algo_lang/tools/flowchart.py` and `linter.py` operate on the AST, not
  generated code.
- `incluir "ficheiro.algo"` (library includes) is resolved by
  `cli.py:_resolver_inclusoes`, which merges functions/structs/globals into
  the main `programa` AST — collisions are a hard error. **`online/executor.py`
  reimplements this resolution rather than reusing `cli.py`'s version**,
  because `cli.py`'s helpers call `sys.exit(1)` on error, which would kill
  the whole web server for every student — see "Cross-cutting" below.

## Alguem (tutor) architecture (`alguem/`)

- Entry point is `algo_lang/cli.py:_chamar_alguem`, triggered by `?` in the
  console — `alguem/` deliberately has no `cli.py` of its own, so there's
  only one way to invoke it.
- `nucleo/tutor.py` (class `Alguem`) holds the conversation. Each turn goes
  through `nucleo/system_prompt.py` (built from `nucleo/politica_pedagogica.py`,
  a configurable policy) and then through `nucleo/guardiao.py` — a *second*,
  independent pass that classifies the response (`SAFE`/`HINT`/
  `PARTIAL_SOLUTION`/`FULL_SOLUTION`/`CODE`) and discards+regenerates it
  (up to 2 attempts, then a fixed safe refusal) if it leaks too much. A
  rejected response never enters conversation history.
- `nucleo/conhecimento_algo.py` imports keyword lists directly from
  `algo_lang.compilador.lexer` rather than hand-duplicating them.
- `nucleo/ficheiros_visiveis.py` gives the tutor visibility into whatever
  `.algo` file the student last acted on in the console (by name, resolving
  `incluir` recursively via regex — deliberately not the real parser, so it
  still works on files with syntax errors).
- `fornecedores/` — 7 LLM provider backends, one class/file each
  (OpenRouter, OpenAI, HuggingFace, OpenCode Go share HTTP logic via
  `_base_openai_compativel.py`; Gemini, Anthropic, Ollama implement
  `AgenteLLM` directly since they split the system prompt differently or,
  for Ollama, run fully local with no API key). Adding a provider: new file
  in `fornecedores/`, register in `fornecedores/__init__.py`'s
  `FORNECEDORES` factory dict.
- `nucleo/registador.py` + `nucleo/identidade.py` log every session to
  `logs/*.jsonl` for the research metrics computed by `scripts/metricas.py`
  (Solution Leakage Rate, Hint Dependency). A persistent-but-anonymous
  student ID (`.estudante_id`, random UUID) is generated automatically —
  not tied to any account or email.
- No network access in this dev environment: **all provider tests mock the
  HTTP layer** (`unittest.mock`) — there is no way to verify real API calls
  here.

## Online service architecture (`online/`)

- Deliberately framework-light: FastAPI + raw `sqlite3` (`bd.py`, no ORM),
  no template engine (HTML served as-is from `estatico/`).
- `executor.py` runs student code via `asyncio.create_subprocess_exec`
  (never `subprocess.run`, which would block the whole server), one
  subprocess per execution, in a per-student folder keyed by pseudonymous
  ID (never email), with CPU/memory limits via `resource.setrlimit`. This is
  "reasonable isolation for a trusted classroom on one VM," not a sandbox
  against a hostile user.
- `alguem_ponte.py` is the only real adaptation needed to reuse `alguem/`:
  it builds an `Alguem` from a DB-stored, per-account encrypted credential
  instead of a local `config.json`.
- `credenciais.py` + `cifragem.py`: each student brings their own LLM API
  key, encrypted at rest (Fernet) under `ONLINE_CHAVE_CIFRAGEM`, which is
  never stored in the DB or code.
- No code persistence: each session is scratch space, no "programs" table.
- `modo_codemirror.py` generates the CodeMirror syntax mode dynamically from
  the compiler's real keyword list, so it can't drift out of date.
- The trace viewer at `/estatico/visualizador/` is the same standalone
  `visualizador/algo-trace-viewer.html` used by the CLI (`algo executa
  --json`), not a second implementation — deliberate reuse.
- Every exception handler returns JSON (`main.py`'s global exception
  handler) — the frontend always expects `response.json()`, so an unhandled
  error must never fall back to a plaintext error page.

## Testing conventions

- `tests/apoio.py` provides `compilar(codigo_algo)` and
  `executar(codigo_algo, entrada="")` helpers used throughout the compiler
  suite — compile/run a string of Algo source and get back generated Python
  or captured stdout.
- Console-integration tests (`tests/test_consola.py`,
  `tests/test_consola_alguem.py`) run the real `algo` command in a
  subprocess against a temp copy of the whole project.
- `alguem/tests/` and `online/tests/` isolate logs/DB into temp dirs via
  `monkeypatch` on the relevant module constants (not env vars) — no test
  in the repo writes to the real `alguem/logs/` or a real database.
- `docs/RoteiroTestesManualALGO.md` is a manual test script for the compiler
  (not automated).

## Cross-cutting gotcha

`algo_lang/cli.py`'s `compilar_ficheiro`/`_resolver_inclusoes` call
`sys.exit(1)` on error — fine for a one-shot CLI invocation, fatal if reused
inside a long-running server. `online/executor.py` intentionally calls the
compiler's lower-level primitives (`parse`/`verificar`/`gerar_python`)
directly and reimplements include-resolution rather than importing the
`cli.py` wrappers. Keep this in mind before "simplifying" `online/executor.py`
to reuse `cli.py` helpers.
