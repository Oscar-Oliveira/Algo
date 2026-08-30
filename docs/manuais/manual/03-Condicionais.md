# 3. Condicionais

## 3.1 `se` / `senao`

```algo
inicio
    idade:inteiro
    escrever("Idade: ")
    ler(idade)

    se idade >= 18 entao
        escrever("Maior de idade")
    senao
        escrever("Menor de idade")
```

- A condição depois de `se` tem de ser `booleano` — `se idade entao` (um
  `inteiro` usado diretamente como condição, como em C/Python) é erro de
  compilação, não "0 é falso, o resto é verdadeiro". Escreve sempre a
  comparação por extenso: `se idade <> 0 entao`.
- `senao` é opcional.

### `senao se` — várias condições em cadeia

```algo
inicio
    nota:decimal
    escrever("Nota: ")
    ler(nota)

    se nota >= 18.0 entao
        escrever("Excelente")
    senao se nota >= 14.0 entao
        escrever("Bom")
    senao se nota >= 9.5 entao
        escrever("Suficiente")
    senao
        escrever("Reprovado")
```

As condições são testadas por ordem, de cima para baixo, e só o
**primeiro** ramo verdadeiro executa (mesmo que uma condição mais abaixo
também fosse verdadeira) — tal como `if`/`elif`/`else` em Python ou
`else if` em C/Java.

## 3.2 `escolher` / `caso` / `contrario`

Alternativa a uma cadeia longa de `senao se` quando se está a comparar
sempre a **mesma** expressão contra vários valores possíveis:

```algo
inicio
    diaSemana:inteiro
    escrever("Dia da semana (1-7): ")
    ler(diaSemana)

    escolher diaSemana
        caso 1
            escrever("Segunda")
        caso 2
            escrever("Terça")
        caso 6, 7
            escrever("Fim de semana")
        contrario
            escrever("Dia inválido")
```

- Um `caso` pode ter **vários valores separados por vírgula** (`caso 6,
  7` acima) — executa se a expressão de `escolher` for igual a
  **qualquer um** deles.
- **Não há fallthrough**: ao contrário de `switch` em C/Java, um `caso`
  nunca "cai" para o seguinte — não precisa de `sair`/`break` no fim de
  cada um. Só um ramo executa (o primeiro cujo valor bate certo), tal
  como numa cadeia `senao se`.
- `contrario` é opcional, tal como `senao` em `se`.
- Os valores de `caso` não têm de ser literais — podem ser qualquer
  expressão do mesmo tipo (ou de um tipo comparável — ver abaixo) que a
  expressão de `escolher`; são comparados com `==`, um a um, por ordem.

### Deteção de `caso` repetido

O compilador rejeita um `caso` cujo valor já apareceu num `caso`
anterior do mesmo `escolher` — esse ramo nunca seria alcançado. A
deteção compara por **valor**, não por tipo exato: `caso 1` e `caso
1.0`, ou `caso "a"` e `caso 'a'`, contam como o mesmo valor (tal como
`1 == 1.0` e `"a" == 'a'` são `verdadeiro` na linguagem):

```algo
inicio
    x:decimal = 2.0
    escolher x
        caso 1
            escrever("um")
        caso 2
        // caso 2.0             // ERRO de compilação: '2.0' já apareceu (é o mesmo que '2')
            escrever("dois")
```

Só é detetado quando o valor do `caso` é reconhecível em compilação (um
literal, incluindo um literal numérico negado como `caso -1`) — dois
`caso` com a mesma variável ou expressão calculada não são comparados
entre si (o compilador não sabe se dão o mesmo valor sem correr o
programa).

## 3.3 Âmbito de uma variável declarada dentro de um ramo

Uma variável declarada dentro de um ramo de `se`/`escolher` só existe
**dentro** desse ramo — sempre desaparece depois do bloco, mesmo que a
MESMA variável (mesmo nome, tipo e número de dimensões) seja declarada
em todos os ramos irmãos:

```algo
inicio
    x:inteiro = 5
    se x > 0 entao
        sinal:cadeia = "positivo"
        escrever(sinal)
    // escrever(sinal)          // ERRO: 'sinal' não existe aqui fora

    idade:inteiro = 20
    se idade >= 18 entao
        estado:cadeia = "adulto"
    senao
        estado:cadeia = "menor"
    // escrever(estado)         // ERRO: 'estado' não existe aqui fora,
                                 // mesmo declarada nos dois ramos
```

Para usar o valor depois do bloco, declara a variável ANTES do `se` e
atribui dentro de cada ramo:

```algo
inicio
    idade:inteiro = 20
    estado:cadeia
    se idade >= 18 entao
        estado = "adulto"
    senao
        estado = "menor"
    escrever(estado)            // válido: 'estado' foi declarada antes do 'se'
```

## Exemplo completo

```algo
algoritmo "ClassificadorTriangulo"

inicio
    a:decimal
    b:decimal
    c:decimal
    escrever("Lado a: ")
    ler(a)
    escrever("Lado b: ")
    ler(b)
    escrever("Lado c: ")
    ler(c)

    se a + b <= c ou a + c <= b ou b + c <= a entao
        escrever("Não é um triângulo válido")
    senao se a == b e b == c entao
        escrever("Equilátero")
    senao se a == b ou b == c ou a == c entao
        escrever("Isósceles")
    senao
        escrever("Escaleno")
```
