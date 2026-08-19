# Progresso da Auditoria (algo_lang) — v4

Acompanha a execução do plano em `algo_lang/AUDITORIA_PLANO.md`. Ver esse
ficheiro para objetivo/âmbito/critérios completos de cada etapa — este
documento é só o estado, para retomar sessão sem perder contexto.

**Como retomar**: lê `AUDITORIA_PLANO.md` primeiro (contexto completo),
depois vê abaixo qual é a primeira etapa com estado `[ ] por fazer` e
continua a partir daí. Não repetir etapas já `[x] concluída` sem motivo
novo.

## Baseline (registada antes de qualquer alteração de código)

Comando: `python -m pytest algo_lang/tests/ -q -m "not slow"`
Resultado: **79 failed, 541 passed, 3 deselected** (623 testes coletados
no total).

As 79 falhas são, por amostragem confirmada (`test_minimo_executa_corretamente`),
`FileNotFoundError: [WinError 2]` ao arrancar um subprocesso (`_winapi.CreateProcess`)
— testes que invocam `algo`/`python` via `subprocess` neste ambiente de
sessão não encontram o executável esperado no `PATH`/venv. **Isto ainda
não está confirmado como "só ambiente" nesta auditoria** — é a mesma
categoria que a 3ª auditoria documentou (baseline histórica: 89 falhas
"de ambiente"), mas o número mudou (79 vs 89) e a suposição tem de ser
reconfirmada na Etapa 8 (Aplicação de consola), não assumida. Lista
completa das 79 falhas guardada nesta sessão em
`C:\Users\oscar\AppData\Local\Temp\claude\...\scratchpad\baseline_failed.txt`
(fora do repositório — regenerar com o comando acima se necessário numa
sessão nova).

**Regra**: ao verificar regressão nas próximas etapas, comparar a
CONTAGEM (541 passed) e a lista de nomes falhados, não assumir que
"algum teste falha" = regressão introduzida por esta auditoria.

**Atualização (Etapa 8)**: a suposição "79 falhas = só ambiente" foi
reconfirmada empiricamente, uma por uma, nas Etapas 5-8 — todas por
`subprocess.run(["algo"/"python", ...])` sem esse executável no `PATH`
desta sessão, exceto 1 (`os.setsid`, incompatibilidade Windows/POSIX
no próprio teste, não relacionada com `PATH`). A Etapa 8 corrigiu um
bug real (`cli.py:main()`, `UnicodeEncodeError` fora do `algo.bat`),
reduzindo a contagem de falhas de **79 para 78** — a partir daqui, as
próximas etapas devem comparar contra **78 failed**, não 79 (ver nota
de progresso da Etapa 8 para o detalhe).

## Estado por etapa

- [x] Etapa 0 — Reconstrução de requisitos e matriz de rastreabilidade (ver `algo_lang/AUDITORIA_MATRIZ_RASTREABILIDADE.md`)
- [x] Etapa 1 — Análise léxica
- [x] Etapa 2 — Análise sintática (parser + AST)
- [x] Etapa 3 — Semântica: tipos, declarações, âmbito, constantes
- [x] Etapa 4 — Semântica: estruturas, arrays e matrizes N-d
- [x] Etapa 5 — Semântica: funções/procedimentos/ref, controlo de fluxo, importar/incluir
- [x] Etapa 6 — Geração de código e equivalência semântica
- [x] Etapa 7 — Execução e erros em tempo de execução
- [x] Etapa 8 — Aplicação de consola (cli.py)
- [x] Etapa 9 — Ferramentas associadas (tracer, flowchart, linter) e consistência
- [x] Etapa 10 — Extensão VS Code
- [x] Etapa 11 — Testes profundos transversais (fuzzing, mutation, propriedades)
- [x] Etapa 12 — Segunda passagem independente e relatório final

Nenhuma etapa foi executada ainda — este documento foi criado no fim da
Fase 2 (planeamento), antes de a Fase 3 (execução) começar.

## Registo de findings (append-only, preencher durante a Fase 3)

_Vazio — por preencher à medida que cada etapa é executada. Formato
sugerido por entrada: `[ID] [SEVERIDADE] ficheiro:linha — descrição
curta — estado (reproduzido / corrigido / teste de regressão)`._

## Notas de progresso (append-only, mais recente no topo)

- 2026-08-19: Etapa 12 concluída (**última etapa do plano — auditoria
  encerrada**). Reauditoria das Etapas 6-9 delegada a um revisor
  independente sem acesso a `AUDITORIA_PROGRESSO.md`/`AUDITORIA_MATRIZ_
  RASTREABILIDADE.md` (só ao `AUDITORIA_PLANO.md`, secção "Regras de
  rigor"), para cumprir de facto o "sem reutilizar as próprias
  conclusões" do plano -- não é possível a mesma sessão que já conhece
  as conclusões auditar-se sem viés de ancoragem, por isso a
  independência real veio de delegar, não de "tentar esquecer".
  **Terceiro bug real encontrado nesta auditoria** (os outros dois:
  Etapa 6, `codegen_minimo.py`; Etapa 8, `cli.py`): `x:decimal = base ^
  expoente`, com `base`/`expoente` ambos `inteiro` e o expoente não
  literal -- semantics.py tipa a expressão como `decimal` (não
  consegue provar em compilação que o expoente nunca é negativo, ver
  `_expoente_estaticamente_nao_negativo`), mas o `**` nativo do Python
  devolve `int` quando os dois operandos são `int` e o expoente
  calculado em runtime acaba não-negativo -- uma variável `decimal`
  ficava silenciosamente com um `int` (`y:decimal = 2^n` imprimia "8",
  não "8.0"), divergindo também de `--minimo`, que já tratava este
  caso corretamente (`codegen_minimo.py` só salta o `float(...)`
  quando o expoente é um LITERAL inteiro não-negativo, uma condição
  mais estrita que a do modo normal antes desta correção). Confirmado
  por reprodução direta (não só leitura): gerado o Python de `y:decimal
  = 2^n; escrever(y)` nos dois modos e corrido -- normal imprimia "8",
  `--minimo` "8.0", antes da correção. **Corrigido**: `codegen.py::_expr`
  (ramo `A.BinOp` op `"^"`) envolve a chamada a `_algo_pot(...)` em
  `float(...)` sempre que `expr._tipo_inferido == "decimal"` e os dois
  operandos são `"inteiro"` -- ponto de geração único, por isso cobre
  automaticamente todos os contextos (atribuição, argumento, elemento
  de array, campo de struct, `devolver`), não só o caso de teste
  reproduzido. **Efeito colateral descoberto ao correr a suite
  completa após a correção**: `test_cadeia_de_potencia_moderada_
  continua_a_funcionar` (existente, `escrever(2^2^2)`) passou a falhar
  -- o expoente do `^` exterior é a sub-expressão `2^2` (não um
  literal), por isso também cai no mesmo ramo "decimal"; o teste
  antigo esperava "16" (int), que já era o MESMO bug, só nunca
  detetado porque `escrever()` direto nunca expôs o tipo declarado.
  Confirmado que `--minimo` já produzia "16.0" para este caso, mesmo
  antes desta correção -- ou seja, já havia uma divergência normal
  vs. `--minimo` não detetada para `2^2^2`, fora do alcance do corpus
  de paridade da Etapa 6 (que só testava expoente literal). Valor
  esperado do teste corrigido para "16.0", com comentário a explicar a
  razão (regra de rigor: não é "enfraquecer um teste correto", é
  corrigir uma expectativa que codificava o próprio bug). 2 testes
  novos em `test_paridade_codegen.py`
  (`potencia_inteira_com_expoente_variavel_atribuida_a_decimal`,
  `potencia_encadeada_expoente_nao_literal`) fecham a lacuna de
  cobertura que deixou isto passar despercebido em duas rondas de
  auditoria. **Restantes áreas reauditadas pelo revisor independente,
  nenhum outro bug encontrado**: equivalência normal/`--minimo` para
  literais aninhados/`ref`/div-mod (reexecutado com programas novos
  nos dois modos), as 7 categorias de erro em runtime (índice de
  texto/array, divisão por zero, overflow, recursão infinita, campo de
  nulo, domínio inválido -- todas com mensagem amigável correta e sem
  fuga de traceback em nenhuma direção), `cli.py` (argumentos,
  encoding, exit codes), consistência tracer/flowchart/linter (os 3
  operam sobre a mesma AST ou sobre a execução real, sem lógica de
  texto duplicada que possa divergir). Procura dirigida por testes
  vácuos nos ficheiros de teste destas 4 áreas (asserts tautológicos,
  `except: pass` sem verificar tipo/mensagem, `pytest.raises` sem
  `match=` nem asserção adicional) -- **nenhum encontrado**; amostra
  verificada manualmente. **2 desatualizações de documentação
  corrigidas** (a 1ª já prevista desde a Etapa 0, secção 11 da
  matriz): `README.md:78` e `docs/ReferenciaCompletaCLI.md:662`
  diziam "334 testes" (número da 3ª auditoria) -- atualizado para 792
  (contagem real desta sessão); `docs/ReferenciaCompletaCLI.md:547-551`
  listava só 3 das 7 categorias reais de erro em runtime amigável
  (faltavam índice de texto, overflow, campo de nulo, domínio
  inválido) -- lista alargada. Achados NÃO corrigidos (decisão do
  responsável do projeto, não tomada unilateralmente, regra de rigor
  de sempre): `ErroSemantico` sem `coluna` (Etapa 0/3); `nulo` ausente
  de `docs/`; os `.docx` não mencionarem `fluxograma`/`linter`/
  `--minimo`/`--debug`/`--json` (pode ser âmbito deliberado, a
  confirmar); `Linter.codigo_fonte` nunca lido (parâmetro morto,
  Etapa 9); 560 sobreviventes de mutation testing não auditados
  mutante-a-mutante (Etapa 11, fora do âmbito pedido). Matriz de
  rastreabilidade atualizada (secção 13, nova). Relatório final
  completo em `algo_lang/AUDITORIA_RELATORIO_FINAL.md` (resumo
  executivo, matriz de cobertura das 12 etapas, bugs por severidade,
  causas estruturais, classificação de confiança 1-5). Suite completa
  sem regressão após a correção: **78 failed, 711 passed, 3
  deselected** (792 coletados = 790 da Etapa 11 + 2 novos); 78 falhas
  idênticas por diff direto -- confirmado que a PRIMEIRA corrida após
  a correção do bug (antes de corrigir o teste antigo) deu 79 failed
  (a regressão esperada e explicada acima), e a segunda corrida, já
  com o teste corrigido, voltou a 78, fechando o ciclo.

  **Esta é a última etapa do plano -- a 4ª auditoria está encerrada.**
  3 bugs reais encontrados e corrigidos ao longo de 12 etapas (Etapas
  6, 8, 12), ~300 testes novos escritos, 79→78 falhas de baseline
  (só ambiente, nunca zero nesta sessão por falta do executável `algo`
  no `PATH`), mutation testing de linha de base estabelecido (79.8%),
  documentação desatualizada corrigida onde encontrada.
- 2026-08-17: Etapa 11 concluída. Três partes, conforme o plano:
  (1) **Fuzzing** — `test_fuzzing_e_propriedades.py` (novo): fuzzing
  por mutação de texto (seed fixo, reprodutível) sobre um corpus
  válido, correndo pelos dois caminhos de codegen (`gerar_python` e
  `gerar_python_minimo`) e fuzzing aleatório de baixo volume no lexer
  -- critério de sucesso do plano ("nunca escapa exceção não
  classificada") confirmado com 0 ocorrências em milhares de
  iterações (exploração prévia, mais ampla, incluída como comentário
  no ficheiro para contexto: 8000+ iterações por caminho, incluindo
  `codegen_minimo.py`, a área onde a Etapa 6 encontrou um bug real --
  nenhuma reprodução aqui, o que é esperado: fuzzing por corrupção de
  TEXTO alcança sobretudo bugs de lexer/parser, não o tipo de bug
  semântico profundo que exige uma AST estruturalmente válida mas
  rara, como o da Etapa 6). (2) **Testes de propriedade** — div/mod
  truncados (identidade da divisão + sinal do resto) e idempotência de
  conversão (inteiro/decimal/booleano ↔ texto), confirmados. (3)
  **Mutation testing** — instalado `mutmut` (aprovado explicitamente
  pelo utilizador, dado implicar nova dependência). **Achado de
  ambiente**: mutmut recusa-se a correr nativamente em Windows (bloqueio
  do próprio mutmut, não configurável) -- contornado via WSL (Ubuntu
  24.04, já disponível nesta máquina), num venv scratch dedicado
  (`pytest`+`mutmut`, não persistido, limpo no fim). 3 tentativas
  falhadas antes de uma configuração funcional: faltava copiar o
  pacote `algo_lang` inteiro (não só `semantics.py`/`codegen.py`) para
  os imports resolverem; a instrumentação do mutmut aprofunda a pilha
  de chamadas o suficiente para um teste de profundidade máxima do
  parser estourar `RecursionError` antes de tempo (destestado, não é
  falha real); faltava copiar `visualizador/` (fora de `algo_lang/`,
  referenciado por um teste). Config final em
  `pyproject.toml::[tool.mutmut]`, com `also_copy` e uma lista de
  `--deselect` documentada (falhas específicas do ambiente WSL desta
  sessão, distintas da baseline Windows). **Resultado, linha de base**:
  2806 mutantes, **2239 mortos, 560 sobreviventes, 7 timeout/erro —
  score global 79.8%** (`semantics.py` 75.0% de 1593; `codegen.py`
  86.1% de 1213). Sobreviventes concentram-se nos maiores dispatchers
  de cada ficheiro (`_verificar_stmt`/`_verificar_chamada`,
  `_expr`/`_gerar_stmt`) -- esperado, mais ramos = mais pontos de
  mutação; não auditados mutante-a-mutante (fora do âmbito desta
  etapa, que pede só a linha de base "para auditorias futuras", não
  correção). 45 testes novos (`test_fuzzing_e_propriedades.py`).
  Matriz de rastreabilidade atualizada (secção 9b, nova). Suite
  completa (Windows, "not slow") sem regressão: **78 failed, 709
  passed, 3 deselected** (797 coletados = 752 da Etapa 10 + 45 novos);
  78 falhas idênticas por diff direto. A alteração a `pyproject.toml`
  (só a secção `[tool.mutmut]`) confirmada sem efeito nenhum na suite
  normal do Windows.
- 2026-08-17: Etapa 10 concluída. **A lacuna prevista pelo plano
  ("sem teste de paridade lexer↔gramática automatizado") já não
  existia**: `test_vscode_grammar_nao_esquece_nenhuma_palavra_chave_
  do_lexer` (secção B27/AL-99) já fazia exatamente isso -- confirmado
  por grep antes de escrever nada (lição consolidada desde a Etapa 2).
  Confirmado também, como o plano pedia explicitamente no início da
  etapa: a suite ad-hoc Node/JS da 3ª auditoria NÃO está neste
  repositório (`editors/vscode-algo/` só tem `package.json`/
  `language-configuration.json`/`syntaxes/`/`README.md`, nenhum
  ficheiro de teste) -- mas irrelevante, já que a lacuna que importava
  (teste automatizado) tinha sido fechada por outro caminho.
  **A lacuna real** (requisito central da etapa, "campo de struct
  distinguível de chamada de biblioteca"): só a LISTA de
  palavras-chave nos comentários da gramática tinha teste -- o
  COMPORTAMENTO real dos padrões regex (`library-calls`,
  `declarations`) nunca tinha sido exercitado, só descrito em
  comentário (referências a B27/B29 da 3ª auditoria). Fechada com 5
  testes novos que correm os padrões regex reais (extraídos do
  `algo.tmLanguage.json`) através do módulo `re` do Python -- a
  sintaxe Oniguruma (TextMate) e `re` coincidem nas construções usadas
  aqui (`\b`, lookahead positivo/negativo, classes de caracteres), por
  isso corre diretamente sem precisar de um motor Oniguruma real.
  Confirmado: `biblioteca.metodo(` reconhecido corretamente,
  `campo.acesso` (sem `(` a seguir) corretamente ignorado (mesmo
  cenário `no.valor`/`c.dobro` já usado na Etapa 9 para confirmar que
  linter/flowchart não têm o mesmo problema, agora do lado da
  gramática); lookahead negativo de `declarations` confirmado a
  ignorar `{ativo: verdadeiro}` como se fosse `nome:tipo`. Nenhum bug
  encontrado -- toda a gramática já se comportava como documentado, só
  faltava a confirmação automatizada. 5 testes novos. Matriz de
  rastreabilidade atualizada (secção 9). Suite completa sem regressão:
  **78 failed, 667 passed, 3 deselected** (752 coletados = 747 da
  Etapa 9 + 5 novos); 78 falhas idênticas por diff direto.
- 2026-08-17: Etapa 9 concluída. A matriz (secção 8) levantava duas
  questões: (1) nenhum teste corria o mesmo programa pelas 3
  ferramentas comparando interpretações; (2) o linter poderia ter a
  mesma ambiguidade textual campo-de-estrutura-vs-chamada-de-biblioteca
  que afeta a gramática TextMate do VS Code. **A questão (2) revelou-se
  inaplicável por arquitetura**: `linter.py` e `flowchart.py` operam
  sobre a AST já tipada pelo parser (`A.Chamada` vs `A.LValue` são
  tipos de nó distintos desde a análise sintática) — a ambiguidade só
  existe para a gramática VS Code porque essa opera sobre TEXTO puro
  via regex, sem árvore de sintaxe nenhuma. Confirmado por leitura de
  `flowchart.py::_eh_chamada_a_rotina` (`isinstance(chamada,
  A.Chamada)` logo à entrada) e empiricamente com um teste novo: um
  campo de estrutura chamado `dobro` coexistindo com uma função
  também chamada `dobro` — o fluxograma distingue corretamente
  `c.dobro = 5` (sem contorno duplo) de `dobro(5)` (com). Achado
  lateral registado, não corrigido: `Linter.codigo_fonte` é guardado
  em `__init__` mas nunca lido em lado nenhum da classe — parâmetro
  morto. Fechada a questão (1) com `test_consistencia_ferramentas.py`
  (novo): um programa com função de utilizador, chamada de biblioteca,
  estrutura e ciclo, corrido por compilador+linter+flowchart+tracer,
  confirmando que as 4 ferramentas concordam sobre o programa ser
  válido e que o CONJUNTO de nomes de rotina que cada uma deriva
  independentemente da mesma AST é idêntico (nenhuma tem um cálculo
  próprio escondido que possa divergir silenciosamente). 2 testes
  novos. Matriz de rastreabilidade atualizada (secção 8). Suite
  completa sem regressão: **78 failed, 662 passed, 3 deselected** (747
  coletados = 745 da Etapa 8 + 2 novos); 78 falhas idênticas por diff
  direto.
- 2026-08-17: Etapa 8 concluída. **Segundo bug real encontrado nesta
  auditoria** (o primeiro foi na Etapa 6): `cli.py:main()` crasha com
  `UnicodeEncodeError` ao tentar imprimir `✔`/`❌` sempre que é invocado
  sem passar por `algo.bat`/`algo.sh` -- confirmado ao investigar por
  que razão `test_cli_corre_via_python_dash_m` (teste já existente,
  para `python -m algo_lang.cli`, uma forma de invocação que o próprio
  ficheiro de testes documenta como suportada) estava na lista de
  falhas da baseline. Causa: a correção original de `AL-35` só foi
  aplicada ao nível do script de arranque (`algo.bat` define
  `chcp 65001`+`PYTHONIOENCODING=utf-8` antes de chamar `algo.exe`) --
  nunca no próprio `cli.py`. Isto deixa vulnerável qualquer invocação
  que não passe pelo `.bat`: `python -m algo_lang.cli` (documentado),
  e também o comando `algo` instalado corrido diretamente a partir de
  um venv ativado à mão (bypass comum, não só um caso de teste
  artificial). **Corrigido**: `sys.stdout.reconfigure(encoding="utf-8",
  errors="replace")` (+ `stderr`) logo no início de `main()`, protegendo
  todos os caminhos de invocação por igual, sem alterar nada nos
  scripts de arranque (continuam a funcionar, apenas redundantes agora
  --defesa em profundidade, não conflito). Confirmado: o teste que
  falhava passa agora; suite completa passou de 79 para **78** falhas
  na baseline (uma REDUÇÃO real, não um artefacto de contagem -- a
  partir de agora as próximas etapas devem comparar contra 78, não 79).
  Segundo achado: a contagem "17 de 31" do `test_consola.py` na matriz
  original (Etapa 0) estava errada -- reconfirmado um a um, são
  realmente 7 (6 por `algo` fora do `PATH`, mesma causa das restantes
  falhas da baseline; 1 por `os.setsid` não existir no Python nativo do
  Windows, uma falha de portabilidade do PRÓPRIO TESTE para SIGINT/
  process groups, registada mas não corrigida -- exigiria reescrever o
  teste para o mecanismo equivalente do Windows,
  `CREATE_NEW_PROCESS_GROUP`+`CTRL_BREAK_EVENT`, fora do âmbito desta
  etapa). `test_algo_sh.py`: confirmado 2 de 3 testes não-`slow` falham
  por tentar correr um script bash como binário nativo do Windows
  (`WinError 193`) -- limitação de plataforma conhecida, não bug de
  lógica. Terceiro achado: nome de ficheiro com Unicode/acentuação
  (lacuna prevista pelo plano) já funcionava corretamente -- fechada
  com 1 teste novo, sem correção necessária. `--entradas` sem valor
  (`B24`) já estava bem coberto (teste puro em processo, não depende do
  `PATH`) -- suposição do plano confirmada, sem lacuna. Matriz de
  rastreabilidade atualizada (secção 7). 2 testes novos (mais a
  correção do 1 já existente). Suite completa: **78 failed, 660
  passed, 3 deselected** (745 coletados = 743 da Etapa 7 + 2 novos);
  lista de 78 falhas = as 79 da Etapa 7 MENOS `test_cli_corre_via_
  python_dash_m` (confirmado por diff direto), nenhuma nova.
- 2026-08-17: Etapa 7 concluída. Leitura completa de `codegen.py`
  (handler de exceções em `_algo_programa`) e das 3 bibliotecas
  (`bibliotecas/*.py`) confirmou a tabela função×exceção-nativa está,
  na prática, muito bem hardened por rondas anteriores (comentários
  `AL-08/AL-09/AL-19/AL-21/AL-64/AL-65/AL-68/AL-85/AL-86/AL-91`
  documentam casos adversariais já corrigidos um a um) — nenhum bug
  novo encontrado nesta etapa (ao contrário da Etapa 6). Dois achados:
  (1) mesma armadilha de ambiente da Etapa 5/6: `test_recursao_
  infinita_da_mensagem_amigavel_via_cli` e `test_aceder_a_campo_de_
  nulo_da_erro_amigavel_nao_traceback` usam `subprocess.run(["algo",
  ...])`, inoperáveis nesta sessão — reescritos em processo
  (`_em_processo`), ambos confirmados corretos; (2) 2 células novas da
  tabela função×input-adversarial nunca exercitadas: `matematica.piso`/
  `teto` com infinito/NaN (só alcançável via `conversao.paraDecimal
  ("inf"/"nan")`, já que a linguagem não tem notação científica em
  literais) e `matematica.potencia` com expoente grande demais para o
  resultado caber num `float` (`OverflowError` na conversão final) —
  ambos confirmados traduzidos corretamente antes de escrever o teste,
  fechando a lacuna de cobertura sem correção necessária. 5 testes
  novos. Matriz de rastreabilidade atualizada (nova secção 6b, para
  não renumerar as restantes). Suite completa sem regressão: **79
  failed, 658 passed, 3 deselected** (743 coletados = 738 da Etapa 6 +
  5 novos); 79 falhas idênticas por diff direto.
- 2026-08-17: Etapa 6 concluída. **Esta é a etapa com o achado mais
  sério de toda a auditoria até agora: um BUG REAL, não uma correção
  de suposição.** Construído `algo_lang/tests/test_paridade_codegen.py`
  (novo, como o plano pedia por nome), com um corpus de 25 programas
  representativos corridos nos dois modos (`codegen.py`/
  `codegen_minimo.py`) e `stdout` comparado byte a byte, mais 2
  divergências já documentadas (booleano impresso como `True`/`False`
  em vez de `verdadeiro`/`falso`; array por valor mutado no chamador)
  reescritas como confirmação explícita da exceção, não como falha.
  Ao construir o corpus, um caso de estrutura aninhada (`{inicio_pt:
  {x: 1.0}, ...}`) fez o **compilador `--minimo` rebentar com
  `ErroInternoCompilador`** num programa 100% válido que compila e
  corre perfeitamente em modo normal — não "resultado diferente",
  **falha a COMPILAR**, contradizendo o próprio contrato documentado de
  `--minimo` ("gera sempre Python, falha só a CORRER"). Investigação
  revelou que o bug afeta os 4 pontos de entrada de literais `{...}`
  (declaração, atribuição, argumento de chamada, `devolver`) sempre que
  um literal de estrutura aparece ANINHADO dentro doutro literal
  (struct-em-struct, struct-em-array) -- e, no caso de "argumento de
  chamada", até para um literal de estrutura NÃO aninhado (nunca tinha
  sido implementado esse ponto de entrada). Causa-raiz: `codegen_minimo.py`
  nunca teve o par `_expr_estrutura_literal`/`_expr_array_literal`
  (recursivo, com o tipo esperado threaded pelo contexto) que
  `codegen.py` já tinha desde AL-78/B8 -- cada sítio construía os
  campos/elementos chamando `_expr()` genérico, que nunca teve ramo
  para `A.EstruturaLiteral`. **Corrigido**: adicionados os 2 métodos a
  `codegen_minimo.py` (sem `_coagir_decimal` -- mantém a ausência de
  coerção decimal já existente em `--minimo` por desenho, para não
  introduzir uma assimetria nova) e atualizados os 4 pontos de entrada,
  incluindo `gerador_base.py::_gerar_atribuicao` (partilhado, mas só
  exercitado por `--minimo` na prática, já que `codegen.py` sobrepõe
  esse método por inteiro). 5 cenários de reprodução confirmados
  falhados ANTES da correção e passados DEPOIS. Achado adicional: o
  ficheiro `test_compila_minimo.py` (36 testes existentes) está
  inteiramente na lista de falhas da baseline (mesma causa das falhas
  da Etapa 5: `subprocess.run(["algo", ...])` sem `algo` no `PATH`
  desta sessão) -- por isso NENHUM desses 36 testes teria detetado este
  bug nesta sessão, mesmo já existindo cobertura ad-hoc de literais de
  estrutura em `--minimo`; `test_paridade_codegen.py` evita a mesma
  armadilha invocando o compilador em processo e só usando
  `sys.executable` (nunca depende do `PATH`) para correr o Python já
  gerado. Matriz de rastreabilidade atualizada (secção 6). 33 testes
  novos no total (30 em `test_paridade_codegen.py`). Suite completa sem
  regressão: **79 failed, 653 passed, 3 deselected** (738 coletados =
  705 da Etapa 5 + 33 novos); 79 falhas idênticas por diff direto —
  incluindo confirmação de que os testes `test_minimo_*` já existentes
  em `test_correcoes_auditoria.py` que correm em processo (via
  `sys.executable`, não `subprocess.run(["algo", ...])`) continuam
  todos a passar, dando confiança adicional de que a correção não
  quebrou nada alcançável nesta sessão.
- 2026-08-17: Etapa 5 concluída. **Achado principal, o mais importante
  desta etapa**: os 4 testes `test_incluir_*_duplicada_da_erro`/
  `test_incluir_constante` que estavam na lista de falhas da baseline
  desde a Etapa 0 (marcados "confirmar ambiente vs bug real") foram
  isolados e corridos sozinhos — falham todos com o mesmo
  `FileNotFoundError: [WinError 2]` de `_winapi.CreateProcess` ao
  tentar arrancar `algo` via `subprocess.run(["algo", ...])`, **a
  mesma causa exata** documentada para as restantes 75 falhas da
  baseline (executável fora do `PATH` nesta sessão) — confirmado
  empiricamente, não assumido. Para confirmar independentemente que a
  LÓGICA de deteção de colisão está correta (não só que o wrapper de
  CLI falha por ambiente), escreveram-se 3 versões em processo dos 3
  testes de colisão (estrutura/função/variável global), usando
  `_carregar_e_resolver_inclusoes` diretamente em vez de subprocess —
  mesmo padrão já usado por `test_incluir_transitivo_*`. Todas as 3
  passam, confirmando a lógica está correta. Segundo achado: escrito
  `test_campo_de_estrutura_dentro_de_array_por_referencia_duas_vezes_
  nao_e_detetado`, fixando como regressão um limite conhecido e
  documentado no código (`_chave_ref_estatica`) — um campo de struct
  DENTRO de um array (`pontos[0].x`) passado 2× por `ref` nunca é
  detetado como aliasing, mesmo com o mesmo índice literal nas duas
  chamadas, ao contrário de variável simples ou campo sem array; não é
  um bug, é documentar o comportamento atual para não ser alterado por
  acidente. Terceiro achado (correção a uma correção anterior): a
  "lacuna" de `escolher`/`caso` com `1` vs `1.0` vs `'1'` (registada na
  Etapa 0) já estava coberta — `test_caso_duplicado_entre_cadeia_e_
  caracter_e_detetado` e `test_caso_duplicado_entre_inteiro_e_decimal_
  e_detetado` (secção B11/AL-83) cobrem exatamente isto; o grep da
  Etapa 0 usou os literais como texto de busca em vez da mensagem de
  erro real ("já apareceu antes"), por isso não os encontrou. Nenhuma
  outra lacuna do plano para esta etapa sobreviveu ao grep (`ref` com
  alargamento de tipo e ciclo de `incluir` já confirmados cobertos na
  Etapa 0). Matriz de rastreabilidade atualizada (secção 5). Suite
  completa sem regressão: **79 failed, 623 passed, 3 deselected** (705
  coletados = 701 da Etapa 4 + 4 novos); 79 falhas idênticas por diff
  direto.
- 2026-08-17: Etapa 4 concluída. Grep exaustivo primeiro (disciplina
  agora consistente desde a Etapa 2) resolveu 3 das 4 "lacunas
  previstas" do plano/matriz **sem escrever nenhum teste**, todas já
  cobertas: (1) a preocupação do `B8` ("só 2 de ≥4 pontos de
  propagação de tipo esperado para literais `{...}`") está desatualizada
  — os 4 pontos de entrada (declaração, atribuição, argumento de
  chamada, `devolver`) já têm teste para array E estrutura onde
  sintaticamente possível, incluindo o caso "array de literais de
  estrutura" (`test_array_de_literais_de_estrutura`); (2) "literal
  maior/menor que declarado" (`B7`/`AL-48`) já tinha teste direto
  (`test_array_com_literal_de_tamanho_diferente_do_declarado_da_erro`).
  **A única lacuna real**: nenhum teste ia além de 3 dimensões —
  fechada com `test_array_4d_indexacao_e_atribuicao` e
  `test_array_literal_4d` (2 testes novos, seguindo o padrão exato dos
  testes 3D existentes). Confirmado por leitura de `semantics.py`/
  `codegen.py` que não há limite de dimensões no código — a
  extrapolação para N arbitrário é segura. Matriz de rastreabilidade
  atualizada (secção 4). Suite completa sem regressão: **79 failed,
  619 passed, 3 deselected** (701 coletados = 699 da Etapa 3 + 2
  novos); 79 falhas idênticas por diff direto.
- 2026-08-17: Etapa 3 concluída. Antes de escrever qualquer teste,
  fez-se `grep` exaustivo por cobertura existente (lição da Etapa 2) —
  confirmou-se que `semantics.py` já tem ~50 testes `test_sem_*` para o
  lado NEGATIVO de cada operador (rejeita par de tipos errado) e que os
  "7 regras de `constante`" do plano mapeiam 1:1 para os 7 testes de
  `test_constante_*`, sem lacuna. Dois achados reais:
  (1) **Matriz de compatibilidade tipo×operador como tabela única**
  (objetivo central da Etapa 3 no plano) — construída em
  `test_matriz_de_compatibilidade_operador_tipo` (26 casos
  parametrizados, extraídos das regras reais de `_tipo_binop`/
  `_compativel`/`_tipos_comparaveis`, não inventados), cobrindo o lado
  POSITIVO que faltava: tipo de resultado inferido para cada par válido
  (ex.: `caracter + caracter` larga para `cadeia`; `div`/`mod` nunca
  contaminam para `decimal`; `/` é sempre `decimal` mesmo com dois
  inteiros exatos). + 1 teste negativo novo, `booleano == inteiro`
  (nunca testado com `booleano` especificamente, só `inteiro`/`cadeia`).
  (2) **A lacuna prevista pelo plano ("sombreamento 3+ níveis de
  aninhamento sem teste") estava errada** — leitura de `Escopo`
  (`semantics.py:37-64`) confirma que 3+ níveis é estruturalmente
  IMPOSSÍVEL nesta linguagem: só há uma fronteira de sombreamento
  (parâmetro/local de função vs. global, via `raiz_funcao`); dentro da
  mesma função, `_nome_ativo` proíbe redeclarar um nome ativo em
  qualquer bloco aninhado, e não há funções aninhadas. O plano
  pressupunha scoping por bloco (comum noutras linguagens), que este
  compilador deliberadamente não implementa. Nenhum teste escrito para
  isto — seria simular um cenário já rejeitado por construção. Matriz
  de rastreabilidade atualizada (secção 3) com ambos os achados.
  **Achado adicional, registado mas não corrigido** (regra de rigor:
  não alterar comportamento silenciosamente): `ErroSemantico` continua
  sem parâmetro `coluna` (assimetria com `ErroLexico`/`ErroSintatico`,
  já identificada na Etapa 0) — avaliado aqui como suspeito de ser
  design deliberado (um erro de tipo tipicamente abrange uma expressão
  inteira, não um único token, ao contrário de erros léxicos/
  sintáticos), não um bug óbvio; decisão de o implementar ou não fica
  para o responsável do projeto, não tomada unilateralmente aqui.
  Suite completa sem regressão: **79 failed, 617 passed, 3 deselected**
  (699 coletados = 673 da Etapa 2 + 26 novos); 79 falhas idênticas por
  diff direto.
- 2026-08-17: Etapa 2 concluída. **Achado principal: a lacuna prevista
  pelo plano ("auditoria exaustiva de todo ponto de recursão
  descendente — `nao`/`-`/`^`") estava errada.** Ao escrever testes
  dedicados para os 4 pontos de recursão documentados em
  `parser.py:35-55` (parênteses, `nao` encadeado, `-` unário encadeado,
  expoente de `^`) e para `LIMITE_PROFUNDIDADE_BLOCO`, descobriu-se que
  3 desses 4 testes de "cadeia muito funda dispara o limite" **já
  existiam** (`test_cadeia_de_nao_muito_funda_da_erro_sintatico_amigavel`,
  `::test_cadeia_de_menos_unario_muito_funda_...`,
  `::test_cadeia_de_potencia_muito_funda_...`, todos ~linha 3433) e o
  teste de blocos também (`test_blocos_aninhados_a_mais_da_erro_sintatico_nao_recursionerror`,
  ~linha 2755) — os testes recém-escritos eram duplicados byte-a-byte
  em comportamento, detetados só porque pytest não permite nomes de
  função repetidos no mesmo módulo (o nome que escolhi por acaso
  colidiu com o já existente, revelando a duplicação antes de correr a
  suite). **Removidos os 5 duplicados**, mantido só o que era mesmo
  novo: 3 testes do lado oposto — cadeia MODERADA e legítima de
  `nao`/`-`/`^` não dispara falso positivo (padrão que já existia para
  parênteses e blocos mas faltava para estes três) — e 1 teste para
  `ler()` sem argumentos, que era mesmo uma lacuna real (`escrever()`
  já tinha verificação dedicada, `ler()` nunca teve, mas continua a dar
  `ErroSintatico` limpo via `esperar("ID")`, confirmado agora).
  Matriz de rastreabilidade atualizada (secção 2) para refletir a
  correção. Total: 4 testes novos (não ~15-20 como o plano estimava —
  a maior parte do que o plano listava como "lacuna" já estava
  coberta). Suite completa sem regressão: **79 failed, 591 passed, 3
  deselected** (673 coletados = 669 da Etapa 1 + 4 novos); lista de 79
  falhas idêntica à da Etapa 1 por `diff` direto (não só contagem).
  **Lição para as próximas etapas**: antes de escrever um teste "novo"
  para uma lacuna prevista no plano/matriz, `grep` primeiro pelo nome
  óbvio no ficheiro de testes — já é a 2ª vez nesta auditoria (depois
  da Etapa 0) que uma lacuna prevista se revela já coberta.
- 2026-08-17: Etapa 1 concluída. 46 testes novos adicionados a
  `algo_lang/tests/test_correcoes_auditoria.py` (secção "Auditoria (4ª
  ronda), Etapa 1"), fechando as 3 lacunas confirmadas na matriz de
  rastreabilidade para o léxico: (1) `test_lexer_conjunto_de_palavras_chave_tem_exatamente_33`
  + `test_lexer_cada_palavra_chave_produz_token_dedicado` (parametrizado,
  33 casos) — nenhum teste enumerava as 33 palavras-chave uma a uma
  antes; inclui `test_lexer_identificador_parecido_com_palavra_chave_nao_e_confundido`
  para confirmar que não há correspondência por prefixo (ex.: "paragem"
  não é confundido com "para"); (2) acentuação portuguesa em
  identificadores e strings — `test_lexer_identificador_com_acentuacao_portuguesa_e_reconhecido`,
  `test_lexer_programa_com_identificador_acentuado_compila_e_executa`,
  `test_lexer_string_com_acentuacao_portuguesa_preserva_carateres`; (3)
  símbolos que são prefixo uns dos outros (`=`/`==`, `<`/`<=`/`<>`,
  `>`/`>=`) nunca tinham teste dedicado ao nível do lexer — `test_lexer_simbolos_prefixo_de_outros_nao_se_confundem`
  (parametrizado) + `test_lexer_menor_seguido_de_maior_sem_espaco_nao_vira_diferente`.
  Nenhuma alteração a `lexer.py` — todos os 46 testes passaram à
  primeira (o comportamento já estava correto, só não estava coberto).
  Regressão confirmada: suite completa `python -m pytest algo_lang/tests/
  -q -m "not slow"` → **79 failed, 587 passed, 3 deselected** (669
  coletados = 623 da baseline + 46 novos); os 79 falhados são
  exatamente os mesmos nomes da baseline (mesma causa `FileNotFoundError`
  de subprocess/ambiente, confirmado por diff de lista, não só
  contagem) — nenhuma regressão introduzida. Nota lateral: uma primeira
  corrida em paralelo com outra sessão pytest no mesmo momento deu 81
  falhas/585 passadas (ruído de dois processos a competir por
  ficheiros temporários dos testes de CLI/tracer/fluxograma); a corrida
  isolada seguinte confirmou os números acima — não correr suites
  completas em paralelo nesta máquina.
- 2026-08-16: Etapa 0 concluída. Matriz de rastreabilidade completa em
  `algo_lang/AUDITORIA_MATRIZ_RASTREABILIDADE.md`. Sem alterações de
  código. Achados principais: (1) 3 "lacunas previstas" no plano
  revelaram-se já cobertas por testes existentes (segundo `inicio`,
  `ref` com alargamento de tipo, ciclo de `incluir`) — não repetir
  trabalho de reprodução nessas áreas nas etapas seguintes; (2) a
  queixa da 3ª auditoria sobre "falta de coluna em erros" está
  desatualizada — coluna já existe e testada em `ErroLexico`/
  `ErroSintatico`, mas `ErroSemantico` continua sem `coluna` (achado
  novo, mais estreito, para avaliar na Etapa 3); (3) `nulo` é palavra-
  chave real e testada mas ausente de toda a documentação em `docs/`
  (`.md` e `.docx`); (4) 4 testes de colisão de `incluir` estão na
  lista de falhas da baseline — confirmar causa (ambiente vs bug real)
  na Etapa 5; (5) rastreabilidade `AL-NN`: 83 IDs distintos no código,
  16 números da sequência 1-99 sem tag no código, dos quais 13 têm
  justificação documentada (melhoria deliberadamente não implementada
  ou decisão de design) e 3 (`AL-03`, `AL-30`, `AL-80`) sem registo em
  lado nenhum — anotado, não considerado bug.
- 2026-08-16: Documento criado. Fase 1 (plano geral) e Fase 2
  (planeamento detalhado por etapa) concluídas e aprovadas pelo
  responsável do projeto. Baseline de testes registada acima. Fase 3
  (execução) ainda não começou.
