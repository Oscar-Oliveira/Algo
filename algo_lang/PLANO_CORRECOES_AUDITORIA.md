# Plano de correções — auditoria de 2026-08-19/20

Plano de implementação para os 35 problemas confirmados em
`docs/AuditoriaCompilador_2026-08-19.md` (11 rondas). Agrupados por
mecanismo/ficheiro partilhado, não pela ordem em que foram encontrados,
porque vários bugs têm a mesma causa raiz e devem ser corrigidos juntos
numa só alteração. Cada grupo indica os ficheiros a tocar, a abordagem
proposta, e os testes de regressão a acrescentar (seguindo a convenção
`AL-XX` já usada em `tests/test_correcoes_auditoria.py`).

Nenhum código foi alterado ainda — isto é só o plano.

---

## Fase 1 — Semântica errada e silenciosa (prioridade máxima)

Estes são os bugs mais perigosos: não crasham, não mostram inglês,
produzem um resultado plausível mas errado. São os que mais corroem a
confiança de um estudante a aprender.

### 1.1 — Cópia por valor de structs/arrays (bug #1, e as suas consequências #13-parte-2 e #14) — ✅ CONCLUÍDO

**Ficheiros**: `compilador/codegen.py`, `compilador/gerador_base.py`

**Abordagem**: criar UM único ponto de cópia partilhado (ex.: um método
`_copiar_se_necessario(expr_python, tipo, dims)` em `gerador_base.py`,
que aplica `copy.deepcopy` sempre que `dims > 0` ou `tipo` é uma
estrutura) e chamá-lo em TODOS os 9 caminhos já mapeados:
- `_gerar_atribuicao` (atribuição simples e a campo/elemento) —
  `gerador_base.py:170-172`
- `_gerar_declaracao` (inicializador a partir de variável) —
  `codegen.py:515-517`
- `Devolver` (devolver variável existente) — `codegen.py:634-635`
- `_expr_vetor_literal`/`_expr_estrutura_literal` — aplicar a mesma
  cópia a cada elemento/campo que seja uma referência a variável
  existente (não um literal escalar), tanto no caminho genérico como no
  caminho de `_gerar_lista_args` que atualmente desvia `VetorLiteral`/
  `EstruturaLiteral` para fora do `deepcopy` — `codegen.py:407-464`

**Não mexer em**: passagem `ref` (aliasing é intencional).

**Testes a acrescentar**: um teste por cada um dos 9 caminhos já
descritos no bug #1, incluindo o caso de nesting (`Ponto[]` dentro de
`Ponto[][]`, campo-struct dentro de struct) para confirmar que
`deepcopy` (não uma cópia superficial) resolve mesmo os níveis
profundos.

**Resolve automaticamente**: bug #14 (`constante` quebrada por
atribuição normal) deixa de reproduzir assim que #1.1 estiver corrigido
— acrescentar um teste de regressão dedicado na mesma leva. Também
resolve a MEIA parte nova do bug #13 (colisão `ref` entre nomes
diferentes que aliasavam) — mas não a colisão `v[i]`/`v[j]` por índice
igual, que é uma limitação já conhecida e testada (`AL-04/AL-81/B9`,
ver 1.2) e fica deliberadamente como está.

---

### 1.2 — Índices negativos nunca validados (bug #31) + dupla avaliação em `ref` (bug #34, alcance completo) — ✅ CONCLUÍDO

**Ficheiros**: `compilador/gerador_base.py` (`_lvalue`/`_lvalue_de_expr`),
`compilador/codegen.py` (`_gerar_lista_args`, `_gerar_chamada_stmt`,
`_gerar_atribuicao`, `_gerar_declaracao`)

Estes dois bugs partilham a mesma zona de código (o mecanismo de
indexação e o de escrita-de-volta de `ref`) e vale a pena corrigi-los
na mesma revisão, com testes cruzados.

**Abordagem para #31 (sinal do índice)**: introduzir um helper de
runtime partilhado, ex. `_algo_indice(colecao, i)`, que faz
`if i < 0: raise IndexError(...)` antes de indexar — chamado por
`_lvalue`/`_lvalue_de_expr` em vez do atual `f"{base}[{indice}]"` cru,
para leitura E escrita, 1D e 2D+ (cada nível de indexação passa pelo
helper). Isto reaproveita o `except IndexError` já existente no rodapé
do programa gerado — nenhuma mudança na tradução de mensagens é
necessária, só deixar de confiar no `IndexError` nativo do Python (que
nunca dispara para índices negativos válidos).

**Abordagem para #34 (avaliação dupla em `ref`)**: nos três caminhos
que geram uma escrita-de-volta de `ref` (`_gerar_chamada_stmt`,
`_gerar_atribuicao`, `_gerar_declaracao`), antes de emitir a
chamada, "elevar" cada subexpressão de índice dentro de um argumento
`ref` para uma variável temporária (`_algo_tmp_idx_N = <expr>`),
avaliada uma única vez, e usar essa temporária tanto no argumento da
chamada como no alvo da escrita-de-volta. Não é preciso fazer isto para
TODOS os índices — só os que não são já uma variável simples ou um
literal (i.e., expressões com potencial efeito secundário: chamadas de
função, principalmente) — para não pessimizar o caso comum. Uma
implementação mais simples e mais segura (mais fácil de justificar
como correta): elevar sempre, para qualquer forma de índice dentro de
um argumento `ref`, e confiar no otimizador/legibilidade menor do
Python gerado.

**Testes a acrescentar**: os 10 casos já verificados do bug #31 (1D/2D,
leitura/escrita, `ref`, computado, array-de-structs) e as 6+ variantes
já mapeadas do bug #34 (campo de array-de-structs, 2D em qualquer
dimensão, 2D em ambas ao mesmo tempo, mesma expressão em dois `ref`,
nos três caminhos de código).

**Não mexer em**: a colisão documentada `v[i]`/`v[j]` (índice igual em
runtime, mesmo variável) — já é um limite conhecido e testado, não faz
parte deste bug.

---

## Fase 2 — Crashes crus / tracebacks Python (traduzir ou apanhar)

### 2.1 — Recursão não guardada em travessias da AST (bugs #7 e #10) — ✅ CONCLUÍDO

**Ficheiros**: `compilador/semantics.py` (`_tipo_expr`/`_tipo_binop`),
`tools/linter.py` (`_extrair_lvalues_e_chamadas`), potencialmente
`compilador/parser.py` (guarda preventiva) e `online/executor.py`

**Abordagem recomendada**: em vez de reescrever `_tipo_binop`/
`_extrair_lvalues_e_chamadas` para serem iterativas (mais trabalho, mais
risco), a correção mais direta e mais segura é **impedir a árvore
demasiado profunda logo no parser**: os métodos `_parse_aditiva`/
`_parse_multiplicativa`/etc. já sabem quantos operadores levam
consumido no `while` — acrescentar uma contagem e, acima de um limite
razoável (ex. 150-190, com margem para o limite real do CPython de
~200 parênteses aninhados encontrado no bug #7), levantar
`ErroSintatico` com uma mensagem amigável ("esta expressão tem operadores
a mais; considera dividi-la em variáveis intermédias"). Isto resolve #7
e #10 ao mesmo tempo (nenhum dos dois é sequer alcançado, porque a AST
nunca fica profunda o suficiente) e não precisa de tocar em
`semantics.py`/`linter.py`/`codegen.py` individualmente.

**Rede de segurança adicional** (defesa em profundidade, barata):
apanhar `RecursionError` explicitamente em `online/executor.py`'s
`compilar_codigo`/`analisar_linter` e convertê-lo num erro amigável,
para o caso de outra travessia recursiva futura ter o mesmo problema
sem passar pelo parser (ex.: se algum dia existir um caminho que gera
a AST de outra forma).

**Testes a acrescentar**: o limiar exato (verificar que compila até ao
limite escolhido e dá erro amigável logo a seguir, tanto para `+` como
para `*` e concatenação de `cadeia`); um teste que a mesma cadeia longa
já não chega a atingir `linter.analisar()` nem a gerar `SyntaxError` ao
executar.

**Depois desta correção**: atualizar
`test_fuzzing_e_propriedades.py:117` para tirar `RecursionError` da
lista de exceções aceitáveis (já não deve poder acontecer) — assim o
fuzzer volta a poder apanhar uma regressão futura da mesma forma.

---

### 2.2 — Mensagens em inglês / não traduzidas (bugs #4, #5, #8, #33, #35) — ✅ CONCLUÍDO

**Ficheiro principal**: `compilador/codegen.py` (`_algo_traduzir_valueerro`,
tabela de tradução), `bibliotecas/matematica.py`

Todos estes já caem num `except ValueError`/`except Exception`
existente — só falta a mensagem exata na tabela de tradução, ou
adicionar o tipo de exceção à cadeia:
- **#4** (`EOFError` em `--entradas` esgotado): acrescentar
  `except EOFError` à cadeia de exceções traduzidas em `codegen.py`,
  com mensagem tipo "o programa tentou ler mais valores do que os que
  o ficheiro de entradas tinha".
- **#5** (`passo=0` em runtime): acrescentar a mensagem
  `"range() arg 3 must not be zero"` à tabela de `_algo_traduzir_valueerro`.
- **#8** (`conversao.paraInteiro`/`paraDecimal` overflow): acrescentar
  `"cannot convert float infinity to integer"` e
  `"int too large to convert to float"` à mesma tabela.
- **#33** (`escrever` de inteiro gigante): acrescentar a mensagem
  `"Exceeds the limit"`/`"integer string conversion"` à tabela, com
  texto tipo "este número tem dígitos a mais para ser mostrado".
- **#35** (`^` vs `matematica.potencia` inconsistentes para inteiros
  grandes): mudar `matematica_potencia` para só forçar `float(...)`
  quando pelo menos um dos operandos já é `decimal` — quando ambos são
  `inteiro`, devolver `base ** exp` sem conversão, tal como o operador
  `^` já faz, para as duas sintaxes ficarem consistentes.

**Testes a acrescentar**: um teste por mensagem, reproduzindo o cenário
exato já documentado, confirmando que a mensagem final está em
português e não cita nomes de funções/API do Python.

---

### 2.3 — Colisão com nomes que o próprio codegen usa (bugs #23 e #27) — ✅ CONCLUÍDO

**Ficheiro**: `compilador/semantics.py` (`verificar_nomes_python`,
`nomes_internos_bibliotecas`)

**Abordagem**: `verificar_nomes_python` já bloqueia palavras-chave do
Python (`keyword.iskeyword`) — acrescentar uma lista explícita dos
nomes que o preâmbulo gerado usa sem qualificação (`sys`, `copy`,
`print`, `input`, e generalizar para incluir qualquer alias importado
pelo `CABECALHO` de QUALQUER biblioteca, não só `matematica`'s `_math`/
`_random` — ler `CABECALHO` de cada biblioteca em `bibliotecas/*.py` e
extrair os nomes `import X as Y` automaticamente, em vez de escrever
uma lista fixa que fica desatualizada quando uma biblioteca nova for
adicionada).

**Testes a acrescentar**: `sys`/`copy`/`print`/`input` e `_math`/
`_random` como nome de global — todos devem dar `ErroSemantico` claro
em compilação, não chegar a gerar Python.

---

### 2.4 — Codificação (bugs #25 e #28) — ✅ CONCLUÍDO

**Ficheiro**: `compilador/codegen.py` (`CABECALHO_RUNTIME`), `cli.py`
(`_ler_ficheiro_algo`)

- **#28** (BOM UTF-8 no ficheiro fonte): trocar `encoding="utf-8"` por
  `encoding="utf-8-sig"` em `_ler_ficheiro_algo` — mudança de uma
  linha, sem efeito quando não há BOM.
- **#25** (stdout não força UTF-8): acrescentar
  `sys.stdout.reconfigure(encoding="utf-8")` (com fallback silencioso
  se `reconfigure` não existir, para compatibilidade) no preâmbulo
  `CABECALHO_RUNTIME` do programa gerado.
- Verificar também a inconsistência apontada entre `--mostrar-python` e
  `--json` na captura de stdout do subprocesso em `cli.py` (mesma
  família, mencionada mas não isolada como bug próprio — vale a pena
  confirmar que a correção do #25 já resolve as duas).

**Testes a acrescentar**: ficheiro fonte com BOM compila normalmente;
`escrever` de emoji/acentos fora do ASCII básico não crasha mesmo numa
codepage restrita (se possível simular em teste; caso contrário, teste
manual documentado).

---

### 2.5 — `NameError` cru para referência antecipada escondida (bug #26) — ✅ CONCLUÍDO

**Ficheiro**: `compilador/semantics.py` (`_registar_decl`)

**Abordagem preferida** (corrige na origem, não só sintoma): quando
`_registar_decl` processa uma `A.Chamada` cujo alvo é uma função
definida no próprio ficheiro, verificar transitivamente que nomes
globais o CORPO dessa função lê (não só os argumentos da chamada) e
confirmar que já estão no `escopo_topo` construído até esse ponto —
mesma lógica já usada para os argumentos, generalizada. Alternativa
mais simples mas menos completa: acrescentar `NameError` à cadeia de
exceções traduzidas em `codegen.py` como rede de segurança (mais barato,
mas só trata o sintoma, não o diagnóstico tardio).

**Recomendação**: fazer as duas — a verificação em compilação dá o
diagnóstico correto e imediato; o `NameError` traduzido cobre qualquer
caso que a análise transitiva não apanhe.

**Testes a acrescentar**: o repro exato do bug (`pegaB()` lendo `b`
antes de `b` ser declarada) deve passar a dar `ErroSemantico` em
compilação.

---

## Fase 3 — Diagnóstico tardio em vez de erro em compilação

### 3.1 — `constante` como tamanho de array não resolvida (bug #29) — ✅ CONCLUÍDO

**Ficheiros**: `compilador/semantics.py` (`_valor_literal_negativo`,
`_tamanho_estatico`), `tools/linter.py`
(`_vetores_com_tamanho_literal`, `_campos_vetor_por_nome`)

**Abordagem**: criar um helper partilhado `_resolver_constante(expr)` em
`semantics.py` que, dado um `A.LValue` referenciando uma `constante` já
registada com um `A.Literal` (ou outra `constante` já resolvida,
recursivamente — para cobrir `N = A + B`), devolve o valor dobrado como
se fosse um literal; devolve `None` para qualquer outra coisa (variável
normal, expressão não-constante). Trocar as três verificações
`isinstance(x, A.Literal)` por `isinstance(x, A.Literal) or
_resolver_constante(x) is not None`, usando o valor resolvido. Expor o
mesmo helper (ou uma cópia equivalente) ao `linter.py`, já que ambos os
ficheiros têm o mesmo problema.

**Testes a acrescentar**: tamanho negativo via `constante` dá erro em
COMPILAÇÃO (não só em runtime); tamanho do literal `{...}`
incompatível com tamanho `constante` dá erro em compilação; o linter
passa a avisar de índice fora dos limites num array de tamanho
`constante`; o linter deixa de avisar (erradamente) que a `constante`
"nunca é usada" quando só é usada como tamanho.

---

## Fase 4 — `linter.py` (correções pequenas e independentes) — ✅ CONCLUÍDO (bug #11 investigado e descartado — ver nota)

**Ficheiro**: `tools/linter.py`

- **#3 e #11** (`_verificar_globais_nao_usadas` e
  `_verificar_uso_de_globais`): em ambas as funções, uma variável de
  ciclo `Para` só deve contar como "local" (não afeta a global
  homónima) se NÃO estiver dentro do corpo principal — dentro de uma
  função, só conta como local se também estiver na lista de nomes
  coletados por `coletar_declaracoes_tipadas` como local. Mesma
  correção, duas funções — fazer as duas juntas.
- **#12** (aviso duplicado de índice fora dos limites em atribuições):
  remover a verificação implícita redundante via `_expressoes_lidas`
  para o alvo (`s.alvo`) de uma `Atribuicao`, já que a verificação
  explícita logo a seguir já cobre o caso.
- **#20** (cegueira a arrays 2D+): em
  `_vetores_com_tamanho_literal`/`_campos_vetor_por_nome`, trocar
  `len(d.dims) == 1` por registar o tamanho de CADA dimensão
  individualmente (uma lista/dict de tamanhos por variável, não um
  único inteiro), e em `_verificar_indices_expr` percorrer todas as
  dimensões do acesso, não só a primeira.

**Testes a acrescentar**: um por bug, mais um teste de regressão que
conta o número de avisos (`len(avisos) == 1`, não só `any(...)`) para
o #12, para não voltar a passar despercebido da mesma forma.

---

## Fase 5 — `cli.py` (correções pequenas e independentes) — ✅ CONCLUÍDO

**Ficheiro**: `cli.py`

- **#6 e #15** (erros de `incluir` não identificam o ficheiro):
  em `_resolver_lista_de_inclusoes`, envolver a chamada a
  `parse_biblioteca` num `try/except (ErroSintatico, ErroLexico)` que
  reatribui o erro ao ficheiro incluído antes de o relançar — mesma
  abordagem que `online/executor.py:190-192` já usa corretamente
  (copiar o padrão de lá).
- **#16** (`--mostrar-python` ignorado com `--debug`/`--json`):
  `cmd_executa_com_trace` deve ler `args.mostrar_python` e imprimir o
  Python gerado tal como `cmd_executa` já faz, ou a ajuda da CLI deve
  passar a documentar a incompatibilidade explicitamente (decisão do
  maintainer — a correção mais simples e mais útil é fazer o `--debug`/
  `--json` também respeitar a flag).
- **#30** (caminho de saída longo no Windows): em `_pasta_saida`,
  envolver `os.makedirs` num `try/except OSError` com mensagem amigável
  ("o caminho de saída é demasiado longo para o Windows; tenta mover o
  ficheiro para uma pasta com um caminho mais curto").

**Testes a acrescentar**: um por bug; o de caminho longo pode ser
difícil de testar de forma portável — considerar `skipif` fora do
Windows ou mock de `os.makedirs`.

---

## Fase 6 — Limite de recursos (precisa de decisão do maintainer)

### 6.1 — Tamanho de array sem limite superior (bug #32) — ✅ CONCLUÍDO (limite: 10 milhões, decisão do maintainer)

**Ficheiros**: `compilador/semantics.py` (`_validar_dims`),
`compilador/codegen.py`/`gerador_base.py`
(`_algo_verificar_tamanho_vetor`)

**Decisão necessária antes de implementar**: qual o tamanho máximo
razoável para um array num contexto de ensino? Um valor demasiado baixo
frustra utilizações legítimas; um valor demasiado alto continua a
permitir o "pendurar-se". Sugestão de ponto de partida: um limite na
ordem dos 1-10 milhões de elementos (a medição da ronda 9 mostra que
10 milhões já demora quase 1 segundo; 100 milhões já demora 13
segundos) — configurável, não fixo no código, se possível.

**Abordagem**: acrescentar o limite escolhido a
`_algo_verificar_tamanho_vetor` (o guarda de runtime já existente, que
já corre antes da list-comprehension), com mensagem amigável ("o
tamanho pedido é maior do que o limite permitido"). Não é preciso
mexer em `semantics.py` para o caso literal, desde que o guarda de
runtime cubra também esse caso (hoje já cobre, só falta o limite
superior).

**Testes a acrescentar**: um tamanho já acima do limite escolhido dá
erro amigável rápido, não fica pendurado.

---

## Fase 7 — Desempenho (não é bug de correção)

### 7.1 — `tracer.py` quadrático em recursão profunda (bug #17) — ✅ CONCLUÍDO

**Ficheiro**: `tools/tracer.py` (`construir_pilha`)

**Abordagem**: manter a pilha de frames incrementalmente (empurrar/
retirar um frame só quando entra/sai de uma chamada) em vez de
reconstruir a cadeia completa a cada linha traçada — troca o custo
total de O(profundidade²) para O(profundidade). Sem prioridade alta
(não é uma correção, `MAX_PASSOS=4000` já protege contra o pior caso),
mas vale a pena arrumar já que está bem localizado.

---

## Fase 8 — Ronda 12 (reauditoria 2026-08-21): 5 bugs reconfirmados nunca corrigidos + 8 bugs novos

Esta fase nasceu de uma reauditoria pedida depois de se assumir
(incorretamente) que as Fases 1-7 tinham fechado tudo. Não tinham: os
bugs #2, #9, #18, #19 e #24 do documento de auditoria estavam
confirmados desde as rondas 1-4 mas nunca tiveram fase própria neste
plano. Reproduzidos de novo, live, antes de escrever este plano. Ver
`docs/AuditoriaCompilador_2026-08-19.md`, secção "Ronda 12", para o
detalhe completo de cada bug (incluindo os 8 novos, #36-#43).

### 8.1 — Fusão de âmbito entre ramos `se`/`senao` (bugs #2, #9, #39) — ✅ CONCLUÍDO (bug #38 investigado e descartado, ver nota)

**Ficheiro**: `compilador/semantics.py` (`_pre_registar_recursivo`)

Os quatro bugs partilham a mesma causa raiz: `_pre_registar_recursivo`
(`semantics.py:350-398`) trata qualquer `Declaracao` encontrada em
QUALQUER bloco alcançável (`A.subblocos`) como incondicionalmente
válida, sem nenhuma noção de exaustividade/alcançabilidade do ramo que
a contém, e sem conciliar `eh_constante`/`valor_resolvido` quando o
mesmo nome aparece em ramos irmãos:
- **#2**: `eh_constante` do ramo visitado primeiro (`s.ramos` antes de
  `s.senao`) vence, independentemente de qual ramo executa.
- **#9**: quando a MESMA declaração (tipo e `eh_constante` iguais)
  aparece em AMBOS os ramos de um `se`/`senao` exaustivo, o nome devia
  ficar disponível depois do `se` — hoje não fica.
- **#39**: `valor_resolvido` (usado por `_resolver_constante`) nunca é
  reconciliado entre ramos irmãos, só `tipo`/`dims`.

**Implementado**:
- **#2**: `_pre_registar_recursivo` (mecanismo de globais visíveis a
  funções) passou a comparar `eh_constante` entre ramos irmãos com o
  mesmo `tipo`/`dims`, tal como já fazia para o tipo -- diverge? dá
  `ErroSemantico` (mesmo padrão da mensagem de tipos diferentes), em
  vez de ficar silenciosamente com o `eh_constante` do primeiro ramo
  visitado em DFS.
- **#39**: mesmo sítio, mesmo padrão -- quando `eh_constante`/tipo
  batem certo mas o `valor_resolvido` (bug #29) diverge entre ramos,
  o valor fica `None` (não resolvível estaticamente) em vez de
  congelado no primeiro ramo. `_resolver_constante` já trata `None`
  como "não é um literal conhecido", por isso o efeito é o esperado:
  o tamanho do vetor deixa de ser verificado em COMPILAÇÃO (fica para
  o guarda de runtime, `_algo_verificar_tamanho_vetor`), mas já não
  rejeita código válido por adivinhar o valor errado.
- **#9**: mecanismo SEPARADO (âmbito local de `_verificar_stmt`, não
  `_pre_registar_recursivo`) -- cada ramo de `A.Se` passou a ter o seu
  `Escopo(escopo)` capturado numa lista; quando há `senao` (ramos
  exaustivos) e um nome aparece nos `.locais` de TODOS os ramos com a
  mesma tupla `(tipo, dims, eh_constante, valor_resolvido)`, é
  propagado para o escopo pai depois do `se` -- disponível ao código
  seguinte, tal como uma declaração normal. Sem `senao`, ou com
  ramos que divergem, fica por declarar (sem erro, só sem
  propagação) -- comportamento anterior preservado nesse caso.

**#38 investigado, correção revertida** -- ver nota completa em
`docs/AuditoriaCompilador_2026-08-19.md`, bug #38: a correção óbvia
(ignorar ramos com condição literal `falso` em
`_pre_registar_recursivo`) quebra
`test_variavel_global_com_tipos_diferentes_em_ramos_irmaos_e_erro`,
já existente e deliberado -- esse teste espera que MESMO um ramo `se
falso` continue a contar para a verificação de tipos entre ramos
irmãos. Resolver #38 sem quebrar essa garantia exigia dois
comportamentos diferentes para o mesmo mecanismo (usar
alcançabilidade só para “registar como visível”, mas não para
“verificar consistência de tipo”) -- mais arriscado do que vale a pena
para um bug `média`. Descartado por agora.

### 8.2 — `escolher` sem nenhum `caso` (bugs #24, #37) — ✅ CONCLUÍDO

**Ficheiros**: `compilador/codegen.py` (geração de `escolher`),
`tools/linter.py`

- **#24** (causa raiz): a geração de `escolher`/`caso` em `codegen.py`
  assume implicitamente que existe pelo menos um `caso`, produzindo um
  `else:` sem `if`/`elif` antes quando `stmt.casos` está vazio.
  Corrigir para gerar sempre uma estrutura válida mesmo com zero
  `caso` (ex.: `if True:` antes do bloco do `contrario`, ou tratar
  "zero `caso`" como equivalente a executar sempre o `contrario`
  diretamente, sem `if` nenhum).
- **#37** (rede de segurança estática): acrescentar um `_verificar_*`
  a `linter.py` que avisa quando `A.Escolha.casos` está vazio
  ("'escolher' sem nenhum 'caso' -- só o 'contrario' é executado, o
  'escolher' aqui não faz nada útil"), para apanhar o padrão mesmo
  antes de #24 ser exercitado.

**Testes a acrescentar**: `escolher` só com `contrario` compila E
executa corretamente (sem `SyntaxError` no Python gerado); mesmo caso
produz exatamente 1 aviso do linter.

### 8.3 — Robustez de `tracer.py`/consola a Python gerado inválido (bug #36) — ✅ CONCLUÍDO

**Ficheiros**: `tools/tracer.py`, `cli.py`

- Mover/envolver a chamada `compile(codigo_py, caminho_py, "exec")`
  (`tracer.py:294`) no mesmo `try/except Exception` que já existe para
  o `exec()` (`tracer.py:309`), traduzindo `SyntaxError` para uma
  mensagem amigável tal como os outros erros de runtime já traduzidos.
- `cmd_executa_com_trace` (`cli.py:295-302`) deve envolver a chamada a
  `gerar_trace(...)` num `try/except` que mostra a mensagem amigável e
  sai com código de erro, em vez de deixar propagar.
- `cmd_consola` (`cli.py:653-672`): alargar o `except` do ciclo de
  comandos para apanhar `Exception` em geral (não só
  `SystemExit`/`KeyboardInterrupt`), consistente com o contrato já
  documentado ali ("um comando com erro só mostra o erro e volta ao
  prompt -- não fecha a consola").

**Testes a acrescentar**: repro do bug #24 sob `--debug`/`--json` dá
mensagem amigável, não traceback; o mesmo repro dentro da consola
mostra o erro e mantém o prompt aberto (não fecha o processo).

### 8.4 — `nan`/`inf`/`-inf`/`Infinity` em `ler()` (bug #19) — ✅ CONCLUÍDO (bug #40 investigado e descartado, ver nota)

**Ficheiro**: `compilador/codegen.py` (`_algo_ler_decimal`,
via novo helper partilhado `_algo_texto_para_decimal`)

**Implementado**: `_algo_texto_para_decimal(texto)` rejeita
`nan`/`inf`/`-inf`/`Infinity` (case-insensitive) e separadores `_` de
milhar, chamado pelo `_algo_ler_decimal` gerado -- entrada interativa
inválida faz o mesmo "Valor inválido, tenta outra vez" que já existe
para `booleano`/`caracter`, em vez de aceitar em silêncio.

**Bug #40 (`conversao.paraDecimal`) investigado e NÃO corrigido, de
propósito**: a mesma rejeição aplicada a `conversao.paraDecimal`
quebrou 2 testes já existentes
(`test_matematica_piso_de_infinito_da_overflow_amigavel`,
`test_conversao_parainteiro_de_infinito_da_erro_amigavel`) que usam
`conversao.paraDecimal("inf")` deliberadamente -- é o único ponto de
todo o ALGO por onde um programa consegue construir um valor
infinito/nan (a linguagem não tem literal nenhum para isso). Os
consumidores (`matematica.piso`/`teto`, `conversao.paraInteiro`) já
traduzem o `OverflowError` resultante de forma amigável. Ver nota
completa em `docs/AuditoriaCompilador_2026-08-19.md`, bug #40.
`conversao.paraDecimal` continua a aceitar `nan`/`inf`/`Infinity`
(mas passou a rejeitar separadores `_`, ver 8.7/bug #43).

### 8.5 — `escrever` de artefactos crus de vírgula flutuante (bug #18) — ✅ CONCLUÍDO

**Implementado**: `_algo_fmt` arredonda qualquer `float` a 12 casas
decimais (`round(v, 12)`) antes de o formatar com `repr`, e normaliza
`-0.0` para `0.0`. `0.1 + 0.2` passa a mostrar `0.3`; `3.0` continua a
mostrar `3.0` (mantém o `.0` que distingue `decimal` de `inteiro`).
Notação científica para magnitudes extremas (ex. `10.0^20` → `1e+20`)
fica deliberadamente por resolver -- decisão documentada no próprio
código (`codegen.py:_algo_fmt`), fora do alcance razoável de "limpar
ruído de vírgula flutuante comum".

### 8.6 — Mensagens do parser que fogem ao `_nome_amigavel` (bugs #41, #42) — ✅ CONCLUÍDO

### 8.7 — Separadores `_` aceites por engano em `conversao.*` (bug #43) — ✅ CONCLUÍDO

---

## Depois de tudo o que está acima

- Atualizar `test_fuzzing_e_propriedades.py:117` (remover
  `RecursionError` da lista de exceções aceitáveis, ver Fase 2.1).
- Correr `py -m pytest algo_lang/tests/ -q -m "not slow"` depois de
  CADA fase (não só no fim) para apanhar regressões cedo.
- Depois de cada correção, atualizar
  `docs/AuditoriaCompilador_2026-08-19.md` a marcar o item como
  corrigido (não apagar — manter o histórico da auditoria).

## Fora do âmbito deste plano (não é `algo_lang/`)

Registados no documento de auditoria mas não planeados aqui em
detalhe, por estarem noutros subprojetos:
- **Bug #21** (`online/executor.py`'s rota WebSocket não apanha
  `RecursionError`) — resolve-se sozinho depois da Fase 2.1, mas a rota
  `/ws/executar` devia mesmo assim ganhar o seu próprio `try/except`
  como rede de segurança, já que WebSockets não passam pelo handler
  global do FastAPI.
- **Bug #22** (`alguem/nucleo/ficheiros_visiveis.py` não ignora
  comentários ao resolver `incluir`) — corrigir aplicando
  `_remover_comentarios_bloco` (ou equivalente) ao texto antes de
  aplicar o regex, espelhando o que o lexer real já faz.
- Consistência de idioma remanescente em `alguem/`, `online/`, e nos
  `docs/*.md` que ainda usam "array" em vez de "vetor".
