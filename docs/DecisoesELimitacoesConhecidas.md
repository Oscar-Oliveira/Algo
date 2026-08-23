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

- **Atribuição, declaração, `retornar`, e literais `{...}` copiam
  structs/vetores por valor** (via `copy.deepcopy`), em vez de partilhar a
  mesma referência. Só `ref` cria aliasing — e isso é intencional (é o
  mecanismo de passagem por referência da linguagem).
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
  através de `+`, `-`, `*`** (ex.: `N = A + B`) — `/` e `%` não são
  dobrados por `_resolver_constante` (`semantics.py`). Um tamanho que
  dependa de divisão/módulo de constantes cai para o guarda de runtime em
  vez de ser verificado em compilação. Incompletude conhecida, julgada de
  impacto baixo demais para justificar a extensão.
- **Funções de biblioteca podem devolver vetores** (ex.: `cadeia.dividir`)
  através do 4º elemento opcional do tuplo em `FUNCOES`
  (`dims_retorno=1`, ver `bibliotecas/__init__.py`).

## Estruturas

- **Comparação `==`/`<>` entre duas structs compara campo a campo**
  (`__eq__` gerado, recursivo em campos-vetor e structs aninhadas) — não é
  comparação por identidade.
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
  `inicio` e dentro de uma função/procedimento; ver `ReferenciaCompletaCLI.md`
  para a regra de âmbito entre `inicio` e as funções.

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

## `cadeia`

- **Comparação lexicográfica é por ordem de código Unicode, não ordem
  alfabética portuguesa** — limitação inerente e esperada, não um bug.
- Indexação direta de `cadeia` com `[]` (`s[0]`) é sintaxe legal na
  gramática mas sempre rejeitada em compilação — usa `cadeia.caracter`.

## Linter

- **Deteção de recursão sem caso base é deliberadamente limitada a
  autochamada direta** (não deteta ciclos indiretos `A→B→A`) — o próprio
  texto do aviso diz "chama-se a si própria", por isso o âmbito está bem
  comunicado, não é uma promessa quebrada.
- A verificação de "global sombreada por variável de ciclo dentro de uma
  função chamada" só olha 1 nível (não segue chamadas transitivas) — a
  mesma filosofia conservadora de "prefere um falso negativo a um falso
  positivo".

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
