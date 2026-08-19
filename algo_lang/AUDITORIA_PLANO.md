# Auditoria integral ao compilador e à aplicação de consola (algo_lang) — Plano

*Gerado na Fase 1+2 de um processo de auditoria em três fases (planeamento
geral → planeamento detalhado por etapa → execução). Nenhum código foi
alterado ao produzir este documento.*

## 0. Âmbito e premissa

**Âmbito**: `algo_lang/` — compilador (lexer, parser, AST, semântica,
codegen), CLI `algo` (comandos + consola interativa), ferramentas
associadas (`tools/tracer.py`, `flowchart.py`, `linter.py`), bibliotecas
embutidas (`bibliotecas/*.py`), extensão VS Code
(`editors/vscode-algo/`).

**Fora do âmbito, deliberadamente**: `alguem/` (tutor LLM) e `online/`
(serviço web) — são subsistemas independentes com o seu próprio README e
já tiveram cobertura de auditoria dedicada (ver `AUDIT_PLAN.md`/
`AUDIT_DONE.md` no histórico git, apagados no commit `25cf5ea`).

## 1. Contexto: por que esta é (pelo menos) a 4ª auditoria

Recuperado do histórico git (ficheiros apagados no commit `25cf5ea`,
recuperáveis com `git show 25cf5ea~1:<caminho>`):

1. **1ª auditoria** (algo_lang, ficheiro já apagado antes desta sessão) —
   30 bugs (`B1`-`B30`, comentados no código como `AL-41`-`AL-71`).
2. **2ª auditoria** (`AUDIT_PLAN.md`/`AUDIT_DONE.md`, âmbito alargado aos 3
   subprojetos) — 108 findings de segurança + 39 novos, 9 fases, todas
   concluídas. Fatia de `algo_lang`: RCE via `afirmar` (`AL-01`/`AL-32`),
   `AL-02`-`AL-40`.
3. **3ª auditoria** (`algo_lang/AUDITORIA.md`, "v1", 5 agentes paralelos +
   extensão VS Code nunca antes auditada) — 31 bugs novos (`B1`-`B31`,
   comentados `AL-72`-`AL-99`).

**Suite atual**: 623 testes coletados em `algo_lang/tests/`
(`test_correcoes_auditoria.py` sozinho tem 343, um por bug encontrado nas
três rondas). `README.md` ainda diz "334" — já desatualizado.

**Porque uma 4ª ronda tende a encontrar mais bugs** (razões identificadas
pela leitura da própria 3ª auditoria, não hipóteses novas):
- Duplicação de regras entre `codegen.py`/`codegen_minimo.py` é causa-raiz
  recorrente (`B13`/`B14`, `B15`, `AL-51`); testes de paridade entre os
  dois geradores só verificam paridade **estrutural**, nunca **comportamental**.
- A extensão VS Code só ganhou testes na 3ª ronda — território
  historicamente negligenciado.
- Cada auditoria excluiu explicitamente a anterior do âmbito ("Esses
  bugs não são repetidos aqui") — nunca houve reauditoria cética de
  correções já dadas como fechadas.
- Sem testes baseados em gramática, fuzzing, mutation testing ou
  combinatórios em nenhuma das três rondas — cobertura dirigida por
  intuição de bug já conhecido, não por cobertura sistemática da
  especificação.
- Sem matriz de rastreabilidade requisito↔teste.

## 2. Elementos comuns a todas as etapas

- **Infra de teste partilhada**: `algo_lang/tests/apoio.py`
  (`compilar(codigo)`, `executar(codigo, entrada="")`); testes de
  CLI/consola correm o `algo` real em subprocesso.
- **Regressão base**: suite completa (`python -m pytest algo_lang/tests/
  -v`) corre antes e depois de qualquer alteração. Baseline no início
  desta auditoria: **623 testes coletados** — registar contagem
  passed/failed real antes de mexer em qualquer coisa (ver
  `AUDITORIA_PROGRESSO.md`).
- **Evidência-tipo**: output real de `pytest -v`, ficheiro `.algo`
  mínimo de reprodução por bug, diff da correção, novo teste em
  `algo_lang/tests/`.
- **Critério de sucesso-tipo**: teste novo falha antes da correção e
  passa depois; suite completa sem regressão; procurar a mesma classe de
  bug nos restantes ficheiros do componente antes de fechar a etapa.

## 3. Etapas

Ordem de dependência:
`0 → 1 → 2 → (3, 4, 5 sequenciais) → 6 → 7 → 8 → 9 → (10 em paralelo a partir de 1) → 11 → 12`

### Etapa 0 — Reconstrução de requisitos e matriz de rastreabilidade
- **Objetivo**: consolidar a especificação real a partir de todas as
  fontes (não só os testes); construir a matriz
  requisito↔construção↔componente↔testes↔lacuna↔risco; formalizar a
  análise de por que as 3 auditorias anteriores não bastaram.
- **Fontes**: `README.md`, `CLAUDE.md`, `context/project-overview.md`,
  `docs/ManualCompletoALGO.md`, `docs/ReferenciaCompletaCLI.md`,
  `docs/RoteiroTestesManualALGO.md`, `docs/*.docx`, os 4 documentos de
  auditoria recuperados.
- **Lacuna já confirmada**: `README.md` diz "334 testes" — hoje são 623.
- **Trabalho concreto**: extrair de `ReferenciaCompletaCLI.md` cada
  construção/regra citada, cruzar com `grep` por construção em
  `algo_lang/tests/`; para cada um dos ~99 IDs `AL-NN` no código,
  confirmar teste de regressão existente e a passar.
- **Critério de conclusão**: matriz completa; toda inconsistência
  documental registada (não corrigida silenciosamente).

### Etapa 1 — Análise léxica (`compilador/lexer.py`)
- **Requisitos**: 33 palavras-chave, identificadores, 5 literais
  primitivos, comentários linha/bloco, indentação, Unicode/acentuação,
  posição linha/coluna.
- **Testes existentes**: `test_correcoes_auditoria.py::test_lexer_*` (7).
- **Lacunas previsíveis**: sem teste dedicado a **coluna** reportada
  (melhoria nunca implementada per `AUDITORIA.md` secção 2); acentuação
  portuguesa em identificadores/strings sem teste explícito; tokens
  prefixo de outros só parcialmente cobertos.
- **Novos testes previstos**: ~10-15.
- **Critérios de sucesso**: cada token com teste válido+inválido;
  linha/coluna confirmadas onde reportadas.
- **Riscos de regressão**: mudar mensagens de erro léxico pode quebrar
  testes existentes com match textual.

### Etapa 2 — Análise sintática (`compilador/parser.py`, `ast_nodes.py`)
- **Requisitos**: todas as construções da gramática, precedência de
  operadores, `LIMITE_PROFUNDIDADE_EXPR`/`_BLOCO`.
- **Testes existentes**: `test_correcoes_auditoria.py::test_parser_*` (5)
  + testes de aninhamento profundo.
- **Lacunas previsíveis**: auditoria exaustiva de todo ponto de recursão
  descendente (não só os já corrigidos); combinações profundas
  `se`/`para`/`funcao`/`escolher` como bloco único nunca testadas.
- **Novos testes previstos**: ~15-20, incluindo teste "meta" que
  percorre todos os `parse_*` recursivos e confirma incremento do
  limite.
- **Critérios de sucesso**: nenhum `RecursionError` cru alcançável.
- **Riscos de regressão**: limites de profundidade baixos demais podem
  invalidar programas legítimos.

### Etapa 3 — Semântica: tipos, declarações, âmbito, constantes
- **Requisitos**: matriz de compatibilidade dos 5 tipos primitivos,
  `constante` (7 regras), sombreamento global/local/parâmetro.
- **Testes existentes**: `test_novas_funcionalidades.py::test_constante_*`
  (7), `test_regressao_base.py`, vários `test_sem_*` em
  `test_correcoes_auditoria.py`.
- **Lacunas previsíveis**: matriz de compatibilidade completa (5×5 tipos
  × operadores) nunca construída como tabela única; sombreamento em 3+
  níveis de aninhamento sem teste.
- **Novos testes previstos**: ~20 (parametrizados).
- **Critérios de sucesso**: toda célula da matriz tem resultado
  documentado e testado.

### Etapa 4 — Semântica: estruturas, arrays e matrizes N-dimensionais
- **Requisitos**: `estrutura` (aninhada, recursiva, literais), arrays
  1..N-d, literais `{...}` aninhados, tamanho declarado vs literal.
- **Testes existentes**: `test_estruturas.py` (17),
  `test_novas_funcionalidades.py` (9 relevantes),
  `test_correcoes_auditoria.py` (~5 relevantes).
- **Lacunas previsíveis**: `B8` documentava propagação de tipo esperado
  cobrindo só 2 de ≥4 pontos de entrada — confirmar hoje; arrays de 4+D
  nunca confirmados (só 3D testado); literal de array de estruturas —
  confirmar existência de teste.
- **Novos testes previstos**: ~12.
- **Critérios de sucesso**: matriz posição×tipo-de-literal (mín. 8
  combinações) 100% coberta.

### Etapa 5 — Semântica: funções/procedimentos/`ref`, controlo de fluxo, `importar`/`incluir`
- **Requisitos**: parâmetros valor/`ref`, `devolver` em todos os
  caminhos, `se`/`escolher`/`para`/`enquanto`/`fazer...enquanto`,
  `importar`, `incluir` recursivo.
- **Testes existentes**: `test_correcoes_auditoria.py` (3 relacionados
  com `ref` duplicado), `test_regressao_base.py`,
  `test_linter.py::test_inclusao_duplicada_*` (3).
- **Lacunas previsíveis**: `ref` com alargamento de tipo (`B12`) —
  confirmar cobertura completa tipo-origem×tipo-destino; ciclo de
  `incluir` (A inclui B, B inclui A) — sem teste dedicado visível,
  risco de recursão infinita no resolvedor.
- **Novos testes previstos**: ~15, incluindo teste de ciclo de `incluir`.
- **Critérios de sucesso**: nenhuma combinação de `ref` corrompe tipo
  silenciosamente; ciclo de `incluir` produz erro claro.

### Etapa 6 — Geração de código e equivalência semântica
- **Objetivo**: o ponto mais fraco identificado pelo histórico —
  paridade comportamental (não só estrutural) entre `codegen.py` e
  `codegen_minimo.py`.
- **Componentes**: `codegen.py`, `codegen_minimo.py`, `gerador_base.py`,
  `bibliotecas/*.py`.
- **Testes existentes**: `test_compila_minimo.py` (36, caso a caso, não
  sistemático).
- **Lacunas previsíveis**: sem suite de paridade comportamental
  sistemática; pares "gémeos" (`matematica.potencia` vs `^`, possíveis
  outros: `cadeia.subcadeia` vs slicing, `conversao.paraInteiro` vs
  `int()` direto) — procurar todos os pares do mesmo padrão.
- **Estratégia central**: corpus de ~30-50 programas representativos,
  compilados+corridos nos dois modos, `stdout` comparado byte a byte.
- **Novos testes previstos**: suite `test_paridade_codegen.py` nova
  parametrizada sobre o corpus + ~10 testes para pares gémeos.
- **Critérios de sucesso**: 100% do corpus com `stdout` idêntico (exceto
  divergências documentadas do contrato `--minimo`).
- **Riscos**: componente historicamente mais instável — alocar mais
  tempo de reprodução aqui.

### Etapa 7 — Execução e erros em tempo de execução
- **Requisitos**: índice fora dos limites, divisão por zero, recursão
  infinita — sempre traduzidos, nunca traceback cru.
- **Lacunas previsíveis**: cobertura "uma exceção conhecida de cada
  vez", nunca sistemática por função de biblioteca.
- **Estratégia**: tabela função×input-adversarial construída a partir da
  assinatura de cada função em `bibliotecas/*.py`.
- **Novos testes previstos**: ~15-20.
- **Critérios de sucesso**: tabela função×exceção-nativa-possível 100%
  "traduzida: sim".

### Etapa 8 — Aplicação de consola (`cli.py`)
- **Requisitos**: 4 comandos + consola interativa, exit codes, encoding,
  caminhos Windows.
- **Testes existentes**: `test_consola.py` (31), `test_algo_sh.py` (6).
- **Lacunas previsíveis**: reconfirmar que a suposição "~89 falhas eram
  só ambiente" (pré `B18`/`B19`) continua válida pós-correção; `--entradas`
  sem valor (`B24`) — confirmar correção; nome de ficheiro com Unicode.
- **Novos testes previstos**: ~10.
- **Critérios de sucesso**: toda combinação comando×flag×cenário com
  exit code e mensagem esperados confirmados.

### Etapa 9 — Ferramentas associadas (tracer, flowchart, linter) e consistência entre elas
- **Requisitos**: `--debug`/`--json` (posição dos passos), fluxograma
  por função, avisos do linter.
- **Testes existentes**: `test_tracer.py` (20), `test_fluxogramas.py`
  (16), `test_linter.py` (50).
- **Lacunas previsíveis**: nenhum teste corre o mesmo programa pelas 3
  ferramentas + compilador comparando interpretações; ambiguidade
  campo-de-struct vs chamada-de-biblioteca (mesma que afetou VS Code,
  `B28`) — confirmar se o linter tem o mesmo problema.
- **Novos testes previstos**: ~15, incluindo teste "meta" de
  consistência cruzada.
- **Critérios de sucesso**: toda construção interpretada identicamente
  pelas 3 ferramentas; monotonicidade do tracer confirmada como
  propriedade.
- **Dependência**: correr depois de fechar Etapa 6 (mapas de linha do
  tracer dependem de `codegen.py`).

### Etapa 10 — Extensão VS Code (`editors/vscode-algo/`)
- **Requisitos**: toda palavra-chave com highlighting; campo de struct
  distinguível de chamada de biblioteca.
- **Lacunas previsíveis**: sem teste de paridade lexer↔gramática
  automatizado (recomendado pela 3ª auditoria, nunca implementado);
  **confirmar no início da etapa** se a suite ad-hoc Node/JS da 3ª
  auditoria ficou no repositório ou não.
- **Novos testes previstos**: `test_paridade_gramatica_vscode.py`
  (Python, comparação de listas de palavras-chave) + suite Node se
  necessário.
- **Critérios de sucesso**: teste automatizado e reproduzível impede
  divergência futura.

### Etapa 11 — Testes profundos transversais (combinatórios, diferenciais, fuzzing, mutation)
- **Pré-condição**: só arranca depois de fechar Etapas 1-10.
- **Estratégia**: fuzzing por mutação sobre o corpus válido +
  fuzzing aleatório de baixo volume; sucesso = nunca `Exception` não
  classificada escapa ao utilizador; mutation testing sobre
  `semantics.py`/`codegen.py`; testes de propriedade
  (`div`/`mod` truncados, idempotência de conversões).
- **Critérios de sucesso**: 0 exceções não classificadas sobreviventes
  ao fuzzing; mutation score reportado como linha de base para
  auditorias futuras.

### Etapa 12 — Segunda passagem independente e relatório final
- **Âmbito**: reauditar Etapas 6, 7, 8, 9 como equipa externa, sem
  reutilizar as próprias conclusões.
- **Estratégia**: ambiente `.venv` limpo; procurar testes que passam sem
  validar nada; confirmar `README.md`/`ReferenciaCompletaCLI.md`
  atualizados.
- **Entregável final**: relatório com resumo executivo, matriz de
  cobertura, bugs por severidade, causas estruturais, correções,
  evidências, classificação de confiança 1-5.

## 4. Regras de rigor (aplicam-se a todas as etapas)

- Não inventar resultados nem afirmar execução de testes não corridos.
- Não usar cobertura percentual como única prova de qualidade.
- Não confundir ausência de falhas encontradas com ausência de falhas.
- Não alterar a especificação silenciosamente perante contradição
  documentação/testes/implementação — registar e apresentar opções.
- Não alterar testes corretos para acomodar um bug; não eliminar testes
  que falham; não reduzir exigência de validações.
- Não corrigir só a mensagem quando o comportamento subjacente está
  errado.
- Manter rastreabilidade requisito↔implementação↔teste↔resultado em
  todas as etapas.
