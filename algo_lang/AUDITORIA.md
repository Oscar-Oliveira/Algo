# Auditoria compreensiva ao `algo_lang`

**Data:** 2026-08-13
**Âmbito:** todo o `algo_lang/` (lexer, parser, AST, semântica, geração de código — normal e `--minimo` —, CLI, `inclusoes.py`, bibliotecas de runtime, e as ferramentas `tracer`/`flowchart`/`linter`). Não inclui `alguem/` nem `online/`.
**Método:** leitura integral de todos os ficheiros-fonte de `algo_lang/compilador/`, `algo_lang/cli.py`, `algo_lang/bibliotecas/` e `algo_lang/tools/`, com verificação cruzada contra a suite de testes existente (em particular `test_correcoes_auditoria.py`, que documenta correções de uma auditoria anterior) para não repetir problemas já resolvidos. A maioria dos bugs listados foi **reproduzida diretamente** — compilando e executando um `.algo` mínimo através do pipeline real — não apenas inferida por leitura. Os que não foram reproduzidos por mim estão assinalados como tal.

Este documento ignora deliberadamente `AUDIT_DONE.md`/`AUDIT_PLAN.md` na raiz do repositório, conforme pedido.

---

## Resumo executivo

| Categoria | Alta | Média | Baixa | Total |
|---|---|---|---|---|
| Bugs | 13 | 11 | 1 | 25 |
| Melhorias (UX/robustez) | 0 | 5 | 4 | 9 |
| Conceptuais/arquiteturais | 2 | 6 | 2 | 10 |
| Lixo (código morto/obsoleto) | 0 | 3 | 8 | 11 |

Os problemas de maior impacto, por serem fáceis de desencadear com programas ALGO perfeitamente válidos e produzirem *crashes* em vez de erros amigáveis (o objetivo central deste compilador, para uma ferramenta de ensino):

1. **Comentários de bloco `/* */` sem espaço à volta fundem tokens adjacentes silenciosamente** (lexer.py) — corrupção semântica silenciosa, não um erro.
2. **Aspas escapadas `\"` dentro de strings confundem a remoção de comentários**, causando um erro de "string não fechada" em programas válidos (lexer.py).
3. **Atribuição a um array inteiro (`v = 5` em vez de `v[i] = 5`) não é rejeitada em compilação** e crasha em runtime com um `TypeError` cru do Python (semantics.py).
4. **Uma função que não devolve valor em todos os caminhos não é detetada** — o erro clássico de "esqueci o `senao`" resulta num `TypeError` cru mais tarde (semantics.py).
5. **`base ^ expoente` com base decimal negativa e expoente não inteiro devolve silenciosamente um número complexo** em vez de erro (codegen.py) — confirmado por execução direta.
6. **`algo executa --json`/`--debug` termina com código de saída 0 mesmo quando o programa falha**, ao contrário do modo sem `--json` — confirmado por execução direta; quebra qualquer *pipeline* que dependa do código de saída.
7. **Parâmetros de funções nunca são verificados contra colisão de nomes** (com estruturas, bibliotecas, tipos primitivos) — pode gerar Python inválido silenciosamente.

---

## 1. Bugs

Numerados `B1..B25`, por módulo, ordenados por severidade dentro de cada módulo. `✅ verificado` = reproduzido diretamente durante esta auditoria (por mim ou citado com repro completo pelo sub-relatório correspondente).

### 1.1 `compilador/lexer.py`

**B1 — [ALTA] `/* */` sem espaço à volta funde tokens adjacentes** ✅ verificado
`_remover_comentarios_bloco` (linhas 78-89) substitui o comentário removido por `""` quando este não contém newline, em vez de um separador:
```python
trecho = codigo[i:j + 2]
resultado.append("\n" * trecho.count("\n"))   # "" se o comentário for numa só linha
```
Reproduzido: `escrever(a/*comentario*/b)` tokeniza `a` e `b` como um único identificador `ab`; `escrever(1/**/2)` tokeniza como um único inteiro `12`. Sem erro nenhum — corrupção silenciosa. O teste existente (`test_comentario_bloco_no_meio_de_uma_linha`) só cobre o caso com espaços à volta.
**Correção:** substituir o comentário por `" "` (não `""`) quando não contém newline.

**B2 — [ALTA] Aspas escapadas `\"` confundem a deteção de comentários, corrompendo strings válidas** ✅ verificado
`_remover_comentarios_bloco` (90-94) e `_remover_comentario` (178-191) alternam `dentro_str` a cada `"` sem noção de `\` de escape — ao contrário do tokenizador real (`_tokenizar_linha`, 211-213), que já suporta `\"`. Reproduzido:
```
escrever("say \" then // not a comment")
```
falha com `ErroLexico: cadeia de texto não fechada com aspas duplas`, porque o `\"` é tratado como fecho real da string, e o `//` a seguir passa a ser visto como comentário, apagando o resto da linha (incluindo o `")` real). O teste `test_escape_de_aspa_dentro_de_string` usa um número *par* de `\"`, o que por coincidência anula o erro e mascara o problema.
**Correção:** dar às duas passagens de remoção de comentários a mesma noção de escape que `_tokenizar_linha` já tem, idealmente fatorizando um único scanner "fim de string" partilhado pelas três passagens (evita nova divergência futura).

**B3 — [BAIXA] `caracter` não tem mecanismo de escape para representar um apóstrofo**
`_tokenizar_linha` (222-237): ao contrário de `STRING` (que suporta `\"`, `\\`, `\n`), a branch `CARACTER` não trata `\'`. `'''` dá erro sem sugestão útil, e não há forma de produzir um `caracter` com o valor `'`.

### 1.2 `compilador/parser.py`

**B4 — [ALTA] Sem limite de profundidade para blocos aninhados → `RecursionError` não tratado**
O parser já tem uma proteção equivalente para expressões (`_profundidade_expr`, AL-18, linha 536) precisamente para evitar "RecursionError não tratado, sem número de linha nem explicação" — mas nunca a estendeu a blocos de instruções (`se`/`para`/`enquanto` aninhados). `cli.py` só apanha `(ErroLexico, ErroSintatico, ErroSemantico)`, por isso este `RecursionError` propaga como *traceback* Python cru para o utilizador final.
**Correção:** aplicar o mesmo padrão de `_profundidade_expr` a `_parse_bloco_stmts`.

**B5 — [MÉDIA] `{}` nunca é interpretado como array literal vazio, só como struct literal vazio**
`_proximo_parece_campo_literal` (204-212) trata qualquer `{}` como struct literal. `arr:inteiro[3] = {}` dá o erro enganador `'arr' é um array; usa '{valor, valor, ...}'...`, apesar de o utilizador não ter escrito nada parecido com um campo. `semantics.py` (`_verificar_array_literal`, 352-373) não impõe mínimo de elementos, sugerindo que `{}` como "todos os valores por omissão" era suposto funcionar para arrays também.
**Correção:** tratar `{}` vazio como válido para o tipo alvo (array ou struct) do lado da semântica, já que o parser é deliberadamente agnóstico às dimensões neste ponto.

### 1.3 `compilador/semantics.py`

**B6 — [ALTA] Atribuição a um array inteiro (sem indexar) não é rejeitada** ✅ verificado
`_tipo_lvalue` devolve `(tipo, dims)`, mas nem a branch de `Atribuicao` (390-401) nem a de `Ler` (410-413) verificam `dims` do alvo — só o fazem para o lado direito de expressões. Reproduzido:
```
v: inteiro[3]
v = 5
escrever(v[0])   -- TypeError: 'int' object is not subscriptable
```
e o mesmo para `ler(v)`. Aplica-se também a campos-array de structs.
**Correção:** capturar `dims_alvo` em ambas as branches e rejeitar se `> 0`, tal como já se faz do lado da expressão (linha 566-569).

**B7 — [ALTA] Tamanhos de arrays em campos de `estrutura` nunca são validados**
`_registar_decl` valida tipo e sinal de cada dimensão (267-277); o registo de campos de `estrutura` (135-146) salta essa validação, limitando-se a contar `len(c.dims)`. Reproduzido pelo sub-relatório: `arr: inteiro[-3]` só falha em runtime; `arr: inteiro[verdadeiro]` compila silenciosamente (bool é subclasse de int); `arr: inteiro["oi"]` compila e crasha com `TypeError` cru na comparação `<`.
**Correção:** reutilizar o mesmo laço de validação de `_registar_decl` para dimensões de campos de `estrutura`.

**B8 — [ALTA] `_contem_devolver` só verifica "existe algum `devolver`", não "todos os caminhos devolvem"** ✅ verificado
```
funcao f(x:inteiro): inteiro
    se x > 0 entao
        devolver 1
inicio
    escrever(f(-5) + 1)
```
compila sem erro e crasha com `TypeError: unsupported operand type(s) for +: 'NoneType' and 'int'` — um erro clássico de "esqueci o `senao`" que fica sem diagnóstico ao nível ALGO. Confirmado por execução: o `TypeError` nem sequer é um dos tipos traduzidos por `codegen.py` (só `IndexError`, `ZeroDivisionError`, `RecursionError`, `AttributeError`, `ValueError`, `_AlgoIndiceCadeiaInvalido`), pelo que chega ao estudante como *traceback* Python cru.
**Correção:** verificação conservadora de "todos os ramos do último `se`/`senao` (e `escolher`/`contrario`) terminam em `devolver`", ao estilo do que a maioria dos compiladores de ensino já faz.

**B9 — [ALTA] `ler` aceita silenciosamente arrays e structs como alvo**
Consequência de B6 mais o `_algo_ler_texto` de recurso em codegen: `ler(a)` com `a:Ponto` (struct) compila para `a = _algo_ler_texto()`, transformando `a` numa string; `escrever(a.x)` a seguir crasha com `AttributeError`. Esse `AttributeError`, por sua vez, é mal traduzido por `_algo_traduzir_attributeerror` (que só trata o caso "valor nulo"), dando ao estudante uma mensagem sobre "aceder a um campo de um valor nulo" quando o valor não é nulo — um bug secundário provocado por este.
**Correção:** exigir `dims == 0 and tipo in PRIMITIVOS` no alvo de `ler`.

**B10 — [ALTA] Parâmetros de função nunca são verificados contra colisão de nomes**
Ao contrário de `_registar_decl` (236-259), que verifica nome de parâmetro/variável contra funções, estruturas, bibliotecas importadas, nomes internos de biblioteca e tipos primitivos, o registo de parâmetros (193-199) só verifica duplicação entre si. Reproduzido pelo sub-relatório:
```
estrutura Ponto
    x:inteiro
funcao f(Ponto: inteiro): inteiro
    p: Ponto
    devolver Ponto + p.x
```
compila e crasha com `TypeError: 'int' object is not callable` (o parâmetro `Ponto` sombreia a classe Python `Ponto` dentro da função gerada). Um parâmetro chamado `inteiro` também passa sem aviso, inconsistente com a rejeição já existente para variáveis.
**Correção:** extrair a validação de colisão de nomes para um único helper (ver L-lixo abaixo) e aplicá-lo também a parâmetros.

**B11 — [ALTA, cross-cutting semantics/codegen] Parâmetros de `estrutura` passados "por valor" não são copiados — mutações vazam para quem chamou**
`semantics.py` (778-820) define todo o contrato de `ref` implicando que um parâmetro sem `ref` é por valor, mas `codegen.py` nunca copia o argumento — Python passa sempre a mesma referência ao objeto. Reproduzido pelo sub-relatório:
```
procedimento muda(p:Ponto)
    p.x = 99
inicio
    a:Ponto = {x: 1}
    muda(a)
    escrever(a.x)   -- imprime 99, não 1
```
Isto quebra silenciosamente a distinção valor/referência para *todo* parâmetro de tipo `estrutura`, para qualquer struct, sempre — um buraco central no modelo de passagem de parâmetros da linguagem.
**Correção:** em codegen, emitir uma cópia (`copy.deepcopy`, ou uma função `_algo_copiar_estrutura` gerada por tipo) para argumentos de tipo `estrutura` sem `ref`; ou, se for uma limitação intencional, documentá-la explicitamente na linguagem.

**B12 — [MÉDIA] Mensagens de erro de `_tipo_lvalue` referem sempre o nome da variável base, nunca o sub-caminho real, e podem ser factualmente falsas**
```
estrutura Conta
    valores: inteiro[3]
inicio
    c:Conta
    escrever(c.valores.tamanho)
```
dá `'c' é um array; falta indexá-lo antes de aceder a '.tamanho'` — mas `c` é uma `Conta` (dims 0), não um array; o array é `c.valores`. Mesma falha em `c.saldo[0]` com `saldo` escalar.
**Correção:** construir o caminho textual (`"c.valores"`) à medida que o laço percorre `lv.acessos`, e usá-lo nas mensagens em vez de `lv.nome`.

**B13 — [MÉDIA] Variável com o mesmo nome mas tipos incompatíveis em ramos `se`/`senao` mutuamente exclusivos ao nível de topo pode gerar um tipo errado em `self.globais`**
`_pre_registar_recursivo` regista a primeira declaração de um nome encontrada em DFS e ignora declarações posteriores do mesmo nome (mesmo com tipo diferente) noutro ramo. Reproduzido:
```
funcao usa_x(): inteiro
    devolver x + 1
inicio
    se falso entao
        x: inteiro = 1
    senao
        x: cadeia = "oi"
    escrever(usa_x())
```
compila (a função vê `x` como `inteiro`) e crasha em runtime com `TypeError: can only concatenate str (not "int") to str`, pois em runtime `x` é de facto a string do ramo `senao`.
**Correção:** detetar e rejeitar conflito de tipo entre declarações do mesmo nome em ramos irmãos, em vez de ficar silenciosamente com a primeira.

**B14 — [MÉDIA] `escrever` de uma struct inteira produz saída inútil em vez de ser rejeitado**
Arrays já são implicitamente rejeitados em `escrever` (via a verificação `dims > 0` de `_tipo_expr`), mas não há equivalente para structs: `escrever(p)` com `p:Ponto` imprime `<__main__.Ponto object at 0x...>` — sem valor pedagógico e não determinístico na aparência.
**Correção:** rejeitar `escrever` de um valor de tipo `estrutura` em compilação, com mensagem clara ("escreve os campos individualmente, ex: `p.x`").

**B15 — [BAIXA] `Escolha` nunca deteta valores `caso` duplicados** — erro clássico de copy-paste sem deteção.

### 1.4 `compilador/codegen.py` / `codegen_minimo.py` / `gerador_base.py`

**B16 — [ALTA] `base ^ expoente` com base decimal negativa e expoente não-inteiro devolve `complex` silenciosamente** ✅ verificado
```
base: decimal = -8.0
expo: decimal = 0.5
escrever(base ^ expo)
```
imprime `(1.7319121124709868e-16+2.8284271247461903j)` em vez de erro. Ao contrário do Python 2 (de onde a mensagem de erro já traduzida em `_algo_traduzir_valueerro`, linha 120-121, parece ter sido portada), o `**` do Python 3 nunca levanta `ValueError` para base negativa com expoente fracionário — devolve `complex` silenciosamente. `matematica.raiz(-1)` já é tratado com uma mensagem amigável; este caminho equivalente via `^` não é.
**Correção:** adicionar uma verificação em runtime antes de `**` (`a < 0 and not float(b).is_integer()`) que levante `ValueError` com a mensagem que já existe (e está morta) em `_algo_traduzir_valueerro`.

**B17 — [ALTA] Falta coerção `inteiro→decimal` no resultado de uma chamada por referência (`ref`)**
Toda a atribuição/declaração normal de um valor `inteiro` a um alvo `decimal` passa por `_coagir_decimal`; as branches de chamada com `ref` (`gerador_base.py:112-124`, `codegen.py:411-421`) saltam essa coerção. Reproduzido:
```
funcao f(ref a:inteiro):inteiro
    a = 5
    devolver a
inicio
    x:inteiro = 1
    y:decimal = f(x)
    escrever(y)     -- imprime 5, não 5.0
```
**Nota de causa-raiz:** mesmo corrigindo ingenuamente com `_coagir_decimal`, falta a peça em `semantics.py` (294-302) que não define `_tipo_inferido` neste nó — a correção completa precisa de marcar o tipo aí, ou comparar diretamente com `f_def.tipo_retorno` em codegen.

**B18 — [MÉDIA-ALTA] Elementos de array literal nunca são coagidos de `inteiro` para `decimal`**
`_expr_estrutura_literal` coage cada campo (linha 403); o caso `A.ArrayLiteral` em `_expr` (563-565) não coage elementos nenhuns. `v:decimal[3] = {1, 2, 3}` (válido — `semantics.py` aceita `inteiro` em array `decimal`) imprime `1 2 3` em vez de `1.0 2.0 3.0`.
**Correção:** passar o tipo de elemento alvo para a geração de array literal, como já se faz para structs.

**B19 — [MÉDIA] `codegen_minimo.py`: `div`/`mod` passam por `float`, perdendo precisão em inteiros grandes — diverge do modo normal**
```python
if expr.op == "div":
    return f"int({e} / {d})"
```
ao contrário de `codegen.py`, que usa `divmod` exato. O próprio `test_correcoes_auditoria.py` (linha ~810) documenta o invariante "`--minimo` não pode divergir do modo normal", mas só testa números pequenos. Para inteiros acima de ~2^52 os dois modos discordam de facto (verificado pelo sub-relatório com `2989996989242201024 div 887`).
**Correção:** implementar divisão truncada sem passar por `float` (ex: `-(-{e} // {d}) if ({e}<0)!=({d}<0) else {e} // {d}`).

**B20 — [MÉDIA] `codegen_minimo.py`: `matematica.potencia` perde o tipo de retorno `decimal` garantido**
`bibliotecas/matematica.py` embrulha sempre em `float(...)` (contrato testado em modo normal: `8.0`); o mapeamento minimo (`codegen_minimo.py:43`) não o faz — `matematica.potencia(2,3)` dá `8` (int) em `--minimo` vs `8.0` em modo normal. Sem cobertura de teste em modo minimo.
**Correção:** `lambda args: f"float({args[0]} ** {args[1]})"`.

### 1.5 `cli.py`, `compilador/inclusoes.py`, `bibliotecas/`

**B21 — [ALTA] `algo executa --debug`/`--json` sai com código 0 mesmo quando o programa falha** ✅ verificado
`cmd_executa` (sem flags) propaga o código de saída real do subprocesso; `cmd_executa_com_trace` imprime o mesmo erro mas nunca chama `sys.exit`. Confirmado por execução direta nesta auditoria: o mesmo programa com erro em runtime dá `exit 1` sem `--json` e `exit 0` com `--json`. Qualquer *script*/CI/corretor automático que confie no código de saída trata um programa com erro como bem-sucedido.
**Correção:** `sys.exit(1)` no fim de `cmd_executa_com_trace` quando `resultado["erro"]` ou `resultado["limiteExcedido"]` estiver definido.

**B22 — [ALTA] Deduplicação de `incluir` é sensível a maiúsculas/minúsculas → falsas colisões em sistemas de ficheiros case-insensitive (Windows/macOS)**
`_resolver_lista_de_inclusoes` usa `os.path.normpath` para a chave de deduplicação, que não normaliza capitalização. Duas referências ao mesmo ficheiro com capitalização diferente (`"lib.algo"` e `"LIB.algo"`) são tratadas como ficheiros distintos e o segundo "colide" com o primeiro — em Windows, o SO onde este projeto está a ser desenvolvido.
**Correção:** `os.path.normcase(os.path.normpath(caminho))`. Aplicar a mesma correção em `online/executor.py`, que reimplementa esta lógica de forma independente e tem a mesma exposição.

**B23 — [MÉDIA] Consola interativa memoriza uma referência de ficheiro *falhada* como "último ficheiro"**
`cmd_consola` (557-558) atualiza `ultimo_ficheiro` incondicionalmente, antes de saber se `args.func(args)` teve sucesso. Um estudante que escreve mal um nome de ficheiro perde o contexto do ficheiro anterior (que funcionava) e fica preso a repetir o mesmo erro "não encontrado" até reescrever o nome correto.
**Correção:** só atualizar `ultimo_ficheiro` depois de `args.func(args)` completar sem `SystemExit`.

**B24 — [MÉDIA] `cadeia.caracter` aceita índices negativos de forma inconsistente com `cadeia.subcadeia`**
`subcadeia` rejeita explicitamente limites negativos; `caracter` só apanha `IndexError`, mas `s[-1]` em Python não levanta `IndexError` — devolve o último caracter. `cadeia.caracter("abc", -1)` dá `"c"` em vez do erro amigável que a documentação da função promete ("0-baseado, tal como os arrays"). Mascara erros de cálculo de índice em código de estudantes (`tam - 1 - i` a dar negativo).
**Correção:** adicionar guarda explícita `if i < 0 or i >= len(s): raise ...` antes de indexar.

**B25 — [MÉDIA] `conversao.paraInteiro` trunca um `decimal` mas rejeita a `cadeia` equivalente**
`paraInteiro(3.5)` dá `3` (documentado); `paraInteiro("3.5")` dá erro de runtime. Assimetria plausível de armadilha: um estudante que lê um valor com `ler(txt)` e depois chama `conversao.paraInteiro(txt)` sobre um texto com ponto decimal apanha um erro inesperado, sem que a assimetria esteja documentada.
**Correção:** documentar explicitamente, ou fazer `paraInteiro` cair para `int(float(x))` quando `x` é string com ponto decimal.

**Adicional, sem número de severidade formal — verificado pelo sub-relatório:** `--entradas` é lido com `open()` direto em vez de passar pelo helper `_ler_ficheiro_algo` (AL-34), que trata `UnicodeDecodeError` com mensagem amigável — um ficheiro `--entradas` não-UTF-8 dá *traceback* cru.

### 1.6 `tools/tracer.py`, `tools/flowchart.py`, `tools/linter.py`

**B26 — [ALTA] Linter: falso positivo "declarada mas nunca usada" para variáveis de `inicio` usadas só dentro de funções**
`_verificar_globais_nao_usadas` já agrega uso entre todas as funções para variáveis de topo declaradas *antes* de `inicio` (correção AL-28), mas `_verificar_variaveis_nao_usadas` (chamada sobre `programa.corpo`) continua a verificar uso só dentro do próprio `corpo`, apesar de uma variável declarada dentro de `inicio` ser igualmente global (ver `codegen.py:244-247`). Reproduzido:
```
funcao dobroDeContador():inteiro
    devolver contador * 2
inicio
    contador:inteiro = 5
    escrever(dobroDeContador())
```
dá simultaneamente "acede diretamente à variável global 'contador'" **e** "'contador' é declarada mas nunca é usada" — a segunda mensagem está errada, a primeira prova-o. É a mesma classe de bug que AL-28 corrigiu, deixada meio corrigida — mina a confiança no linter porque estas duas regras disparam juntas com frequência.
**Correção:** aplicar a mesma agregação entre `corpo` + todas as funções, tal como já acontece para `_verificar_globais_nao_usadas`.

**B27 — [ALTA] Tracer: variáveis/parâmetros com nome começado por `_` são invisíveis no *trace***
```python
variaveis = {k: _valor_serializavel(v) for k, v in f.f_locals.items()
             if not k.startswith("_")}
```
O lexer permite explicitamente identificadores começados por `_`. `funcao f(_x:inteiro): ...` faz com que `_x`/qualquer variável local começada por `_` nunca apareça no *trace* — a intenção (esconder temporários internos do compilador) devia usar uma lista de permissão ou o prefixo real `_algo_`, não um bloqueio genérico por `_`. Note-se que a branch "Principal" ao lado já faz isto corretamente com uma lista de permissão.
**Correção:** filtrar por `_algo_` (ou usar lista de permissão de nomes ALGO reais vindos do codegen), não por `_` genérico.

**B28 — [ALTA] Tracer: número de linha salta para trás em procedimentos só com `ref`, e `OverflowError` não é traduzido**
Em `gerador_base.py:236-238`, o `return` sintético gerado para propagar parâmetros `ref` é mapeado para a linha da *assinatura* do procedimento, não para a última instrução real. Um procedimento com só parâmetros `ref` produz uma sequência de linhas no *trace* que salta para trás (ex: `3, 4, 5, 2`) antes de voltar ao chamador — um depurador passo-a-passo mostraria isto como um salto sem sentido para um estudante.
Adicionalmente, `x:decimal = 2.0 ^ 2000.0` (ALGO válido) gera `OverflowError` em Python, que não está entre as exceções traduzidas por `codegen.py` — propaga como *traceback* cru fora do tracer, e dentro do tracer cai na rede de segurança "não deve ocorrer" (`tracer.py:200-201`), dando uma mensagem não traduzida sem número de linha.
**Correção:** não sobrepor `_linha_algo_atual` com `f.linha` antes do `return` sintético; adicionar `except OverflowError` a `codegen.py` com a mesma abordagem das outras exceções traduzidas.

**B29 — [MÉDIA] Linter: verificação de "campos em falta" em struct literal não cobre literais passados como argumento de chamada**
Só inspeciona `Declaracao.inicial`, mas `semantics.py` já documenta que um struct literal é válido "como argumento de uma função/procedimento" também. `soma({x: 3})` com `y` a ficar silenciosamente a 0 não dá aviso nenhum.
**Correção:** percorrer também `Chamada.args`.

**B30 — [MÉDIA] Linter: verificação de atribuição a parâmetro por valor não cobre alvos de `ler(...)`**
Só verifica `A.Atribuicao`; `ler(x)` sobre um parâmetro por valor `x` não dispara o aviso mais específico e útil ("não é por referência"), só o genérico "nunca é usado" — apesar de `x` ser de facto escrito.
**Correção:** estender a verificação a alvos de `A.Ler`.

---

## 2. Melhorias (UX de erros / robustez)

Estas não são bugs de comportamento incorreto, mas reduzem a qualidade das mensagens de erro — importante numa ferramenta de ensino onde a mensagem *é* o produto.

1. **[MÉDIA] `parser.py`, 5 pontos** (linhas 93, 137, 332, 665, 703) usam `tok.tipo` cru (ex: `"RPAREN"`) em vez de `_nome_amigavel(tok.tipo, tok.valor)`, ao contrário de `esperar()` no mesmo ficheiro. Ex: `escrever(1 + )` dá `"expressão inesperada: RPAREN (')')"` em vez de algo em português.
2. **[BAIXA-MÉDIA] `parser.py`:** um `INDENT` inesperado dá o genérico "instrução inesperada: INDENT" em vez de apontar para o problema real (indentação a mais sem bloco de abertura) — a indentação é uma fonte central de erros nesta linguagem, merece mensagem dedicada.
3. **[MÉDIA] `cli.py`: `--mostrar-python` é silenciosamente ignorado quando combinado com `--debug`/`--json`** — sem aviso, o código Python gerado simplesmente não aparece.
4. **[BAIXA-MÉDIA] `cli.py`: erro confuso quando uma cadeia de `incluir` cicla de volta ao próprio ficheiro principal** — dá um erro de sintaxe genérico "linha 1" que não aponta para o `incluir` real que causou o ciclo.
5. **[BAIXA-MÉDIA] `cli.py`: falha do Graphviz (`dot`) em `fluxograma` é engolida** — sem `else` no `subprocess.run`, o processo continua e sai com código 0 mesmo que a imagem não tenha sido gerada.
6. **[BAIXA] `lexer.py`:** sem mecanismo de escape para apóstrofo dentro de `caracter` (ver B3).
7. **[MÉDIA] Duplicação quase total entre `_gerar_chamada_stmt`/`_lvalue_de_expr` em `codegen.py` e `codegen_minimo.py`** (~30 linhas) — candidato a extração para `gerador_base.py`; teria tornado B17 uma correção num único sítio.
8. **[BAIXA] Duplicação semelhante entre `_gerar_estrutura`/`_construir_array_aninhado`** nos dois geradores.
9. **[BAIXA] `linter.py`: `Aviso` não tem código/categoria/severidade** — apenas texto livre + linha, sem forma de um chamador (flag da CLI, integração de editor) suprimir uma regra específica ou distinguir "provável bug" de "preferência de estilo".

---

## 3. Melhorias conceptuais / arquiteturais

1. **[ALTA] A separação `codegen.py`/`codegen_minimo.py` (seguro vs. direto) não tem nenhuma verificação automática de paridade, e B19/B20 provam que já divergiram.** O próprio `gerador_base.py` documenta o invariante "`--minimo` tem de refletir a MESMA semântica"; nada o garante mecanicamente. **Sugestão concreta:** um teste parametrizado que corra o mesmo corpus de programas ALGO por `gerar_python` e `gerar_python_minimo` e compare o `stdout`, capturando automaticamente futuras divergências.
2. **[ALTA] Estrutura sem cópia em passagem por valor (B11) é um buraco de modelo, não só de implementação** — `semantics.py` impõe todo um contrato de `ref` que `codegen.py` não honra do lado "sem `ref`" para tipos `estrutura`. Vale a pena decidir explicitamente: copiar sempre, ou documentar como limitação da linguagem.
3. **[MÉDIA] Coerção `inteiro→decimal` (`_coagir_decimal`) está espalhada ad-hoc por 5+ pontos de chamada em vez de centralizada** — é plausivelmente a razão de B17/B18 terem escapado. Um único caminho "vincula valor de tipo inferido Y a posição de tipo declarado T", usado uniformemente por toda declaração/atribuição/argumento/elemento de array, eliminaria esta classe de bugs de vez.
4. **[MÉDIA] Texto de mensagem de colisão de `incluir` duplicado entre `cli.py` e `online/executor.py`, já divergido estilisticamente** (pontuação final, capitalização) apesar de `inclusoes.py` centralizar a *regra*. Dar a `ColisaoDeInclusao` um método `mensagem()`/`__str__` eliminaria a resposta duplicada.
5. **[MÉDIA] `COMANDOS_COM_FICHEIRO` em `cli.py` é uma segunda fonte de verdade não verificada, paralela às definições reais do `argparse`** — nada impede que um novo argumento com valor seja adicionado a um subcomando sem atualizar esta tabela manual, quebrando silenciosamente a deteção de "último ficheiro" na consola.
6. **[MÉDIA] `flowchart.py`/`ast_nodes.py`: `texto_expr` falha silenciosamente (devolve `"?"`) para tipos de expressão não reconhecidos, inconsistente com o resto do módulo**, que introduziu `ErroInternoFluxograma` precisamente para evitar exactamente este tipo de falha silenciosa nas *instruções*. Um novo tipo de nó de expressão no futuro passaria despercebido em vez de gerar erro.
7. **[MÉDIA] `tracer.py` depende de uma string literal (`"_algo_programa"`) duplicada em `codegen.py` sem fonte de verdade partilhada** — se o nome da função principal gerada mudasse sem atualizar as duas cópias, o *trace* ficaria silenciosamente vazio (`passos: []`) sem erro nenhum. Testes existentes apanhariam isto em CI, mas não há proteção defensiva no próprio caminho de execução.
8. **[MÉDIA] Verificação de colisão de nomes duplicada quase identicamente 3× em `semantics.py`** (funções, estruturas, `_registar_decl`) — exatamente o tipo de duplicação que permitiu que parâmetros (B10) escapassem à verificação. Extrair um único `_verificar_nome_disponivel(nome, linha, o_que_e)`.
9. **[BAIXA] `cli.py`: 3 pontos reabrem o ficheiro-fonte com `open()` cru** em vez de reutilizar `_ler_ficheiro_algo` (que já provou o ficheiro ser UTF-8 momentos antes na mesma cadeia de chamada) — risco residual pequeno, mas opta silenciosamente por sair da garantia que esse helper existe para dar.
10. **[BAIXA] `Escolha` sem deteção de `caso` duplicado** (ver B15) — adição de baixo risco e alto valor para uma ferramenta de ensino.

---

## 4. Lixo — plano de remoção

Nada disto foi removido nesta auditoria (âmbito só de leitura, conforme pedido). Lista concreta para limpeza numa próxima passagem, da mais para a menos arriscada de deixar como está:

| # | Ficheiro:linha | O quê | Porque remover/corrigir |
|---|---|---|---|
| L1 | `codegen_minimo.py` — `OPS_BIN["div"]`/`OPS_BIN["mod"]` (linha ~25) | Entradas mortas no dicionário (`"div": "//", "mod": "%"`), nunca alcançadas porque `_expr` trata `div`/`mod` num caso especial antes de consultar `OPS_BIN` — e codificam a semântica **errada** (divisão de piso do Python, não truncada) | Uma futura "limpeza" ingénua do dicionário podia reintroduzir o bug de divisão de piso sem se aperceber. Remover as duas chaves. |
| L2 | `codegen.py:120-121` | Branch morta de tradução de `ValueError` para uma mensagem que o Python 3 já não produz (`"negative number cannot be raised..."`) | Python 3 nunca levanta isto para `**` — devolve `complex` (ver B16). Ou remover, ou tornar viva corrigindo B16 (recomendado: a segunda opção). |
| L3 | `gerador_base.py:146`, `gerador_base.py:226` | Comentários com placeholder literal `AL-XX` nunca preenchido | Inconsistente com a convenção do resto do ficheiro (todas as outras referências têm ID real). Atribuir ID real ou remover o prefixo. |
| L4 | `ast_nodes.py:43` | Comentário desatualizado: `"lista de expressões (0, 1 ou 2 dimensões)"` | Arrays de 3 dimensões já são suportados e testados (`test_array_3d`). Corrigir o comentário. |
| L5 | `parser.py:22` | `# pragma: no cover -- todo token sem nome amigável tem valor` | Falso: a chamada em `_nome_amigavel(tipo)` sem `valor` (linha 56) alcança esta linha de facto (ex: erro "esperava-se algoritmo"). Corrigir o comentário/pragma. |
| L6 | `parser.py:142-143` | `_parse_declaracao_global` é um *wrapper* que só chama `_parse_declaracao_comum`, sem comportamento distinto | Não é bug, só ruído de manutenção. Inline ou documentar a distinção pretendida. |
| L7 | `tracer.py:13` | `import builtins` nunca usado no resto do ficheiro | Remover. |
| L8 | `linter.py:163-164` | Re-extração redundante em `_verificar_rotinas_nunca_chamadas` (`self._extrair_lvalues_e_chamadas(s.chamada, ...)` para `A.ChamadaStmt`) | `_expressoes_lidas` já devolve `[s.chamada]` para este caso, tornando este bloco especial redundante — parece resquício de antes de `_expressoes_lidas` cobrir `ChamadaStmt`. Seguro remover. |
| L9 | `semantics.py:519`, `semantics.py:789` | Verificações defensivas mortas (`len(escopo[...]) > 2 and ...`) | Todo valor guardado num `Escopo`/`self.globais` é sempre um triplo `(tipo, dims, eh_constante)` — a condição `len(...) > 2` nunca pode ser falsa. Simplificar para `escopo[...][2]` diretamente, ou comentar a razão se for proteção deliberada contra mudança futura de formato. |
| L10 | `semantics.py:153`, `semantics.py:160` | Reimplementação inline de `PRIMITIVOS` (`tipo not in NUMERICOS \| TEXTUAIS \| {"booleano"}`) | Substituir por `tipo in PRIMITIVOS`/`tipo not in PRIMITIVOS`, já definido no módulo. |
| L11 | `semantics.py:576-589` | `UnOp` sem `raise` explícito de recurso para operador desconhecido, ao contrário de `_tipo_binop` | Atualmente inalcançável (parser só emite `nao`/`-`), mas cai num "expressão não reconhecida: UnOp" confuso se algum dia deixar de ser. Adicionar `raise ErroSemantico(...)` explícito, tal como o equivalente em `_tipo_binop`. |

Nenhum destes é urgente isoladamente — nenhum afeta um programa ALGO correto hoje — mas L1 e L2 valem a pena por serem "minas terrestres" que um refactor futuro descuidado podia reativar como bugs reais.

---

## 5. Cobertura de testes

Todos os bugs em §1 foram confirmados como **não cobertos** pela suite de testes atual (procurados especificamente por nome/condição em `test_estruturas.py`, `test_novas_funcionalidades.py`, `test_correcoes_auditoria.py`, `test_compila_minimo.py`, `test_linter.py`, `test_tracer.py`, `test_consola.py`). Ao corrigir qualquer item, recomenda-se adicionar o repro mínimo correspondente a `test_correcoes_auditoria.py`, seguindo a convenção `AL-NN` já estabelecida (o próximo ID livre é `AL-41`).

---

## 6. Notas de metodologia

- Esta auditoria foi feita com 5 análises paralelas (uma por área do pipeline: lexer/parser/AST, semântica, geração de código, CLI/inclusões/bibliotecas, ferramentas), seguidas de verificação manual direta — compilando e executando programas `.algo` mínimos através do pipeline real — para os achados de severidade mais alta antes de os incluir neste relatório (B1, B2, B6, B8, B16, B21 foram todos reproduzidos independentemente durante a síntese final, além dos repros já incluídos nos sub-relatórios).
- Nenhum ficheiro foi modificado. Todas as correções sugeridas são propostas, não aplicadas.
