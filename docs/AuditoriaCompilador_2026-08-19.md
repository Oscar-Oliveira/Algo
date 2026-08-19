# Auditoria ao compilador (algo_lang) — 2026-08-19

**Nota de fiabilidade:** este documento teve 2 rondas. A 1ª ronda (4 agentes,
âmbito "bugs de correção") deu `lexer.py`/`parser.py`/`ast_nodes.py` como
"sem bugs" e descreveu o bug #1 (aliasing) como limitado a 3 sítios. O
utilizador pediu uma repetição "mais a funda" depois de apanhar, ele
próprio, um problema de consistência de idioma que a 1ª ronda tinha passado
ao lado (ver secção "Consistência de idioma"). A 2ª ronda, com agentes
instruídos a assumir que a 1ª tinha lacunas e a tentar ativamente mais
casos adversariais/mais classes do mesmo bug, **encontrou bugs novos,
incluindo um em `lexer.py`/`parser.py`, o conjunto de ficheiros que a 1ª
ronda tinha dado como limpo.** As secções novas estão marcadas "(ronda 2)".

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
`semantics.py:200-238`.

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
`linter.py:283-301`, `_verificar_globais_nao_usadas`.

Trata qualquer `para <var>` no programa inteiro (corpo principal OU dentro de
qualquer função) como prova de uso da global homónima. Mas dentro de uma
função, `_gerar_funcao` (`gerador_base.py:251-263`) exclui esse `para` do
`global` da função — é uma variável local independente, nunca toca a global.
Mesma classe de erro que o AL-63/B23 já corrigiu na função irmã
(`_verificar_uso_de_globais`), não replicada aqui.

### 4. (média) `ler()` a mais com `--entradas` esgota o ficheiro e mostra `EOFError` em inglês
Sem tratamento em `codegen.py`'s cadeia de `except` (que traduz `IndexError`,
`ZeroDivisionError`, `OverflowError`, `RecursionError`, `AttributeError`,
`ValueError`, `_AlgoIndiceCadeiaInvalido`). Cai no `except Exception` genérico
de `tracer.py:261-262`, cujo comentário diz "não deve ocorrer" — mas ocorre,
com um simples ficheiro `--entradas` mais curto do que o esperado. Mensagem
real vista pelo estudante: `EOF when reading a line` — texto cru em inglês.

### 5. (menor) `passo` calculado em runtime igual a 0 vaza mensagem em inglês
`semantics.py:722-725` só rejeita um `passo` **literal** igual a 0 em tempo de
compilação. Um `passo` que só dá 0 em runtime (ex.: vindo de uma variável)
chega a `range(ini, fim, 0)` sem guarda, e `_algo_traduzir_valueerro` não tem
caso para essa mensagem → cai no genérico `"valor inválido (range() arg 3
must not be zero)."`, com o texto interno do Python à mistura.

### 6. (cosmético) Erro de inclusão do ficheiro principal por engano não identifica o ficheiro
Se uma biblioteca incluir por engano o próprio ficheiro principal, o erro de
sintaxe resultante ("um ficheiro incluído só pode conter...") não diz qual
ficheiro está em causa. Não crasha, só confunde. Impacto muito baixo.

### 7. (ronda 2, grave) Cadeia plana de operadores (`1+1+1+...`) crasha com `RecursionError` cru
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

### 8. (ronda 2, média) `conversao.paraInteiro`/`paraDecimal` vazam `OverflowError` do Python em inglês
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
problemas de correção encontrados em nenhuma das duas rondas (nota:
`conversao.py` teve o bug #8, ronda 2).

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
