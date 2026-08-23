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

## Itens a rever (dúvida levantada, ainda sem decisão)

- **Campo-vetor não pode ser inicializado num literal de estrutura** — ver
  [Estruturas](#estruturas) abaixo. Sinalizado como estranho; vale a pena
  decidir se compensa suportar.

---

## Cópia por valor e `ref`

- **Atribuição, declaração, `devolver`, e literais `{...}` copiam
  structs/vetores por valor** (via `copy.deepcopy`), em vez de partilhar a
  mesma referência. Só `ref` cria aliasing — e isso é intencional (é o
  mecanismo de passagem por referência da linguagem).
- **Limitação conhecida, não corrigida**: dois parâmetros `ref` que
  apontem para o MESMO objeto em runtime (`ref v[i], ref v[j]` com `i==j`
  em runtime; ou `ref p1.x, ref p2.x` depois de `p2 = p1`) fazem com que a
  escrita do primeiro seja silenciosamente sobreposta pela do segundo — o
  compilador não consegue provar estaticamente que os dois acessos nunca
  colidem quando o índice é uma expressão computada, ou quando dois nomes
  diferentes podem ser o mesmo objeto. Testado e fixado deliberadamente
  como comportamento atual (`test_indices_diferentes_do_mesmo_vetor_por_
  referencia_continua_a_compilar`,
  `test_campo_de_estrutura_dentro_de_vetor_por_referencia_duas_vezes_nao_e_
  detetado`, em `tests/test_correcoes_auditoria.py`) — corrigir isto a
  sério exigiria detetar aliasing em runtime, não só em compilação.
- Índices em expressões de índice de um argumento `ref` com efeitos
  secundários (ex.: uma chamada de função) são avaliados **exatamente uma
  vez**, e o mesmo valor é reutilizado tanto para ler como para escrever
  de volta — evita o valor de leitura e o de escrita acabarem em posições
  diferentes do array.

## Vetores

- **Índices negativos são sempre rejeitados** em runtime (leitura, escrita,
  1D/2D+, `ref`, literal ou computado) — não há wraparound à a Python.
- **Tamanho máximo de um vetor: 10 milhões de elementos, POR DIMENSÃO**
  (decisão do maintainer, escolhida por ser o ponto onde a construção já
  demora ~1s). **Não é um limite sobre o produto entre dimensões** — um
  `v:inteiro[9999999][9999999]` (cada dimensão individualmente abaixo do
  limite) continua sem guarda agregada. Bounding o produto exigiria
  rastrear todas as dimensões de um vetor em conjunto; deixado como está.
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
- **Um campo-vetor de uma estrutura não pode ser inicializado diretamente
  num literal `{campo: valor}`** — `semantics.py`, `_verificar_estrutura_
  literal`, rejeita com "o campo '{nome}' é um vetor; não pode ser
  inicializado diretamente num literal de estrutura". É preciso construir
  a struct primeiro e atribuir o campo-vetor depois, separadamente.
  Comportamento deliberado e consistente com o resto do tratamento de
  `EstruturaLiteral`/`VetorLiteral` (nenhum dos dois tenta inferir forma a
  partir do valor à direita quando o valor é ele próprio um vetor dentro
  de um contexto de campo) — mas nunca foi ativamente decidido que seja
  assim *porque* é a melhor UX, só que é a implementação mais simples e
  consistente com as restantes regras. **Ver "Itens a rever" no topo.**
- Structs mutuamente recursivas (`A↔B`, ciclos de 3+) são aceites; o campo
  do ciclo fica `nulo` em runtime em vez de recursão infinita no próprio
  compilador.

## `devolver` e caminhos de execução

- **`_todos_caminhos_devolvem` (verifica que uma função sempre devolve um
  valor) é deliberadamente conservadora**: pode recusar um programa
  tecnicamente correto num caso extremo que não reconhece (ex.: um `para`
  com limites literais que garantem ≥1 iteração não conta como "sempre
  devolve"; um `se` sem `senao` nunca conta, mesmo que os dois ramos reais
  do domínio cubram todos os casos) — mas nunca aceita, em silêncio, um
  programa que de facto tem um caminho sem `devolver`. Um `sair`/
  `continuar` alcançável dentro de um ciclo impede esse ciclo de "contar"
  como garantidamente terminando em `devolver`, porque pode abandonar o
  corpo antes de lá chegar.
- **Não existe `devolver` sem valor dentro de um `procedimento`** — a
  gramática exige sempre uma expressão a seguir a `devolver`. Nota de
  desenho, não uma limitação a corrigir.
- **`sair`/`continuar` só afetam o ciclo mais interior** que os contém, e
  só são válidos dentro de um ciclo (`enquanto`/`para`/`fazer...enquanto`)
  — rejeitados em compilação fora desse contexto.

## `constante` e âmbito entre ramos

- Uma declaração (mesmo tipo/`eh_constante`/`dims`) que apareça em TODOS
  os ramos de um `se`/`senao` ou `escolher`/`contrario` **exaustivo**
  fica visível depois do bloco, como uma declaração normal. Um conjunto
  de ramos **não-exaustivo** (sem `senao`/`contrario`) nunca propaga —
  sem erro, só sem disponibilizar o nome a seguir.
- **Limitação conhecida, investigada e descartada**: uma declaração feita
  num único ramo não-exaustivo de `se`/`escolher` (sem `senao`/
  `contrario`) ainda assim se torna "visível" para chamadas de função
  através de `_pre_registar_recursivo` (que trata qualquer bloco
  alcançável como válido, sem noção de exaustividade). A correção óbvia
  (ignorar ramos com condição literal `falso`) quebra um teste já
  existente e deliberado
  (`test_variavel_global_com_tipos_diferentes_em_ramos_irmaos_e_erro`),
  que espera que MESMO um ramo `se falso` continue a contar para a
  verificação de tipos entre ramos irmãos. Resolver isto sem quebrar essa
  garantia exigiria dois comportamentos diferentes para o mesmo
  mecanismo (alcançabilidade só para "registar como visível", não para
  "verificar consistência de tipo") — avaliado como mais arriscado do
  que vale a pena; revertido.

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
  (`LIMITE_CPU_SEGUNDOS`, `cli.py`) para apanhar ciclos infinitos/recursão
  sem memoização — o modo `--debug`/`--json` já tinha `MAX_PASSOS=4000`
  em `tools/tracer.py`, mas esse limite não protegia o caminho mais
  comum, sem trace.
