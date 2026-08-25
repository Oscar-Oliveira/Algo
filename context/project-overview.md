# Project Overview

This file provides guidance when working with code in this repository.

## What this is

**Algo** is a Portuguese-language algorithmic pseudocode language (compiles to Python) for teaching programming. **Alguem** ("someone") is an LLM-based Socratic tutor bundled with it. It helps students without ever solving the exercise or writing code for them. Both are used two ways that **share the exact same compiler, unmodified**: a local CLI (`algo_lang/`) and a multi-user web service (`online/`, FastAPI).

The whole project, including code, comments, docstrings, commit messages, tests, and identifiers, is written in **Portuguese**. Match that when editing existing files. Do not switch to English identifiers or comments in Portuguese modules.

Three largely independent sub-projects, each with its own README with far more detail than this file:
- `algo_lang/` — the compiler/CLI. No dependency on `alguem/` or `online/`.
- `alguem/` — the LLM tutor (see `alguem/README.md`).
- `online/` — the FastAPI web service (see `online/README.md`). Imports `algo_lang` and `alguem` but never modifies them.

## Commands

No linter/formatter is configured. Match existing style by hand.

```bash
# Compiler test suite — from repo root (ARCH-05: moved into algo_lang/, consistent with alguem/tests/ and online/tests/)
python3 -m pytest algo_lang/tests/ -v
python3 -m pytest algo_lang/tests/test_estruturas.py -v      # single file
python3 -m pytest algo_lang/tests/test_estruturas.py -k nome_do_teste  # single test

# Alguem (tutor) test suite (173 tests) — from repo root
python3 -m pytest alguem/tests/ -v

# Online (web service) test suite (83 tests)
cd online && python3 -m pytest -v

# Run the CLI/console locally (creates a venv on first run, no manual activation needed)
./algo.sh          # Linux/macOS
algo.bat           # Windows
````

Tests marked `slow` (in `algo_lang/tests/`) actually build a real venv via `algo.sh`. Skip with `-m "not slow"` for a quick loop.

The `online/` service needs two env vars to boot (it refuses to start without them): `ONLINE_CHAVE_CIFRAGEM` (Fernet key, encrypts stored LLM credentials) and `ONLINE_CHAVE_SESSAO` (session cookie signing key). Generate via `python3 -c "from cifragem import gerar_chave_nova; print(gerar_chave_nova())"` and `python3 -c "import secrets; print(secrets.token_hex(32))"`.

## Compiler pipeline (`algo_lang/compilador/`)

Straight-line pipeline, each stage its own file:

```text
lexer.py (tokenizar) → parser.py (parse/parse_biblioteca, recursive-descent)
→ ast_nodes.py (No subclasses) → semantics.py (verificar — type checking)
→ codegen.py (gerar_python) → runnable Python
```

* `codegen.py` generates normal Python, with helper functions for safety. It shares its dispatch structure with `gerador_base.py` (`GeradorCodigoBase`), a leftover split from a since-removed `codegen_minimo.py`/`compila --minimo` fast path (no type checking, direct 1:1 mappings) — `codegen.py`'s `GeradorCodigo` is its only remaining subclass.
* `algo_lang/tools/tracer.py` adds step-by-step execution tracing (used by `executa --debug`/`--json`) by running the real generated Python under `sys.settrace()`. The compiler itself has no notion of debugging. Codegen only emits code plus a line map (`gerar_python_com_mapa`).
* `algo_lang/tools/flowchart.py` and `linter.py` operate on the AST, not generated code.
* `incluir "ficheiro.algo"` (library includes) is resolved by `cli.py:_resolver_inclusoes`, which merges functions/structs/globals into the main `programa` AST. Collisions are a hard error. **`online/executor.py` reimplements this resolution rather than reusing `cli.py`'s version**, because `cli.py`'s helpers call `sys.exit(1)` on error, which would kill the whole web server for every student.

## Alguem (tutor) architecture (`alguem/`)

* Entry point is `online/alguem_ponte.py:construir_alguem`. `alguem/` deliberately has no `cli.py` of its own and is no longer reachable from the `algo_lang/` console (removed on purpose to keep the compiler free of any dependency on it) — the web service is the only way to invoke it.
* `nucleo/tutor.py` (class `Alguem`) holds the conversation. Each turn goes through `nucleo/system_prompt.py` (built from `nucleo/politica_pedagogica.py`, a configurable policy) and then through `nucleo/guardiao.py`, a *second*, independent pass that classifies the response (`SAFE`/`HINT`/`PARTIAL_SOLUTION`/`FULL_SOLUTION`/`CODE`) and discards plus regenerates it (up to two attempts, then a fixed safe refusal) if it leaks too much. A rejected response never enters conversation history.
* `nucleo/conhecimento_algo.py` imports keyword lists directly from `algo_lang.compilador.lexer` rather than hand-duplicating them.
* `nucleo/ficheiros_visiveis.py` gives the tutor visibility into whatever `.algo` file the student last acted on in the console (by name, resolving `incluir` recursively via regex, deliberately not the real parser, so it still works on files with syntax errors).
* `fornecedores/` contains seven LLM provider backends, one class/file each. OpenRouter, OpenAI, HuggingFace, and OpenCode Go share HTTP logic via `_base_openai_compativel.py`. Gemini, Anthropic, and Ollama implement `AgenteLLM` directly since they split the system prompt differently or, for Ollama, run fully locally with no API key. Adding a provider requires a new file in `fornecedores/` and registration in `fornecedores/__init__.py`'s `FORNECEDORES` factory dict.
* `nucleo/registador.py` and `nucleo/identidade.py` log every session to `logs/*.jsonl` for the research metrics computed by `scripts/metricas.py` (Solution Leakage Rate, Hint Dependency). A persistent but anonymous student ID (`.estudante_id`, random UUID) is generated automatically and is not tied to any account or email.
* No network access exists in this dev environment. **All provider tests mock the HTTP layer** (`unittest.mock`). There is no way to verify real API calls here.

## Online service architecture (`online/`)

* Deliberately framework-light: FastAPI + raw `psycopg`/PostgreSQL (`bd.py`, no ORM; migrated from SQLite), no template engine (HTML served as-is from `estatico/`).
* Students can belong to a `grupo` (class), managed by an admin, joined at registration via an optional server-generated code (`grupos.py`); a deactivated group blocks login for its members, no exception for admins. A general `log_atividade` table (`atividade.py`) records account/group/admin-privilege events, separate from the Alguem tutor's own `.jsonl` logs — its admin UI tab is temporarily hidden by CSS, not removed. Admin privilege grants/revokes (`autenticacao.tornar_admin`/`remover_admin`) are guarded against self-removal and against leaving zero active admins.
* `executor.py` runs student code via `asyncio.create_subprocess_exec` (never `subprocess.run`, which would block the whole server), one subprocess per execution, in a per-student folder keyed by pseudonymous ID (never email), with CPU/memory limits via `resource.setrlimit`. This provides reasonable isolation for a trusted classroom on one VM, not a sandbox against a hostile user.
* `alguem_ponte.py` is the only real adaptation needed to reuse `alguem/`. It builds an `Alguem` from a DB-stored, per-account encrypted credential instead of a local `config.json`.
* `credenciais.py` and `cifragem.py`: each student brings their own LLM API key, encrypted at rest (Fernet) under `ONLINE_CHAVE_CIFRAGEM`, which is never stored in the DB or code.
* No code persistence. Each session is scratch space, with no `programs` table.
* `modo_codemirror.py` generates the CodeMirror syntax mode dynamically from the compiler's real keyword list, so it cannot drift out of date.
* The trace viewer lives only in `online/estatico/visualizador/algo-trace-viewer.html`, served at `/estatico/visualizador/`. The CLI's `algo executa --json` generates the `_trace.json` file the viewer loads, but no longer ships its own copy of the viewer — it's online-only. `algo-trace-viewer.jsx` next to it is the same app's React source, kept for editing.
* Every exception handler returns JSON (`main.py`'s global exception handler). The frontend always expects `response.json()`, so an unhandled error must never fall back to a plaintext error page.

## Testing conventions

* `algo_lang/tests/apoio.py` provides `compilar(codigo_algo)` and `executar(codigo_algo, entrada="")` helpers used throughout the compiler suite. They compile/run a string of Algo source and return generated Python or captured stdout.
* Console integration tests (`algo_lang/tests/test_consola.py`) run the real `algo` command in a subprocess against a temporary copy of `algo_lang/`.
* `alguem/tests/` and `online/tests/` isolate logs/DB into temporary directories via `monkeypatch` on the relevant module constants (not env vars). No test in the repository writes to the real `alguem/logs/` or a real database.
* `docs/bin/RoteiroTestesManualALGO.md` is a manual test script for the compiler (not automated, archived).

## Cross-cutting gotcha

`algo_lang/cli.py`'s `compilar_ficheiro` and `_resolver_inclusoes` call `sys.exit(1)` on error. This is fine for a one-shot CLI invocation but fatal if reused inside a long-running server. `online/executor.py` intentionally calls the compiler's lower-level primitives (`parse`/`verificar`/`gerar_python`) directly and reimplements include resolution rather than importing the `cli.py` wrappers. Keep this in mind before "simplifying" `online/executor.py` to reuse `cli.py` helpers.
