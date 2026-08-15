# Auditoria profunda — algo_lang (v1)

## Estado: os 31 bugs (secção 1) e o lixo trivial (secção 4, L1-L3) estão corrigidos

Todos os `B1`–`B31` foram corrigidos e verificados empiricamente (repro
antes/depois, a correr o compilador real ou, para a extensão VS Code, o
motor real de tokenização `vscode-textmate`/`vscode-oniguruma`), com teste
de regressão para cada um em `algo_lang/tests/test_correcoes_auditoria.py`
(secção "Segunda auditoria", comentários `AL-72` a `AL-99`). As secções 2
(melhorias UX) e 3 (conceptuais/arquiteturais) ficaram **por decidir** —
não foram implementadas nesta passagem, por serem mudanças de design com
mais superfície de decisão, não simples correções de bug.

Suite de testes: baseline original 420 passed / 89 failed (89 falhas
pré-existentes de ambiente Windows, ver secção 6) → agora **475 passed /
77 failed**, com os mesmos 77 falhas de ambiente inalteradas (nenhuma
delas nova nem causada por estas correções) e zero regressões em qualquer
passo intermédio. As 12 falhas a menos não são testes nomeados
"ambiente" que afinal passaram a passar — eram sintoma real de B18/B19
(consola quebrada por `shlex`/`sys.exit`), confirmando que uma fração do
que parecia "só ambiente" era bug real.

---

Auditoria de código a **toda** a pasta `algo_lang/`: compilador (lexer, parser,
AST, semântica, codegen), CLI, bibliotecas padrão, ferramentas (tracer,
flowchart, linter) e a extensão VS Code. Objetivo: identificar bugs,
melhorias de código e melhorias conceptuais antes de fechar a versão 1 do
compilador.

Esta é a **segunda** auditoria deste tipo. A primeira (ficheiro entretanto
apagado, ver histórico git) corrigiu 30 bugs (B1–B30, comentados no código
como `AL-41` a `AL-71`) em lexer/parser/semantics/codegen/cli/tools. Esses
bugs **não são repetidos aqui**; esta auditoria focou-se em encontrar
problemas da mesma família que escaparam à primeira passagem, mais território
nunca antes auditado (a extensão VS Code).

Ver secção 6 para metodologia.

## Resumo executivo

**31 bugs encontrados** (12 ALTA, 14 MÉDIA, 5 BAIXA), a maioria com repro
concreto confirmado a correr o compilador real (não só inspeção de código).
Os dois mais críticos foram re-verificados manualmente nesta sessão,
diretamente contra o compilador:

- **B4** — um segundo bloco `inicio` no mesmo programa é aceite em silêncio
  e **substitui** o primeiro (o primeiro bloco inteiro desaparece, sem erro
  nenhum). Confirmado: `executar()` do programa de teste devolve só a saída
  do segundo bloco.
- **B12** — um parâmetro `ref a:decimal` aceita uma variável `inteiro` do
  chamador e devolve-lhe um valor decimal, corrompendo silenciosamente o seu
  tipo declarado. Confirmado: `x:inteiro = 5` fica com o valor Python `5.5`
  depois de passada a um `ref` decimal.
- **B13** — `matematica.potencia` com base negativa e expoente fracionário
  despeja um traceback Python cru (`TypeError`) ao estudante. Encontrado
  **independentemente por dois agentes de auditoria diferentes** (codegen e
  bibliotecas), o que reforça a confiança no achado.
- **B18/B19** — na consola interativa, colar um caminho Windows sem aspas
  (`\`) corrompe-o (`shlex` em modo POSIX trata `\` como escape), e mesmo
  sem esse problema, `executa` bem-sucedido nunca atualiza "o último
  ficheiro usado" por causa de um `sys.exit(0)` incondicional. Isto explica
  uma fração significativa das falhas de teste já conhecidas neste ambiente
  Windows — não são só "falhas de ambiente", há bugs reais por trás.
- **B25** — o tracer (`executa --debug`/`--json`) pode mostrar a consola do
  programa a "andar para trás" quando o corpo `inicio` é uma única chamada
  a função/procedimento — sobrescreve o passo errado da lista.
- **B27/B28** — a extensão VS Code nunca tinha sido auditada: a palavra-chave
  `nulo` não tem highlighting nenhum, e qualquer acesso a campo de estrutura
  (`no.valor`) é colorido como se fosse uma chamada de biblioteca.

Prioridade recomendada para fechar a v1: os 12 bugs ALTA primeiro (secção 1),
com destaque para B4, B12, B18/B19 por afetarem correção silenciosa de
programas comuns, não apenas casos extremos.

---

## 1. Bugs

Convenção: `[SEVERIDADE] ficheiro:linha — descrição`. IDs `B1`–`B31`,
sequenciais, sem relação com os `AL-NN`/`B1`-`B30` da auditoria anterior
(esses já estão corrigidos).

### 1.1 `compilador/lexer.py`

- [x] **B1** [MÉDIA] `lexer.py:222-225` — só o espaço é tratado como
  separador fora da indentação; um **tab a meio de uma linha** (ex.
  `x:inteiro\t=\t5`, comum ao colar de um editor com tabs de alinhamento)
  dispara `ErroLexico("caractere inesperado '\t'")` em vez de ser ignorado
  como whitespace.
- [x] **B2** [MÉDIA] `lexer.py:177-184` — a indentação pode **saltar mais de
  um nível de uma vez** sem erro (ex. `se ... entao` seguido de um corpo
  indentado 2 unidades em vez de 1, no mesmo nível de aninhamento) — não há
  verificação de que cada novo bloco só aumenta exatamente 1 unidade
  relativamente ao nível envolvente.
- [x] **B3** [BAIXA] `lexer.py:268-281` — `1.` é aceite como `1.0`, mas
  `.5` **não** é reconhecido como decimal (tokeniza como `DOT`+`INT`), dando
  um erro sintático confuso a jusante em vez de uma mensagem sobre o dígito
  em falta.

### 1.2 `compilador/parser.py` / `compilador/ast_nodes.py`

- [x] **B4** [ALTA] `parser.py:77-99` (`parse_programa`) — **um segundo
  bloco `inicio` é aceite silenciosamente e substitui o primeiro**, sem erro
  nenhum. `while not self.ver("EOF")` trata `INICIO` como mais um ramo do
  loop, sem verificar se `corpo` já tinha sido preenchido. Confirmado
  empiricamente nesta sessão: o Python gerado só contém o segundo bloco — o
  primeiro desaparece sem aviso. Um `raise` explícito em caso de segundo
  `inicio` resolve.
- [x] **B5** [ALTA] `parser.py:584-630` (`_parse_nao`, `_parse_unaria`,
  `_parse_potencia`) — cadeias longas de `nao`, `-` unário ou `^` **não são
  cobertas pelo limite de profundidade** (`LIMITE_PROFUNDIDADE_EXPR`, que só
  é incrementado em `_parse_expr`), e provocam `RecursionError` não tratado
  (traceback Python cru — `cli.py` só apanha `ErroLexico`/`ErroSintatico`/
  `ErroSemantico`). Confirmado por repro com 500–1000 operadores encadeados.
  Mesma classe de bug que `LIMITE_PROFUNDIDADE_EXPR` foi introduzido para
  prevenir, mas não cobre estes 3 pontos de recursão direta.
- [x] **B6** [MÉDIA] `ast_nodes.py:266-267` (`coletar_identificadores`) —
  ao reportar colisão de nome de **campo de estrutura** com palavra
  reservada do Python, usa a linha da `estrutura X` (`e.linha`) em vez da
  linha real do campo (`c.linha`), que já está disponível e correta.

### 1.3 `compilador/semantics.py`

- [x] **B7** [ALTA] `semantics.py:342-351` (`_registar_decl`) — o **tamanho
  declarado de um array nunca é validado contra o número de elementos do
  literal** de inicialização. `v:inteiro[5] = {1,2,3}` compila sem erro; o
  Python gerado ignora o tamanho declarado e cria um array de 3 elementos,
  dando `IndexError` confuso mais tarde em `v[4]`.
- [x] **B8** [ALTA] `semantics.py:442,465` (`_verificar_estrutura_literal` /
  `_verificar_array_literal`) — **literais de estrutura aninhados são
  sempre rejeitados**, mesmo quando o tipo esperado é conhecido pelo
  contexto: nem um literal `{...}` dentro doutro literal de estrutura
  (`r:Retangulo = {canto: {x: 5}}`), nem um literal de estrutura como
  elemento de um array (`v:Ponto[2] = {{x:1}, {x:2}}`) compilam — dão "não
  há informação suficiente para saber que forma se espera". A propagação do
  tipo esperado ("hole-filling") só está implementada em 2 dos ≥4 sítios que
  precisam dela (ver melhoria conceptual em 3).
- [x] **B9** [MÉDIA] `semantics.py:959-965` — a deteção de `ref` duplicado
  numa chamada não cobre o **mesmo campo de estrutura passado duas vezes**
  (`trocar(p.x, p.x)` compila sem erro), apesar do nome do campo ser
  estaticamente comparável (ao contrário de `v[i]` vs `v[j]`, que
  corretamente não é sinalizado).
- [x] **B10** [MÉDIA] `semantics.py:193-219` (`_pre_registar_recursivo`) —
  mensagem de erro **errada** quando um bloco aninhado do corpo principal
  redeclara uma variável **global** com tipo diferente: mostra a mensagem
  pensada para "conflito entre ramos irmãos" em vez de "variável já
  declarada" (que aparece corretamente se o tipo repetido for igual).
- [x] **B11** [MÉDIA] `semantics.py:624-637` — deteção de `caso` duplicado
  não normaliza tipos compatíveis com o mesmo valor: `caso "a"` seguido de
  `caso 'a'` (cadeia vs caracter), ou `caso 1` seguido de `caso 1.0`
  (inteiro vs decimal), não são detetados como duplicados apesar de serem o
  mesmo valor em runtime — o segundo ramo fica inalcançável sem aviso.

### 1.4 `compilador/codegen.py` / `codegen_minimo.py` / `gerador_base.py`

- [x] **B12** [ALTA] `semantics.py:977` (efeito visível no Python gerado por
  `codegen.py:_gerar_lista_args`) — **parâmetros `ref` aceitam alargamento
  de tipo** (a mesma verificação "larga" usada para passagem por valor,
  `_compativel`, é reaproveitada sem alteração para `ref`), corrompendo
  silenciosamente a variável do chamador. Confirmado nesta sessão: `x:inteiro
  = 5` passado a `ref a:decimal` fica com o valor Python `5.5` depois da
  chamada. O mesmo problema existe com `cadeia`/`caracter` (pode devolver
  string com mais de 1 símbolo a uma variável `caracter`).
- [x] **B13** [ALTA] `bibliotecas/matematica.py:14-20`/`:19` — `matematica.
  potencia(base, exp)` com base negativa e expoente fracionário faz
  `float(base ** exp)`, e `base ** exp` do Python devolve `complex` nesse
  caso, logo `float(complex)` levanta `TypeError` — não capturado pelo
  tratamento de exceções gerado (`_algo_traduzir_valueerro` só cobre
  `ValueError` e afins), resultando em traceback cru. O operador `^` já tem
  exatamente esta proteção (`_algo_pot`, comentário AL-57/B16); a função de
  biblioteca é um caminho gémeo que não a reutiliza. **Encontrado
  independentemente por dois agentes de auditoria diferentes** (secções
  codegen e cli/bibliotecas), confirmando o achado.
- [x] **B14** [ALTA] `codegen_minimo.py:25` (`OPS_BIN["^"] = "**"`) — em
  modo `--minimo`, `^` mapeia diretamente para `**` nativo, sem a proteção
  de `_algo_pot`. `(-8.0) ^ 0.5` corre **sem exceção nenhuma** e imprime um
  número complexo cru — o pior cenário possível (nem erro nem resultado
  correto), e inconsistente com o próprio modo normal e com o resto de
  `--minimo` (onde `matematica.potencia` pelo menos levanta `TypeError`
  nativo via `float(...)`).
- [x] **B15** [MÉDIA] `codegen.py:522-529` e `codegen_minimo.py:192-199`
  (`_construir_array_aninhado`) — para arrays multidimensionais, a
  **dimensão interior pode ser avaliada mais de uma vez** (a compreensão de
  listas Python aninhada reavalia a expressão da dimensão interior a cada
  iteração da exterior), com efeito duplicado se essa expressão tiver
  efeitos laterais. Mesma classe de bug já corrigida para `para...passo`,
  não replicada aqui. Agravado por esta função estar **duplicada** entre os
  dois ficheiros em vez de partilhada via `gerador_base.py`.
- [x] **B16** [MÉDIA] `codegen.py:354-397` (`_gerar_estrutura`) — o mapa de
  linhas do tracer fica **errado durante construção/comparação de
  estruturas**: `__init__`/`__eq__` gerados ficam fixados à linha da
  definição `estrutura X`, não à linha real de uso em runtime, injetando
  passos espúrios no trace `--debug`/`--json` sempre que há `==` entre
  estruturas.
- [x] **B17** [MÉDIA] `codegen_minimo.py:274-330` — vários pontos (ex.
  `_lvalue_de_expr`) assumem, com o comentário "`semantics.py` já valida
  isto", que a verificação de tipos correu — **falso** para `--minimo`, que
  deliberadamente salta `verificar()`. Um programa sintaticamente válido mas
  semanticamente inválido pode fazer o **próprio compilador** rebentar em
  tempo de compilação (`ErroSemantico`/erro interno), contradizendo o
  contrato do `--minimo` ("gera sempre Python, falha só a correr").

### 1.5 `cli.py`, `compilador/inclusoes.py`, `bibliotecas/`

- [x] **B18** [ALTA] `cli.py:549` — `shlex.split(linha)` na consola
  interativa usa modo POSIX por omissão, em que `\` é caráter de escape:
  colar um caminho Windows sem aspas (`C:\Users\...\prog.algo`, comum ao
  copiar do Explorador) **corrompe o caminho** (as barras desaparecem), e a
  consola reporta "ficheiro não encontrado" sem qualquer pista da causa
  real. Confirmado como a causa raiz de várias falhas de
  `test_consola.py` neste ambiente Windows.
- [x] **B19** [ALTA] `cli.py:188` (`cmd_executa`) — `sys.exit(resultado.
  returncode)` corre **incondicionalmente**, mesmo em sucesso (`returncode
  == 0`). Como a consola só atualiza `ultimo_ficheiro` depois do bloco
  `except SystemExit: continue`, o comando `executa`/`e` (o mais usado)
  **nunca memoriza o último ficheiro**, mesmo depois de correr com sucesso —
  quebrando a funcionalidade "reutiliza o último ficheiro" precisamente para
  o caso mais comum.
- [x] **B20** [MÉDIA] `cli.py:220-221` — leitura do ficheiro de
  `--entradas` não tem o tratamento de `UnicodeDecodeError` que
  `_ler_ficheiro_algo` já tem para o `.algo` principal; um ficheiro de
  entradas noutra codificação dá traceback cru.
- [x] **B21** [MÉDIA] `bibliotecas/conversao.py:31-43` —
  `conversao.paraInteiro("inf")`/`"Infinity"` escapa ao tratamento interno
  de `OverflowError` (só o `except ValueError` interno está preparado) e
  acaba com a mensagem genérica de "overflow numérico" em vez de "o texto
  não pode ser convertido para um número inteiro".
- [x] **B22** [MÉDIA] `bibliotecas/matematica.py:36-39` —
  `matematica.aleatorio(a, b)` com `a > b` mostra o texto interno do Python
  (`"empty range in randrange(5, 3)"`, incluindo um número que não
  corresponde a nenhum argumento escrito pelo estudante) em vez de uma
  mensagem amigável dedicada.
- [x] **B23** [BAIXA] `cli.py:242-244`, `cli.py:323-324` — releem
  `args.ficheiro` diretamente com `open()`, ignorando `_ler_ficheiro_algo`
  (e o seu tratamento de `UnicodeDecodeError`), apesar do conteúdo já ter
  sido lido e validado momentos antes.
- [x] **B24** [BAIXA] `cli.py:353-374` — `executa --entradas` sem valor
  (esquecendo o nome do ficheiro) é interpretado como falta do ficheiro
  principal quando há `ultimo_ficheiro`, dando um erro do `argparse` que não
  aponta para a causa real.

### 1.6 `tools/tracer.py`, `tools/flowchart.py`, `tools/linter.py`

- [x] **B25** [ALTA] `tracer.py:142-180`
  (`_indice_do_ultimo_passo_em_principal`) — quando o corpo `inicio` é (ou
  termina n)uma única instrução que chama uma função/procedimento, a
  função **sobrescreve o passo errado** da lista (assume que o último passo
  "só Principal" está perto do fim; se for o único desse tipo, está na
  posição 0). Resultado: a consola do trace **"anda para trás"** ao avançar
  passo a passo — afeta tanto `--json` (visualizador) como `--debug`.
  Reproduzido com um programa trivial (`escrever(f(10))` como única
  instrução de `inicio`). O teste de regressão existente cobre o mesmo
  formato de programa mas só verifica valores finais, nunca a posição do
  passo na lista — por isso nunca apanhou isto.
- [x] **B26** [MÉDIA] `linter.py:495-515` — a verificação de índices fora
  dos limites em arrays de tamanho literal só olha para variáveis
  declaradas diretamente; **não inspeciona campos de `estrutura`** que
  sejam arrays de tamanho literal (`t.notas[10] = 99` para um campo
  `notas:inteiro[5]` não dá aviso nenhum).

### 1.7 `editors/vscode-algo/`

Território nunca antes auditado. Verificado com o motor real usado pelo VS
Code (`vscode-textmate` + `vscode-oniguruma`), tokenizando excertos
concretos — não só inspeção de regex.

- [x] **B27** [ALTA] `syntaxes/algo.tmLanguage.json` — a palavra-chave
  `nulo` (usada em código real, ex. `enquanto no <> nulo fazer`) **não
  aparece em nenhum padrão da gramática** — fica sem highlighting nenhum,
  ao contrário de `verdadeiro`/`falso`. É a única das 33 palavras-chave do
  lexer totalmente omissa.
- [x] **B28** [ALTA] `syntaxes/algo.tmLanguage.json:86-93`
  (`library-calls`) — o padrão `\b(\w+)(\.)(\w+)\b` não exige `(` a seguir,
  ao contrário do parser real (que só reconhece `biblioteca.metodo(` como
  chamada). Resultado: **todo acesso a campo de estrutura** (`no.valor`,
  `pessoa.idade`) fica colorido como chamada de biblioteca —
  indistinguível visualmente de `matematica.raiz(x)`. Em acessos
  encadeados (`lista.cabeca.valor`) o segundo `.valor` fica sem scope
  nenhum. Como `estrutura` é uma funcionalidade central da linguagem, isto
  afeta uma fração significativa de qualquer programa com structs.
- [x] **B29** [MÉDIA] `syntaxes/algo.tmLanguage.json:94-102`
  (`declarations`) — o padrão `nome:tipo` também dispara dentro de literais
  de estrutura (`{campo: valor}`) sempre que o valor é um identificador nu:
  `{ativo: verdadeiro}` colore `verdadeiro` como `storage.type.algo` (tipo)
  em vez de `constant.language.algo` (valor); o mesmo para `nulo` ou
  qualquer variável lida como valor de campo.
- [x] **B30** [BAIXA] `language-configuration.json:26-29` —
  `decreaseIndentPattern` cobre `senao|caso|contrario` mas não a linha
  `enquanto <condição>` que fecha um `fazer...enquanto` (do-while) — essa
  linha não desfaz a indentação automaticamente ao digitar.
- [x] **B31** [BAIXA] `syntaxes/algo.tmLanguage.json:58-64`
  (`program-header`) — o título entre aspas usa `"[^"]*"` em vez da regra
  `strings` (que suporta `\"` escapado); um título com aspa escapada corta
  a correspondência cedo.

---

## 2. Melhorias (UX de erros / robustez)

- **`semantics.py:143-151`** — referenciar uma `constante` global no
  tamanho de um array-campo de `estrutura` dá "a variável 'N' não foi
  declarada" (factualmente errado — está declarada, só não é visível nesse
  contexto). Mensagem dedicada seria mais clara.
- **`parser.py:682`** — o erro genérico de `_parse_primario` não usa
  `_nome_amigavel()` como o resto do parser, deixando vazar nomes internos
  de tokens (`"expressão inesperada: RPAREN (')')"`).
- **`parser.py:379-389`** — `escrever()`/`ler()` sem argumentos dão erro
  confuso (`"expressão inesperada: RPAREN"`) em vez de mensagem dedicada.
- **Vírgulas a mais (trailing commas)** em literais de array/estrutura ou
  listas de argumentos não têm mensagem dedicada — mesma causa-raiz do
  ponto anterior, repetida em vários pontos do parser.
- **Operadores relacionais encadeados** (`a < b < c`) são corretamente
  proibidos mas com mensagem genérica que não explica a regra; sem teste
  nenhum (nem para a rejeição, nem para a mensagem).
- **Falta de coluna** em `ErroLexico`/`ErroSintatico` — só a linha é
  reportada; obriga a "procurar à vista" em linhas longas.
- **`cli.py`** — divergência entre `ler(booleano)` (só aceita
  "verdadeiro"/"v"/"true") e `conversao.paraBooleano` (aceita qualquer
  texto não vazio como verdadeiro) — vale documentar ou alinhar.
- **`bibliotecas/cadeia.py`** — `subcadeia` com intervalo invertido
  (`ini > fim`, ambos dentro dos limites) devolve `""` silenciosamente, sem
  o mesmo cuidado que `matematica.aleatorio` já tem para limites invertidos.
- **`inclusoes.py`** — colisões de nome **entre categorias diferentes**
  (ex. função incluída vs. global do programa principal) só são apanhadas
  mais tarde por `semantics.py`, com mensagem genérica que perde o contexto
  "veio do ficheiro incluído X".
- **`README.md` da extensão VS Code** afirma validação manual exaustiva
  "token a token" da gramática; os bugs B27–B29 mostram que essa validação,
  a ter existido, não cobriu casos comuns (acesso a campo, `nulo`, literais
  de estrutura) — e não há nada reproduzível no repositório para a
  reconfirmar.

## 3. Melhorias conceptuais / arquiteturais

Fio condutor de vários dos bugs acima: **a mesma regra reimplementada em
vários sítios independentes diverge com o tempo.** Já era a causa de bugs
na primeira auditoria (AL-42); aparece de novo em pelo menos 4 formas
distintas nesta:

- **Propagação do "tipo esperado" para literais `{...}`** implementada em
  apenas 2 dos ≥4 sítios que precisam dela (`_registar_decl` e
  `_verificar_chamada`, mas não recursivamente dentro de
  `_verificar_estrutura_literal`/`_verificar_array_literal`) — causa direta
  de B8. Recomenda-se extrair um único
  `_verificar_valor_com_tipo_esperado(expr, tipo, dims, escopo)` chamado
  recursivamente pelos 4 pontos.
- **`matematica.potencia` vs operador `^`** implementam a mesma proteção
  (base negativa/expoente fracionário) em dois locais gémeos e
  independentes — B13 é a proteção esquecida num deles.
- **`_construir_array_aninhado`** duplicada entre `codegen.py` e
  `codegen_minimo.py` em vez de partilhada via `gerador_base.py` — causa
  direta de B15 só ter sido corrigido nalgum dos dois no passado.
- **Deteção de fronteiras de string/char** triplicada no lexer
  (`_remover_comentarios_bloco`, `_remover_comentario`, `_tokenizar_linha`),
  cada uma com a sua própria versão de "estou dentro de uma string?". Não
  há bug atualmente alcançável a partir disto, mas é a mesma fragilidade
  estrutural que já produziu AL-42.

Outros pontos estruturais:

- **Arrays não podem ser parâmetros de função/procedimento**, nem por
  valor nem por `ref` — a única forma de partilhar um array entre rotinas é
  via global. Para uma linguagem de ensino de algoritmos (onde
  ordenar/pesquisar/inverter um array como procedimento é o exercício
  canónico), isto é uma limitação de expressividade significativa. Vale
  confirmar que é decisão intencional para a v1.
- **Assimetria `ErroInternoCompilador` vs `ErroSemantico`** — `codegen.py`
  tem uma classe dedicada para não expor bugs do compilador como erros do
  aluno; `codegen_minimo.py` nunca recebeu o mesmo tratamento, e (B17)
  alguns desses pontos são mesmo alcançáveis em `--minimo`, não só
  defensivos.
- **Testes de paridade `codegen.py`/`codegen_minimo.py` só verificam
  paridade estrutural** (que tipos de nó cada dispatcher trata), não
  comportamental — daí bugs como B13/B14 (mesma construção, comportamento
  runtime diferente) escaparem. Vale acrescentar testes que corram o mesmo
  programa pelos dois geradores e comparem `stdout`.
- **`parser.py`**: `p.campo(args)` (campo de estrutura chamado como se
  fosse método) é tratado sintaticamente como "chamada de biblioteca" só
  por não haver informação de tipos no parser — a mensagem de erro
  resultante em `semantics.py` ("biblioteca não importada") é enganadora
  para este caso específico.
- **`LIMITE_PROFUNDIDADE_EXPR`/`LIMITE_PROFUNDIDADE_BLOCO`** não são um
  mecanismo central/automático — cada nova função recursiva-descendente
  precisa de "se lembrar" de o incrementar manualmente; já foi esquecido
  duas vezes no mesmo ficheiro (causa raiz de B5).
- **Extensão VS Code**: recomenda-se fortemente gerar (ou pelo menos
  validar automaticamente) as listas de palavras-chave da gramática
  TextMate a partir de `compilador/lexer.py`, no mesmo espírito de
  `online/modo_codemirror.py` — que tem a mesma lacuna para `nulo`, mas
  falha **em voz alta** (via `warnings.warn`) em vez de silenciosamente
  como a gramática TextMate. Mesmo sem reescrever a gramática como geração
  dinâmica, um teste que compare as duas listas evitaria que isto volte a
  desalinhar.
- **`ast_nodes.Parametro`** é o único nó da AST sem campo `linha` —
  inofensivo hoje (parâmetros só existem numa única linha), mas
  inconsistente com todos os outros nós.
- Comentário desatualizado em `ast_nodes.py:43` sugere limite de 2
  dimensões para arrays; confirmado que a linguagem já suporta N dimensões
  em toda a pipeline — só a documentação está errada.

## 4. Lixo

- `semantics.py:162,169` — reimplementam à mão `NUMERICOS | TEXTUAIS |
  {"booleano"}` em vez de usar o conjunto `PRIMITIVOS` já existente
  exatamente para isto.
- `codegen.py:660-662` — ramo genérico `isinstance(expr, A.ArrayLiteral)`
  em `_expr()` parece inatingível (semantics.py já rejeita `ArrayLiteral`
  fora dos 2 contextos tratados antes), mas não está marcado
  `# pragma: no cover` como os outros ramos defensivos do ficheiro —
  inconsistência de estilo, não bug.
- `ast_nodes.py:148` — `Literal.__init__` é o único construtor de nó da
  AST com valor por omissão para `linha` (`linha=0`); confirmado que nunca
  é exercitado (todos os 7 locais que constroem `Literal` passam `linha`
  explicitamente).

## 5. Cobertura de testes

Gaps identificados pelos 5 agentes, agrupados por área (nenhum destes tem
teste de regressão hoje):

**Lexer/parser/AST**
- Dois blocos `inicio` no mesmo programa (B4) — zero cobertura para um bug
  crítico.
- Cadeias longas de `nao`/`-`/`^` encadeado (B5).
- Colisão de nome de campo de estrutura com palavra reservada do Python
  (B6) — só há cobertura para variável/função/parâmetro/nome de estrutura.
- Tab a meio de linha fora da indentação (B1).
- Salto de indentação de mais de 1 nível (B2).
- `escrever()`/`ler()` sem argumentos; vírgula a mais em listas.
- Operadores relacionais encadeados.
- `p.campo(args)` num campo de estrutura.
- Arrays com mais de 2 dimensões (comportamento nunca confirmado por teste).

**Semantics**
- Struct literal aninhado, e struct literal como elemento de array literal
  (B8) — ambos partem hoje.
- Tamanho declarado de array vs tamanho real do literal (B7).
- `caso` duplicado entre tipos compatíveis com valor igual (B11).
- Mesmo campo de estrutura passado 2x por referência (B9).
- Sombreamento de global com tipo diferente num bloco aninhado (B10).
- Constante global referenciada no tamanho de um campo-array de estrutura.

**Codegen**
- `matematica.potencia` com base negativa/expoente fracionário — nem em
  modo normal, nem `--minimo` (B13/B14).
- `ref` com alargamento de tipo (B12), incluindo `cadeia`/`caracter`.
- Array multidimensional com expressão de dimensão interior com efeito
  lateral (B15).
- Construção/comparação de estruturas sob `--debug`/`--json` (B16).
- Reatribuição de literal de estrutura em `--minimo`.
- Paridade comportamental `codegen.py` vs `codegen_minimo.py` para
  programas type-safe representativos, além do único exemplo existente.

**CLI/bibliotecas**
- "`executa` bem-sucedido não atualiza `ultimo_ficheiro`" (B19) — os testes
  que deviam apanhar isto estão de facto a falhar, mas por B18 (mascara
  B19).
- Caminhos com `\` não citados na consola (B18).
- `--entradas` com codificação inválida (B20).
- `conversao.paraInteiro("inf"/"Infinity")` (B21).
- `conversao.paraBooleano` com texto arbitrário não reconhecido.

**Tools/VS Code**
- Ordem/posição dos passos do tracer, não só valores finais (B25) — reforçar
  `test_trace_nao_corrompe_passo_quando_ultima_instrucao_chama_funcao` para
  verificar que a consola cresce monotonamente.
- Índices fora de limites em arrays que são campos de estrutura (B26).
- **A extensão VS Code não tem testes automatizados nenhuns** — dado que o
  resto do projeto tem cultura de testes extensa e que esta auditoria
  encontrou 5 bugs reais usando o próprio motor de tokenização do VS Code,
  isto é um gap real a fechar antes da v1: um teste leve (mesmo em Python,
  comparando `lexer.PALAVRAS_CHAVE` com o texto da gramática) já teria
  apanhado B27.

## 6. Notas de metodologia

Auditoria feita por 5 agentes independentes em paralelo, cada um com âmbito
fechado e instrução explícita de **não se limitar a correr os testes
existentes**: ler os ficheiros na íntegra e raciocinar sobre casos-limite,
depois **reproduzir empiricamente** cada suspeita compilando/correndo
programas Algo reais (não apenas inspeção de código):

1. `compilador/lexer.py`, `parser.py`, `ast_nodes.py`
2. `compilador/semantics.py`
3. `compilador/codegen.py`, `codegen_minimo.py`, `gerador_base.py`
4. `cli.py`, `compilador/inclusoes.py`, `bibliotecas/`
5. `tools/tracer.py`, `flowchart.py`, `linter.py`, `editors/vscode-algo/`

Cada agente teve acesso ao contexto da auditoria anterior (bugs já
corrigidos) para evitar duplicação, mas foi instruído a ficar alerta a
bugs da mesma família que pudessem ter escapado — o que efetivamente
aconteceu várias vezes (B13 encontrado por dois agentes distintos, B15/B17
na mesma família de B16/AL-51, etc.).

Os dois findings mais críticos e mais surpreendentes (B4 e B12) foram
**re-verificados manualmente nesta sessão**, fora dos agentes, correndo o
compilador diretamente contra programas de teste mínimos — ambos
confirmados. Os restantes não foram todos re-verificados manualmente por
esta sessão orquestradora, mas cada agente reportou tê-los reproduzido
empiricamente (compilação/execução real), não apenas por leitura.

Âmbito: só `algo_lang/`. `alguem/` e `online/` ficaram deliberadamente de
fora, exceto onde mencionados como contexto (ex. `online/modo_codemirror.py`
como exemplo de boa prática a replicar na extensão VS Code).

Nenhum ficheiro de código foi alterado durante esta auditoria — é apenas
leitura/análise. Nenhum bug foi corrigido ainda.
