# 9. Ficheiros e `incluir`

`incluir "ficheiro.algo" como <nome>` junta o conteúdo de outro
ficheiro `.algo` teu ao programa principal — diferente de `importar`
(capítulo 8), que só serve para as três bibliotecas embutidas da
linguagem.

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

incluir "geometria.algo" como geo

inicio
    escrever(geo.areaCirculo(2.0))     // 12.56636
```

O caminho em `incluir "..."` é relativo à **pasta do ficheiro que tem o
`incluir`** — não necessariamente a pasta do programa principal (ver
9.3 para inclusões encadeadas).

## 9.2 `como <nome>` é sempre obrigatório

`incluir` exige sempre um alias — não há forma de incluir um ficheiro
sem escolher o nome pelo qual as suas funções ficam acessíveis:

- **Funções/procedimentos** do ficheiro incluído passam a chamar-se
  `<nome>.funcao(...)` — nunca `funcao(...)` sozinho.
- **`constante` e variáveis globais** do ficheiro incluído **não**
  levam prefixo nenhum, com qualquer alias — ficam acessíveis tal como
  estão escritas no ficheiro incluído (`PI`, não `geo.PI`).

```algo
algoritmo "Principal"

incluir "geometria.algo" como geo

inicio
    escrever(geo.areaCirculo(2.0))     // 12.56636 -- função, com prefixo
    escrever(PI)                        // 3.14159  -- constante, sem prefixo
```

Esta assimetria existe porque só as funções precisam de namespace para
evitar colisão de nomes de uma forma previsível — uma `estrutura` ou
variável global incluída continua sujeita à verificação de colisão da
secção 9.3.

## 9.3 Colisões e inclusões repetidas

- Uma `estrutura`/variável global incluída com o mesmo nome de algo que
  já existe no programa principal (ou noutra inclusão já processada) é
  erro de compilação — mesmo entre categorias diferentes (uma
  `estrutura`/variável incluída colidindo com uma função já mangled com
  o mesmo nome, por exemplo). Como o alias é sempre obrigatório, uma
  **função** incluída só colide se o seu nome mangled (`<nome>_funcao`)
  já existir no programa principal:

  ```algo
  algoritmo "Principal"

  incluir "geometria.algo" como geo

  constante PI:decimal = 3.14    // ERRO: colide com o PI de geometria.algo
  ```

- Incluir o **mesmo ficheiro duas vezes com o mesmo alias** é
  inofensivo — a segunda vez é ignorada. Com um alias **diferente** da
  primeira vez, é erro de compilação (evita que o mesmo conteúdo
  apareça duas vezes sob dois nomes diferentes, o que seria confuso).
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

incluir "validacoes.algo" como val

inicio
    nota:decimal
    escrever("Nota (0 a 20): ")
    ler(nota)

    se nao val.ehPositivo(nota) entao
        escrever("A nota não pode ser negativa")
    senao se nao val.dentroDoIntervalo(nota, 0.0, 20.0) entao
        escrever("A nota tem de estar entre 0 e 20")
    senao
        escrever("Nota válida: ", nota)
```
