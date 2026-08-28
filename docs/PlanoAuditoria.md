# Plano de auditoria — compilador, documentos e online

Âmbito: `algo_lang/` (compilador), `docs/` + `context/` + `CLAUDE.md`
(documentação), `online/` (serviço web). **`alguem/` fica de fora**, por
pedido explícito.

Alternativa a uma reescrita ("v2"): auditoria incremental por execução
real, não por leitura/suposição. **Um único documento para tudo** — plano
e achados das três frentes, incluindo os achados que antes viviam em
`docs/manual/ACHADOS.md` (agora fundidos aqui, esse ficheiro deixou de
existir). Nada de achados espalhados por mais nenhum sítio.

## Metodologia

- Cada achado é **confirmado a correr o código real** (compilar/executar
  um programa, correr um teste, chamar um endpoint) antes de ser
  registado na secção "Achados" abaixo — nunca só inferido do código.
- Estado por achado: 🟢 confirmado só por leitura de código (baixo risco)
  · 🟡 confirmado a correr · ⚪ por decidir (observação, pode ser
  intencional — decisão do maintainer, não minha).
- Achados ficam registados, não corrigidos em silêncio — corrigir é um
  passo explícito e separado, sempre com a suite completa corrida
  antes/depois para confirmar zero regressão nova.

## Estado de partida (levantado em 2026-08-28)

- **Compilador**: os 10 capítulos do manual já foram auditados (6 achados
  já corrigidos e removidos deste documento — ver nota no início da
  secção "Achados"). A mudança de semântica `estrutura`/`vetor` de tipo
  por valor para tipo por referência (`AUDITORIA_2026-08-19 Fase 1.1`)
  já foi confirmada e commitada (commit `b75190e`). Não cobre a camada
  de ferramentas (`cli.py`, `linter.py`, `flowchart.py`, `tracer.py`) nem
  a estrutura interna do código. `pytest algo_lang/tests/ -m "not slow"`:
  908 passam, 44 falham — confirmadas como falhas de **ambiente** (testes
  que invocam o comando `algo` diretamente via subprocesso, fora do PATH
  neste ambiente), não bugs — ver achado 1.
- **Documentos**: `docs/bin/` (citado em `context/project-overview.md`
  como existente) foi apagado deliberadamente no commit `ca1f1a4`
  (2026-08-24) junto com o manual antigo em `.docx`, substituído por
  `docs/manual/` — referência já corrigida. Fora isso, nunca auditados
  como frente própria.
- **Online**: nunca auditado desta forma. 83 testes próprios
  (`online/tests/`), 3043 linhas em `online/*.py` (`main.py` 971L,
  `executor.py` 632L são os dois maiores). Superfície sensível por
  natureza (autenticação, execução de código de estudantes, credenciais
  LLM cifradas) — candidata a mais atenção por linha do que o resto.

## Fases

### Fase 0 — Baseline
`pytest algo_lang/tests/ -m "not slow"` e `cd online && pytest -v`;
registar passa/falha de cada uma como baseline para comparar depois de
cada fase seguinte.

### Fase 1 — ~~Compilador: fechar a Fase 1.1 já em curso~~ ✅ feito
`estrutura`/`vetor` por referência confirmado como design final e
commitado (`b75190e`).

### Fase 2 — Compilador: camada de ferramentas — 🔶 em curso
Auditar por execução `cli.py`, `linter.py`, `flowchart.py`, `tracer.py`
— nunca cobertos pela auditoria do manual. Exercitar caminhos principais
e de erro contra o compilador real (avisos do linter, fluxogramas com
estruturas de controlo aninhadas, trace de erro em runtime, `cli.py` com
flags inválidas/combinações raras). Também o sítio certo para marcar as
44 falhas de ambiente com um marker pytest dedicado, se houver tempo —
ver achado 1.

Já cobertos e corrigidos (confirmados por execução, suite completa
verde antes/depois): `tracer.py` — `_valor_serializavel` rebentava com
"recursão infinita" num programa válido com um ciclo real entre
`estrutura`s (consequência da Fase 1.1, ciclos passaram a ser
possíveis); corrigido com deteção de ciclo por caminho (`<ciclo>` em
vez de recursar), teste de regressão em `test_tracer.py`.
`linter.py` — `_verificar_atribuicao_a_parametro_por_valor` avisava
(errado) que mutar um campo/elemento de um parâmetro `estrutura`/vetor
sem `ref` não era visto por quem chamou; corrigido para só avisar
quando o PRÓPRIO parâmetro é reatribuído (continua correto), testes
atualizados em `test_linter.py`. `flowchart.py` — testado com ciclos
aninhados + `sair`/`continuar`, sem problemas encontrados (a
duplicação de aresta a seguir a `sair`/`retornar` é intencional, já
documentada no código). Por cobrir ainda: `cli.py` com flags
inválidas/combinações raras, mais casos de `flowchart.py`.

### Fase 3 — Documentos: consistência e referências
Verificar que `docs/`, `context/project-overview.md` e `CLAUDE.md`
descrevem o repositório como ele é hoje — não como era (a referência a
`docs/bin/` já foi corrigida, ver Estado de partida). Seguir cada
referência a ficheiro/comando/flag citada nesses documentos; confirmar
`ManualCLI.md` contra as flags reais de `cli.py --help`; verificar se
`docs/manual/00-Indice.md` continua correto depois da Fase 1.

### Fase 4 — Online: auditoria por execução
Primeira auditoria desta frente. Prioridade a `executor.py` (isolamento
de subprocessos, limites de recursos), `autenticacao.py`/
`credenciais.py`/`cifragem.py` (sessões, cifragem em repouso),
`grupos.py` (bloqueio de grupo desativado), `main.py` (handler de
exceção global devolve sempre JSON). Correr a suite própria
(`cd online && pytest -v`), depois exercitar manualmente os fluxos
principais e de erro contra um servidor local (registo, login, execução
de um programa ALGO com erro, pedido sem autenticação, grupo
desativado). Precisa de `ONLINE_CHAVE_CIFRAGEM`/`ONLINE_CHAVE_SESSAO`
(ver `context/project-overview.md` para gerar).

### Fase 5 — Regressão final
`pytest algo_lang/tests/ -v` completo (incluindo `slow`) e
`cd online && pytest -v` completo, uma vez no fim. Critério de sucesso:
ambas 100% verdes (as 44 falhas de ambiente já não existem se a Fase 2
as tiver isolado com marker).

## Achados

Só os achados ainda **abertos** (por corrigir ou por decidir) ficam
aqui. Os já corrigidos foram removidos deste documento depois de
confirmados fechados — o histórico completo (11 achados do manual, 6
deles corrigidos) fica em `git log`/`git show HEAD:docs/manual/ACHADOS.md`
se algum dia for preciso consultá-lo, mas deixa de viver neste
documento vivo.

#### 1. [Compilador] 44 falhas de teste são de ambiente, não bugs — 🟡 confirmado a correr

`pytest algo_lang/tests/ -m "not slow"`: 44 falham, todas por
`FileNotFoundError` — testes que invocam `subprocess.run(["algo", ...])`
e o comando `algo` não está no PATH deste ambiente (só existe depois de
`algo.sh`/`algo.bat` criar a venv). Mascaram regressões reais (uma falha
nova nesses ficheiros passa despercebida no meio das 44 já esperadas).
Candidato a marker pytest dedicado na Fase 2.

## Fora de âmbito

- `alguem/` — excluído por pedido explícito.
- Reescrita ("v2") de qualquer um dos três projetos.
- Novas funcionalidades (linguagem, documentação ou serviço online).
