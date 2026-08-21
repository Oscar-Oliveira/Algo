# Auditoria ao compilador (algo_lang) — 2026-08-19

**Nota de fiabilidade:** este documento teve 11 rondas, cada uma pedida
explicitamente pelo utilizador ("vai mais a fundo") depois de rondas
anteriores se terem revelado incompletas. A 1ª ronda (4 agentes, âmbito
"bugs de correção") deu `lexer.py`/`parser.py`/`ast_nodes.py` como "sem
bugs" e descreveu o bug #1 (aliasing) como limitado a 3 sítios — ambos
errados, como as rondas seguintes mostraram. O utilizador também apanhou,
ele próprio, um problema de consistência de idioma que a 1ª ronda tinha
passado ao lado (ver secção "Consistência de idioma") — o que motivou a
2ª ronda. A 3ª e 4ª rondas continuaram a encontrar bugs novos e
genuínos, incluindo em ficheiros já dados como "limpos" nas rondas
anteriores. **A 4ª ronda também corrigiu-se a si própria**: uma parte do
bug #13 (reportado na ronda 3 como novo) afinal já era uma limitação
conhecida e testada — ver a nota dentro do próprio bug #13. Nem tudo o
que cada ronda encontra fica confirmado pela ronda seguinte; é assim que
deve ser lido este documento — como o melhor estado do conhecimento
disponível agora, não como palavra final. Secções estão marcadas por
ronda onde relevante. **A ronda 12** (reauditoria pedida depois de se
assumir que tudo estava corrigido) confirma que essa assunção também
estava errada: 5 bugs já confirmados (#2, #9, #18, #19, #24) nunca
tiveram fase no plano de correções nem foram corrigidos, apesar de
continuarem listados como "confirmados" desde as rondas 1-10 — ver
secção "Ronda 12" para o achado completo e 8 bugs novos.

## Âmbito e método

Leitura integral (não por amostragem) de todo o código não-teste de `algo_lang/`
(6119 linhas): `lexer.py`, `parser.py`, `ast_nodes.py`, `semantics.py`,
`codegen.py`, `gerador_base.py`, `inclusoes.py`, `bibliotecas/*.py`, `cli.py`,
`tools/tracer.py`, `tools/flowchart.py`, `tools/linter.py`. Feita em 4 auditorias
paralelas (front-end léxico/sintático, verificador semântico, gerador de
código, CLI/ferramentas), cada uma obrigada a **reproduzir** qualquer bug
suspeito com um `.algo` mínimo antes de o reportar — nada especulativo.

Baseline de testes: `py -m pytest algo_lang/tests/ -q -m "not slow"` →
**659 passaram, 33 falharam**. As 33 falhas são todas de ambiente (testes que
chamam `subprocess`/`algo` na PATH, que não resolve dentro desta sandbox
Windows/git-bash) — confirmado inspecionando cada traceback, nenhuma é do
compilador.

## Bugs de correção confirmados (com reprodução)

### 1. (grave) Structs/arrays ficam "aliased" em vez de copiados — 9 caminhos confirmados, não 3

**[CORRIGIDO — Fase 1.1 do `PLANO_CORRECOES_AUDITORIA.md`]** Ponto único
de cópia (`_copiar_se_necessario`, `gerador_base.py`) aplicado nos 4
locais de código que na prática cobrem os 9 caminhos (os restantes 5
eram consequências dos mesmos 4 locais): `_gerar_atribuicao` (base),
`_gerar_declaracao` e `Devolver` (`codegen.py`), e os dois construtores
de literal `_expr_vetor_literal`/`_expr_estrutura_literal`
(`codegen.py`). Também cobre `devolver` de um vetor inteiro (dims>0),
um caso não enumerado explicitamente nos 9 mas alcançável pela mesma
falha (`permitir_vetor=True` em `devolver`). 16 testes de regressão
acrescentados a `test_correcoes_auditoria.py`, incluindo o bug #14
(constante quebrada por atribuição normal) e cópia profunda em campo
struct-com-vetor aninhado.

`codegen.py:407-464,515-517,634-635`, `gerador_base.py:170-172`. A 1ª ronda
encontrou 3 exemplos; a 2ª ronda mapeou o alcance completo, com reprodução
individual de cada um:

**Confirmados com bug** (todos verificados, todos imprimem o valor mutado em
vez do original):
1. Atribuição simples `p2 = p1`.
2. Declaração com inicializador `p2: Ponto = p1`.
3. `devolver g` (variável existente, não literal).
4. Atribuição a campo de struct aninhado: `r.canto = p1`.
5. Literal de vetor com elementos que são variáveis struct: `v:Ponto[2] = {p1, p2}`.
6. Elemento-a-elemento num vetor de structs: `arr[0] = arr[1]`.
7. Elemento de vetor a partir de variável: `arr[0] = p1`.
8. Campo de literal de struct a partir de variável: `r: Retangulo = {canto: p1}`.
9. **Literal de vetor passado diretamente como argumento**, `f({p1, p2})` —
   `_gerar_lista_args` desvia literais `VetorLiteral`/`EstruturaLiteral`
   para `_expr_vetor_literal`/`_expr_estrutura_literal` **sem** passar pelo
   `copy.deepcopy` que protege todos os outros formatos de argumento — ou
   seja, mesmo a via "seguro por design" (passagem por parâmetro) tem uma
   fuga quando o argumento é um literal `{...}` com uma variável lá dentro.
10. Mesma fuga com **literal de struct** como argumento: `f({canto: p1})`.

**Confirmados como seguros** (não são o bug, verificados para não haver
falso alarme): `ref` (aliasing é intencional, correto por design);
`muta(p1)` — struct passada diretamente como argumento, protegida por
`deepcopy`; `a2 = a1` (vetor inteiro, não struct) — na verdade
`semantics.py` já rejeita esta atribuição categoricamente
(`ErroSemantico: '...' é um vetor; não pode ser atribuído diretamente`),
por isso este caminho é inatingível, não há bug aí.

**Repro original (caso 1), verificado por mim, independentemente:**
```algo
algoritmo "T"
estrutura Ponto
    x: inteiro
    y: inteiro
inicio
    p1: Ponto
    p2: Ponto
    p1.x = 1
    p1.y = 2
    p2 = p1
    p2.x = 99
    escrever(p1.x)
    escrever(p2.x)
```
Python gerado: `p2 = p1` (sem cópia). Saída real: `99` / `99`. Esperado: `1` / `99`.

**Causa raiz (2 partes):** (a) qualquer caminho de atribuição/declaração/
devolução para um alvo de tipo struct ou elemento-de-vetor-de-struct que
não passe por `_gerar_lista_args` faz um `=` de Python simples, sem cópia;
(b) mesmo dentro de `_gerar_lista_args`, literais `{...}` contendo
variáveis existentes escapam ao `deepcopy` porque são tratados por um
ramo especial antes do ramo genérico que aplica a cópia. Uma correção
completa tem de cobrir os 9 caminhos, não só os 3 originais, e usar
`copy.deepcopy` (não uma cópia superficial) para não deixar `Ponto[]`
dentro de `Ponto[][]` ou campos-struct-dentro-de-struct ainda aliased.

### 2. (grave) `constante` perde-se entre ramos irmãos `se`/`senao`

**[CORRIGIDO — Fase 8.1 do `PLANO_CORRECOES_AUDITORIA.md`, ronda 12]**
`_pre_registar_recursivo` passou a comparar `eh_constante` entre ramos
irmãos com o mesmo tipo -- diverge? `ErroSemantico`, em vez de ficar
com o valor do primeiro ramo visitado em DFS. Fica um erro de
COMPILAÇÃO em vez de mutação silenciosa em runtime.

`semantics.py:200-238` (repro original).

Se o mesmo nome é declarado `constante` num ramo e mutável no ramo irmão,
`_pre_registar_recursivo` fica só com o `eh_constante` do ramo que visita
primeiro (ordem de `ast_nodes.subblocos`: sempre `s.ramos` antes de
`s.senao`), independentemente de qual ramo executa de facto. Verificado
(por mim, independentemente):

```algo
algoritmo "T"
procedimento mexe()
    x = 999
procedimento mostra()
    escrever("x =", x)
inicio
    se falso entao
        x:inteiro = 10
    senao
        constante x:inteiro = 5
    mostra()
    mexe()
    mostra()
```
Compila sem erro nenhum. Saída real: `x =5` / `x =999` — a `constante`
(a que de facto executa, no `senao`) foi mutada em silêncio por `mexe()`.

### 3. (média) Linter não deteta global morta quando só é "usada" via variável de ciclo dentro de função

**[CORRIGIDO — Fase 4 do `PLANO_CORRECOES_AUDITORIA.md`]** Confirmado
em runtime (repro direto, comparando `escrever` antes/depois de
chamar um procedimento cujo único "uso" de uma global é como
variável de ciclo `para`): a global mantém-se inalterada -- `para var`
dentro de uma função é sempre local, nunca muta uma global homónima.
`_verificar_globais_nao_usadas` só conta um `para var` como uso da
global quando está no CORPO PRINCIPAL (onde `_algo_programa()` já
declara `global` para tudo incondicionalmente) -- dentro de uma
função, já não conta.
`linter.py:283-301`, `_verificar_globais_nao_usadas`.

Trata qualquer `para <var>` no programa inteiro (corpo principal OU dentro de
qualquer função) como prova de uso da global homónima. Mas dentro de uma
função, `_gerar_funcao` (`gerador_base.py:251-263`) exclui esse `para` do
`global` da função — é uma variável local independente, nunca toca a global.
Mesma classe de erro que o AL-63/B23 já corrigiu na função irmã
(`_verificar_uso_de_globais`), não replicada aqui.

### 4. (média) `ler()` a mais com `--entradas` esgota o ficheiro e mostra `EOFError` em inglês

**[CORRIGIDO — Fase 2.2 do `PLANO_CORRECOES_AUDITORIA.md`]** `except
EOFError` acrescentado à cadeia de exceções traduzidas em
`codegen.py`. Como o `.py` gerado inclui a sua própria cadeia
`try/except`, `tools/tracer.py` (usado por `--debug`/`--json`) herda a
correção automaticamente via `_ALGO_ERRO_RUNTIME` — não precisou de
alteração própria.
Sem tratamento em `codegen.py`'s cadeia de `except` (que traduz `IndexError`,
`ZeroDivisionError`, `OverflowError`, `RecursionError`, `AttributeError`,
`ValueError`, `_AlgoIndiceCadeiaInvalido`). Cai no `except Exception` genérico
de `tracer.py:261-262`, cujo comentário diz "não deve ocorrer" — mas ocorre,
com um simples ficheiro `--entradas` mais curto do que o esperado. Mensagem
real vista pelo estudante: `EOF when reading a line` — texto cru em inglês.

### 5. (menor) `passo` calculado em runtime igual a 0 vaza mensagem em inglês

**[CORRIGIDO — Fase 2.2]** Mensagem "range() arg 3 must not be zero"
acrescentada à tabela de `_algo_traduzir_valueerro`.
`semantics.py:722-725` só rejeita um `passo` **literal** igual a 0 em tempo de
compilação. Um `passo` que só dá 0 em runtime (ex.: vindo de uma variável)
chega a `range(ini, fim, 0)` sem guarda, e `_algo_traduzir_valueerro` não tem
caso para essa mensagem → cai no genérico `"valor inválido (range() arg 3
must not be zero)."`, com o texto interno do Python à mistura.

### 6. (cosmético) Erro de inclusão do ficheiro principal por engano não identifica o ficheiro

**[CORRIGIDO — Fase 5 do `PLANO_CORRECOES_AUDITORIA.md`, ver bug #15]**
Mesma causa raiz e correção do bug #15 -- `parse_biblioteca` também é
o sítio que rejeita um ficheiro sem a forma de uma biblioteca (ex.: o
próprio principal, incluído por engano).
Se uma biblioteca incluir por engano o próprio ficheiro principal, o erro de
sintaxe resultante ("um ficheiro incluído só pode conter...") não diz qual
ficheiro está em causa. Não crasha, só confunde. Impacto muito baixo.

### 7. (ronda 2, grave) Cadeia plana de operadores (`1+1+1+...`) crasha com `RecursionError` cru

**[CORRIGIDO — Fase 2.1 do `PLANO_CORRECOES_AUDITORIA.md`]** Guarda no
parser (`parser.py`), mas não como um simples contador local por
nível (`_parse_aditiva`/`_parse_multiplicativa`/etc.) como o plano
sugeria inicialmente -- um contador desse tipo não compõe
corretamente quando o PRIMEIRO operando de uma cadeia já é ele
próprio profundo (esse operando fica mais enterrado na árvore final
depois dos wraps seguintes, não menos, e já tinha sido "esquecido"
pelo contador antes da cadeia externa sequer começar a contar).
Implementado em vez disso como profundidade REAL da árvore,
guardada como atributo em cada nó (`_algo_prof_arv`, calculado
bottom-up em `_criar_binop`/`_criar_unop`, chamado em todos os
sítios que constroem um `BinOp`/`UnOp`), verificada contra
`LIMITE_PROFUNDIDADE_ARVORE = 150` -- com margem folgada abaixo dos
~200 parênteses aninhados que o CPython aguenta ao EXECUTAR o `.py`
gerado. Testado explicitamente que compõe corretamente entre níveis
de precedência diferentes (`e`/`aditiva` combinados), não só dentro
do mesmo nível. Rede de segurança adicional (`RecursionError` →
`ErroCompilacao`) acrescentada em `online/executor.py` para qualquer
outra travessia recursiva presente ou futura que escape ao parser.
`parser.py` (comentário nas linhas ~48-55) deixa deliberadamente
`_parse_ou`/`_parse_e`/`_parse_relacional`/`_parse_aditiva`/
`_parse_multiplicativa` fora do guarda de profundidade
`LIMITE_PROFUNDIDADE_EXPR`, porque avançam num `while` (a pilha do
*parser* não cresce com uma cadeia plana do mesmo operador). Correto para
o parser — mas o `while` continua a construir uma árvore `BinOp`
encadeada com profundidade igual ao nº de operadores, e não há guarda
nenhuma para quem depois **percorre** essa árvore recursivamente:
`semantics.py`'s `_tipo_expr`/`_tipo_binop` recursam uma vez por elemento
da cadeia e rebentam a pilha real do Python.

Verificado: 497 termos (`1+1+...+1`, 497×) compila normalmente; **498
termos** dá `RecursionError: maximum recursion depth exceeded`, traceback
Python cru, sem `try/except` nenhum a apanhar. Mesmo problema confirmado
com uma cadeia de `*` (testado a 2000 termos). Não é um caso extremo
artificial — é um programa sintaticamente normal, só "longo".

**Refinamento (ronda 5): o limiar real, ao EXECUTAR (não só compilar), é
muito mais baixo — ~201 termos, não 498, e falha de forma diferente.**
`codegen.py:740` envolve cada `BinOp` em parênteses Python literais, por
isso uma cadeia plana de N operadores produz código Python com N
parênteses aninhados. O próprio parser do CPython tem um limite de
aninhamento (~200): **200 termos compila e corre bem; 201 termos falha**
com `SyntaxError: too many nested parentheses` — um erro cru do Python,
gerado ao executar o `.py` já compilado, sem nenhum `try/except` a
apanhar (mesma lacuna do bug #21). Mesmo problema confirmado para
concatenação de `cadeia` (`"a"+"a"+...`). Não é uma causa raiz diferente
— é o mesmo mecanismo do `BinOp` — mas o ponto onde um estudante real
bate primeiro é ~201, não 498, e a mensagem que vê é ainda mais
desligada de "erro de ALGO" do que um `RecursionError`.

### 8. (ronda 2, média) `conversao.paraInteiro`/`paraDecimal` vazam `OverflowError` do Python em inglês

**[CORRIGIDO — Fase 2.2]** Mensagens "cannot convert float infinity to
integer" e "int too large to convert to float" acrescentadas à tabela
de `_algo_traduzir_valueerro`.
`bibliotecas/conversao.py:37-56`. Por design (comentário AL-91/B21), estas
funções apanham `OverflowError` e voltam a levantá-lo como `ValueError`
para caírem na tradução de `_algo_traduzir_valueerro` — mas a mensagem
exata não está na tabela de tradução (`codegen.py:107-122`), por isso cai
no genérico `"valor inválido (...)."`, com o texto do Python à mistura.
Verificado: `conversao.paraInteiro(x)` com `x` = `ler()` de `"inf"` →
`"Erro em tempo de execução: valor inválido (cannot convert float
infinity to integer)."`; `conversao.paraDecimal(x)` com `x` = `10^400`
(inteiro válido, sem overflow nessa parte) → `"...valor inválido (int too
large to convert to float)."`.

### 9. (ronda 2, média) Falso-negativo: usar uma variável logo após um `se`/`senao` que a declara em ambos os ramos dá erro

**[CORRIGIDO — Fase 8.1, ronda 12]** `_verificar_stmt` (caso `A.Se`)
passou a capturar o `Escopo` de cada ramo numa lista; quando há
`senao` e um nome aparece nos `.locais` de TODOS os ramos com a mesma
tupla `(tipo, dims, eh_constante, valor_resolvido)`, é propagado para
o escopo pai depois do `se`. Sem `senao`, ou com ramos que divergem,
continua por declarar (sem propagação, sem erro).

`semantics.py:198` (`escopo_topo`, um dict simples nunca atualizado pelos
`Escopo` filhos criados para cada ramo — ao contrário de `self.globais`,
que `_pre_registar_recursivo` já preenche e que as *funções* conseguem
ver). Verificado:
```algo
algoritmo "T"
inicio
    se verdadeiro entao
        x:inteiro = 10
    senao
        x:inteiro = 20
    escrever(x)
```
Dá `Erro semântico na linha 7: a variável 'x' não foi declarada`, mesmo
`x` estando declarado (com o mesmo tipo) nos dois ramos — código
perfeitamente válido é rejeitado. Assimetria com o facto de uma função
(não o corpo principal) conseguir ver essa mesma variável através de
`self.globais`. É o oposto do bug #2 (lá algo inválido passava; aqui algo
válido é rejeitado), mas mesma zona de código (`_pre_registar_recursivo`/
`escopo_topo`).

### 10. (ronda 3, grave) `linter.py` tem o SEU PRÓPRIO `RecursionError` cru — e este é alcançável de facto, sem passar por `verificar()`

**[CORRIGIDO — Fase 2.1, ver bug #7]** Resolvido pela mesma correção
do bug #7: a AST nunca fica profunda o suficiente para chegar a
`linter.py` (nem a `verificar()`), independentemente de qual dos dois
o programa alcança primeiro. `online/executor.py:analisar_linter`
ganhou também a rede de segurança (`RecursionError` → `ErroCompilacao`
amigável) para o caso, hoje hipotético, de outra travessia recursiva
futura reintroduzir o mesmo problema sem passar pelo parser.
`tools/linter.py:231` (`_extrair_lvalues_e_chamadas`, chamada logo a abrir por
`_verificar_variaveis_nao_usadas`) recursa em `expr.esq`/`expr.dire` sem
guarda, tal como o bug #7 — mas é um sítio independente, com o seu
próprio limiar (~995 termos em vez de ~498). O `cli.py` está protegido
porque `cmd_verifica` chama sempre `verificar()` primeiro (que crasha a
um limiar mais baixo) — mas `online/executor.py:528-540`
(`analisar_linter`) **salta `verificar()` de propósito** ("o linter só
percorre a AST", no próprio docstring), e é isso que o endpoint
`/api/linter` do serviço web chama. Um estudante que submeta uma
expressão suficientemente longa ao linter online (sem nunca compilar)
atinge este `RecursionError` sem nenhuma proteção — o `main.py` do
`online/` apanha-o com o handler genérico e devolve um `500` opaco, não
o erro amigável que o resto do compilador tenta sempre dar. **Nota para
a correção do bug #7**: proteger só `semantics.py` não chega — o guarda
tem de proteger também `linter.py` (e idealmente ficar num sítio comum,
ex. no próprio `ast_nodes.py`, para não ter de ser replicado em cada
consumidor da AST).

Mesmo formato confirmado, mas **não** alcançável na prática (`verificar()`
crasha sempre primeiro, a um limiar mais baixo, em todos os caminhos reais
encontrados): `ast_nodes.py:306-307` (`texto_expr`, usado por `afirmar` e
por `flowchart.py`) e `codegen.py:740` (`_expr()`). Ficam documentados
porque, se o guarda do bug #7 for colocado só em `semantics.py`, estes
dois tornam-se pontos de falha à espera de um caminho que salte
`verificar()` — tal como aconteceu com o linter.

### 11. (ronda 3, média) `linter.py`: variável de ciclo `para` com o nome de uma global não é detetada como acesso direto à global

**[INVESTIGADO — Fase 4 do `PLANO_CORRECOES_AUDITORIA.md` — NÃO é um
bug real, descartado]** A premissa deste item ("a global É mutada
diretamente pelo ciclo") está factualmente errada, confirmado com um
repro direto executado (não só lido): `idx:inteiro` global, `idx = 99`,
chama um procedimento com `para idx de 1 ate 3 fazer escrever(idx)`,
volta a `escrever(idx)` depois -- saída real `1 2 3 99`, não `1 2 3 3`.
O Python gerado para o procedimento **não tem `global idx`** (confirma
o bug #3, na verdade a favor da correção OPOSTA a esta): `_gerar_funcao`
já trata QUALQUER variável de ciclo `para` como local, via
`A.coletar_declaracoes_tipadas`, que inclui incondicionalmente o nome
de qualquer `Para` -- não há exceção para o caso "sem declaração local
explícita" que este item presume. O raciocínio de `semantics.py:697-710`
citado aqui é sobre RESOLUÇÃO DE NOME em COMPILAÇÃO (para decidir se
`para idx` é válido, aceitando o fallback para uma global do mesmo nome
já existente), não sobre COMO O PYTHON GERADO trata o âmbito em
RUNTIME -- são dois mecanismos independentes que o relatório original
confundiu. Reforça isto um teste já existente na suite antes desta
correção, `test_linter_variavel_de_ciclo_global_dentro_de_funcao_nao_e_
assinalada`, que já fixa deliberadamente o comportamento correto
(NÃO avisar "acede diretamente" neste caso) -- o oposto do que este
item pedia. Nenhuma alteração feita a `_verificar_uso_de_globais` por
esta razão; `_verificar_globais_nao_usadas` (bug #3, irmã deste) foi
corrigida à parte, com uma premissa diferente e correta.

### 12. (ronda 3, cosmético) `linter.py` duplica o aviso de índice fora dos limites em atribuições

**[CORRIGIDO — Fase 4]** Não literalmente como o plano descrevia
("remover a verificação implícita via `_expressoes_lidas`") --
`_expressoes_lidas` é partilhada por outros verificadores (variáveis/
globais/parâmetros não usados), que PRECISAM de `s.alvo` incluído
quando indexado/com campo (`v[i] = 5` conta como "v usado"); removê-lo
aí quebraria essas outras verificações. Em vez disso, o `continue`
foi adicionado só dentro de `_verificar_indices_fora_dos_limites`,
saltando especificamente a instância de `s.alvo` vinda de
`_expressoes_lidas` (identidade `is`, não igualdade), já que a
verificação explícita logo a seguir já cobre o caso. Testado a
CONTAGEM de avisos (`len(...) == 1`), não só `any(...)`, como o plano
pedia.
`tools/linter.py:637-645` — `s.alvo` de uma `Atribuicao` é verificado duas
vezes (uma vez implicitamente via `_expressoes_lidas`, outra vez
explicitamente logo a seguir), produzindo o mesmo aviso **duas vezes**
para `v[10] = 1` com `v` de tamanho 5. Os testes existentes só verificam
`any(...)`, nunca a contagem, por isso passou despercebido.

### 13. (grave) `ref` perde uma escrita em silêncio quando dois parâmetros `ref` colidem em runtime — parte já conhecida, parte nova
`semantics.py:1063-1072`/`1159-1174` já documenta que não consegue
verificar estaticamente `v[i]` vs `v[j]` (podem ser o mesmo índice em
runtime). O codegen implementa `ref` copiando os argumentos para dentro
da chamada e escrevendo os resultados de volta numa única atribuição-
tuplo Python: `v[i], v[j] = f(v[i], v[j])`. Quando `i == j` em runtime,
os dois alvos são o mesmo slot — o Python atribui da esquerda para a
direita, por isso o efeito do PRIMEIRO `ref` é silenciosamente
sobrescrito pelo segundo. Verificado: `i=j=1`, procedimento faz `a=a+1;
b=b+100` → resultado observado é só `+100` (perde-se o `+1`). Também
reproduzido com índices 2D (`m[i][j]`/`m[j][i]`, ronda 4).

**Correção à ronda 3: esta metade (colisão `v[i]`/`v[j]`) NÃO é uma
descoberta nova.** Um agente da ronda 4, ao cruzar os achados com a suite
de testes existente, encontrou `test_correcoes_auditoria.py:4743-4770`
(`test_campo_de_estrutura_dentro_de_vetor_por_referencia_duas_vezes_nao_e_detetado`),
que já fixa este comportamento deliberadamente, citando o mesmo trecho de
`semantics.py` e as tags AL-04/AL-81/B9, com um comentário explícito no
próprio teste: *"Limitação CONHECIDA e deliberada... este teste fixa o
comportamento ATUAL... como regressão — não é uma correção, é documentar
o limite conhecido."* Ou seja, esta parte já era um limite documentado e
testado do compilador, não uma descoberta desta auditoria — fica
registado aqui só para dar o quadro completo, não como bug novo.

**A parte que É nova, e continua a ser reportada como tal:** isto não
fica só no caso documentado dos índices.
`_chave_ref_estatica` trata dois nomes de variável *textualmente
diferentes* (`p1.x` vs `p2.x`) como sempre seguros para dois parâmetros
`ref` — nunca considera que possam ser o MESMO objeto em runtime. Mas o
bug #1 (aliasing) já garante que isso acontece (`p2 = p1` faz `p1`/`p2`
apontarem para o mesmo objeto). Verificado:
```algo
p1.x = 1; p2 = p1
incrementarDuasVezes(ref p1.x, ref p2.x)
```
Resultado: só o efeito do segundo `ref` sobrevive — exatamente o mesmo
sintoma do caso `v[i]`/`v[j]`, mas alcançável através de nomes
diferentes, que a verificação estática explicitamente considerava
seguros. **Isto significa que corrigir só o bug #1 (aliasing) não chega
— mesmo depois de corrigido, o `ref` continua vulnerável ao caso `v[i]`/
`v[j]` original**; e enquanto o bug #1 não for corrigido, este é um
segundo sintoma independente do mesmo problema de fundo.

### 14. (ronda 3, grave) `constante` quebra-se com uma atribuição vulgar, via o bug #1

**[CORRIGIDO automaticamente pela Fase 1.1 — ver bug #1]** Consequência
direta do bug #1; deixou de reproduzir assim que a cópia por valor foi
corrigida. Teste de regressão dedicado acrescentado (`test_bug14_...`).
Consequência direta do bug #1, mas vale a pena destacar por mostrar a
gravidade real: `_verificar_nao_constante` (`semantics.py:838-841`) só
olha para o NOME da variável do lado esquerdo — não tem noção de que uma
variável não-`constante` possa, em runtime, ser o MESMO objeto que uma
`constante`. Verificado:
```algo
constante c:Ponto = {x: 1}
p:Ponto
p = c        -- 'p' não é constante, passa a verificação
p.x = 99     -- muda 'p', não 'c' -- semantics.py não vê problema
escrever(c.x, p.x)
```
Resultado: `c.x` passa a `99` — a constante mudou de valor sem que o
programa alguma vez escrevesse em `c` diretamente. Isto é o bug #2
(constante entre ramos) e o bug #1 (aliasing) a combinarem-se: mesmo que
o bug #2 seja corrigido isoladamente, `constante` continua sem proteção
real nenhuma enquanto o bug #1 não for corrigido.

### 15. (ronda 3, média) Erro de sintaxe num ficheiro incluído não diz qual ficheiro

**[CORRIGIDO — Fase 5]** `_resolver_lista_de_inclusoes` envolve a
chamada a `parse_biblioteca` num `try/except (ErroLexico,
ErroSintatico)` que reatribui o erro ao ficheiro incluído
(`inc.caminho`) antes de sair -- mesmo padrão já usado corretamente em
`online/executor.py`.
`cli.py:90-91`, dentro de `_resolver_lista_de_inclusoes` — `parse_biblioteca`
levanta `ErroSintatico`/`ErroLexico` com apenas `linha`/`coluna`, nunca o
caminho do ficheiro, e nada nesta função captura/reatribui o erro ao
ficheiro incluído. Verificado: um `lib.algo` com erro de sintaxe na sua
linha 2, incluído por um `principal.algo` cuja própria linha 2 é o
`incluir "lib.algo"` (perfeitamente válido), produz `"❌ Erro de sintaxe
na linha 2, coluna 1: ..."` — um estudante vai olhar para a linha 2 do
SEU ficheiro e não encontrar nada de errado. Contraste: o caminho de
colisão de nomes já identifica corretamente o ficheiro de origem
(`ColisaoDeInclusao` guarda `caminho_origem`) — só o caminho de erro de
parsing é que não.

### 16. (ronda 3, menor) `--mostrar-python` é ignorado em silêncio quando combinado com `--debug`/`--json`

**[CORRIGIDO — Fase 5]** `cmd_executa_com_trace` agora lê
`args.mostrar_python` e imprime o Python gerado (já em memória, de
`dados["codigo"]`) tal como `cmd_executa` já fazia -- decisão do
maintainer conforme o plano previa: fazer `--debug`/`--json` também
respeitar a flag, em vez de só documentar a incompatibilidade.
Encontrado ao corrigir: 4 testes existentes construíam
`argparse.Namespace(...)` manualmente sem o atributo
`mostrar_python`, agora obrigatório -- atualizados.
`cli.py:186-189` — `cmd_executa` desvia logo para `cmd_executa_com_trace`
quando `--debug`/`--json` está presente, e essa função nunca lê
`args.mostrar_python`. O código Python é gerado e escrito em disco na
mesma, só não é impresso — sem aviso nenhum ao utilizador de que a flag
foi ignorada, apesar de a ajuda da CLI não listar `--mostrar-python` como
incompatível com `--debug`/`--json`.

### 17. (ronda 3, desempenho, não correção) `tracer.py`: custo quadrático em recursão profunda sob `--debug`/`--json`

**[CORRIGIDO — Fase 7.1 do `PLANO_CORRECOES_AUDITORIA.md`]** Pilha
mantida incrementalmente (`pilha_frames`/`pilha_incremental`, ver
`gerar_trace`), empurrada/retirada nos eventos `call`/`return`; a cada
`line`, só a entrada do TOPO (a frame atual) é recalculada -- as
ancestrais mantêm-se congeladas tal como estavam da última vez que
cada uma foi a frame atual (garantido pela execução de thread única
do Python: uma frame ancestral não pode mudar enquanto uma mais funda
está a correr). Cada entrada é sempre SUBSTITUÍDA, nunca mutada, para
não corromper o `list(pilha_incremental)` já guardado num passo
anterior. `construir_pilha` (a função original, O(profundidade) por
chamada) manteve-se só para o único sítio que ainda precisa dela --
o caso especial do retorno final da função principal, que corre uma
única vez, não é o caminho quente.

**Medido, mesmo cenário exato do relatório original**: profundidade
500 → 0.018s (era 0.65s, ~36×), 1000 → 0.030s (era 2.3s, ~77×), 1990
→ 0.091s (era 9.5s, ~104×) -- e a escala já não é quadrática (0.091s
para ~4× a profundidade de 0.018s é ~5×, não os ~16× que O(n²)
preveria). Verificado explicitamente que a correção não introduziu
nenhuma regressão de correção: cada frame ancestral numa recursão de
profundidade 4 mostra o seu PRÓPRIO valor de `n` (4, 3, 2, 1, 0), não
o valor do topo repetido -- exatamente o tipo de bug que uma
implementação incremental incorreta introduziria.
`tools/tracer.py`'s `construir_pilha` percorre a cadeia de frames completa
a CADA linha traçada, tornando o custo total O(profundidade²). Medido
numa função recursiva legítima (corre instantaneamente sem trace):
profundidade 500 → 0.65s, 1000 → 2.3s, 1990 (mesmo abaixo do limite de
4000 passos) → **9.5s**. Não é um bug de correção (`MAX_PASSOS=4000`
continua a proteger contra um crash), mas é uma lentidão real e fácil de
desencadear, em profundidades que o compilador já trata instantaneamente
fora do modo debug.

### 18. (ronda 4, grave, alto impacto real) `escrever` mostra artefactos crus de vírgula flutuante em código trivial

**[CORRIGIDO — Fase 8.5, ronda 12]** `_algo_fmt` arredonda `float` a 12
casas decimais antes de formatar, e normaliza `-0.0` para `0.0`.
`0.1+0.2` → `0.3`; `3.0` continua `3.0`. Notação científica para
magnitudes extremas (`10.0^20` → `1e+20`) fica deliberadamente por
resolver, ver comentário em `codegen.py:_algo_fmt`.

`codegen.py:30-36` (`_algo_fmt`) não trata `decimal` de forma nenhuma —
cai direto em `str(v)` do Python. Verificado:
- `escrever(0.1 + 0.2)` → `"0.30000000000000004"` — o artefacto clássico
  de vírgula flutuante, mostrado cru a um principiante, sem arredondamento
  nenhum.
- `escrever(10.0 ^ 20)` → `"1e+20"` — notação científica do Python, sem
  tradução, apesar de todos os outros pontos de formatação/erro deste
  projeto serem cuidadosamente traduzidos.
- `escrever(0.0 * -1.0)` → `"-0.0"` — zero negativo, atingível por
  aritmética normal (não só por um literal).

**Porque é que isto importa mais do que a maioria dos outros bugs desta
lista:** `escrever` é o comando mais usado por qualquer estudante, em
qualquer programa, e `0.1 + 0.2` é uma das primeiras expressões que
qualquer principiante escreve. Ao contrário de um crash raro ou de um
caso extremo, este bug aparece por defeito, sem esforço nenhum, na
primeira aula sobre números decimais.

### 19. (ronda 4, grave) `ler()` para `decimal` aceita `"nan"`/`"inf"`/`"-inf"`/`"Infinity"` em silêncio

**[CORRIGIDO — Fase 8.4, ronda 12]** Novo helper partilhado
`_algo_texto_para_decimal` (`codegen.py`) rejeita
`nan`/`inf`/`-inf`/`Infinity` e separadores `_`; `_algo_ler_decimal`
passou a usá-lo, voltando a pedir o valor ("Valor inválido...") em vez
de aceitar em silêncio. `conversao.paraDecimal` NÃO recebeu a mesma
correção -- ver bug #40 (ronda 12) para o porquê.

`_algo_ler_decimal` (`codegen.py:51-56`) é só `float(input(...))` dentro
de um `try/except ValueError` — e `float()` do Python aceita estas
palavras (case-insensitive) sem levantar erro nenhum. Verificado: input
`"nan"` → aceite, `escrever(x)` mostra `"nan"`, e `escrever(x == x)`
mostra **`"falso"`** para a mesma variável, sem diagnóstico nenhum. Isto
é o único ponto de entrada para `nan`/`inf` num programa ALGO — toda a
aritmética normal (`0.0/0.0`, `matematica.raiz(-1)`, overflow de `^`) já
está protegida e traduzida (correção anterior AL-68/B28, confirmada a
funcionar) — só `ler()` ficou de fora dessa proteção.

### 20. (ronda 4, grave) Deteção de índices fora dos limites do `linter.py` é completamente cega a arrays 2D+

**[CORRIGIDO — Fase 4]** `_vetores_com_tamanho_literal`/
`_campos_vetor_por_nome` passaram a guardar uma LISTA de tamanhos (um
por dimensão, `None` onde não é estaticamente resolúvel) em vez de um
único inteiro; `_verificar_indices_expr` avança um `nivel` a cada
acesso `indice` consecutivo, comparando cada dimensão contra o seu
próprio tamanho. Testado com os dois casos exatos do repro
(`tabuleiro[8][0]`/`tabuleiro[0][8]`) mais o equivalente para
campo-vetor 2D de `estrutura`.
`tools/linter.py:603-635` (`_vetores_com_tamanho_literal` e
`_campos_vetor_por_nome`, mecanismo AL-98/B26) filtram com
`len(d.dims) == 1` — qualquer variável ou campo de struct com 2+
dimensões nunca é registado, por isso **nenhuma dimensão, nem sequer a
mais externa, é verificada**. Verificado:
```algo
tabuleiro:inteiro[8][8]
escrever(tabuleiro[8][0])   -- fora dos limites na 1ª dimensão
escrever(tabuleiro[0][8])   -- fora dos limites na 2ª dimensão
```
Nenhum dos dois produz aviso (o equivalente 1D produz corretamente).
Mesma lacuna confirmada para campos-array 2D dentro de structs. Grelhas/
matrizes/tabelas de registos são exatamente o que se escreve numa
disciplina introdutória — e é aí que o linter agora garante
silenciosamente "está tudo bem" a um estudante cujo código depois
crasha em runtime com o erro genérico de índice.

### 21. (ronda 4, média, WebSocket) `/ws/executar` do serviço `online/` não apanha `RecursionError` — quebra a garantia "todo o erro vira JSON"
`online/executor.py:286` (`compilar_codigo`) só apanha
`ErroSemantico`/`ErroInternoCompilador`; o `RecursionError` do bug #7
propaga sem ser apanhado. Nas rotas HTTP (`/api/fluxograma`,
`/api/rasto`) isto ainda é contido pelo handler global do FastAPI
(devolve um JSON `500` genérico, mesma gravidade do bug #10). Mas
`compilar_codigo` só é chamado a partir de `/ws/executar` — uma rota
**WebSocket**, não HTTP — e o handler global do `main.py`
(`@app.exception_handler(Exception)`, cujo comentário promete "qualquer
erro não tratado devolve sempre JSON") **nunca é invocado para
WebSockets** (confirmado com uma app FastAPI isolada, reproduzindo a
mesma versão do Starlette usada no projeto). Na prática: um estudante
que submeta, na funcionalidade principal de "executar" (não só no
linter), um programa com uma cadeia de operadores suficientemente longa
(bug #7) tem a ligação fechada abruptamente pelo servidor ASGI, sem
mensagem de erro nenhuma — pior do ponto de vista do estudante do que o
JSON genérico das rotas HTTP, e falsifica a garantia que o próprio
código documenta. Não expõe traceback nenhum (o socket é só fechado),
por isso não é uma fuga de informação — mas é uma falha nova e
independente das já descritas.

**Achado positivo relacionado, não é bug:** ao contrário de `cli.py`
(bug #15), a reimplementação própria do `online/executor.py` para
resolução de `incluir` (`executor.py:190-192`) já identifica
corretamente o ficheiro incluído num erro de sintaxe (`"Erro em
'lib.algo': ..."`) — uma melhoria incidental da reimplementação, não
partilha o bug #15.

### 22. (ronda 5, fora do compilador, em `alguem/`) Resolução de `incluir` por regex do tutor não ignora comentários — pode expor ficheiros irrelevantes ao LLM
`alguem/nucleo/ficheiros_visiveis.py:16,72` (`PADRAO_INCLUIR`) percorre o
texto cru do ficheiro sem remover comentários `/* ... */` primeiro — ao
contrário do lexer real (`lexer.py:63`,
`_remover_comentarios_bloco`, que corre antes de tokenizar). Verificado:
um `incluir "decoy.algo"` escrito dentro de um comentário `/* ... */`
(ex.: uma nota ao estudante tipo "não uses `incluir \"decoy.algo\"` aqui,
isto é só um exemplo") é corretamente ignorado pelo compilador real
(`inclusoes == []`), mas `resolver_ficheiros_visiveis` resolve-o na
mesma e entrega o conteúdo completo de `decoy.algo` ao tutor. Numa pasta
com um ficheiro de rascunho ou uma solução alternativa comentada cujo
nome apareça por acaso dentro de um comentário, o tutor passa a ver
código que o compilador nunca vê e que não faz parte do programa real do
estudante — pode enviesar as dicas dadas. **Nota de âmbito**: isto está
em `alguem/`, não em `algo_lang/` (o compilador) — fica registado porque
o utilizador pediu para ir "mais a fundo" e este é o género de
divergência-por-reimplementação que já apareceu noutros sítios (bug #15
vs. a reimplementação correta em `online/executor.py`), mas é uma
correção fora do âmbito original desta auditoria ao compilador.

**Checado e sem divergência**: ciclos de inclusão mútua (`main→b1→b2→b1`)
— compilador real e regex do tutor concordam exatamente no conjunto de
ficheiros; sensibilidade a maiúsculas — ambos exigem `incluir` em
minúsculas; disfarce dentro de um literal `cadeia` — impossível, porque
literais `cadeia` não podem atravessar linhas (`ErroLexico` correto) e
`incluir` é palavra reservada, por isso nenhuma linha que o lexer real
aceite pode conter texto `incluir "..."` que não seja um `incluir`
genuíno.

**`conhecimento_algo.py`** (a "base de conhecimento" que o tutor usa):
todas as afirmações concretas testadas (indexação de vetores desde 0,
`para i de.. ate..` exigir `i` pré-declarado, `fazer...enquanto` correr
pelo menos uma vez, `div`/`mod`/`<>`, a regra de indentação) batem certo
com o comportamento real. Não faz nenhuma afirmação sobre a proteção de
`constante` ou sobre a segurança de aliasing em `ref` (as áreas onde
rondas anteriores encontraram bugs reais) — por isso não ensina nada de
factualmente errado nesses pontos, só não os menciona.

### 23. (ronda 6, grave) Nome de global igual a um módulo/builtin que o próprio codegen usa (`sys`, `copy`, `print`) parte o compilador de formas diferentes — uma delas mente ao estudante

**[CORRIGIDO — Fase 2.3 do `PLANO_CORRECOES_AUDITORIA.md`]**
`NOMES_RESERVADOS_CODEGEN = {"sys", "copy", "print", "input"}`
(`semantics.py`), verificado nos mesmos 3 sítios que já protegem
`nomes_internos_bibliotecas` (funções, estruturas, e
`_verificar_nome_disponivel` -- variáveis/parâmetros, cobrindo
também parâmetros, não só globais). Testado com `pytest.mark.
parametrize` para os 4 nomes.
`semantics.py:20-34` (`verificar_nomes_python`) só bloqueia palavras-chave
do Python (`keyword.iskeyword`) — não bloqueia nomes de builtins/módulos
que o próprio código gerado usa sem qualificação (`sys`, `copy`, `print`,
provavelmente `input` também). Como o codegen faz `global <nome>` para
toda a declaração de topo, uma global do estudante com um destes nomes
rebate o `import sys`/`import copy` do preâmbulo ou o `print`/`input`
embutido. Três variantes verificadas, cada uma pior que a anterior:
- `sys:inteiro = 5` + um erro de índice → o próprio `sys.exit(1)` do
  handler de erro falha com `AttributeError: 'int' object has no
  attribute 'exit'`, traceback cru.
- `print:inteiro = 5` + `escrever(print)` → `TypeError: 'int' object is
  not callable`, traceback cru (nem sequer está na lista de exceções
  traduzidas).
- **`copy:inteiro = 5` + passar uma struct por valor a uma função** → o
  `copy.deepcopy(...)` interno falha com `AttributeError`, que o
  handler genérico de `AttributeError` (desenhado para "acesso a campo
  de nulo") interpreta mal e imprime **`"Erro em tempo de execução:
  tentaste aceder a um campo de um valor nulo."`** — nada é nulo, a
  função nem chegou a ser chamada. Esta é a pior variante de toda a
  auditoria: não crasha, mente de forma plausível.

Trivialmente alcançável — `sys`, `copy` e `print` são nomes de variável
perfeitamente normais que um estudante escolheria sem pensar duas vezes.

### 24. (ronda 6, média) `escolher` só com `contrario` (sem nenhum `caso`) compila sem erro mas gera Python inválido

**[CORRIGIDO — Fase 8.2, ronda 12]** `_gerar_escolha`
(`gerador_base.py`) passou a emitir o corpo do `contrario`
diretamente, sem `if`/`else` nenhum, quando `stmt.casos` está vazio
(não há nada a que um `else:` se possa juntar). `linter.py` (bug #37,
ronda 12) também passou a avisar deste padrão estaticamente.

`parser.py:532-543` não exige pelo menos um `caso` antes de um
`contrario` opcional; `semantics.py:744-781` também não valida
`len(s.casos) >= 1`. `gerador_base.py:207-220` (`_gerar_escolha`) só
emite `if`/`elif` dentro do ciclo `for valores, corpo in stmt.casos` —
se essa lista estiver vazia, o `else:` do `contrario` fica sem nenhum
`if` antes, à mesma indentação. Verificado:
```algo
escolher x
    contrario
        escrever("sempre")
```
Compila sem erro nenhum (`compilar()` sai limpo); o Python gerado tem um
`else:` solto, e ao EXECUTAR dá `SyntaxError: invalid syntax` — sucesso
silencioso na compilação, crash misterioso ao correr, exatamente o
padrão que esta auditoria tem andado a caçar.

### 25. (ronda 6, média) Caracteres unicode fora do codepage do ambiente crasham com mensagem enganadora — relevante em produção

**[CORRIGIDO — Fase 2.4 do `PLANO_CORRECOES_AUDITORIA.md`]**
`sys.stdout.reconfigure(encoding="utf-8")` acrescentado ao
`CABECALHO_RUNTIME`, atrás de um `hasattr` (sob `tools/tracer.py`
`--debug`/`--json`, `sys.stdout` é redirecionado para um
`io.StringIO()` em memória, sem `.reconfigure()`). **Efeito colateral
descoberto ao corrigir**: `algo_lang/tests/apoio.py`'s `executar()` (e
mais 3 sítios em `test_novas_funcionalidades.py`/
`test_correcoes_auditoria.py`) capturavam o stdout do subprocesso com
`text=True` sem `encoding="utf-8"` explícito -- antes, isto "funcionava"
por coincidência (pai e filho usavam ambos a codificação por omissão
do sistema, cp1252 neste ambiente Windows); com o filho agora sempre
UTF-8, o pai tinha de decodificar como UTF-8 também, ou "café"
aparecia como "caf�" nos testes que comparam texto acentuado. Corrigido
nos 4 sítios; **bónus**: isto também resolveu, sem ser esse o alvo, uma
falha pré-existente da suite (`test_afirmar_falso_termina_o_programa`)
que já estava a ser mascarada pelo mesmo mecanismo. Ficaram por tratar
(fora do âmbito desta correção, sem risco de regressão porque já
falham por `FileNotFoundError` neste sandbox -- `algo` não está no
PATH) ~30 outros `subprocess.run(text=True)` sem `encoding=` explícito
nos testes que invocam o `algo` CLI a sério (`test_algo_sh.py`,
`test_consola.py`, `test_fluxogramas.py`, `test_linter.py`,
`test_tracer.py`, e alguns em `test_correcoes_auditoria.py`) -- vale a
pena uma limpeza dedicada nesses ficheiros num ambiente onde `algo`
resolve.
`codegen.py`'s `CABECALHO_RUNTIME` nunca força UTF-8 no stdout do
programa gerado. `escrever("café ☕")` está corretamente escapado como
literal Python (a parte de escaping de strings, incluindo barra
invertida/aspas/`\n`/chaves/`%`, foi verificada limpa nesta ronda) — mas
ao **executar**, se o stdout do subprocesso resolver para uma codepage
que não tenha `☕` (ex.: `cp1252` no Windows), obtém-se
`UnicodeEncodeError`, que é subclasse de `ValueError` e por isso cai no
`except ValueError` do próprio programa gerado, sendo relabelled como
`"Erro em tempo de execução: valor inválido ('charmap' codec can't
encode character...)."` — uma mensagem sem relação nenhuma com o
problema real (o código do estudante estava perfeitamente correto).
**Relevante para produção, não só para esta sandbox**: `online/
executor.py:_env_minimo` limpa deliberadamente quase todas as variáveis
de ambiente do subprocesso do estudante (incluindo `LANG`/`LC_ALL`/
`PYTHONIOENCODING`), por isso a codificação em produção fica ao critério
do que a imagem base resolver por omissão, não uma garantia explícita —
para uma linguagem que assume acentos portugueses (e que este teste
também usou emoji) isto devia ser forçado (`sys.stdout.reconfigure
(encoding="utf-8")` no preâmbulo gerado), não deixado ao ambiente.

### 26. (ronda 6, grave) Referência antecipada a uma global escondida dentro do corpo de uma função escapa à deteção — `NameError` cru, sem tradução nenhuma

**[CORRIGIDO — Fase 2.5 do `PLANO_CORRECOES_AUDITORIA.md`]** As duas
correções, como o plano recomendava. (1) `_globais_lidas_
transitivamente` (`semantics.py`) percorre o corpo da função chamada
(e, transitivamente, de qualquer outra função do próprio ficheiro que
ela chame, com proteção contra recursão mútua) recolhendo que globais
lê; `_registar_decl` rejeita se alguma ainda não estiver no escopo
construído até esse ponto. Cobre o repro exato do bug (chamada como
valor inicial de uma DECLARAÇÃO) e testado com transitividade,
sombreamento por parâmetro, recursão mútua e chamadas de biblioteca
(não devem disparar). (2) `except NameError` acrescentado à cadeia
traduzida em `codegen.py`, como rede de segurança para os casos que a
verificação estática não cobre por desenho (ex.: a mesma referência
antecipada através de uma ATRIBUIÇÃO normal, não uma declaração) --
testado que continua amigável em runtime nesse caso.
`semantics.py:387-398` já rejeita corretamente uma referência direta a
uma global ainda não declarada (`a:inteiro = b + 1` antes de `b`
existir). Mas `_registar_decl` só valida os ARGUMENTOS de uma chamada
contra o `escopo_topo` construído até esse ponto — não valida o que o
CORPO da função chamada lê. `_verificar_funcao` verifica esse corpo
contra `self.globais` (o conjunto COMPLETO, independente da ordem de
declaração), por isso passa despercebido. Verificado:
```algo
funcao pegaB():inteiro
    devolver b
a:inteiro = pegaB()
b:inteiro = 10
```
Compila sem erro. O codegen emite as globais pela ordem do código-fonte
(`a = pegaB()` antes de `b = 10`), por isso ao executar:
`NameError: name 'b' is not defined` — e `NameError` **não está** na
lista de exceções traduzidas do rodapé do programa gerado (`IndexError`,
`ZeroDivisionError`, `OverflowError`, `RecursionError`,
`AttributeError`, `ValueError`, `_AlgoIndiceCadeiaInvalido` — sem
`NameError`), por isso o estudante recebe um traceback Python cru e
completo, quebrando totalmente a promessa de erros sempre amigáveis.

### 27. (ronda 7, grave) Global chamada `_math`/`_random` quebra `matematica.*` — mesma classe do bug #23, agora numa biblioteca

**[CORRIGIDO — Fase 2.3, ver bug #23]** `_nomes_importados_no_cabecalho`
(`semantics.py`) extrai os aliases `import X as Y` de cada
`CABECALHO` de biblioteca AUTOMATICAMENTE (regex, não uma lista fixa
por biblioteca) -- só se aplica quando essa biblioteca está mesmo
importada no programa (testado: `_math`/`_random` continuam
permitidos como nome de variável se `Matematica` nunca for
importada).
`bibliotecas/matematica.py:5` injeta `import math as _math\nimport random
as _random\n` no preâmbulo. A guarda `nomes_internos_bibliotecas`
(`semantics.py:87-91`) só protege nomes no formato
`"{biblioteca}_{metodo}"` (ex.: `matematica_raiz`) — nunca os aliases do
próprio `CABECALHO`. Verificado:
```algo
importar Matematica
_math:inteiro = 5
inicio
    escrever(matematica.raiz(4.0))
```
Compila sem erro. A global `_math = 5` rebate o `_math` do módulo
Python; `matematica.raiz` (que resolve `_math` como global só na hora da
chamada) falha com `AttributeError: 'int' object has no attribute
'sqrt'`, apanhado pelo handler de `AttributeError` (desenhado para
"acesso a campo de nulo") → **mesma mentira do bug #23**: `"Erro em
tempo de execução: tentaste aceder a um campo de um valor nulo."`, sem
relação nenhuma com o problema real. Mesmo resultado com `_random`
partindo `matematica.aleatorio`. Só afeta globais (uma variável local
com o mesmo nome não quebra nada, por ficar apenas na função). A guarda
tem de passar a cobrir também os aliases importados pelo `CABECALHO` de
cada biblioteca, não só os nomes `{biblioteca}_{metodo}`.

**Relacionado, não é bug hoje mas é frágil**: `cadeia.py`/`conversao.py`
têm `CABECALHO = ""`, por isso não há colisão entre bibliotecas
diferentes ainda — mas isso é por acidente (nenhuma outra biblioteca
precisa de header ainda), não por desenho; o dia em que uma segunda
biblioteca precisar de `_math` ou parecido, colide sem aviso nenhum.
Importar a mesma biblioteca duas vezes duplica o `CABECALHO`/funções no
Python gerado, mas é inofensivo (Python tolera reimportar/redefinir).
`matematica:inteiro = 5` já está corretamente bloqueado.

### 28. (ronda 7, grave) BOM UTF-8 no ficheiro fonte crasha na coluna 1, linha 1, com um caractere que o estudante não consegue ver

**[CORRIGIDO — Fase 2.4, ver bug #25]** `encoding="utf-8-sig"` em
`_ler_ficheiro_algo` (`cli.py`), exatamente como sugerido -- mudança
de uma linha, no-op quando não há BOM (testado). A nota relacionada
sobre `--mostrar-python` vs `--json` mostrarem acentos de forma
diferente resolveu-se sozinha com a correção do bug #25: ambos os
caminhos correm o MESMO ficheiro gerado, que agora força UTF-8 no seu
próprio stdout independentemente de como é invocado.
`cli.py:48` (`_ler_ficheiro_algo`) abre o ficheiro com
`encoding="utf-8"`, que NÃO remove um BOM (`EF BB BF`) inicial —
seria preciso `encoding="utf-8-sig"` para isso. Um BOM inicial é
exatamente o que vários editores Windows (incluindo o Bloco de Notas, ao
"Guardar como UTF-8") escrevem por omissão. Verificado: um programa
perfeitamente válido, só com BOM à frente, dá `❌ Erro léxico na linha
1, coluna 1: caractere inesperado '﻿'` — um caractere invisível em
praticamente qualquer editor de texto, por isso o estudante não tem
forma de perceber o que está errado só pela mensagem. Correção direta:
trocar `"utf-8"` por `"utf-8-sig"` em `_ler_ficheiro_algo` (é um no-op
seguro quando não há BOM).

**Checado e correto**: ficheiro fonte gravado em `cp1252`/`latin-1` (em
vez de UTF-8) já dá um erro amigável e claro (`UnicodeDecodeError`
apanhado, correção anterior AL-34, confirmada), não um traceback nem
mojibake silencioso; o mesmo para UTF-16. Os ficheiros que o compilador
ESCREVE (`.py` de `--mostrar-python`/`compila`, `.json` de `--json`,
`.dot` de `fluxograma`) usam sempre `encoding="utf-8"` explícito e
preservam acentos corretamente.

**Nota relacionada com o bug #25**: `executa --mostrar-python` (sem
`--json`) e `executa --json` capturam o stdout do subprocesso de forma
diferente — o primeiro mostrou `Jos�` para o mesmo `"José"` que o
segundo mostrou correto. Mesma família do bug #25 (falta de
`encoding="utf-8"` explícito nalgum ponto da captura), não investigado
a fundo por ser simétrico ao que already está documentado. Também vale
a pena notar: o próprio `❌` que `afirmar` imprime ao falhar é gerado
pelo COMPILADOR, não escrito pelo estudante — por isso até um programa
sem nenhum acento pode sofrer do bug #25 assim que um `afirmar` falhar,
num ambiente cuja codepage não tenha esse símbolo.

### 29. (ronda 8, grave) `constante` usada como tamanho de array não é tratada como um literal em TRÊS sítios diferentes — mesma causa raiz, três sintomas

**[CORRIGIDO — Fase 3.1 do `PLANO_CORRECOES_AUDITORIA.md`]**
`_resolver_constante` (`semantics.py`) dobra um `A.LValue` para uma
`constante` inteira já registada ao seu valor, recursivamente através
de `+`/`-`/`*` (cobre `M = N + 1`); o valor resolvido fica guardado na
própria entrada do escopo (agora um 4-tuplo, não 3), calculado tanto
em `_registar_decl` como em `_pre_registar_recursivo` (para uma
`constante` declarada dentro de `inicio`, não só antes, também ficar
resolúvel a partir de dentro de uma função). Os três sítios trocaram
`isinstance(x, A.Literal)` por também tentar `_resolver_constante`.
Em `tools/linter.py`, cópia independente e mais simples
(`_valores_constantes`, achatada por NOME em vez de com escopo real,
mesma filosofia de "ambíguo = excluir" que `_campos_vetor_por_nome`
já usava) -- não dá para reutilizar a versão de `semantics.py`
diretamente (precisa de `Escopo`/`self.funcoes`, que não existem no
mundo do linter, que corre sobre AST possivelmente ainda não
semanticamente válida). **Bug relacionado, encontrado ao corrigir**:
o "efeito colateral" do linter não contar `N` como usado quando só
servia de tamanho vinha na verdade de `_expressoes_lidas` (não de
`_vetores_com_tamanho_literal`) -- nunca incluía `s.dims` de uma
`A.Declaracao` na lista de expressões lidas, para NENHUM tamanho
(literal ou `constante`); corrigido também. 16 testes de regressão
(10 em `semantics.py`/`linter.py` diretamente, mais os já existentes
confirmados sem regressão).
`semantics.py:469-478` (`_valor_literal_negativo`), `semantics.py:518-
526` (`_tamanho_estatico`) e `linter.py:603-635`
(`_vetores_com_tamanho_literal`/`_campos_vetor_por_nome`) só reconhecem
`isinstance(x, A.Literal)` — uma `constante N:inteiro = 5` usada como
`v:inteiro[N]` é internamente uma referência a variável (`A.LValue`),
não um literal, apesar de ser tão previsível em compilação como o
literal `5`. Três sintomas confirmados, todos com a mesma causa raiz:
- **Linter nunca verifica limites** de um array com tamanho `constante`:
  `constante N:inteiro = 3; v:inteiro[N]; v[10] = 1` — zero avisos (o
  equivalente com `v:inteiro[3]` avisa corretamente). Mesma lacuna para
  tamanhos de campos-array em structs. Efeito colateral: o linter
  também não conta o uso de `N` como tamanho do array como "uso", por
  isso ainda por cima avisa (erradamente) que `N` "é declarada mas nunca
  é usada".
- **Tamanho negativo via `constante` não é rejeitado em compilação**:
  `constante N:inteiro = -3; v:inteiro[N]` compila sem erro (o
  equivalente literal `v:inteiro[-3]` já dá erro de compilação); só
  falha ao EXECUTAR, com uma mensagem amigável mas tardia — o estudante
  só descobre o problema se e quando correr o programa, não ao compilar.
- **Tamanho do literal `{...}` incompatível com uma declaração de
  tamanho `constante` não é apanhado em compilação**: `constante
  N:inteiro = 3; v:inteiro[N] = {1,2}` compila sem erro (o equivalente
  literal `v:inteiro[3] = {1,2}` já dá erro de compilação); só se nota
  ao aceder ao elemento em falta, em runtime, com um erro de índice
  amigável mas igualmente tardio.

Nenhum destes três é um crash cru — o runtime já protege todos os casos
com mensagens amigáveis — mas em todos os três a qualidade do
diagnóstico piora claramente por a `constante` não ser resolvida ao seu
valor antes destas verificações "só literal", ao contrário do resto da
compilação (dobragem de constantes multi-nível, ex. `N = A + B` com `A`/
`B` também `constante`, funciona bem para gerar código correto — só
estas verificações específicas de tamanho/limites ficam cegas a
`constante`).

### 30. (ronda 8, grave) Caminho de saída demasiado longo no Windows crasha com um `OSError` cru

**[CORRIGIDO — Fase 5]** `os.makedirs` em `_pasta_saida` envolvido num
`try/except OSError`, mensagem amigável sugerindo mover o ficheiro
para um caminho mais curto. Testado com `unittest.mock.patch` em vez
de um caminho real de ~260 caracteres (frágil entre ambientes, como o
próprio plano já antecipava).
`cli.py:38`, dentro de `_pasta_saida()` (chamada por `compilar_ficheiro`,
`cmd_executa_com_trace` e `cmd_fluxograma` — os três pontos de entrada
que compilam para disco). `os.makedirs(pasta, exist_ok=True)` não tem
nenhum `try/except` à volta, e nesta máquina Windows (sem suporte a
caminhos longos ativado) um caminho de saída a rondar os ~260 caracteres
dá `FileNotFoundError: [WinError 206] The filename or extension is too
long`, propagado cru até ao topo — nenhuma das mensagens amigáveis deste
ficheiro (ex.: a verificação AL-33 mesmo antes, para quando o caminho de
saída já existe como ficheiro) apanha este caso. É facilmente alcançável
por um estudante com uma estrutura de pastas de curso aninhada, ou com o
Ambiente de Trabalho sincronizado por OneDrive (`C:\Users\<nome>\OneDrive
- <Instituição>\...`), um cenário comum, não extremo.

### 31. (ronda 9, muito grave) Índices negativos em arrays NUNCA são guardados — leitura, escrita, 2D, `ref`, structs, literal ou computado. Wraparound do Python vaza silenciosamente para o elemento errado

**[CORRIGIDO — Fase 1.2 do `PLANO_CORRECOES_AUDITORIA.md`]** Novo
helper de runtime `_algo_indice` (`codegen.py`) chamado a partir do
único sítio que constrói texto de acesso indexado
(`gerador_base.py:_lvalue`), para leitura E escrita, em cada nível de
indexação (1D/2D+). Reaproveita o `except IndexError` já existente
para a mensagem amigável. 7 testes de regressão acrescentados.
`gerador_base.py:231-238` (`_lvalue`) é o ÚNICO sítio que gera código
para acesso indexado — partilhado entre leitura e escrita — e emite
`base[expr]` em Python cru, sem guarda nenhuma:
```python
def _lvalue(self, lv: A.LValue, tipos):
    base = lv.nome
    for tag, valor in lv.acessos:
        if tag == "indice":
            base += f"[{self._expr(valor, tipos)}]"   # sem guarda
        else:
            base += f".{valor}"
    return base
```
Como o Python faz *wraparound* nativo para índices negativos dentro do
intervalo (`lista[-1]` dá o último elemento em vez de erro), **nunca há
`IndexError` nenhum para apanhar** — o handler de runtime já existente
nunca chega a disparar, porque o Python não vê nada de errado. Dez
combinações verificadas, TODAS silenciosamente erradas (leem/escrevem no
elemento errado em vez de dar erro):
1. Leitura 1D literal: `v[-1]` → devolve o último elemento.
2. Escrita 1D literal: `v[-1] = 99` → escreve no último elemento.
3-6. Leitura/escrita 2D em qualquer das duas dimensões: `m[-1][0]`,
   `m[0][-1]` (e as versões de escrita) → todas fazem wraparound.
7. Parâmetro `ref` a um array: `v[-1] = 99` dentro do procedimento
   propaga-se corretamente para o último elemento do array do chamador
   (o mecanismo de `ref` funciona; é a falta de guarda no índice que é o
   problema).
8-9. Índice negativo COMPUTADO (não literal), leitura e escrita —
   **sem a assimetria literal-vs-computado que aparece noutros bugs
   desta auditoria**: os dois são igualmente desprotegidos, porque ambos
   passam pela mesma `_expr()`.
10. Elemento de array-de-structs com índice negativo (`pessoas[-1].nome`)
    → devolve o último elemento em vez de dar erro.

**Isto é precisamente o perigo que a correção AL-64/B24 já identificou e
corrigiu para `cadeia.caracter`** — o próprio comentário dessa correção
descreve exatamente este mecanismo de wraparound do Python — mas nunca
foi replicado para a indexação de arrays em geral. É um "silêncio
enganador": ao contrário da maioria dos bugs desta auditoria (que
crasham ou vazam uma mensagem em inglês), este dá um resultado
*plausível e sem aviso nenhum*, lendo/escrevendo o elemento errado.

**Verificado como correto**: o linter (`_verificar_indices_expr`,
`linter.py:663`) já verifica o limite inferior corretamente para 1D com
tamanho literal (`not (0 <= indice < tamanho)`) — avisa de `v[-1]`
(duplicado, bug #12 já conhecido). A cegueira a 2D (bug #20) aplica-se
também aqui, mas não é um bug novo, é o mesmo alcance já mapeado.

### 32. (ronda 9, grave) Tamanho de array enorme fica pendurado indefinidamente, sem feedback nenhum — pior do que um crash

**[CORRIGIDO — Fase 6.1 do `PLANO_CORRECOES_AUDITORIA.md`]** Limite de
10 milhões por dimensão (decisão do maintainer, dentro do intervalo
que o plano sugeria) acrescentado a `_algo_verificar_tamanho_vetor`
(`codegen.py`) -- o único sítio por onde QUALQUER dimensão de vetor
passa antes de `range()`, literal ou calculada, cobrindo os dois
casos sem precisar de tocar em `semantics.py`. **Limitação conhecida,
fora do âmbito desta correção**: o limite é POR DIMENSÃO, não sobre o
PRODUTO entre dimensões -- um vetor `v:inteiro[9999999][9999999]`
(cada dimensão individualmente sob o limite) continua sem guarda
agregada, podia gerar ~1e14 células. Bounding o produto exigiria um
mecanismo novo (rastrear todas as dimensões de UM vetor em conjunto),
não só estender o guarda já existente por-chamada -- deixado como
está, consistente com o âmbito que o próprio plano descreveu
(estender `_algo_verificar_tamanho_vetor`, não redesenhar a
construção de vetores multidimensionais).
`codegen.py:565-589` (`_construir_vetor_aninhado`) constrói o array por
uma list-comprehension Python normal (custo O(N) em tempo de
interpretador, não uma alocação em bloco) e não tem limite superior
nenhum, nem em compilação (`semantics.py:438-467`, `_validar_dims`, só
rejeita negativos) nem em runtime (`_algo_verificar_tamanho_vetor`,
idem). Medido: `v:inteiro[10000000]` ~0.85s; `v:inteiro[100000000]`
~13.3s; `v:inteiro[10**12]` — **ainda a correr sem output nenhum e sem
erro nenhum** ao fim de 15s, extrapolação sugere horas. Sem diferença
entre tamanho literal e tamanho vindo de uma variável (aqui, ao
contrário de outros bugs desta auditoria, os dois estão igualmente
desprotegidos). Um estudante que escreva um zero a mais no tamanho de um
array não recebe nenhuma mensagem amigável nem um `MemoryError` cru — o
processo fica simplesmente pendurado, sem diagnóstico nenhum. Nota para
`online/`: os limites de CPU/memória do subprocesso (`resource.setrlimit`
em `executor.py`) acabam por matar o processo, mas o estudante só vê um
timeout/kill sem explicação, já que a camada de tradução de erros do
ALGO nunca chega a correr.

### 33. (ronda 9, média) `escrever` de um `inteiro` gigante (mas legítimo) crasha com uma mensagem que cita internals do Python

**[CORRIGIDO — Fase 2.2]** Mensagem "Exceeds the limit"/"integer
string conversion" acrescentada à tabela de `_algo_traduzir_valueerro`.
`2 ^ 100000` (30103 dígitos) é um `inteiro` perfeitamente legítimo nesta
linguagem (que assume precisão arbitrária), mas `escrever(x)` dá:
```
Erro em tempo de execução: valor inválido (Exceeds the limit (4300 digits)
for integer string conversion; use sys.set_int_max_str_digits() to
increase the limit). (linha 5)
```
Causa: a proteção do próprio Python 3.11+ contra DoS na conversão
inteiro→texto (limite de 4300 dígitos por omissão) dispara dentro de
`_algo_escrever`. É apanhado como `ValueError` genérico (não crasha cru),
mas não está na tabela de tradução de `_algo_traduzir_valueerro`, por
isso a mensagem cita `sys.set_int_max_str_digits()` — algo que não
significa nada para um estudante português e não explica o problema real
(o número é demasiado comprido para imprimir, não é "um valor
inválido"). Confirma que "precisão arbitrária, sem overflow" não é bem
verdade — o CÁLCULO não tem limite, mas ESCREVER o resultado tem, por
volta de 2^14284, silenciosamente.

### 34. (ronda 10, muito grave — alcance ampliado na ronda 11) Índice com efeito secundário passado por `ref` é avaliado DUAS VEZES — leitura e escrita podem acabar em posições diferentes do array

**[CORRIGIDO — Fase 1.2 do `PLANO_CORRECOES_AUDITORIA.md`]** Novo
helper `_hoistear_indices_ref` (`codegen.py`) eleva cada índice de um
argumento `ref` para uma variável temporária avaliada uma única vez,
antes da chamada; leitura (`args_str`) e escrita (`out_vars`) passam a
usar o mesmo nó da AST já hasteado. Eleva sempre (não só quando há
efeito lateral óbvio), aplicado nos três caminhos que geram
escrita-de-volta de `ref` (`_gerar_chamada_stmt`, `_gerar_atribuicao`,
`_gerar_declaracao`). 5 testes de regressão acrescentados (1D, 2D,
campo-após-índice, dois `ref` independentes na mesma chamada, e um
caso sem efeito lateral para confirmar que continua a funcionar). A
colisão `v[i]`/`v[j]` por índice runtime igual continua deliberadamente
não corrigida (limitação conhecida, ver bug #13).
`codegen.py:672-687` (`_gerar_chamada_stmt`) e os caminhos análogos em
`_gerar_atribuicao`/`_gerar_declaracao` (`codegen.py:498-547`) e
`gerador_base.py:130-142` calculam `out_vars` (o alvo da escrita de
volta) e `args_str` (o argumento da chamada) **independentemente**, cada
um reemitindo o texto Python da MESMA expressão ALGO original — nada
partilha ou armazena o valor de uma avaliação para a outra. Para um
argumento `ref` cujo índice tem um efeito secundário (ex.: uma função
que avança um contador), isto gera `v[f()] = chamada(v[f()])` — o Python
chama `f()` duas vezes, uma para ler, outra (já com o contador
avançado) para decidir onde escrever. Verificado:
```algo
idx:inteiro
funcao proximoIndice():inteiro
    idx = idx + 1
    devolver idx - 1
procedimento incrementa(ref x:inteiro)
    x = x + 100
inicio
    idx = 0
    v:inteiro[5] = {0,0,0,0,0}
    incrementa(v[proximoIndice()])
    escrever(v[0]," ",v[1]," ",v[2]," ",v[3]," ",v[4])
```
Saída real: `0 100 0 0 0` — o `+100` foi parar a `v[1]`, não a `v[0]`
(que foi o elemento realmente lido). Confirmado também com dois
argumentos `ref` independentes numa troca (`trocar(v[proxA()],
w[proxB()])`): os valores acabam em posições que ninguém pretendia
tocar. **Confirmado com contagem exata de chamadas** (a função do índice
também imprime "chamado N"): duas chamadas para uma única instrução.
Controlo: um índice sem efeito secundário (`v[contador]`, variável
simples) funciona corretamente — o bug é especificamente sobre
expressões de índice com efeito secundário, não indexação em geral.
Silencioso, sem erro nenhum, resultado plausível — exatamente o tipo de
bug mais difícil de depurar desta auditoria.

**Alcance ampliado (ronda 11)**: mapeado exaustivamente, na mesma linha
do que a ronda 2 fez ao bug #1. Confirmado buggy em mais seis formas,
para além do índice de array simples já documentado:
- Campo de array-de-structs com índice de efeito secundário
  (`pessoas[proximaIndice()].idade`).
- Array 2D, efeito secundário em qualquer das duas dimensões
  isoladamente (`m[f()][0]`, `m[0][f()]`).
- Array 2D com efeito secundário em AMBAS as dimensões na mesma
  expressão (`m[proxA()][proxB()]`) — a variante mais confusa: cada
  função é chamada duas vezes, a escrita acaba numa célula
  "diagonalmente" diferente da que foi lida.
- A MESMA expressão de índice com efeito secundário usada para DOIS
  parâmetros `ref` na mesma chamada (`somaAmbos(v[f()], v[f()])`) — até
  4 chamadas à função de efeito secundário para uma única instrução;
  nenhum dos elementos realmente lidos chega a ser escrito, dois
  elementos completamente diferentes são alterados em vez disso.
- Confirmado que o mesmo mecanismo existe nos TRÊS caminhos de código
  que geram `ref` — chamada solta (`_gerar_chamada_stmt`), atribuição
  (`_gerar_atribuicao`) e declaração com inicializador
  (`_gerar_declaracao`) — não é exclusivo de um só.

**Confirmado como seguro** (não é o bug): um argumento passado por VALOR
(sem `ref`) com um índice de efeito secundário é avaliado exatamente uma
vez — o problema é específico ao mecanismo de escrita de volta do `ref`,
não à indexação com efeitos secundários em geral. Uma base de expressão
(não uma variável simples) com efeito secundário como alvo `ref`
(`f().campo = ...`) não é sequer sintaxe válida — a gramática exige que
todo o lvalue comece por um `ID` simples.

**Causa raiz confirmada, única e partilhada**: `_lvalue`/
`_lvalue_de_expr` (`gerador_base.py:231-238`) e `_gerar_lista_args`
(`codegen.py:407-443`) reconstroem o texto Python da MESMA expressão
ALGO de forma completamente independente — nada partilha o resultado de
uma avaliação com a outra, em nenhum dos três caminhos. Uma correção
real precisa de uma passagem que "eleve" cada subexpressão de índice com
potencial efeito secundário para uma variável temporária, avaliada uma
única vez e reutilizada tanto na leitura como na escrita de volta.

### 35. (ronda 10, grave) `^` e `matematica.potencia` fazem a MESMA matemática de formas inconsistentes para inteiros grandes

**[CORRIGIDO — Fase 2.2]** Não exatamente como o plano sugeria
("quando ambos são inteiro, devolver `base ** exp` sem conversão") --
isso quebrava o contrato já testado de `matematica.potencia` devolver
sempre `decimal` mesmo para resultados pequenos (`matematica.
potencia(2, 3)` passava a imprimir `"8"` em vez de `"8.0"`,
confirmado pelo teste `test_matematica_potencia_devolve_sempre_
decimal` já existente, que falhava com essa mudança). Em vez disso,
`matematica_potencia` tenta sempre `float(resultado)` primeiro (mantém
o `.0` no caso normal) e só cai para o inteiro em bruto quando esse
próprio `float()` rebenta com `OverflowError` -- replicando o
comportamento de SUCESSO do operador `^` só nesse caso extremo (a
função só falha, de forma amigável, mais tarde ao imprimir, bug #33,
já corrigido na mesma leva).
`codegen.py:182-192` (`_algo_pot`, operador `^`) devolve `a ** b`
diretamente, sem forçar `float`; `bibliotecas/matematica.py:24-27`
(`matematica_potencia`) faz sempre `float(base ** exp)`. Para
`2^100000` (inteiro exato, 30103 dígitos): via `^`, calcula-se
perfeitamente (só falha ao IMPRIMIR, bug #33 já documentado); via
`matematica.potencia(2, 100000)`, falha **imediatamente**, mesmo sem
nunca imprimir o resultado, com `"o resultado é grande demais para ser
representado (overflow numérico)."` — porque o `float()` forçado tenta
converter um inteiro de 30 mil dígitos e rebenta com `OverflowError`
muito antes de qualquer impressão. A mesma operação matemática, com a
mesma sintaxe de resultado esperado, comporta-se de forma completamente
diferente consoante se escreve `2^100000` ou
`matematica.potencia(2,100000)` — apesar do comentário do código dizer
explicitamente que a proteção de `matematica.potencia` (AL-85/B13) é "a
mesma proteção" do operador `^` (AL-57/B16). Casos comuns (base
negativa/expoente fracionário, `0^-1`, overflow em `decimal`, `0^0`)
continuam consistentes entre os dois — só este caso de inteiro grande
diverge. Nota menor à parte: `matematica.raiz(-4.0)` e `(-4.0)^0.5`
(mesma operação) dão mensagens de erro com redação diferente, nenhuma
delas crua, só inconsistente.

## Ronda 12 (2026-08-21) — reauditoria pedida pelo utilizador

**Achado prévio, mais importante do que qualquer bug novo desta ronda:**
o `PLANO_CORRECOES_AUDITORIA.md` e este documento davam a impressão de que
os 35 bugs confirmados tinham todos sido corrigidos ("a última [ronda]
corrigiu muitos bugs até não encontrar nenhum novo", nas palavras do
utilizador ao pedir esta reauditoria). Não é verdade: **5 bugs já
confirmados nas rondas 1-10 nunca tiveram fase no plano nem tag
`[CORRIGIDO]`**, e os 5 foram reproduzidos de novo, live, contra o código
atual, antes de começar a procurar bugs novos: **#2** (`constante`
perdida entre ramos irmãos `se`/`senao`), **#9** (falso-positivo "variável
não foi declarada" quando declarada em ambos os ramos), **#18**
(artefactos crus de vírgula flutuante em `escrever`), **#19** (`ler()`
aceita `nan`/`inf` para `decimal` sem validação) e **#24** (`escolher` só
com `contrario` compila mas gera Python inválido, `SyntaxError` cru). Os
bugs #13 (parte conhecida), #21 e #22 continuam deliberadamente fora de
âmbito (ver secção "Fora do âmbito" do plano). Ficam já marcados como
"reconfirmados, ainda por corrigir" — ver `PLANO_CORRECOES_AUDITORIA.md`
Fase 8.

Metodologia desta ronda: 4 auditorias paralelas (front-end léxico/
sintático/AST, verificador semântico, gerador de código + bibliotecas,
CLI/ferramentas), cada uma obrigada a reproduzir com um `.algo` mínimo
antes de reportar, mesma disciplina das rondas anteriores. Baseline:
`py -m pytest algo_lang/tests/ -q -m "not slow"` → **750 passaram, 33
falharam** (as 33 continuam a ser só as falhas de ambiente/subprocess já
conhecidas, confirmado por inspeção).

### 36. (ronda 12, grave) `--debug`/`--json` — e a consola interativa — rebentam por completo com um traceback cru sempre que o Python gerado for sintaticamente inválido

**[CORRIGIDO — Fase 8.3 do `PLANO_CORRECOES_AUDITORIA.md`]** `compile()`
em `tools/tracer.py:gerar_trace` passou a estar dentro de um
`try/except SyntaxError`, devolvendo o mesmo formato de erro que
qualquer outra falha, sem tentar traçar nada. `cmd_consola`
(`cli.py`) passou a apanhar `Exception` em geral no ciclo de comandos
(não só `SystemExit`/`KeyboardInterrupt`), consistente com o contrato
já documentado da consola.

`tools/tracer.py:294` chama `compile(codigo_py, caminho_py, "exec")`
**antes** do `try/except Exception` que só começa em `tracer.py:309` (e
que só envolve o `exec()`, não o `compile()`). `cli.py:295-302`
(`cmd_executa_com_trace`) chama `gerar_trace(...)` sem `try/except`
nenhum à volta. Ao contrário de `cmd_executa` normal (`cli.py:236`, que
isola a falha num subprocesso e só recebe um `returncode`), qualquer bug
do compilador que gere Python sintaticamente inválido (ex.: bug #24, já
confirmado) propaga um `SyntaxError` cru até ao utilizador sob
`--debug`/`--json`, expondo caminhos de ficheiros internos.

**Pior ainda:** dentro da consola interativa, o ciclo de comandos
(`cmd_consola`, `cli.py:653-672`) só apanha `SystemExit`/
`KeyboardInterrupt` à volta de `args.func(args)` — um `SyntaxError` (ou
qualquer outra exceção não-`SystemExit`) vindo de `gerar_trace` **não é
apanhado ali**, o que fecha a consola inteira. Isto contradiz
diretamente o contrato já documentado da própria consola
(`cli.py:606`): *"Um comando com erro só mostra o erro e volta ao
prompt -- não fecha a consola."* Não é específico ao bug #24 — qualquer
bug futuro de codegen que gere Python inválido tem o mesmo efeito.

Repro (com o bug #24 ainda por corrigir):
```algo
algoritmo "T"
inicio
    x:inteiro = 3
    escolher x
        contrario
            escrever("sempre")
```
`executa --debug`/`executa --json` neste ficheiro: traceback cru,
consola fecha-se se corrido dentro dela.

### 37. (ronda 12, média) `linter.py` não avisa de `escolher` sem nenhum `caso` — o padrão exato que rebenta em runtime (bug #24)

**[CORRIGIDO — Fase 8.2]** Novo `_verificar_escolha_sem_casos` em
`tools/linter.py`, chamado a partir de `analisar()`.

`analisar()` (`tools/linter.py:31-93`) nunca inspeciona
`stmt.casos`/`stmt.contrario` de um `A.Escolha` quanto a estar vazio.
`_parse_escolha` (`parser.py:557-576`) permite `casos == []` sem
restrição nenhuma (o `while self.ver("CASO")` simplesmente não executa
nenhuma vez), por isso o padrão do bug #24 é totalmente alcançável e
totalmente silencioso para o linter — o estudante só descobre o
problema ao correr o programa (e, com o bug #36 ainda por corrigir,
descobre-o com um traceback cru ou a consola a fechar-se).

Repro: `analisar()` sobre o programa do repro do bug #36 devolve `[]`.

### 38. (ronda 12, investigado — descartado, conflito com desenho já testado) Global declarada só dentro de UM ramo `se` sem `senao` é tratada como sempre visível

`_pre_registar_recursivo` (`semantics.py:350-398`) percorre TODOS os
blocos alcançáveis via `A.subblocos` e insere qualquer `Declaracao`
encontrada diretamente em `destino`/`self.globais` (linha 396,
incondicional), sem noção nenhuma de se o `se` que a envolve está
garantido a executar. Não é preciso um ramo irmão em conflito — um
único `se` sem `senao` já dispara isto.

Repro:
```algo
algoritmo "T"
funcao usa():inteiro
    devolver x
inicio
    se falso entao
        x:inteiro = 10
    escrever(usa())
```
Compila sem `ErroSemantico` nenhum. Em runtime (o ramo nunca executa,
`x` nunca é atribuída), dispara o `NameError` traduzido: `Erro em tempo
de execução: a variável 'x' foi usada antes de existir um valor nela.
(linha 3)` — mensagem amigável mas enganadora, já que a linha 3 é
`devolver x`, não a causa real (a única declaração de `x` está dentro de
um ramo comprovadamente morto, `se falso`). Devia ser um erro de
COMPILAÇÃO, não uma surpresa em runtime.

`semantics.py:350-398` (`_pre_registar_recursivo`).

**Tentativa de correção, revertida:** ignorar ramos cuja condição é
literalmente `falso` ao percorrer `_pre_registar_recursivo` (não
registar declarações lá dentro como "globais visíveis") corrige o
repro acima, mas **quebra
`test_variavel_global_com_tipos_diferentes_em_ramos_irmaos_e_erro`**
(já existente, `test_correcoes_auditoria.py:3004`), que testa
DELIBERADAMENTE que `se falso entao x:inteiro=1 senao x:cadeia="oi"`
continua a dar `ErroSemantico` de tipos incompatíveis -- ou seja, o
desenho já testado e intencional é tratar QUALQUER ramo que declare um
nome (morto ou não, decidido só pela presença textual, nunca por
alcançabilidade) como parte do conjunto que tem de concordar em tipo.
Resolver #38 sem quebrar essa garantia exigiria distinguir "usar #38
para SILENCIAR o registo" de "usar #38 só para a verificação de
consistência de tipos" -- dois comportamentos diferentes para o mesmo
mecanismo, mais arriscado do que vale a pena para este bug (nem
`grave`, é `média`). Revertido; `_pre_registar_recursivo` continua sem
nenhuma noção de alcançabilidade, como estava. Fica descartado por
agora -- não é indecidível em geral (o caso de um `se falso` literal É
decidível), mas a correção mínima e segura para ESSE caso específico
colide com uma garantia diferente que já tem teste próprio.

### 39. (ronda 12, média) `constante` com o MESMO tipo mas valores DIFERENTES em ramos irmãos `se`/`senao` funde para o valor errado — análogo ao bug #2, mas no valor, não na flag `eh_constante`

**[CORRIGIDO — Fase 8.1]** Mesmo mecanismo do bug #2 -- quando
tipo/`eh_constante` batem certo mas `valor_resolvido` diverge entre
ramos, passa a ficar `None` (não resolvível estaticamente) em vez de
congelado no primeiro ramo. `_resolver_constante` já trata `None` como
"não é um literal conhecido", por isso o tamanho do vetor deixa de ser
verificado em compilação (fica para o guarda de runtime), mas já não
rejeita código válido.

A verificação de compatibilidade tipo/dims em `semantics.py:380-386`
aceita duas declarações irmãs sempre que `(tipo, dims)` batem certo —
nunca olha para, nem concilia, o valor resolvido (`valor_resolvido`,
acrescentado pela correção do bug #29). O ramo visitado primeiro em DFS
(`s.ramos` antes de `s.senao`) fica com o valor congelado para sempre; o
valor do ramo irmão — que pode ser o que executa de facto em runtime —
é descartado em silêncio.

Repro:
```algo
algoritmo "T"
funcao tam():inteiro
    v:inteiro[x] = {1,2,3,4,5,6,7,8,9,10}
    devolver 3
inicio
    se falso entao
        constante x:inteiro = 5
    senao
        constante x:inteiro = 10
    escrever(tam())
```
Atual: `ErroSemantico: ... o vetor tem tamanho declarado 5 mas o literal
'{...}' tem 10 elemento(s)`. Esperado: compila sem erro — `x` vale 10 em
runtime (o `senao` é o ramo que executa), que bate certo com os 10
elementos do literal. O compilador rejeita código semanticamente
correto porque congelou `x` a 5 (o valor do ramo `s.ramos`, visitado
primeiro), não 10.

`semantics.py:380-386` (fusão que ignora `valor_resolvido`) e
`_resolver_constante` (`semantics.py:658-690`, linhas 686-689, que lê o
valor obsoleto guardado na entrada partilhada do âmbito).

### 40. (ronda 12, investigado — não é bug) `conversao.paraDecimal` aceita `"nan"`/`"inf"`/`"-inf"`/`"Infinity"` — inicialmente reportado como o mesmo defeito do bug #19, corrigido depois de quebrar 2 testes existentes

Reportado inicialmente como "mesmo defeito do bug #19 por um caminho de
código diferente" (`conversao_paraDecimal` faz `float(x)` direto, sem
rejeitar as palavras especiais que `float()` do Python aceita). A
correção proposta (rejeitar `nan`/`inf`/`Infinity` aqui também) foi
implementada e **quebrou 2 testes já existentes e a passar**,
`test_matematica_piso_de_infinito_da_overflow_amigavel` e
`test_conversao_parainteiro_de_infinito_da_erro_amigavel` — ambos usam
`conversao.paraDecimal("inf")` deliberadamente, porque **é o único
ponto de todo o ALGO por onde um programa consegue construir um valor
infinito/nan**, já que a linguagem não tem literal nenhum para isso no
código-fonte. Ao contrário de `ler()` (entrada interativa de um
estudante, onde `"nan"` é quase sempre um erro de digitação, não um
valor pretendido — aí sim faz sentido rejeitar, ver bug #19), esta
função de biblioteca é chamada a partir de código escrito
deliberadamente, e os consumidores existentes (`matematica.piso`/
`teto`, `conversao.paraInteiro`) já traduzem o `OverflowError`
resultante para uma mensagem amigável — não há nenhum valor "perigoso"
a escapar sem aviso. **Correção revertida** para `conversao.paraDecimal`
especificamente (mantém `float(x)` a aceitar `nan`/`inf`/`Infinity`);
a rejeição de separadores `_` de milhar (bug #43, sem uso legítimo
nenhum, não usada por teste nenhum) mantém-se. `_algo_ler_decimal`
(bug #19) mantém a sua própria correção, independente desta.

`bibliotecas/conversao.py` (`conversao_paraDecimal`).

### 41. (ronda 12, menor) 4 mensagens de erro do parser escritas à mão fogem ao helper `_nome_amigavel` e mostram o nome cru do tipo de token

**[CORRIGIDO — Fase 8.6]** Os 4 sítios passaram a chamar
`_nome_amigavel(tok.tipo, tok.valor)`, tal como `esperar()` já fazia.

O parser tem um helper `_nome_amigavel()` desenhado exatamente para não
mostrar ao estudante constantes de token em bruto (`NEWLINE`, `COLON`,
etc.), e `esperar()` usa-o sempre. Mas 4 sítios contornam-no e
interpolam `tok.tipo`/`self.atual().tipo` diretamente: `parser.py:162`
(apanha-tudo de `parse_programa`), `parser.py:207` (`_parse_tipo`),
`parser.py:455` (apanha-tudo de `_parse_stmt`), `parser.py:876`
(apanha-tudo de `parse_biblioteca`).

Repro: `x:\n` como corpo → `esperava-se um tipo, encontrou NEWLINE`
(devia ser algo como "encontrou fim de linha"); `:` sozinho no corpo →
`instrução inesperada: COLON`; `+` a seguir ao cabeçalho → `... encontrou
MAIS` (devia mostrar `'+'`). Mesma classe dos bugs #4/#5/#8/#25/#30/#33
(já corrigidos) — só que estes 4 escaparam por serem mensagens do
próprio parser, não exceções do runtime Python traduzidas.

### 42. (ronda 12, menor) `_nome_amigavel()` esconde o texto real de um identificador inesperado — ao contrário de todos os outros tipos de literal

**[CORRIGIDO — Fase 8.6]** `_nome_amigavel` passou a devolver
`f"um identificador ({valor!r})"` quando `tipo == "ID"` e há valor,
antes de consultar `NOMES_AMIGAVEIS`.

`NOMES_AMIGAVEIS["ID"] = "um identificador"` (`parser.py:13`) faz
`_nome_amigavel()` devolver essa string genérica e nunca cair no ramo
`f"{tipo.lower()} ({valor!r})"` que mostra o valor real — porque `ID`
ESTÁ no dicionário, o `return` antecipado (`parser.py:18-19`) dispara
antes de `valor` ser sequer consultado. `INT`/`FLOAT`/`STRING`/
`CARACTER` não estão no dicionário, por isso esses SIM mostram o valor
via o ramo de recurso.

Repro: `x = 5 abc` → `esperava-se fim de linha mas encontrou um
identificador` (não diz qual); `x = 5 5` → `... encontrou int (5)` (este
sim mostra o valor). Relevante na prática porque "identificador a mais"
é provavelmente o erro de sintaxe mais comum que um estudante encontra
(palavra a mais, operador em falta entre dois nomes, erro ortográfico
numa palavra-chave que cai para `ID`) — incluindo `escrever(1e10)`, que
o lexer (sem suporte a notação científica) tokeniza como `INT(1)` +
`ID("e10")`, dando `esperava-se ')' mas encontrou um identificador` sem
indicar `e10` como o culpado.

`parser.py:17-22` (`_nome_amigavel`) + entrada `"ID"` na linha 13.

### 43. (ronda 12, cosmético) `conversao.paraInteiro`/`paraDecimal` aceitam separadores `_` de milhar do Python, que o próprio léxico do Algo não suporta

**[CORRIGIDO — Fase 8.7]** Ambas as funções rejeitam explicitamente
`"_" in x` antes de delegar a `int(x)`/`float(x)`.

Repro: `conversao.paraInteiro("1_000")` → `1000`;
`conversao.paraDecimal("1_000.5")` → `1000.5`. `"1_000"` não é um número
em nenhum sentido reconhecível por um estudante português — o lexer do
Algo não trata `_` como separador de dígitos — mas ambas as funções
delegam direto para `int(x)`/`float(x)` do Python, que implementam a
PEP 515. Impacto real baixo (entrada improvável), mas é uma lacuna de
correção de domínio genuína.

`bibliotecas/conversao.py:37` (`int(x)`) e `:53` (`float(x)`) — sem
validação prévia antes de delegar aos construtores do Python.

## Meta-achado (ronda 10): porque é que o bug #31 (índices negativos) escapou a 97+ correções anteriores

Investigação dedicada, não apenas mais um bug. Conclusão com evidência
concreta: a correção AL-64/B24 (que introduziu a guarda de índice
negativo) foi feita **só dentro de `bibliotecas/cadeia.py`**, para
`cadeia_caracter` especificamente — o comentário da própria correção
compara-se ao `cadeia.subcadeia`, no MESMO ficheiro, mas nunca menciona
indexação de vetores, que vive num ficheiro completamente diferente
(`gerador_base.py:_lvalue`, o caminho partilhado por toda a indexação de
arrays). Quem corrigiu o AL-64 estava a pensar nas funções irmãs dentro
de `cadeia.py`, não no mecanismo genérico de indexação. Agravante: existe
um teste mesmo ao lado dessa correção
(`test_indice_fora_dos_limites_em_vetor_continua_a_mencionar_vetor`,
`test_correcoes_auditoria.py:883`) que dá uma falsa sensação de
cobertura — testa `v[10]` (fora dos limites por CIMA, que o Python já
deteta nativamente com `IndexError`) mas nunca testa um índice negativo,
o único caso que o Python NÃO deteta sozinho. E o linter (AL-98/B26) já
sabia detetar índices negativos literais — mas nunca foi cruzado com a
falta de guarda em runtime, porque são duas correções em ficheiros e
"tags" AL diferentes, nunca ligadas uma à outra. Não é um problema de
alcance do fuzzer (o fuzzer deste projeto muta texto-fonte, não gera
valores de índice, por isso nem sequer é o mecanismo certo para apanhar
isto) — é um problema de correção feita na camada errada, mascarada por
um teste vizinho que testa a metade fácil do problema.

## Meta-achado (ronda 4): o teste de fuzzing não conseguiria ter apanhado os bugs #7/#10, por desenho

`algo_lang/tests/test_fuzzing_e_propriedades.py:117`
(`test_fuzz_mutacao_modo_normal_nunca_escapa_excecao_nao_classificada`)
tem exatamente o propósito de garantir que nenhuma exceção não
classificada escapa do pipeline `parse→verificar→gerar_python` — mas o
seu próprio `except (ErroLexico, ErroSintatico, ErroSemantico,
RecursionError): pass` trata `RecursionError` como resultado
**aceitável**, ao mesmo nível dos erros tipados do próprio compilador.
Ou seja, mesmo que o gerador de mutações produzisse exatamente a forma
dos bugs #7/#10, o teste engoliria isso em silêncio, não o reportaria.
Confirmado que o corpus de mutações atual (edições a nível de caracter,
máx. 5 por iteração, sobre programas-semente curtos) nunca chega a gerar
uma cadeia de 498+ termos na prática — mas o desenho do teste já
"legitima" esse resultado antes mesmo de o encontrar. Vale a pena
corrigir esta lista de exceções aceitáveis ao corrigir os bugs #7/#10,
para o teste passar a apanhar regressões futuras da mesma forma.

## Consistência de idioma — problema apontado pelo utilizador, não coberto pela 1ª ronda

A 1ª ronda de auditoria (4 agentes acima) tinha âmbito **"bugs de
correção"**, não **"pureza/consistência do idioma"** — por isso não verificou
se a própria linguagem Algo, exposta ao estudante, é 100% português, que é
uma regra explícita do projeto (`CLAUDE.md`: *"o projeto inteiro... é escrito
em português"*). Isto foi um erro de âmbito, não uma verificação feita e
falhada — mas o resultado prático (passar ao lado de algo pedido
explicitamente pelo dono do projeto) é o mesmo, por isso fica registado aqui
como falha da auditoria.

**Primeira tentativa (errada):** apontei `ref` como a palavra em inglês. O
utilizador corrigiu-me — `ref` é abreviatura válida de "referência",
consistente com `div`/`mod` (também abreviaturas portuguesas). Não é o
problema.

**Palavra correta, identificada pelo utilizador: `array`.** Ao contrário de
`ref` (uma palavra-chave isolada), este era sistémico: **0 ocorrências de
"vetor"** em todo o `algo_lang`, contra **~190 ocorrências de "array"/
"arrays"**, incluindo dezenas de mensagens de erro mostradas diretamente ao
estudante (`semantics.py`: 71×, `linter.py`: 33×, `parser.py`: 13×), o nome
da classe AST `ArrayLiteral`, várias funções internas
(`_verificar_array_literal`, `_expr_array_literal`,
`_algo_verificar_tamanho_array`, etc.) e `docs/ReferenciaCompletaCLI.md`
(15×).

**Corrigido nesta sessão** (renomeação `array`→`vetor` / `arrays`→`vetores`,
preservando `bytearray()` — uso legítimo de um builtin do Python em
`cli.py`, não relacionado): `algo_lang/bibliotecas/cadeia.py`,
`algo_lang/compilador/ast_nodes.py` (`ArrayLiteral`→`VetorLiteral`),
`codegen.py`, `gerador_base.py`, `parser.py`, `semantics.py`,
`tools/linter.py`, 5 ficheiros de teste (`test_correcoes_auditoria.py`,
`test_estruturas.py`, `test_linter.py`, `test_novas_funcionalidades.py`,
`test_tracer.py`) e `docs/ReferenciaCompletaCLI.md`. Verificado com
`py -m pytest algo_lang/tests/ -q -m "not slow"` antes/depois: **659
passaram / 33 falharam em ambos** (as 33 são as falhas de ambiente/
subprocess já conhecidas) — sem regressões.

**Por resolver, fora do âmbito desta auditoria ao compilador** (ficam
inconsistentes com a mudança acima, decisão do utilizador se/quando
alinhar):
- `alguem/nucleo/conhecimento_algo.py` — base de conhecimento do tutor
  Alguem ensina "Arrays começam em 0" ao estudante.
- `online/paginas_privadas/ajuda.html` — página de ajuda do serviço web,
  secção inteira "10. Arrays" em prose.
- `docs/RoteiroTestesManualALGO.md` — 6 ocorrências.
- `exemplos/soma/soma.py` — ficheiro `.py` já compilado/gerado a partir de
  um `.algo`, contém a mensagem de erro antiga ("posição de array que não
  existe"); ficaria desatualizado até o `.algo`-fonte ser recompilado.

Não toquei em `online/estatico/app.js` nem nos ficheiros vendor
(`codemirror6.js`, `react*.js`, `babel.min.js`, `tailwind.js`) — usam
`Array`/`Array.from`/`Array.isArray` como o tipo nativo do JavaScript, sem
relação com a linguagem Algo.

Restante verificação de pureza de idioma (mantida da 1ª tentativa, continua
válida): nomes de tipos primitivos, nomes de funções das bibliotecas
(exceto `paraAscii`/`deAscii`, sigla técnica internacional) e flags da CLI
(exceto `--debug`/`--json`, convenção internacional de ferramentas) — todos
em português.

## O que foi verificado e não teve problemas

**Retificação da 1ª ronda:** o veredito anterior "`lexer.py`/`parser.py`/
`ast_nodes.py` sem bugs" não se sustentou — ver bug #7 (ronda 2) acima,
encontrado exatamente nestes ficheiros com testes mais agressivos
(cadeias longas de operadores). O resto do que a 1ª ronda tinha testado
nestes 3 ficheiros (precedência/associatividade, indentação, literais,
comentários, unicode) foi re-testado na 2ª ronda com casos ainda mais
adversariais (recursão/aninhamento profundo, literais no limite,
indentação ambígua, structs mutuamente recursivos, erros de parser) e
esses continuam a comportar-se corretamente.

`inclusoes.py` e as três bibliotecas (`cadeia.py`, `matematica.py`) — sem
problemas de correção encontrados em nenhuma das três rondas (nota:
`conversao.py` teve o bug #8, ronda 2). `cli.py` teve os bugs #15/#16
(ronda 3), mas o resto (`_shlex_split_sem_escape`, resolução de
inclusões-diamante e ciclos de 3+, deteção de colisão entre bibliotecas
diferentes, `_pasta_saida`, `--entradas` com ficheiro vazio/linhas a
mais) aguentou-se sob teste agressivo. `tools/flowchart.py` também
aguentou-se (protegido a montante pelo limite de aninhamento do parser).
`cadeia.*`/`matematica.*` aguentaram-se mesmo com unicode acentuado,
valores extremos e casos de fronteira (`potencia(0,0)`, `teto(-1.5)`,
`aleatorio(5,5)`).

**Ronda 4 — coerção numérica e arrays multi-dimensionais:** `3/2`→`1.5`
(divisão real), `3 div 2`→`1`, `-7 div 2`→`-3` (trunca em direção a
zero, como prometido); coerção `inteiro`→`decimal` correta em todos os
contextos testados (atribuição, campo de struct, literal de vetor,
parâmetro, retorno); `escrever` de struct/vetor diretamente já é
corretamente rejeitado (correção anterior AL-55/B14, confirmada);
arrays 3D/4D/5D com leitura elemento-a-elemento corretos; literais
"esfarrapados" (`{{1,2,3},{4,5}}` com tamanho inconsistente) são
corretamente rejeitados em compilação; uma linha de um array 2D passada
por valor a uma função 1D é corretamente copiada (`deepcopy`), não
aliased; `ref` numa linha inteira ou num array 2D inteiro funciona
corretamente. **Nota**: os bugs #1 (aliasing) e #13 (ref) foram
confirmados a reproduzir também em contexto multi-dimensional (struct
com campo-array dentro de um array de structs; índices 2D) — isto
confirma que o alcance já mapeado cobre estes casos, não é uma
descoberta nova independente.

**Ronda 5:** valores por omissão de structs/arrays (proteção contra
"mutable default argument") corretos a qualquer profundidade testada
(campo-array direto, struct-dentro-de-struct, array-de-structs-com-
campo-array); structs mutuamente recursivas (`A↔B`, e um ciclo de 3,
`A→B→C→A`) tratadas corretamente pela deteção de ciclos em
`gerador_base.py:_estruturas_recursivas` (correção anterior AL-39,
confirmada, campo do ciclo fica `nulo` em vez de recursão infinita no
próprio compilador); `escrever` com vários argumentos não insere
separador nenhum entre eles (`"x =",5` → `"x =5"`) — confirmado que isto
é deliberado, não um bug (toda a suite de testes já escreve o separador
explicitamente quando o quer); operadores `+`/`<`/`>`/`==` em
`cadeia`/`caracter` são simétricos nas duas ordens (`cadeia+inteiro` E
`inteiro+cadeia` ambos corretamente rejeitados, não só um dos lados);
comparação lexicográfica de `cadeia` correta (só por ordem de código
Unicode, não ordem alfabética portuguesa — isto é uma limitação inerente
e esperada, não um bug); `"ab"*3` corretamente rejeitado. O `tracer.py`
captura o estado de cada passo com cópia profunda (`_valor_serializavel`,
`tracer.py:40-50`), não por referência — confirmado com o próprio bug #1
como caso de teste: o histórico do trace mostra fielmente o momento exato
em que `p1`/`p2` passam a ser iguais (bug real do compilador), mas não
introduz nenhuma corrupção própria a mais — passos antigos nunca mudam
retroativamente quando uma mutação posterior acontece. Um resultado
negativo genuíno: a ferramenta de debug é fiável mesmo quando o que
mostra é um comportamento da linguagem que está errado.

**Ronda 6:** `flowchart.py` verificado limpo com o binário real do
Graphviz (`dot -Tsvg`, não só inspeção manual) — escaping de labels
(aspas, barra invertida, `\n`) correto em todos os casos testados, IDs
de nós nunca colidem, e `cmd_fluxograma` já dá um aviso amigável (não
crasha) quando `dot` não está instalado — finalmente verificado
diretamente, sem depender de subprocess. Colisões de nomes entre
namespaces diferentes (função vs. struct, global vs. função, parâmetro a
sombrear global, campo de struct com o mesmo nome do tipo, dois structs
com campo do mesmo nome) — todas corretamente geridas, sem problema
nenhum (só a colisão com builtins do Python, bug #23, é real).
`escolher`/`caso`: múltiplos valores por `caso` (`caso 1,2,3`)
corretamente combinados com `or`; sem fallthrough (cada `caso` gera
`if`/`elif` independente); valores duplicados entre `caso`s literais
corretamente rejeitados em compilação; discriminante com efeito
secundário (uma chamada de função) avaliado exatamente uma vez, não uma
vez por `caso` — confirmado com um contador. Escaping de strings ao
reemitir para Python (barra invertida, aspas escapadas, `\n`, chaves e
`%` literais) — correto em todos os casos testados.

**Ronda 7:** `ref` combinado com recursão (acumulador recursivo, `ref`
reencaminhado para a própria chamada recursiva, duas referências `ref` a
convergir para o mesmo slot, recursão mútua com `ref` em ambas as
funções, recursão profunda de 300-1000 níveis com `ref` para struct/
vetor) — tudo correto; a colisão do bug #13 reaparece quando dois `ref`
convergem em contexto recursivo, mas não piora, confirma só o alcance já
mapeado. `afirmar`: mensagem automática (`texto_expr`) e mensagem
personalizada corretas, condição avaliada exatamente uma vez, `afirmar`
sobre comparação de structs funciona; **o limiar exato do bug #7 fica
finalmente cravado**: `verificar()` crasha a 498 termos (como já
documentado), mas `texto_expr` sozinho (usado só para construir a
mensagem de falha do `afirmar`) tem um limiar próprio mais alto, ~999
termos — mas nunca é alcançável independentemente, porque `verificar()`
crasha sempre primeiro no pipeline real. `algo verifica`: código de
saída sempre 0 com avisos (por desenho, avisos nunca bloqueiam), sempre
1 com erro de compilação real, formato de saída (`"linha N: mensagem"`)
100% consistente entre as ~17 regras do linter.

**Ronda 8:** avaliação de curto-circuito de `e`/`ou` totalmente correta
— herdada diretamente do `and`/`or` nativo do Python (o codegen faz
substituição direta de string, sem reimplementar lógica booleana à mão),
confirmado que o lado direito não avaliado nunca corre (nem sequer
quando conteria um erro como divisão por zero), e que `nao`/cadeias de
3+ operandos preservam o curto-circuito. Coerção de tipo em `devolver`
totalmente correta para os 5 tipos primitivos, literal/variável/chamada
aninhada/por ramo — reutiliza a mesma maquinaria já validada para
atribuição. Arrays de tamanho 0 corretos (sem off-by-one). Pasta de
saída partilhada: impossível colidir por desenho (cada pasta deriva do
nome do ficheiro fonte); recompilar por cima de um ficheiro mais curto
trunca corretamente; falha de compilação não deixa `.py` parcial;
`--json` executado duas vezes substitui completamente o ficheiro
anterior; acesso concorrente ao ficheiro de saída não bloqueia no
Windows.

**Ronda 9:** indexação direta de `cadeia` com `[]` (`s[0]`) é sintaxe
legal mas rejeitada de forma limpa e total em compilação, leitura E
escrita, sem inconsistência nenhuma com `cadeia.caracter` (que continua
a funcionar corretamente em runtime, incluindo índices negativos, já
corrigido antes); `procedimento` usado como se tivesse valor de retorno
— corretamente rejeitado em qualquer contexto de expressão (atribuição,
argumento, condição, aritmética); parâmetros duplicados na mesma
assinatura (mesmo nome, com/sem `ref`) — corretamente rejeitados antes
de chegar ao codegen; redeclaração de variável local (mesmo tipo ou
tipo diferente) — corretamente rejeitada. Nota de desenho, não bug: não
existe `devolver` sem valor dentro de um `procedimento` — a gramática
exige sempre uma expressão a seguir a `devolver`. Um ciclo `para` de 10
milhões de iterações com aritmética simples corre corretamente em ~2.2s,
sem limite escondido nenhum (só a construção de arrays grandes tem o
problema do bug #32, não os ciclos em geral).

**Ronda 10:** tipo do índice de um array é bem verificado — `booleano`
e `decimal` (incluindo `2.0`, um valor "inteiro" mas de tipo `decimal`)
são sempre rejeitados em compilação, com o mesmo `_tipo_lvalue`
partilhado por leitura/escrita/2D/`ref`/campos-array, sem a lacuna que
existe para o SINAL do índice (bug #31). Ao contrário do sinal, aqui não
há brecha nenhuma para explorar a coincidência de `bool` ser subtipo de
`int` em Python.

**Ronda 11:** coerção `inteiro`→`decimal` em argumentos de chamada de
função (literal, variável, chamada recursiva, biblioteca, literal de
struct/vetor inline) — correta em todos os casos, sem a assimetria
literal-vs-variável que aparece noutros bugs; passar um `inteiro` por
`ref` a um parâmetro `decimal` é corretamente rejeitado em compilação
(tipos por referência têm de ser exatamente iguais). Funções de
biblioteca de categoria "primitivo" (`conversao.paraTexto`/
`paraInteiro`/`paraDecimal`/`paraBooleano`) rejeitam corretamente
argumentos struct e array, sem fuga nenhuma para `_algo_fmt`. Deteção de
recursão sem caso base no linter é deliberadamente limitada a
auto-chamada direta (não deteta `A→B→A`) — mas o próprio texto do aviso
já diz "chama-se A SI PRÓPRIA", por isso não é uma promessa quebrada,
é um limite conhecido e bem comunicado.

`online/executor.py`: tracebacks crus dos bugs #4/#5/#8 (ainda não
corrigidos) são reencaminhados literalmente como "saída do programa" via
WebSocket, incluindo o caminho da pasta temporária do servidor — mesma
causa-raiz já documentada, não um bug novo, mas confirma que corrigir
esses bugs no compilador também limpa esta exposição no `online/`.

**Ronda 3 — contrato semantics.py↔codegen.py, para além do bug #1:**
igualdade estrutural de structs (`__eq__` gerado) recursa corretamente
por campos-array e structs aninhadas; `_todos_caminhos_devolvem` bate
certo com a geração de `if`/`elif`/`else` do codegen — sem gaps novos
para além dos já descritos nos bugs #13/#14 (que são consequências do
bug #1, não gaps independentes).

**Ronda 2 — verificações que confirmaram estar corretas (não são bugs, incluídas para mostrar o que foi mesmo testado):**
- Tamanho de vetor negativo calculado em runtime (não literal) — já tem
  guarda amigável (`_algo_verificar_tamanho_vetor`), ao contrário do
  `passo=0` (bug #5). Serviu de controlo positivo para calibrar o resto
  da verificação.
- Divisão/mod por zero calculado em runtime — sempre traduzido, literal
  ou não.
- `escolher`/`caso`/`contrario` com `constante` inconsistente entre casos
  — mesmo mecanismo do bug #2 (não é um bug adicional independente, é o
  mesmo bug alcançável por outra sintaxe).
- Âmbito local dentro de funções (branches `se`/`senao` locais) — cada
  ramo tem o seu próprio `Escopo` descartável, sem contaminação cruzada;
  não sofre da mesma classe do bug #2.
- Nenhuma outra propriedade além de `tipo`/`dims`/`eh_constante` é
  fundida entre declarações irmãs — `Declaracao` não tem mais campos, e
  `self.funcoes`/`self.estruturas` rejeitam duplicados diretamente (nunca
  fundem), por isso não há mais nenhum sítio com o formato do bug #2.
