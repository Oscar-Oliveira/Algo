# Roteiro de Testes Manuais — ALGO

Este roteiro percorre tudo o que foi construído, por ordem. Cada teste
tem: o que fazer, o que colar (se for preciso), e o que esperar de
resultado. Usa as caixas `[ ]` para ires marcando — no fim tens uma
checklist-resumo com tudo outra vez, para uma vista de olhos rápida.

Vais precisar de: a pasta extraída do `.zip`, e um editor de texto
qualquer para criares os ficheiros `.algo` de teste (Bloco de Notas,
TextEdit, VS Code, o que preferires).

---

## 0. Preparação

- [ ] Extrai o `.zip` para uma pasta à tua escolha
- [ ] Confirma que vês estes ficheiros/pastas na raiz: `algo_lang/`,
      `exemplos/`, `tests/`, `pyproject.toml`, `README.md`, `algo.sh`,
      `algo.bat`, `algo.command`
- [ ] Cria uma pasta à parte, por exemplo `testes-manuais/`, para lá
      colocares os ficheiros `.algo` que vais escrever ao longo deste
      roteiro (mantém a pasta do ALGO limpa)

---

## 1. Instalação

Escolhe o método que vais usar no dia a dia (podes testar os dois, mas
não é obrigatório).

### 1a. Script de arranque (recomendado)

- [ ] Corre o script do teu sistema:
  - Linux: `./algo.sh` (num terminal, dentro da pasta)
  - macOS: duplo-clique em `algo.command` (ou `./algo.command` na
    Terminal)
  - Windows: duplo-clique em `algo.bat` (ou `algo.bat` numa consola)
- [ ] **Esperado**: na primeira vez, aparece "Primeira utilização: a
      preparar o ambiente..." e demora uns segundos; no fim, ou abre a
      consola do ALGO (ver secção 5) ou mostra o resultado do comando
      que tenhas passado
- [ ] Fecha e corre outra vez. **Esperado**: desta vez é imediato, sem
      a mensagem de "Primeira utilização"

### 1b. Instalação manual com pip (alternativa)

- [ ] Dentro da pasta do projeto: `pip install -e .`
- [ ] **Esperado**: termina sem erros
- [ ] `algo executa exemplos/soma.algo` (a partir daqui, todos os
      comandos deste roteiro assumem que tens o comando `algo`
      disponível desta forma; se estiveres a usar o script de arranque,
      substitui `algo` por `./algo.sh`, `./algo.command` ou `algo.bat`
      em todos os exemplos abaixo)

---

## 2. Primeiro programa (teste rápido de fumo)

- [ ] Cria `testes-manuais/ola.algo`:

```
algoritmo "Ola"
inicio
    escrever("Ola, ALGO!")
```

- [ ] `algo executa testes-manuais/ola.algo`
- [ ] **Esperado**: `Ola, ALGO!` no ecrã, e uma pasta nova
      `testes-manuais/ola/` criada, com `ola.py` lá dentro

---

## 3. Sintaxe da linguagem

Cada teste tem o ficheiro `.algo` para colares, o comando, e o
resultado exato esperado.

### 3.1 Tipos, variáveis, operadores

- [ ] `testes-manuais/tipos.algo`:

```
algoritmo "Tipos"
inicio
    a:inteiro = 7
    b:decimal = 2.5
    c:cadeia = "texto"
    d:caracter = 'x'
    flag:booleano = verdadeiro
    escrever(a + 3, " ", a div 2, " ", a mod 2, " ", a ^ 2)
    escrever(b * 2)
    escrever(c, " ", d)
    escrever(flag, " ", nao flag)
```

- [ ] `algo executa testes-manuais/tipos.algo`
- [ ] **Esperado**:
```
10 3 1 49
5.0
texto x
verdadeiro falso
```

### 3.2 Decisão: `se`/`senao`, `escolher`/`caso`

- [ ] `testes-manuais/decisao.algo`:

```
algoritmo "Decisao"
inicio
    n:inteiro = 7
    se n mod 2 == 0 entao
        escrever("par")
    senao
        escrever("impar")

    escolher n
        caso 1, 2, 3
            escrever("baixo")
        caso 7
            escrever("sete")
        contrario
            escrever("outro")
```

- [ ] `algo executa testes-manuais/decisao.algo`
- [ ] **Esperado**:
```
impar
sete
```

### 3.3 Ciclos: `para`, `enquanto`, `fazer...enquanto`

- [ ] `testes-manuais/ciclos.algo`:

```
algoritmo "Ciclos"
inicio
    i:inteiro
    para i de 1 ate 3 fazer
        escrever("para: ", i)

    x:inteiro = 0
    enquanto x < 3 fazer
        x = x + 1
    escrever("enquanto: ", x)

    y:inteiro = 0
    fazer
        y = y + 1
    enquanto y < 3
    escrever("fazer-enquanto: ", y)
```

- [ ] `algo executa testes-manuais/ciclos.algo`
- [ ] **Esperado**:
```
para: 1
para: 2
para: 3
enquanto: 3
fazer-enquanto: 3
```

### 3.4 Arrays e matrizes (lembra-te: começam em 0)

- [ ] `testes-manuais/arrays.algo`:

```
algoritmo "Arrays"
inicio
    v:inteiro[3] = {10, 20, 30}
    escrever(v[0], " ", v[1], " ", v[2])

    m:inteiro[2][2] = {{1, 2}, {3, 4}}
    escrever(m[0][0], " ", m[0][1], " ", m[1][0], " ", m[1][1])
```

- [ ] `algo executa testes-manuais/arrays.algo`
- [ ] **Esperado**:
```
10 20 30
1 2 3 4
```

### 3.5 Funções, procedimentos e `ref`

- [ ] `testes-manuais/funcoes.algo`:

```
algoritmo "Funcoes"
funcao dobro(x:inteiro):inteiro
    devolver x * 2
procedimento trocar(ref a:inteiro, ref b:inteiro)
    temp:inteiro = a
    a = b
    b = temp
inicio
    escrever(dobro(5))
    p:inteiro = 3
    q:inteiro = 9
    trocar(p, q)
    escrever("p=", p, " q=", q)
```

- [ ] `algo executa testes-manuais/funcoes.algo`
- [ ] **Esperado**:
```
10
p=9 q=3
```

### 3.6 Recursividade

- [ ] `testes-manuais/recursao.algo`:

```
algoritmo "Recursao"
funcao fatorial(n:inteiro):inteiro
    se n <= 1 entao
        devolver 1
    devolver n * fatorial(n - 1)
inicio
    escrever(fatorial(5))
```

- [ ] `algo executa testes-manuais/recursao.algo`
- [ ] **Esperado**: `120`

### 3.7 Estruturas

- [ ] `testes-manuais/estruturas.algo`:

```
algoritmo "Estruturas"
estrutura Ponto
    x:inteiro
    y:inteiro
inicio
    a:Ponto = {x: 1, y: 2}
    b:Ponto = {x: 1, y: 2}
    c:Ponto
    escrever(a.x, ",", a.y)
    se a == b entao
        escrever("iguais")
    se a == c entao
        escrever("ERRO: nunca devia aparecer")
    senao
        escrever("diferentes de c (correto)")
```

- [ ] `algo executa testes-manuais/estruturas.algo`
- [ ] **Esperado**:
```
1,2
iguais
diferentes de c (correto)
```

### 3.8 Bibliotecas (`Math`, `Cadeia`)

- [ ] `testes-manuais/bibliotecas.algo`:

```
algoritmo "Bibliotecas"
importar Math
importar Cadeia
inicio
    escrever(math.raiz(16.0))
    escrever(cadeia.maiusculas("ola"))
    escrever(cadeia.inverter("abc"))
```

- [ ] `algo executa testes-manuais/bibliotecas.algo`
- [ ] **Esperado**:
```
4.0
OLA
cba
```

### 3.9 `afirmar`

- [ ] `testes-manuais/afirmar.algo`:

```
algoritmo "Afirmar"
funcao dobro(x:inteiro):inteiro
    devolver x * 2
inicio
    afirmar dobro(5) == 10, "dobro(5) devia ser 10"
    escrever("passou no teste")
```

- [ ] `algo executa testes-manuais/afirmar.algo`
- [ ] **Esperado**: `passou no teste`

---

## 4. Comandos do CLI

### 4.1 `compila` (só gera o `.py`, não corre)

- [ ] `algo compila testes-manuais/ola.algo`
- [ ] **Esperado**: `✔ Compilado para: .../ola.py` — e não deve
      aparecer nenhuma saída de execução (porque não corre o programa)

### 4.2 `lint`

- [ ] `testes-manuais/lint_teste.algo`:

```
algoritmo "LintTeste"
inicio
    x:inteiro = 5
    y:inteiro = 10
    escrever(x)
```

- [ ] `algo lint testes-manuais/lint_teste.algo`
- [ ] **Esperado**: um aviso a dizer que `y` é declarada mas nunca
      usada

### 4.3 `fluxograma`

- [ ] `algo fluxograma testes-manuais/decisao.algo`
- [ ] **Esperado**: `✔ Fluxograma gerado: .../decisao.dot`; se tiveres
      o Graphviz instalado, também `✔ Imagem gerada: .../decisao.png` —
      abre essa imagem e confirma que vês um diagrama com losangos de
      decisão

### 4.4 `executa --debug`

- [ ] `algo executa testes-manuais/ciclos.algo --debug`
- [ ] **Esperado**: a mesma saída do teste 3.3, mas com uma linha
      `[debug linha N] ...` a mostrar as variáveis depois de cada passo

### 4.5 `executa --json`

- [ ] `algo executa testes-manuais/ciclos.algo --json`
- [ ] **Esperado**: além da execução normal, `✔ Trace gerado:
      .../ciclos_trace.json` — abre esse ficheiro num editor de texto e
      confirma que é JSON válido (começa com `{` e tem uma lista
      `"passos"`)

### 4.6 `compila --minimo`

- [ ] `algo compila --minimo testes-manuais/afirmar.algo`
- [ ] **Esperado**: `✔ Compilado para: .../afirmar_min.py`
- [ ] Abre `testes-manuais/afirmar/afirmar_min.py` num editor. **Esperado**:
      código Python bem mais curto e direto do que o `.py` normal — sem
      funções tipo `_algo_escrever`, e a linha do `afirmar` deve ser
      literalmente `assert (dobro(5) == 10), "dobro(5) devia ser 10"`

---

## 5. Consola interativa

- [ ] Escreve só `algo` (ou `./algo.sh` / `algo.bat` / duplo-clique em
      `algo.command`), sem mais nada a seguir
- [ ] **Esperado**: abre um ecrã com "Consola ALGO" e a lista dos 4
      comandos principais
- [ ] Escreve: `executa testes-manuais/ola.algo`
- [ ] **Esperado**: compila e corre, mostra `Ola, ALGO!`
- [ ] Escreve só: `lint` (sem nome de ficheiro)
- [ ] **Esperado**: usa `ola.algo` automaticamente (o último usado) —
      não deve pedir o nome outra vez
- [ ] Escreve: `ajuda`
- [ ] **Esperado**: lista detalhada dos 4 comandos, cada um com as
      respetivas flags e exemplos
- [ ] Escreve um comando propositadamente errado: `xyz`
- [ ] **Esperado**: mostra um erro e sugere escrever `ajuda` — **a
      consola não deve fechar**, continua a mostrar `algo>`
- [ ] Escreve: `sair`
- [ ] **Esperado**: mensagem de despedida, a consola fecha

---

## 6. Casos que já foram bugs (para confirmares que continuam corrigidos)

Estes já foram problemas reais, encontrados e corrigidos ao longo do
projeto — vale a pena confirmares que continuam bem.

### 6.1 Nome que colide com palavra reservada do Python

- [ ] `testes-manuais/colisao.algo`:

```
algoritmo "Colisao"
inicio
    class:inteiro = 5
    escrever(class)
```

- [ ] `algo executa testes-manuais/colisao.algo`
- [ ] **Esperado**: erro claro em ALGO, do tipo `'class' não pode ser
      usado como nome -- é uma palavra reservada do Python` — **não**
      deve compilar nem dar um erro python cru tipo `SyntaxError`

### 6.2 Indentação: tabs e espaços não podem misturar-se na mesma linha

- [ ] Escreve um ficheiro `testes-manuais/indent.algo` em que a
      indentação de uma linha misture tabs com espaços (no teu editor,
      confirma se está a inserir tabs ou espaços — a maioria mostra
      isso no rodapé)
- [ ] `algo executa testes-manuais/indent.algo`
- [ ] **Esperado**: erro léxico claro a mencionar a mistura de tabs e
      espaços

### 6.3 `passo 0` num ciclo `para`

- [ ] `testes-manuais/passozero.algo`:

```
algoritmo "PassoZero"
inicio
    i:inteiro
    para i de 1 ate 10 passo 0 fazer
        escrever(i)
```

- [ ] `algo executa testes-manuais/passozero.algo`
- [ ] **Esperado**: erro de compilação claro (`o 'passo' de um ciclo
      'para' não pode ser 0`) — **não** deve mostrar um traceback
      Python

### 6.4 Array com índice fora dos limites

- [ ] `testes-manuais/indicemau.algo`:

```
algoritmo "IndiceMau"
inicio
    v:inteiro[3]
    escrever(v[10])
```

- [ ] `algo executa testes-manuais/indicemau.algo`
- [ ] **Esperado**: mensagem amigável (`índice fora dos limites`), sem
      traceback Python à mostra

---

## 7. Atualizar (se voltares a fazer isto no futuro)

- [ ] Extrai uma nova versão do `.zip` **por cima** da pasta atual
      (mesmo nome, mesmo sítio)
- [ ] Corre o script de arranque outra vez
- [ ] **Esperado**: arranca logo (sem "Primeira utilização"), já com o
      código novo — não precisas de apagar nada

---

## Checklist-resumo

- [ ] 0. Preparação — ficheiros extraídos
- [ ] 1. Instalação — funciona (script de arranque e/ou pip)
- [ ] 2. Primeiro programa — corre e dá o resultado certo
- [ ] 3.1 Tipos/operadores — resultado certo
- [ ] 3.2 Decisão (`se`/`escolher`) — resultado certo
- [ ] 3.3 Ciclos — resultado certo
- [ ] 3.4 Arrays/matrizes — resultado certo
- [ ] 3.5 Funções/procedimentos/`ref` — resultado certo
- [ ] 3.6 Recursividade — resultado certo
- [ ] 3.7 Estruturas — resultado certo
- [ ] 3.8 Bibliotecas — resultado certo
- [ ] 3.9 `afirmar` — resultado certo
- [ ] 4.1 `compila` — gera o `.py` sem correr
- [ ] 4.2 `lint` — deteta a variável não usada
- [ ] 4.3 `fluxograma` — gera o diagrama
- [ ] 4.4 `--debug` — mostra as variáveis passo a passo
- [ ] 4.5 `--json` — gera um `.json` válido
- [ ] 4.6 `compila --minimo` — gera Python mínimo
- [ ] 5. Consola interativa — abre, lembra o ficheiro, `ajuda`, erro
      não fecha, `sair` funciona
- [ ] 6.1 Colisão com palavra Python — erro claro
- [ ] 6.2 Indentação mista — erro claro
- [ ] 6.3 `passo 0` — erro claro, sem traceback
- [ ] 6.4 Índice fora dos limites — erro amigável, sem traceback
- [ ] 7. Atualização — substituir ficheiros funciona sem reinstalar

Se chegaste ao fim com tudo marcado, está tudo a funcionar como
esperado. Se alguma coisa não bateu certo com o "Esperado", diz-me
exatamente qual o passo e o que aconteceu em vez disso.
