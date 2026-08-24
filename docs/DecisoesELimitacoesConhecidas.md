# Decisões e limitações conhecidas do compilador (algo_lang)

Fonte única de verdade para comportamento do compilador que é **deliberado,
limitado de propósito, ou já foi investigado e descartado como bug** — em
vez de estar disperso em comentários de código citando números de bug (`AL-NN`,
`bug #NN`) e em relatórios de auditoria separados.

Este documento substitui `PLANO_CORRECOES_AUDITORIA.md` e
`docs/AuditoriaCompilador_2026-08-19.md` (ambos removidos). Esses ficheiros
tinham o histórico de 14 rondas de auditoria — bugs encontrados, corrigidos,
e a análise passo a passo. Esse histórico deixou de ser necessário para
perceber o estado atual: **este ficheiro descreve só o que é verdade hoje**,
não a jornada até lá. Para o histórico de correções, ver `git log`.

Cada item abaixo é uma escolha de design ou uma limitação conhecida que
continua no código de propósito — não um bug por corrigir. Se achares que
algum item aqui não devia ser assim, é exatamente para isso que este
documento existe: para poderes rever e decidir, em vez de a decisão ficar
enterrada num comentário.

## Cópia por valor e `ref`

- **`estrutura`: atribuição, declaração, `retornar`, e literais `{...}`
  copiam por valor** (via `copy.deepcopy`), em vez de partilhar a mesma
  referência. **`vetor`: só `retornar`, literais `{...}`, e passagem
  como argumento (sem `ref`) copiam por valor** — atribuição
  (`v2 = v1`) e declaração a partir doutra variável (`v3:T[N] = v1`)
  nunca chegam a copiar nada, são rejeitadas em compilação
  (`ErroSemantico`) antes disso: `_tipo_expr` (`semantics.py`) recusa um
  vetor "nu" fora de `permitir_vetor` (só argumento de chamada e
  `retornar` passam essa flag), e o alvo de uma atribuição rejeita
  `dims_alvo > 0` incondicionalmente. Em ambos os casos, só `ref` cria
  aliasing — e isso é intencional (é o mecanismo de passagem por
  referência da linguagem).
- **Um campo de `estrutura` pode ser marcado `ref`** (ex.:
  `seguinte:ref No`), restrito a um campo escalar cujo tipo seja outra
  `estrutura` — aliasing em vez de cópia, tal como um parâmetro `ref`,
  ver `docs/manual/07-Estruturas.md` secção 7.5. `_gerar_estrutura`
  (`codegen.py`) gera um `__deepcopy__` dedicado para qualquer
  `estrutura` com pelo menos um campo `ref`, para que esse aliasing
  sobreviva a uma cópia por valor do contentor inteiro (sem isto, o
  `copy.deepcopy` por omissão do Python copiaria recursivamente
  através do campo `ref` também, quebrando a partilha).
- **Aliasing entre dois parâmetros `ref` da MESMA chamada, com o mesmo
  nome de variável base** (ex.: `ref v[i], ref v[j]` com `i==j` em
  runtime, ou `ref pontos[k].x, ref pontos[m].x` com `k==m`) é detetado —
  em compilação quando possível (`_caminhos_ref_colidem`, `semantics.py`
  — cobre variáveis simples e campos sem índice), e em runtime quando o
  caminho passa por um índice que só se conhece ao correr o programa
  (`_verificar_aliasing_ref_runtime`, `codegen.py` — usa os índices já
  resolvidos por `_hoistear_indices_ref` para comparar os dois caminhos
  posição a posição; um nome de campo diferente prova que nunca colidem,
  sem emitir guarda nenhum). Ver
  `test_indices_diferentes_do_mesmo_vetor_por_referencia_continua_a_compilar`
  e `test_campo_de_estrutura_dentro_de_vetor_por_referencia_duas_vezes_e_
  detetado_em_runtime`, em `tests/test_correcoes_auditoria.py`.
- Índices em expressões de índice de um argumento `ref` com efeitos
  secundários (ex.: uma chamada de função) são avaliados **exatamente uma
  vez**, e o mesmo valor é reutilizado tanto para ler como para escrever
  de volta — evita o valor de leitura e o de escrita acabarem em posições
  diferentes do array.

## Vetores

- **Índices negativos são sempre rejeitados** em runtime (leitura, escrita,
  1D/2D+, `ref`, literal ou computado) — não há wraparound à a Python.
- **Tamanho máximo de um vetor: 10 milhões de elementos NO TOTAL**
  (decisão do maintainer, escolhida por ser o ponto onde a construção já
  demora ~1s) — `_algo_verificar_tamanho_vetor_agregado` (`codegen.py`)
  verifica o PRODUTO de todas as dimensões, de uma vez, antes de começar
  a construir o vetor, para um `v:inteiro[9999][9999][9999]` (cada
  dimensão individualmente pequena, mas o produto ~10¹²) falhar
  rápido com uma mensagem amigável em vez de tentar alocar terabytes de
  memória. `MemoryError` também está traduzido (rede de segurança para
  qualquer outra via de esgotar memória).
- **`constante` usada como tamanho de vetor só é resolvida em compilação
  através de `+`, `-`, `*`, `^`** (ex.: `N = A + B`) — `/` e `%` não são
  dobrados por `_resolver_constante` (`semantics.py`). Um tamanho que
  dependa de divisão/módulo de constantes cai para o guarda de runtime em
  vez de ser verificado em compilação. Incompletude conhecida, julgada de
  impacto baixo demais para justificar a extensão.
- **Funções de biblioteca podem devolver vetores** (ex.: `cadeia.dividir`)
  através do 4º elemento opcional do tuplo em `FUNCOES`
  (`dims_retorno=1`, ver `bibliotecas/__init__.py`).
- **O tamanho REAL de um vetor devolvido por uma chamada (biblioteca ou
  do próprio programa) é validado em runtime contra o tamanho
  declarado** (`_algo_verificar_tamanho_vetor_resultado`, `codegen.py`)
  quando inicializa uma declaração de tamanho fixo (ex.: `partes:cadeia[3]
  = cadeia.dividir(...)`) — ao contrário de um literal `{...}`, cujo
  tamanho `semantics.py` já valida em compilação, o tamanho de uma
  chamada só é conhecido ao correr o programa. Sem esta verificação, um
  resultado maior do que o declarado ficava silenciosamente legível além
  do tamanho declarado.
- **O resultado de uma chamada pode ser indexado/aceder a um campo
  diretamente** (`foo()[0]`, `foo().campo`, `cadeia.dividir(...)[0]`),
  sem precisar de uma variável intermédia — `A.Chamada` tem um campo
  `acessos`, tal como `A.LValue` (`_parse_acessos`, `parser.py`, chamado
  depois de reconhecer uma chamada em `_parse_primario`). A validação de
  tipo/dims é partilhada com `A.LValue` via `_percorrer_acessos`
  (`semantics.py`); a geração de código é a mesma ideia de `_lvalue`
  (`gerador_base.py`), aplicada ao texto Python da chamada. Uma chamada
  com `ref` continua proibida dentro de uma expressão (`_tem_ref`),
  independentemente de ter `acessos` — e não pode ser alvo de atribuição
  (`foo()[0] = 5`), porque o alvo de uma atribuição só pode começar por
  um identificador (`_parse_lvalue`), nunca por uma chamada.

## Estruturas

- **Comparação `==`/`<>` entre duas structs compara campo a campo**
  (`__eq__` gerado, recursivo em campos-vetor e structs aninhadas) — não é
  comparação por identidade.
- **`__eq__` entre duas structs não é seguro contra ciclos formados por
  campos `ref`** — desde que um campo `ref` permite formar um ciclo de
  referências real (impossível antes, porque a cópia por valor cortava
  sempre o ciclo), comparar (`==`/`<>`) duas structs que formem um ciclo
  através de campos `ref` causa `RecursionError` (o `__eq__` gerado não
  tem memoização, ao contrário do `__deepcopy__` gerado para o mesmo
  caso, que usa `memo` e por isso é seguro). Limitação conhecida, de
  baixo impacto — não corrigida de propósito (ver
  `test_ciclo_de_dois_nos_via_ref_sobrevive_a_copia_por_valor`, em
  `test_estruturas.py`, que testa só a cópia, não a igualdade).
- **Um campo-vetor de uma estrutura pode ser inicializado diretamente num
  literal `{campo: {...}}`** — `semantics.py`, `_verificar_estrutura_
  literal`, reconhece um `A.VetorLiteral` como valor de campo e delega em
  `_verificar_vetor_literal` (mesma validação de forma/tamanho que um
  vetor normal), tal como já fazia para `A.EstruturaLiteral` aninhado.
  Atribuir um valor não-vetor a um campo-vetor continua a ser erro ("o
  campo '{nome}' é um vetor; inicializa-o com '{valor, valor, ...}'").
- Structs mutuamente recursivas (`A↔B`, ciclos de 3+) são aceites; o campo
  do ciclo fica `nulo` em runtime em vez de recursão infinita no próprio
  compilador.
- **Um campo-vetor do próprio tipo (direta ou mutuamente recursivo)**
  (ex.: `estrutura No: filhos:No[2]`, uma árvore) **fica vazio (`[]`) por
  omissão**, em vez de tentar construir eagerly os N elementos
  declarados — `_estruturas_recursivas` (`gerador_base.py`) inclui
  campos-vetor no grafo de recursão (não só escalares), e
  `_gerar_estrutura` (`codegen.py`) usa `[]` em vez de
  `_construir_vetor_aninhado` quando o tipo do campo é recursivo. Mesma
  ideia que um campo escalar recursivo (ex.: `seguinte:No`) já ficava
  `nulo`; sem isto, a construção nunca terminava (`RecursionError`).

## `retornar` e caminhos de execução

- **`_todos_caminhos_devolvem` (verifica que uma função sempre devolve um
  valor) é deliberadamente conservadora**: pode recusar um programa
  tecnicamente correto num caso extremo que não reconhece (ex.: um `para`
  com limites literais que garantem ≥1 iteração não conta como "sempre
  devolve"; um `se` sem `senao` nunca conta, mesmo que os dois ramos reais
  do domínio cubram todos os casos) — mas nunca aceita, em silêncio, um
  programa que de facto tem um caminho sem `retornar`. Um `sair`/
  `continuar` alcançável dentro de um ciclo impede esse ciclo de "contar"
  como garantidamente terminando em `retornar`, porque pode abandonar o
  corpo antes de lá chegar.
- **`retornar` sem expressão só é válido dentro de um `procedimento`**,
  para sair mais cedo (`semantics.py`, ramo `ctx_funcao.eh_procedimento`
  de `A.Retornar`) — devolve os mesmos parâmetros `ref` que o fim do
  corpo devolveria implicitamente. Dentro de uma `funcao`, `retornar`
  exige sempre uma expressão a seguir; um `procedimento` não pode usar
  `retornar <expr>` (procedimentos não devolvem valor).
- **`sair`/`continuar` só afetam o ciclo mais interior** que os contém, e
  só são válidos dentro de um ciclo (`enquanto`/`para`/`fazer...enquanto`)
  — rejeitados em compilação fora desse contexto.

## `constante` e âmbito entre ramos

- Uma declaração (mesmo tipo/`eh_constante`/`dims`) que apareça em TODOS
  os ramos de um `se`/`senao` ou `escolher`/`contrario` **exaustivo**
  fica visível depois do bloco, como uma declaração normal. Um conjunto
  de ramos **não-exaustivo** (sem `senao`/`contrario`) nunca propaga —
  sem erro, só sem disponibilizar o nome a seguir. Isto vale dentro de
  `inicio` e dentro de uma função/procedimento; ver
  `bin/ReferenciaCompletaCLI.md` para a regra de âmbito entre `inicio`
  e as funções.

## Operadores e coerção de tipos

- **`+` nunca converte número para texto**: exige os dois lados numéricos
  (soma) ou os dois lados `cadeia`/`caracter` (concatenação) —
  `inteiro`/`decimal` + `cadeia` é erro de compilação
  (`_tipo_binop`, `semantics.py`). Só existe conversão explícita via
  `conversao.paraTexto` (biblioteca `Conversao`). Avaliado ao escrever os
  exemplos de `exemplos/01_variaveis_tipos/`: mantido de propósito, por
  consistência com o resto da linguagem (nenhum outro operador faz
  coerção implícita entre tipos incompatíveis) — não corrigir sem
  reavaliar o impacto em toda a gramática de `+` (`booleano`/`caracter`
  soltos, etc.). Até se chegar a `Conversao`, `escrever` com vários
  argumentos separados por vírgula é a forma correta de misturar texto e
  números, em vez de montar uma única `cadeia` concatenada.

## `escrever` e formatação

- **`escrever` com vários argumentos não insere nenhum separador entre
  eles** (`escrever("x =", 5)` → `"x =5"`) — deliberado; o separador
  (ex.: espaço) tem de ser escrito explicitamente.
- **`decimal` é arredondado a 12 casas decimais antes de ser mostrado**, e
  `-0.0` é normalizado para `0.0` — remove ruído de vírgula flutuante
  comum (`0.1 + 0.2` mostra `0.3`, não `0.30000000000000004`) sem afetar
  o `.0` que distingue `decimal` de `inteiro` (`3.0` continua `3.0`).
- **Notação científica para magnitudes extremas não é traduzida**
  (`10.0^20` mostra `1e+20`, não uma forma "amigável") — deliberadamente
  fora do alcance considerado razoável para "limpar ruído comum".

## `ler()` e conversões

- **`ler()` para `decimal` rejeita `nan`/`inf`/`-inf`/`Infinity`** (pede o
  valor outra vez) — entrada interativa onde isto é quase sempre um erro
  de digitação.
- **`conversao.paraDecimal` continua a ACEITAR `nan`/`inf`/`-inf`/
  `Infinity` de propósito** — ao contrário de `ler()`. É o único ponto de
  todo o ALGO por onde um programa consegue construir esses valores
  deliberadamente (a linguagem não tem literal para infinito/nan). Os
  consumidores (`matematica.piso`/`teto`, `conversao.paraInteiro`) já
  traduzem o `OverflowError` resultante para uma mensagem amigável, por
  isso não há valor "perigoso" a escapar sem tratamento — só sem
  validação na entrada. Investigado como possível bug, rejeitado depois
  de quebrar 2 testes que dependem deste comportamento de propósito.
- **`matematica.piso`/`teto`/`conversao.paraInteiro` de `nan` dão o
  fallback GENÉRICO de `_algo_traduzir_valueerro`** ("valor inválido
  (cannot convert float NaN to integer).", em vez de uma mensagem
  específica como a que existe para infinito) — investigado, não é um
  traceback cru (o critério que importa: `ValueError` sempre traduzido
  para português, mesmo que o texto entre parênteses fique em inglês
  para uma causa sem tradução dedicada). Ver
  `test_matematica_teto_de_nan_da_erro_amigavel`.
- **`matematica.potencia` devolve o `int` em bruto (não `float`) quando o
  resultado é grande demais para caber num `float`** (`OverflowError`) —
  em vez de propagar o erro. Réplica deliberada do comportamento do
  operador `^` usado FORA de um contexto `decimal` (ex.:
  `escrever(10^1000)`, que também nunca força `float()` e por isso
  também nunca rebenta para o mesmo valor extremo) — não do `^` DENTRO
  de um contexto `decimal` (`x:decimal = 10^1000`, que força `float()` e
  por isso pode rebentar). Ver
  `test_matematica_potencia_com_expoente_grande_calcula_e_imprime_sem_overflow`
  (bug #35 da auditoria original). Quebra, de propósito, a invariante de
  que `decimal` nunca aparece sem `.0` — julgado preferível a rejeitar um
  cálculo exato só porque não cabe num `float`.

## `cadeia`

- **Comparação lexicográfica é por ordem de código Unicode, não ordem
  alfabética portuguesa** — limitação inerente e esperada, não um bug.
- Indexação direta de `cadeia` com `[]` (`s[0]`) é sintaxe legal na
  gramática mas sempre rejeitada em compilação — usa `cadeia.caracter`.
- **`cadeia.procurar`/`substituir`/`dividir` rejeitam todos um texto
  vazio no argumento relevante** (o texto a procurar/substituir/o
  separador) com uma mensagem amigável dedicada — `str.find`/`replace`/
  `split` do Python com um texto vazio dão resultados surpreendentes sem
  valor pedagógico (`find("")` "encontra" em toda a posição, `split("")`
  rebenta, `replace("", x)` insere `x` entre cada caracter).

## `incluir ... como <alias>`

- **Um alias é validado como qualquer outro identificador** — colide com
  nome de função/estrutura/biblioteca importada/variável/parâmetro, tal
  como `matematica`/`cadeia`/etc. já colidiam (`_verificar_nome_
  disponivel`, `semantics.py`). Sem isto, uma variável local com o mesmo
  nome do alias fazia `alias.metodo()` resolver silenciosamente para a
  função incluída em vez do campo da variável, sem erro nenhum.
- **Incluir o MESMO ficheiro duas vezes exige o MESMO alias (ou nenhum)
  nas duas vezes** — a deduplicação por caminho absoluto (`cli.py`/
  `online/executor.py`) compara o alias da ocorrência atual com o da
  primeira; um alias diferente (incluindo "sem alias" vs "com alias") dá
  um erro dedicado em vez de a segunda ocorrência ser silenciosamente
  ignorada.
- **Uma função incluída com alias é tratada como uma função ALGO normal
  do próprio ficheiro** para todos os efeitos que dependem disso — pode
  ter parâmetros `ref` (`_tem_ref` resolve o alias antes de decidir) e
  pode ler uma variável global do próprio ficheiro incluído, com a
  mesma verificação de referência-antecipada que uma função local
  (`_resolver_nome_funcao_local`, `semantics.py`) — ao contrário de uma
  biblioteca embutida verdadeira (`matematica`, `cadeia`, ...), que
  nunca tem `ref` nem lê globais ALGO.

## Linter

- **Deteção de recursão sem caso base é deliberadamente limitada a
  autochamada direta** (não deteta ciclos indiretos `A→B→A`) — o próprio
  texto do aviso diz "chama-se a si própria", por isso o âmbito está bem
  comunicado, não é uma promessa quebrada.
- A verificação de "global sombreada por variável de ciclo dentro de uma
  função chamada" só olha 1 nível (não segue chamadas transitivas) — a
  mesma filosofia conservadora de "prefere um falso negativo a um falso
  positivo".
- **Atribuir a um parâmetro por valor é assinalado tanto para o
  parâmetro inteiro (`p = ...`) como para um campo/elemento seu
  (`p.campo = ...`, `v[i] = ...`)** — struct/vetor são copiados por
  valor (ver "Cópia por valor e `ref`" acima), por isso mutar um
  campo/elemento é exatamente a mesma confusão passagem-por-valor-vs-
  referência que reatribuir o parâmetro inteiro, só que mais idiomática
  (é a forma natural de tentar "modificar" uma struct/vetor por valor).

## Limites de recursos

- `algo executa` (sem `--debug`/`--json`) tem um limite de **10s de CPU**
  (`LIMITE_CPU_SEGUNDOS`, `cli.py`), via `resource.setrlimit`, para
  apanhar ciclos infinitos/recursão sem memoização.
- `algo executa --debug`/`--json` corre em processo (sem subprocesso,
  por isso sem `resource.setrlimit`) e tem DOIS limites independentes em
  `tools/tracer.py`: `MAX_PASSOS=4000` (número de linhas executadas) e,
  desde que `MAX_PASSOS` sozinho não protegia contra um ciclo com poucas
  iterações mas caro por iteração, `LIMITE_TEMPO_SEGUNDOS=10` (tempo de
  CPU acumulado entre passos, via `time.process_time()` -- mesma
  filosofia do `LIMITE_CPU_SEGUNDOS` do caminho sem trace, incluindo
  nunca contar tempo bloqueado em `ler()`). Nenhum dos dois consegue
  interromper uma ÚNICA linha demasiado cara a meio da sua própria
  execução (`sys.settrace` só devolve o controlo entre linhas) -- isso é
  trabalho de guardas dedicados como `_algo_verificar_tamanho_vetor_agregado`
  (ver "Vetores", abaixo), não deste limite geral.
