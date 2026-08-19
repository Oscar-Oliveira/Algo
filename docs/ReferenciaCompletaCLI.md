# ALGO — linguagem algorítmica em português → Python

Compilador de uma linguagem algorítmica (pseudocódigo estruturado, em
português) que transpila para Python, pensado para ensino de programação
no ensino superior.

## Decisões de design

### Porquê infinitivo, não imperativo, nas palavras-chave de ação

As 8 palavras-chave que são verbos (`escrever`, `ler`, `devolver`,
`fazer`, `escolher`, `importar`, `incluir`, `afirmar`) estão todas no
**infinitivo**, deliberadamente — não em imperativo (`escreve`, `lê`,
`devolve`...). Já foi questionado se o imperativo não seria mais
natural, dado que um programa é, em certo sentido, uma sequência de
comandos. A decisão foi manter o infinitivo, por três razões:

1. **Abstração pura da ação.** Quando um aluno pensa num algoritmo,
   está a mapear um procedimento — "primeiro é preciso ler o valor,
   depois calcular a média, no fim escrever o resultado" — não a dar
   ordens a alguém. O infinitivo reflete diretamente esse fluxo mental
   de descrição, sem o enquadrar como uma instrução dada a uma pessoa
   ou máquina específica.

2. **Atemporalidade.** O infinitivo não prende a ação a um sujeito nem
   a um momento (presente, passado, mandato direto). Um algoritmo é
   uma *receita*: a descrição de um procedimento que só vai ser
   seguido mais tarde, quando o programa correr — e não por acaso é
   assim que se escrevem receitas em português ("bater os ovos, juntar
   o açúcar"), não no imperativo ("bate os ovos!"). É o mesmo
   fenómeno: descrever um procedimento é diferente de o executar ali,
   naquele momento.

3. **Consistência visual e sintática.** Mantida em todas as
   instruções, a forma no infinitivo dá ao código uma leitura coesa,
   mais perto de uma especificação de passos do que de um diálogo:

   ```
   fazer
       escrever "Introduza um valor:"
       ler x
   enquanto x < 0
   ```

O imperativo (`faz`, `escreve`, `lê`) não está errado — é a escolha
natural em linguagens de produção (`print`, `write`), onde o objetivo
já não é ensinar a pensar em algoritmos, mas instruir uma máquina de
forma direta e eficiente. O ALGO não está nessa fase: o objetivo é que
o aluno construa a sequência lógica do processo, não que "dê ordens ao
computador". É essa diferença de propósito, não uma preferência
estética, que justifica a escolha.

## Estrutura do projeto

```
algo-lang-pacote/
├── algo.sh                    script de arranque -- Linux
├── algo.command                script de arranque -- macOS (duplo-clique)
├── algo.bat                    script de arranque -- Windows (duplo-clique)
├── algo_lang/                 pacote instalável (o compilador em si)
│   ├── cli.py                  comando "algo" -- liga tudo abaixo
│   ├── compilador/              lexer, parser, verificador de tipos, gerador de Python
│   │   ├── lexer.py
│   │   ├── parser.py
│   │   ├── ast_nodes.py
│   │   ├── semantics.py
│   │   └── codegen.py
│   ├── tools/                    ferramentas à volta do compilador
│   │   ├── flowchart.py           algo fluxograma
│   │   ├── linter.py              algo verifica
│   │   └── tracer.py              algo executa --debug/--json
│   ├── bibliotecas/               matematica., cadeia., conversao. (importar Matematica / Cadeia / Conversao)
│   ├── tests/                     suite de testes automatizados (pytest)
│   └── editors/vscode-algo/       extensão de realce de sintaxe para o VS Code
├── exemplos/                   ficheiros .algo de demonstração (não fazer parte do pacote)
├── visualizador/                algo-trace-viewer.html -- abre os .json do --json
├── alguem/                      tutor de algoritmia baseado em LLM (independente do compilador)
│   ├── README.md                  configuração, arquitetura, como chamar
│   ├── config.json / config.exemplo.json
│   ├── nucleo/                    política pedagógica, escada de ajuda, system prompt
│   ├── fornecedores/              cada fornecedor de LLM na sua classe/ficheiro
│   └── cli.py
└── pyproject.toml
```

Regra simples para saberes onde mexer: **linguagem em si** (nova
sintaxe, novo tipo, nova regra semântica) → `algo_lang/compilador/`;
**ferramenta à volta da linguagem** (novo tipo de aviso, novo formato de
diagrama) → `algo_lang/tools/`; **função pronta a usar dentro de
programas ALGO** → `algo_lang/bibliotecas/`.

## Instalação

Precisas de **Python 3.8+** instalado no sistema (não precisas de saber
nada sobre ambientes virtuais — os scripts abaixo tratam disso).

### Opção 1 — script de arranque (recomendado, não precisas de instalar nada à mão)

Dentro desta pasta, consoante o teu sistema:

| Sistema | Como correr |
|---|---|
| Linux | `./algo.sh` |
| macOS | duplo-clique em `algo.command` (ou `./algo.command` na Terminal) |
| Windows | duplo-clique em `algo.bat` (ou `algo.bat` na consola) |

Na primeira vez, o script demora uns segundos a preparar tudo sozinho
(cria um ambiente virtual Python numa pasta `.venv` ao lado dele, e
instala o ALGO lá dentro); nas vezes seguintes arranca logo. Não
precisas de ativar nada à mão — o script trata disso por ti.

Sem argumentos nenhuns, isto abre a [consola interativa](#consola-interativa).
Com argumentos, funciona exatamente como o comando `algo` normal, por
exemplo `./algo.sh executa soma.algo`.

Notas por sistema:
- **macOS**: da primeira vez que abrires `algo.command` por duplo-clique,
  o Gatekeeper pode bloquear ("não é possível abrir porque é de um
  desenvolvedor não identificado") — clica com o botão direito no
  ficheiro, escolhe "Abrir", e confirma. Só é preciso da primeira vez.
- **Windows**: o instalador do Python tem de ter marcada a opção
  *"Add python.exe to PATH"* (é a norma, mas convém confirmar).

### Opção 2 — instalação manual com pip

Se preferires o processo tradicional (ou já tens o teu próprio venv
ativo):

```bash
pip install -e .
```

Isto instala o comando `algo` no Python ativo no momento (o teu, ou o de
um venv que já tenhas ativado à mão).

## Utilização

```bash
algo executa meuprograma.algo
```

Lê `meuprograma.algo`, verifica sintaxe e tipos, gera `meuprograma.py` e
executa-o. Todos os ficheiros gerados (`.py`, `.dot`, imagens) ficam
numa **subpasta com o nome do algoritmo**, ao lado do ficheiro `.algo`
— por exemplo, `meuprograma.algo` gera `meuprograma/meuprograma.py`,
não `meuprograma.py` solto ao lado do código-fonte.

```bash
algo executa meuprograma.algo --mostrar-python   # mostra o Python gerado
algo executa meuprograma.algo --debug            # mostra o valor das variáveis a cada passo, na consola
algo executa meuprograma.algo --json             # gera um trace completo em .json (para o visualizador web)
algo verifica meuprograma.algo                   # avisos de estilo (variáveis não usadas, etc.)
algo fluxograma meuprograma.algo                 # fluxograma do principal + 1 por cada função/procedimento
```

O ficheiro `..._trace.json` gerado por `--json` abre-se no **visualizador
web**, que está em `visualizador/algo-trace-viewer.html` (duplo-clique
para abrir — não precisa de instalação nenhuma).

## Consola interativa

Escrever só `algo` (sem nenhum comando a seguir) abre uma consola: cada
linha é um dos comandos acima, sem teres de repetir `algo` nem reabrir o
programa a cada vez. Cada comando tem também um atalho de uma letra —
`e` (executa), `v` (verifica), `f` (fluxograma), `a` (ajuda), `s` (sair).

```
$ algo
--------------------------------------------------------------
  Consola ALGO
--------------------------------------------------------------
  ...

algo> e soma.algo
✔ Compilado para: soma/soma.py
----- Execução -----
...
algo> v
✔ Nenhum aviso — o linter não encontrou nada a assinalar.
algo> sair
```

Repara que o segundo comando (`v`) não precisou de indicar o
ficheiro outra vez — a consola lembra sempre o último ficheiro usado na
sessão, e só o pedes de volta se indicares um nome diferente. Um
comando com erro (de compilação, ou um nome de comando que não existe)
não fecha a consola, só mostra o erro e volta ao prompt.

## Alguem — o tutor de algoritmia

Escrever `?` dentro da consola (secção anterior) chama o **Alguem**, um
tutor baseado em LLM que ajuda a pensar num exercício sem o resolver
por ti — nunca escreve código, prioriza perguntas e pistas progressivas
sobre respostas diretas. **Só se chama de dentro da consola do ALGO**
(não tem script de arranque próprio). Mostra-lhe automaticamente, pelo
nome, o ficheiro em que estiveste a trabalhar (e qualquer ficheiro que
ele inclua via `incluir`); dentro da conversa, `ficheiros` mostra o que
tem visível, e `ficheiro nome.algo` troca de ficheiro. Um segundo passo
de verificação (o **Guardião Pedagógico**) reavalia cada resposta antes
de a mostrares — se detetar código ou uma solução completa, descarta-a
e pede ao modelo para tentar outra vez com uma pista mais pequena, em
vez de confiar só no *system prompt*. Vive na pasta `alguem/`,
independente do compilador (`algo_lang/compilador/` não depende de
nada de lá). Para o configurares (fornecedor de LLM, modelo, chave de
API), consulta `alguem/README.md`.

## Estrutura de um programa

```
algoritmo "NomeDoPrograma"

importar Matematica
incluir "outroficheiro.algo"

total:inteiro = 0            // variável global (visível em todas as funções)

funcao dobro(x:inteiro):inteiro
    devolver x * 2

inicio
    y:inteiro = dobro(5)     // variáveis locais: declara-se onde precisares
    escrever(y)
```

Não existe uma zona fixa de "variáveis". Declaras uma variável onde
precisares dela, com `nome:tipo`. **Só as variáveis declaradas fora de
qualquer `funcao`/`procedimento`** (diretamente no programa principal —
antes ou dentro do `inicio`) são globais e ficam visíveis dentro das
funções; tudo o resto é local a cada função.

Os blocos são delimitados por **indentação** — usa sempre espaços, não
tabs.

## Tipos de dados

| Tipo        | Equivalente Python | Exemplo         |
|-------------|--------------------|-----------------|
| `inteiro`   | `int`               | `10`            |
| `decimal`   | `float`              | `3.14`          |
| `booleano`  | `bool`               | `verdadeiro`, `falso` |
| `cadeia`    | `str` (texto)        | `"Bom dia"` (aspas duplas) |
| `caracter`  | `str` de 1 símbolo   | `'a'` (aspas simples) |

## Declaração e atribuição

```
idade:inteiro                  // declaração, valor por omissão (0)
nome:cadeia = "Rita"           // declaração com valor inicial
notas:decimal[30]              // array (1 dimensão)
tabuleiro:inteiro[8][8]        // matriz (2 dimensões, índices começam em 0)
cubo:inteiro[3][3][3]          // 3 dimensões -- ou mais, se precisares

idade = 20                     // atribuição usa '='
```

> Os índices de um array vão de `0` a `tamanho - 1`, tal como em Python,
> Java, C# e na generalidade das linguagens de programação — um array
> `inteiro[5]` tem posições válidas `v[0]` a `v[4]`. Um ciclo típico para
> percorrer um array é `para i de 0 ate tamanho - 1 fazer`.

Um array também pode ser inicializado com uma lista de valores entre
`{ }`, com o mesmo número de níveis de aninhamento que dimensões:

```
primos:inteiro[5] = {2, 3, 5, 7, 11}
tabuleiro:inteiro[2][2] = {{1, 2}, {3, 4}}
cubo:inteiro[2][2][2] = {{{1,2},{3,4}}, {{5,6},{7,8}}}
```

## Constantes

`constante` declara um valor que não pode ser alterado depois — nem por
atribuição, nem por `ler()`, nem passado por `ref`. Tem sempre de ter um
valor inicial, e não pode ser um array. Pode ser global (fora de qualquer
função) ou local a uma função:

```
constante IVA:decimal = 1.23

funcao precoComIva(preco:decimal):decimal
    devolver preco * IVA
```

## Operadores

- Atribuição: `=`
- Igualdade / diferença: `==`  `<>`
- Relacionais: `<`  `>`  `<=`  `>=`
- Lógicos: `e`  `ou`  `nao`
- Aritméticos: `+`  `-`  `*`  `/`  `div` (divisão inteira)  `mod` (resto)  `^` (potência)
- `+` também concatena texto: `"Olá, " + nome + "!"`

## Entrada / saída

```
escrever("O valor é: ", x)
ler(x)
```

## Condicional

```
se x > 10 entao
    escrever("grande")
senao se x > 0 entao
    escrever("pequeno positivo")
senao
    escrever("não positivo")
```

## Ciclos

Tal como qualquer outra variável, a variável de controlo de um `para`
tem de estar declarada **antes** do ciclo -- não é declarada
implicitamente pelo próprio `para`. E só existe dentro do corpo do
ciclo (ou do bloco `se`/`enquanto`/`escolher` onde for declarada): usá-la
depois do ciclo/bloco terminar é um erro de compilação.

```
i:inteiro
para i de 1 ate 10 fazer
    escrever(i)

para i de 10 ate 1 passo -1 fazer
    escrever(i)

enquanto x < 100 fazer
    x = x * 2

fazer
    x = x + 1
enquanto x < 10
```

### Sair de um ciclo a meio

O ALGO não tem `parar`/`break`: a única forma de terminar uma
função/procedimento a meio de um ciclo é `devolver`, e `devolver` só é
permitido dentro de `funcao`/`procedimento` (nunca no `inicio`). Para um
ciclo dentro do `inicio` que precise de terminar antes da condição
"natural" (menu com opção de sair, procurar um valor e parar assim que
o encontrar, ler até um valor-sentinela), usa uma variável `booleano`
como bandeira de controlo, alterada algures dentro do próprio corpo do
ciclo:

```
continuar:booleano = verdadeiro
opcao:inteiro
enquanto continuar fazer
    escrever("1-Somar  2-Sair")
    ler(opcao)
    se opcao == 1 entao
        escrever("resultado: ", 2 + 2)
    senao se opcao == 2 entao
        continuar = falso
```

`algo verifica` avisa se a bandeira nunca chega a ser alterada dentro
do corpo do ciclo -- normalmente sinal de que falta o `continuar =
falso` (ou equivalente) nalgum ramo.

## escolher / caso

```
escolher diaSemana
    caso 1
        escrever("Segunda-feira")
    caso 6, 7
        escrever("Fim de semana")
    contrario
        escrever("Dia útil")
```

## Funções e procedimentos

Uma função devolve valor (`devolver`); um procedimento não. Parâmetros
usam sempre `nome:tipo`, e podem ser passados por **valor** (por omissão)
ou por **referência** (`ref`) — em qualquer um dos dois, função ou
procedimento:

```
procedimento trocar(ref a:inteiro, ref b:inteiro)
    temp:inteiro = a
    a = b
    b = temp

funcao incrementar(ref x:inteiro):inteiro
    x = x + 1
    devolver x

inicio
    p:inteiro = 3
    q:inteiro = 9
    trocar(p, q)                  // p passa a 9, q passa a 3

    novo:inteiro = incrementar(p) // p também é alterado; novo recebe o valor devolvido
```

Uma chamada a uma função/procedimento com parâmetros `ref` só pode ser
usada como instrução isolada, ou diretamente à direita de uma atribuição
(`x = f(...)`) — nunca dentro de outra expressão maior, porque precisa de
atualizar as variáveis originais.

### Âmbito (escopo)

Uma variável declarada dentro de uma função/procedimento é local a essa
função. Uma variável declarada fora de qualquer função (no programa
principal) é global — visível e alterável a partir de qualquer função. Um
parâmetro ou uma declaração local pode ter o mesmo nome de uma variável
global: nesse caso, dentro dessa função, o nome refere-se sempre à
variável local (sombra a global).

## Bibliotecas

As funções auxiliares da linguagem estão agrupadas em bibliotecas com
namespace, tal como `matematica.raiz(x)` ou `cadeia.comprimento(s)`. É preciso
importar a biblioteca antes de a usar:

```
importar Matematica
importar Cadeia

inicio
    escrever(matematica.raiz(16.0))    // 4.0
    escrever(cadeia.maiusculas("ola")) // OLA
```

### Bibliotecas embutidas

**Matematica** (`importar Matematica`):

| Função | Descrição |
|---|---|
| `matematica.raiz(x)` | raiz quadrada |
| `matematica.potencia(b, e)` | b elevado a e |
| `matematica.absoluto(x)` | valor absoluto |
| `matematica.piso(x)` | arredonda por baixo |
| `matematica.teto(x)` | arredonda por cima |
| `matematica.aleatorio(a, b)` | inteiro aleatório entre a e b |

**Cadeia** (`importar Cadeia`):

| Função | Descrição |
|---|---|
| `cadeia.comprimento(s)` | número de caracteres |
| `cadeia.maiusculas(s)` | converte para maiúsculas |
| `cadeia.minusculas(s)` | converte para minúsculas |
| `cadeia.inverter(s)` | inverte a cadeia |
| `cadeia.subcadeia(s, ini, fim)` | sub-cadeia entre índices (0-baseado; `fim` exclusivo, tal como as fatias do Python) |
| `cadeia.caracter(s, i)` | o caracter na posição `i` (0-baseado, tal como os arrays) |

**Conversao** (`importar Conversao`) — converte entre os 5 tipos primitivos:

| Função | Descrição |
|---|---|
| `conversao.paraTexto(x)` | qualquer tipo primitivo → `cadeia` |
| `conversao.paraInteiro(x)` | qualquer tipo primitivo → `inteiro` (booleano vira 0/1, decimal trunca, texto faz parse) |
| `conversao.paraDecimal(x)` | qualquer tipo primitivo → `decimal` |
| `conversao.paraBooleano(x)` | qualquer tipo primitivo → `booleano` (`0`/`""`/`"falso"` → falso, resto → verdadeiro) |
| `conversao.paraCaracter(t)` | `cadeia` com exatamente 1 caracter → `caracter` |
| `conversao.paraAscii(c)` | `caracter` → `inteiro` (código do caracter) |
| `conversao.deAscii(i)` | `inteiro` → `caracter` (inverso de `paraAscii`) |

### Adicionar novas bibliotecas

As bibliotecas estão em `algo_lang/bibliotecas/`. Para criar uma nova,
adiciona um ficheiro `.py` nessa pasta com três variáveis:

```python
NOME = "nomeDaBiblioteca"        # usado em 'importar NomeDaBiblioteca'
CABECALHO = "import alguma_coisa\n"   # código Python injetado uma vez (pode ser "")
FUNCOES = {
    "metodo": (["numeric"], "decimal", "def nomeDaBiblioteca_metodo(x):\n    return x\n"),
    # nome_metodo -> (categorias_dos_argumentos, tipo_de_retorno, código_python)
    # categorias possíveis: "numeric", "inteiro", "cadeia"
}
```

Fica logo disponível como `nomeDaBiblioteca.metodo(...)`, sem mais
configuração.

### Incluir os teus próprios ficheiros

`incluir "caminho/para/ficheiro.algo"` junta as funções e procedimentos
(e variáveis globais) desse ficheiro ao teu programa, sem namespace — o
ficheiro incluído contém apenas declarações e `funcao`/`procedimento`,
sem `algoritmo` nem `inicio`:

```
// geometria.algo
funcao areaCirculo(raio:decimal):decimal
    pi:decimal = 3.14159
    devolver pi * raio * raio
```

```
// principal.algo
algoritmo "Principal"
incluir "geometria.algo"

inicio
    escrever(areaCirculo(3.0))
```

## Comentários

```
// isto é um comentário até ao fim da linha

/* isto é um comentário
   que pode ocupar
   várias linhas */
```

## afirmar — validar os teus próprios exercícios

`afirmar` verifica uma condição em tempo de execução; se for falsa, o
programa para e mostra uma mensagem — útil para confirmares que uma
função faz o que deve, sem teres de escrever um programa de testes à
parte:

```
funcao dobro(x:inteiro):inteiro
    devolver x * 2

inicio
    afirmar dobro(5) == 10, "dobro(5) devia ser 10"
    escrever("passou no teste")
```

Se a condição for verdadeira, `afirmar` não produz nenhuma saída e o
programa continua normalmente. A mensagem (depois da vírgula) é opcional.

## Erros de execução

Alguns erros só podem ser detetados quando o programa está a correr (não
na compilação) — por exemplo aceder a uma posição de array que não
existe, ou dividir por zero. Nesses casos, o compilador ALGO mostra uma
mensagem em português em vez do traceback do Python:

```
Erro em tempo de execução: tentaste aceder a uma posição de array que
não existe (índice fora dos limites).
```

São reconhecidos assim: índice de texto ou de array fora dos limites,
divisão por zero, overflow numérico, recursão infinita (função que
nunca chega ao caso base), aceder a um campo de um valor nulo, e
valores fora do domínio válido de uma operação (ex.: raiz quadrada de
um número negativo, ou converter um texto inválido para número).

## Estruturas (registos)

`estrutura` agrupa vários campos com nome sob um único tipo, tal como um
"struct"/"record". Os campos acedem-se com `.`:

```
estrutura Ponto
    x:inteiro
    y:inteiro

estrutura Retangulo
    canto:Ponto        // uma estrutura pode conter outra
    largura:inteiro
    altura:inteiro

funcao area(r:Retangulo):inteiro
    devolver r.largura * r.altura

procedimento deslocar(ref p:Ponto, dx:inteiro, dy:inteiro)
    p.x = p.x + dx
    p.y = p.y + dy

inicio
    p1:Ponto              // campos começam com o valor por omissão do seu tipo
    p1.x = 3
    p1.y = 4
    deslocar(p1, 10, 20)

    pontos:Ponto[10]      // array de estruturas: cada posição é independente
    pontos[0].x = 100
```

Também podes inicializar uma estrutura com um literal `{campo: valor, ...}`
— campos que omitas ficam com o valor por omissão do seu tipo:

```
p1:Ponto = {x: 3, y: 4}
p2:Ponto = {x: 10}          // y fica 0 (valor por omissão de inteiro)
```

> Nota: em Python (o alvo principal), tal como os arrays, uma estrutura
> passada por valor a uma função partilha os mesmos dados do original —
> só `ref` garante que as alterações se propagam de volta de forma
> explícita e visível no código. Evita alterar campos de um parâmetro que
> não seja `ref`.

## Fluxogramas

```bash
algo fluxograma meuprograma.algo
algo fluxograma meuprograma.algo --funcao nomeDaFuncao
algo fluxograma meuprograma.algo --formato svg
```

Por omissão, gera um ficheiro `.dot` (formato Graphviz) para o programa
principal **e também um para cada função/procedimento** do programa —
por exemplo, um programa com uma função `dobro` gera
`meuprograma.dot` e `meuprograma_dobro.dot`. Usa `--funcao` para gerar
só o fluxograma de uma função/procedimento específico, em vez de todos.
Se tiveres o Graphviz instalado (comando `dot`), as imagens (`.png` por
omissão) são geradas automaticamente a partir dos `.dot`. Caso
contrário, os `.dot` podem ser abertos em qualquer visualizador de
Graphviz (incluindo sites online, para colar o conteúdo do ficheiro).

Uma instrução que chama uma função/procedimento **definido no teu
programa** aparece com um retângulo de **contorno duplo** — o símbolo
tradicional de fluxograma para "sub-rotina" — em vez de tentar meter a
lógica dessa função dentro do mesmo diagrama (o que ficaria ilegível,
sobretudo com recursividade): o diagrama próprio dessa função é o
`.dot`/imagem com o nome correspondente. Chamadas a bibliotecas
(`matematica.raiz(...)`) não têm este destaque, porque não têm um diagrama
próprio.

## Realce de sintaxe no VS Code

Há uma extensão mínima de realce de sintaxe (cores) para ficheiros
`.algo` em `algo_lang/editors/vscode-algo/`. Para instalar, copia essa
pasta para a pasta de extensões do VS Code (`~/.vscode/extensions/` no
macOS/Linux, `%USERPROFILE%\.vscode\extensions\` no Windows) e reinicia
o editor. Instruções completas e detalhes técnicos em
`algo_lang/editors/vscode-algo/README.md`.

## Linter

```bash
algo verifica meuprograma.algo
```

Analisa o programa em busca de possíveis enganos que não impedem a
compilação — por isso são avisos, não erros:

- Variáveis declaradas mas nunca usadas (variáveis de controlo de `para`
  ficam de fora desta verificação, porque é normal usá-las só para
  contar iterações)
- Parâmetros nunca usados
- Funções/procedimentos nunca chamados em lado nenhum do programa
- Divisão por zero óbvia (`x / 0`)
- Comparações sempre verdadeiras/falsas (`x == x`)
- Parâmetros ou variáveis locais com o mesmo nome de uma variável global
  (não é proibido, mas pode confundir)
- Uma função/procedimento que acede diretamente a uma variável global
  **mutável** (leitura ou escrita), em vez de a receber como parâmetro —
  funciona, mas acopla a função ao resto do programa e torna-a mais
  difícil de perceber e reutilizar isoladamente. Aceder a uma
  `constante` global não conta para este aviso, porque um valor fixo
  não tem o mesmo problema (é o equivalente a usar `math.PI`)
- Ciclo `enquanto`/`faz...enquanto` controlado por uma variável
  `booleano` (bandeira) que nunca é alterada dentro do próprio corpo do
  ciclo — nunca termina (ver [Sair de um ciclo a meio](#sair-de-um-ciclo-a-meio))
- Função/procedimento que se chama a si próprio sem nenhuma estrutura
  de controlo (`se`/`escolher`/`para`/`enquanto`/`faz...enquanto`) em
  lado nenhum do corpo — nunca atinge um caso base
- Comparação de igualdade (`==`/`<>`) entre dois valores `decimal` —
  arriscada por imprecisão de vírgula flutuante

## Testes automatizados

Há uma suite de testes (pytest) na pasta `algo_lang/tests/`, com 792 testes
cobrindo a linguagem base, `estrutura` (incluindo literais), `constante`,
comentários de bloco, literais de array (com N dimensões), `afirmar`,
erros de execução amigáveis, o modo `--debug`, o linter e fluxogramas.

```bash
pip install -e ".[dev]"     # instala o pytest
pytest algo_lang/tests/ -v
```

Os testes de fluxograma que dependem do Graphviz (`dot`) são
automaticamente ignorados se o Graphviz não estiver instalado no
sistema.

## Verificação de tipos em tempo de compilação

O compilador verifica tipos antes de gerar Python, com erros claros e
com o número da linha:

```
❌ Erro semântico na linha 4: não é possível atribuir um valor
   do tipo 'cadeia' à variável 'x' (tipo 'inteiro')
```

Também deteta: condições não booleanas, limites de `para` não inteiros,
chamadas com argumentos errados, funções sem `devolver`, índices de
array não inteiros, bibliotecas não importadas, e variáveis não
declaradas.

## Exemplos incluídos

Na pasta `exemplos/` (na raiz do projeto, ao lado de `algo_lang/`):
- `soma.algo` — declarações inline, array, ciclo `para`
- `troca.algo` — `ref` em procedimentos e em funções
- `matriz_escolha.algo` — matriz 2D, `escolher/caso`, `enquanto`, `fazer...enquanto`, variável global
- `leitura.algo` — `ler()`, `caracter`, concatenação com `+`
- `estruturas.algo` — `estrutura`, aninhamento, `ref` com estruturas, array de estruturas
- `novas_funcionalidades.algo` — `constante`, comentários de bloco, literais de array, `afirmar`
- `avancado.algo` — literais de estrutura `{campo: valor}`, arrays de 3 dimensões
- `bibliotecas_demo.algo` + `geometria.algo` — `importar` e `incluir`

```bash
cd exemplos
algo executa soma.algo
```
