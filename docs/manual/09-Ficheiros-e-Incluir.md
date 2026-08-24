# 9. Ficheiros e `incluir`

`incluir "ficheiro.algo"` junta o conteúdo de outro ficheiro `.algo`
teu ao programa principal — diferente de `importar` (capítulo 8), que
só serve para as três bibliotecas embutidas da linguagem.

## 9.1 Um ficheiro incluído não é um programa completo

Um ficheiro pensado para ser incluído **não tem** `algoritmo "Nome"`
nem bloco `inicio` — só o que pode aparecer antes de `inicio` num
programa normal: `constante`, variáveis globais, `estrutura`,
`funcao`/`procedimento`, e o seu próprio `incluir` (ver 9.3).

```algo
// geometria.algo
constante PI:decimal = 3.14159

funcao areaCirculo(raio:decimal):decimal
    retornar PI * raio * raio
```

```algo
// principal.algo
algoritmo "Principal"

incluir "geometria.algo"

inicio
    escrever(areaCirculo(2.0))     // 12.56636
```

As funções/`constante`/variáveis do ficheiro incluído passam a existir
**tal como se estivessem definidas diretamente no programa principal**
— chamam-se sem prefixo nenhum (`areaCirculo(...)`, não
`geometria.areaCirculo(...)`), a não ser que uses `como` (9.2).

O caminho em `incluir "..."` é relativo à **pasta do ficheiro que tem o
`incluir`** — não necessariamente a pasta do programa principal (ver
9.3 para inclusões encadeadas).

## 9.2 `incluir ... como <alias>`

Junta um prefixo às funções do ficheiro incluído, para evitar colisão
de nomes ou só para deixar claro de onde vêm:

```algo
algoritmo "Principal"

incluir "geometria.algo" como geo

inicio
    escrever(geo.areaCirculo(2.0))     // 12.56636
```

Com `como`, o nome **sem** prefixo deixa de existir — só
`geo.areaCirculo(...)` funciona, `areaCirculo(...)` sozinho já não. O
alias namespacea só as **funções**; uma `estrutura` ou variável global
do ficheiro incluído continua a juntar-se sem prefixo, com ou sem
`como`.

## 9.3 Colisões e inclusões repetidas

- Um `funcao`/`estrutura`/variável global incluído com o mesmo nome de
  algo que já existe no programa principal (ou noutra inclusão já
  processada) é erro de compilação — mesmo entre categorias diferentes
  (uma função incluída chamada `Ponto` colidindo com uma `estrutura
  Ponto` já definida, por exemplo):

  ```algo
  algoritmo "Principal"

  incluir "geometria.algo"

  funcao areaCirculo(raio:decimal):decimal    // ERRO: colide com a incluída
      retornar 0.0

  inicio
      escrever(areaCirculo(2.0))
  ```

- Incluir o **mesmo ficheiro duas vezes com o mesmo alias** (ou sem
  alias nas duas vezes) é inofensivo — a segunda vez é ignorada. Com um
  alias **diferente** da primeira vez, é erro de compilação (evita que
  o mesmo conteúdo apareça duas vezes sob dois nomes diferentes, o que
  seria confuso).
- Um ficheiro incluído pode ele próprio ter `incluir` (inclusão
  transitiva) — o caminho desse `incluir` aninhado é relativo à pasta
  **desse** ficheiro, não à do programa principal. Um ciclo (A inclui
  B, B inclui A) não trava o compilador — o mesmo caminho já processado
  nunca é reprocessado.
- Incluir um ficheiro que não existe é erro de compilação com uma
  mensagem que nomeia o caminho em falta, não um erro genérico de
  sistema de ficheiros.

## Exemplo completo

```algo
// validacoes.algo
funcao ehPositivo(x:decimal):booleano
    retornar x > 0.0

funcao dentroDoIntervalo(x:decimal, minimo:decimal, maximo:decimal):booleano
    retornar x >= minimo e x <= maximo
```

```algo
// principal.algo
algoritmo "NotaValida"

incluir "validacoes.algo"

inicio
    nota:decimal
    escrever("Nota (0 a 20): ")
    ler(nota)

    se nao ehPositivo(nota) entao
        escrever("A nota não pode ser negativa")
    senao se nao dentroDoIntervalo(nota, 0.0, 20.0) entao
        escrever("A nota tem de estar entre 0 e 20")
    senao
        escrever("Nota válida: ", nota)
```
