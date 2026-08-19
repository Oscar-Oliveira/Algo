# Relatório Final — 4ª Auditoria ao Compilador ALGO

Entregável da Etapa 12 (`AUDITORIA_PLANO.md`). Cobre as 12 etapas
executadas entre 2026-08-16 e 2026-08-19. Para o detalhe requisito a
requisito, ver `AUDITORIA_MATRIZ_RASTREABILIDADE.md`; para a narrativa
completa etapa a etapa (incluindo becos sem saída e correções ao
próprio plano), ver `AUDITORIA_PROGRESSO.md`.

## 1. Resumo executivo

A 4ª auditoria confirmou que o compilador `algo_lang` está, na
generalidade, sólido: das ~150 lacunas previstas pelo plano inicial
(Fase 2), a maioria revelou-se já coberta por auditorias anteriores —
o padrão dominante em quase todas as 12 etapas foi "grep primeiro,
confirmar que já existe teste, corrigir a matriz de rastreabilidade em
vez de escrever trabalho duplicado" (disciplina consolidada a partir
da Etapa 2, depois de a Etapa 2 ter começado por escrever 5 testes que
eram duplicados byte-a-byte de testes já existentes).

Ainda assim, a auditoria encontrou e corrigiu **3 bugs reais** — nenhum
deles cosmético, todos silenciosos (nenhum causa crash imediato nem
mensagem de erro, todos produzem um resultado observável errado ou
inconsistente sem avisar o estudante):

1. **Etapa 6**: `--minimo` rebentava (`ErroInternoCompilador`) em
   programas 100% válidos com literais de estrutura aninhados.
2. **Etapa 8**: `cli.py` crashava com `UnicodeEncodeError` sempre que
   corrido sem passar pelo `algo.bat`/`algo.sh` (ex.: `python -m
   algo_lang.cli`).
3. **Etapa 12**: uma variável `decimal` inicializada com `base ^
   expoente` (expoente não literal, ambos inteiros) ficava
   silenciosamente com um `int` em vez de `float` no modo normal —
   divergindo de `--minimo` e do próprio tipo que o compilador lhe
   atribui.

O terceiro bug foi encontrado pela reauditoria independente pedida
por esta etapa (secção 2), o que valida a decisão de delegar a um
revisor sem acesso às conclusões das etapas anteriores em vez de
"reler com olhos novos" dentro da mesma sessão.

Nenhum teste vácuo (que passa sem validar nada) foi encontrado nas
áreas reauditadas. Duas desatualizações de documentação foram
corrigidas (contagem de testes desatualizada em 2 ficheiros; lista
incompleta de categorias de erro em runtime). Um baseline de mutation
testing foi estabelecido (79.8%, Etapa 11) como referência para
auditorias futuras, não como alvo em si.

**Estado no fecho desta auditoria**: 792 testes coletados, 711
passam, 78 falham por uma única causa de ambiente confirmada
(executável `algo`/`python` fora do `PATH` desta sessão local — ver
secção 6), 3 deselecionados (`slow`).

## 2. Metodologia da Etapa 12

O plano pede uma "segunda passagem independente... como equipa
externa, sem reutilizar as próprias conclusões" sobre as Etapas 6-9.
Como a mesma sessão que já executou essas etapas conhece as suas
conclusões, "reler com olhos novos" dentro da mesma conversa não
elimina o viés de ancoragem. Em vez disso, a reauditoria foi
**delegada a um subagente novo**, sem acesso a `AUDITORIA_PROGRESSO.md`
nem a `AUDITORIA_MATRIZ_RASTREABILIDADE.md` (só ao `AUDITORIA_PLANO.md`,
secção "Regras de rigor", para herdar o padrão de rigor sem herdar
conclusões). Instruído a:

- Montar um `.venv` limpo e correr a suite completa, com contagens e
  lista de falhas verificadas diretamente (não assumidas).
- Ler o código-fonte das 4 áreas (codegen/paridade, erros em runtime,
  `cli.py`, ferramentas) e tentar quebrá-lo escrevendo e correndo
  programas `.algo` novos, não só analisar estaticamente.
- Procurar dirigidamente testes vácuos nos ficheiros de teste
  relevantes.
- Comparar `README.md`/`docs/ReferenciaCompletaCLI.md` contra o
  comportamento real do código.
- Reportar cada achado com severidade, localização exata, reprodução
  concreta e nível de confiança 1-5 — nunca inventar um resultado não
  corrido.

O achado principal do revisor (o bug do `^`/`decimal`, secção 4) foi
**reproduzido de forma independente por esta sessão** antes de ser
aceite: gerado o Python real dos dois modos para `y:decimal = 2^n`,
corrido, confirmado "8" (normal, errado) vs "8.0" (`--minimo`,
correto) — só depois disso a correção foi aplicada. Isto segue a regra
de rigor "não inventar resultados": um achado de um revisor
(subagente ou humano) é tratado como uma alegação a verificar, não
como facto até ser reproduzido.

## 3. Matriz de cobertura — resumo por etapa

| Etapa | Área | Bugs reais | Testes novos | Confiança (1-5) |
|---|---|---|---|---|
| 0 | Reconstrução de requisitos | — | 0 (matriz) | 5 |
| 1 | Léxico | 0 | 46 | 5 |
| 2 | Sintático | 0 | 4 | 5 |
| 3 | Semântica — tipos/âmbito/`constante` | 0 | 27 | 5 |
| 4 | Semântica — estruturas/arrays N-d | 0 | 2 | 5 |
| 5 | Semântica — funções/`ref`/`incluir` | 0 | 4 | 4 — limite conhecido e documentado (não corrigido, por desenho) em `ref` de campo dentro de array |
| 6 | Geração de código / paridade | **1** | 33 | 4 — ver achado adicional da Etapa 12 no mesmo ficheiro |
| 7 | Erros em runtime | 0 | 5 | 4 — lista de categorias na documentação estava incompleta (corrigido na Etapa 12) |
| 8 | `cli.py` | **1** | 3 | 4 — cobertura fica limitada pela falha de ambiente (subprocess/`PATH`) para uma fração dos testes |
| 9 | Ferramentas (tracer/flowchart/linter) | 0 | 2 | 5 |
| 10 | Extensão VS Code | 0 | 5 | 4 — único ponto do projeto com ambiguidade estrutural real (texto/regex, sem parser) |
| 11 | Fuzzing/propriedades/mutation | 0 | 45 | 4 — mutation testing é uma linha de base (79.8%), não uma auditoria dos 560 sobreviventes |
| 12 | Segunda passagem independente | **1** | 2 | ver secção 5 |

Total: **~178 testes novos** ao longo da auditoria (soma dos números
acima; o total de testes do projeto cresceu de 623 para 792 coletados
porque a suite já continha testes doutras origens além desta
auditoria).

## 4. Bugs encontrados, por severidade

### CRÍTICO
Nenhum encontrado (nenhum bug causou perda de dados, corrupção
silenciosa generalizada, ou comportamento indefinido fora dos 3 casos
abaixo).

### MAJOR

**BUG-1 (Etapa 6)** — `codegen_minimo.py` rebentava em compilação
(`ErroInternoCompilador`), não só em execução, para qualquer programa
com um literal de estrutura `{...}` aninhado dentro doutro literal
(struct-em-struct, struct-em-array), nos 4 pontos de entrada
(declaração, atribuição, argumento de chamada, `devolver`) —
contradizendo o próprio contrato documentado de `--minimo` ("gera
sempre Python, só falha depois a CORRER"). Um programa 100% válido,
que compila e corre bem em modo normal, simplesmente não compilava em
`--minimo`.
- **Causa-raiz**: `codegen_minimo.py` nunca teve o par de métodos
  recursivos `_expr_estrutura_literal`/`_expr_array_literal` que
  `codegen.py` já tinha desde uma auditoria anterior (AL-78/B8) — cada
  ponto de entrada construía campos/elementos chamando `_expr()`
  genérico, sem ramo para `A.EstruturaLiteral` aninhado.
- **Correção**: `algo_lang/compilador/codegen_minimo.py`,
  `algo_lang/compilador/gerador_base.py`. 5 cenários de reprodução
  confirmados falhados antes / passados depois.
- **Evidência**: `algo_lang/tests/test_paridade_codegen.py` (novo,
  30 testes, incl. 3 regressões dedicadas a este bug).

**BUG-2 (Etapa 8)** — `cli.py:main()` crashava com
`UnicodeEncodeError` ao imprimir `✔`/`❌` sempre que invocado sem
passar por `algo.bat`/`algo.sh` — ou seja, `python -m algo_lang.cli`
(forma de invocação já documentada como suportada pelos próprios
testes) e o comando `algo` instalado corrido diretamente a partir de
um venv ativado à mão.
- **Causa-raiz**: a correção original (`AL-35`, de uma auditoria
  anterior) só foi aplicada ao nível do script de arranque
  (`algo.bat` define `chcp 65001`/`PYTHONIOENCODING=utf-8` antes de
  chamar `algo.exe`), nunca dentro do próprio `cli.py`.
- **Correção**: `algo_lang/cli.py` —
  `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` (+
  `stderr`) logo no início de `main()`, protegendo todos os caminhos
  de invocação por igual, redundante mas inofensivo com os scripts de
  arranque existentes.
- **Evidência**: `test_consola.py::test_cli_corre_via_python_dash_m`
  (já existia, estava na lista de falhas da baseline; passa desde a
  correção — a baseline de falhas de ambiente baixou de 79 para 78).

**BUG-3 (Etapa 12)** — `x:decimal = base ^ expoente`, com `base` e
`expoente` ambos `inteiro` e o expoente não sendo um literal —
`semantics.py` tipa a expressão como `decimal` (regra conservadora:
não consegue provar em compilação que o expoente nunca é negativo),
mas o `**` nativo do Python devolve `int` quando os dois operandos são
`int` e o expoente calculado em runtime acaba não-negativo. Uma
variável `decimal` ficava silenciosamente com um `int` Python — visível
sobretudo na impressão (`8` em vez de `8.0`), quebrando o contrato de
tipo do próprio compilador e divergindo do modo `--minimo` (que já
tratava este caso corretamente, por acidente de ter uma condição mais
estrita: só salta `float(...)` quando o expoente é um literal).
- **Causa-raiz**: `codegen.py::_expr` gerava `_algo_pot(a, b)`
  diretamente para o operador `^`, sem consultar `expr._tipo_inferido`
  como já fazia `_coagir_decimal` para outras conversões
  inteiro→decimal — `_coagir_decimal` não se aplicava aqui porque o nó
  já estava marcado "decimal" pelo próprio `semantics.py` (a condição
  de `_coagir_decimal` só dispara quando o nó está marcado
  "inteiro" e o alvo é "decimal", não cobrindo o caso em que o nó já
  é nominalmente "decimal" mas o valor Python subjacente pode ainda
  ser `int`).
- **Correção**: `algo_lang/compilador/codegen.py`, ramo `A.BinOp` /
  `"^"` de `_expr()` — envolve `_algo_pot(...)` em `float(...)` quando
  `expr._tipo_inferido == "decimal"` e os dois operandos têm tipo
  `"inteiro"`. Ponto de geração único, por isso a correção cobre
  automaticamente todos os contextos de uso (atribuição, argumento,
  elemento de array, campo de struct, `devolver`).
- **Efeito colateral revelado pela correção**: um teste existente
  (`test_cadeia_de_potencia_moderada_continua_a_funcionar`,
  `escrever(2^2^2)`) esperava "16", que já era o mesmo bug (o `^`
  exterior tem como expoente a sub-expressão `2^2`, não um literal, por
  isso também cai na mesma regra "decimal") — corrigido para "16.0",
  com o raciocínio documentado no próprio teste.
- **Evidência**: `test_paridade_codegen.py::potencia_inteira_com_
  expoente_variavel_atribuida_a_decimal`,
  `::potencia_encadeada_expoente_nao_literal` (novos, fecham a lacuna
  de cobertura — o corpus da Etapa 6 só testava expoente literal).

### MINOR / observações registadas, não corrigidas
Por decisão explícita de não alterar comportamento ou documentação
sem confirmação do responsável do projeto (regra de rigor do plano):

- `ErroSemantico` não tem parâmetro `coluna`, ao contrário de
  `ErroLexico`/`ErroSintatico` — pode ser deliberado (um erro de tipo
  tipicamente abrange uma expressão inteira, não um token único).
- `nulo` (palavra-chave) não aparece em nenhum documento de `docs/`.
- Os 3 ficheiros `.docx` de referência não mencionam
  `fluxograma`/`linter`/`--minimo`/`--debug`/`--json` — pode ser
  âmbito deliberado (documentos focados só na linguagem, não no CLI).
- `Linter.codigo_fonte` é guardado em `__init__` mas nunca lido —
  parâmetro morto, inofensivo.
- Campo de estrutura dentro de um array (`pontos[0].x`), passado 2×
  por `ref` na mesma chamada, nunca é detetado como aliasing — limite
  conhecido e documentado no próprio código (`_chave_ref_estatica`),
  fixado como comportamento atual por um teste de regressão, não
  "corrigido" (mudar isto é uma decisão de desenho, não um bug óbvio).
- 560 dos 2806 mutantes gerados na Etapa 11 sobreviveram — concentrados
  nos maiores dispatchers de cada ficheiro (mais ramos = mais pontos
  de mutação); não auditados mutante-a-mutante (fora do âmbito
  pedido, que era só estabelecer a linha de base).

## 5. Causas estruturais

Os 3 bugs reais partilham um padrão: **lógica que existe corretamente
num sítio do código, mas não foi replicada (ou foi replicada de forma
mais fraca) num sítio irmão**, tipicamente entre o modo normal e
`--minimo`, ou entre o script de arranque e o entry point Python:

- BUG-1: `codegen.py` já tinha os métodos recursivos para literais
  aninhados; `codegen_minimo.py` nunca os ganhou quando foi criado.
- BUG-2: a correção de encoding só foi aplicada ao script `.bat`, não
  ao `cli.py` que ele invoca — qualquer caminho de invocação que
  contorne o `.bat` herda a vulnerabilidade original.
- BUG-3: `_coagir_decimal` cobre a conversão inteiro→decimal para
  expressões marcadas "inteiro"; o operador `^` introduz um terceiro
  caso (marcado "decimal" pela incerteza do sinal do expoente, mas
  ainda capaz de produzir um `int` em runtime) que não se encaixa na
  condição existente e por isso escapou a essa rede de segurança.

Nos 3 casos, o "gémeo" mais robusto ou mais recente do código já tinha
a lógica certa (`codegen.py` normal, `algo.bat`, `--minimo`
respetivamente) — sugerindo que, quando uma correção é aplicada a um
de dois caminhos paralelos (normal/`--minimo`, `.bat`/`cli.py`), vale
a pena perguntar explicitamente "isto também se aplica ao caminho
irmão?" antes de fechar o trabalho. Nenhuma mudança de processo é
proposta aqui unilateralmente — fica como observação para o
responsável do projeto avaliar.

## 6. A causa de ambiente (78 falhas, não corrigida — não é um bug)

Confirmada de forma consistente e repetida ao longo de toda a
auditoria (Etapas 1, 5, 6, 7, 8, 9, 10, 11, 12): `subprocess.run(["algo",
...])`/`["python", ...])` falha com `FileNotFoundError: [WinError 2]`
nesta sessão local porque nenhum dos dois executáveis está resolvível
por nome simples no `PATH` do ambiente de sandbox. `sys.executable`
(caminho absoluto resolvido pelo próprio processo Python) sempre
funcionou como alternativa. Isto **não é um bug do compilador** — é
uma característica do ambiente desta sessão de auditoria, não do
projeto em produção (onde `algo.bat`/`algo.sh` garantem que o
executável está no `PATH` antes de correr qualquer coisa). Confirmado
de novo pelo revisor independente da Etapa 12, com uma causa técnica
adicional identificada (não crítica para o veredito): tentativas de
corrigir o `PATH` a partir do git-bash para um processo filho nativo
do Windows corrompem o valor do `PATH` herdado, mesmo com o diretório
certo nominalmente incluído.

## 7. Classificação de confiança global — por subsistema

| Subsistema | Confiança (1-5) | Justificação |
|---|---|---|
| Léxico | 5 | 46 testes dedicados, incl. Unicode/acentuação e símbolos-prefixo; nenhum bug em 2 rondas de auditoria |
| Sintático | 5 | Limites de recursão e erros amigáveis bem cobertos; única lacuna real (`ler()` sem argumentos) fechada |
| Semântica (tipos/âmbito/estruturas/arrays) | 5 | Matriz de compatibilidade tipo×operador construída e confirmada; sombreamento estruturalmente impossível além de 1 nível (não uma lacuna) |
| Geração de código / paridade normal↔`--minimo` | 4 | 2 bugs reais encontrados (Etapas 6 e 12) na mesma família (parity gaps); corrigidos, mas a existência de 2 instâncias sugere que pode haver uma 3ª ainda não encontrada nalgum canto do operador `^`/coerções de tipo não testado |
| Erros em runtime | 4 | Todas as 7 categorias verificadas por execução direta, mensagens corretas, sem fuga de traceback; ponto fraco era só a documentação incompleta, já corrigida |
| `cli.py` | 4 | 1 bug real corrigido; cobertura de teste fica genuinamente limitada pela falha de ambiente para uma fração dos testes desta área, não totalmente reverificável nesta sessão |
| Ferramentas (tracer/flowchart/linter) | 5 | Arquitetura (AST partilhada ou execução real) torna divergência estruturalmente difícil; confirmado por teste de consistência dedicado |
| Extensão VS Code | 4 | Único ponto do projeto sem parser real (regex sobre texto); comportamento agora testado diretamente, mas a ambiguidade estrutural continua a existir por natureza da tecnologia (TextMate), não é "corrigível" sem trocar de abordagem |
| Testes vácuos | 5 | Procura dirigida nas 4 áreas reauditadas (Etapa 12) não encontrou nenhum |
| Documentação | 4 | 2 desatualizações corrigidas; ficam por confirmar com o responsável do projeto 2 observações que podem ser âmbito deliberado, não lacunas |

**Confiança global na 4ª auditoria**: **4/5**. Não é 5 porque (a) a
cobertura de `cli.py` e das ferramentas de linha de comando fica
genuinamente limitada pela falha de ambiente desta sessão para uma
fração not-trivial dos seus próprios testes, exigindo reverificação
num ambiente com `algo` no `PATH`; e (b) o padrão dos 2 bugs de
paridade normal/`--minimo` (Etapas 6 e 12) sugere que esta família de
divergências pode não estar completamente esgotada, mesmo depois de
alargado o corpus de paridade duas vezes.

## 8. Evidências — números finais

- Testes coletados no fecho desta auditoria: **792** (623 no início).
- Resultado da suite completa (`python -m pytest algo_lang/tests/ -q
  -m "not slow"`, Windows, `sys.executable`): **78 failed, 711 passed,
  3 deselected**.
- As 78 falhas são 100% de ambiente (secção 6), reconfirmadas
  individualmente ao longo de 8 etapas distintas, nunca uma vez
  atribuídas a uma regressão real sem investigação.
- Mutation testing (Etapa 11, linha de base, `semantics.py` +
  `codegen.py`): 2806 mutantes, 2239 mortos, 560 sobreviventes, score
  global 79.8%.
- 3 bugs reais encontrados e corrigidos, cada um com reprodução
  confirmada antes/depois da correção e teste de regressão dedicado.
- 0 regressões introduzidas por qualquer correção desta auditoria
  (confirmado por diff direto da lista de nomes de testes falhados,
  não só por contagem, em todas as 12 etapas).

## 9. Recomendações para uma 5ª auditoria futura

- Reverificar `cli.py`/ferramentas de CLI/`algo.sh` num ambiente com o
  executável `algo` genuinamente no `PATH` (Linux/macOS nativo, ou
  Windows com o pacote instalado e a shell corretamente configurada) —
  a fração de testes destas áreas nunca correu de facto nesta sessão.
- Considerar auditar os 560 mutantes sobreviventes da Etapa 11,
  concentrados em `_verificar_stmt`/`_verificar_chamada`
  (`semantics.py`) e `_expr`/`_gerar_stmt` (`codegen.py`) — não feito
  aqui por estar fora do âmbito pedido (só linha de base).
- Confirmar com o responsável do projeto as 4 observações de
  documentação/design não corrigidas (secção 4, "Minor").
- Dado o padrão dos 3 bugs encontrados (lógica não replicada entre
  caminhos irmãos), ao rever qualquer correção futura a `codegen.py`
  ou `codegen_minimo.py`, verificar explicitamente se o caminho irmão
  precisa da mesma correção.
