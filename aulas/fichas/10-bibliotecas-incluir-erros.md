# Ficha de Trabalho — Aula 10: Bibliotecas, `incluir` e Tratamento de Erros

## Antes de começares

- `importar Matematica`/`Cadeia`/`Conversao` no topo do ficheiro; chama-se com `nome_em_minusculas.funcao(...)`.
- `incluir "ficheiro.algo" como <nome>` junta as `funcao`/`procedimento` de outro ficheiro teu (chamas com `<nome>.funcao(...)`); `constante`/variáveis globais continuam sem prefixo.
- `afirmar condicao, mensagem` para o programa logo se a condição for falsa; nunca é desativado.
- Os exercícios 2 e 8 precisam de **dois** ficheiros `.algo` (uma "biblioteca" e um "principal") — usa a mesma pasta para os dois, e `incluir` com o nome do ficheiro da biblioteca.
- Testa sempre o teu programa a correr, não só a lê-lo.

## Parte 1 — Exercícios desta aula

### Exercício 1 — Verificador de palíndromo

Usa `importar Cadeia`. Pede uma palavra, e usa `cadeia.minusculas` e `cadeia.inverter` para verificar se é um palíndromo (lê-se igual ao contrário — ex.: "ovo", "reviver").

### Exercício 2 — Conversor de temperatura com `incluir`

Cria um ficheiro `biblioteca_conversoes.algo` com as funções `celsiusParaFahrenheit` e `fahrenheitParaCelsius`. Cria um ficheiro `principal.algo` que os `incluir`, pede uma temperatura em Celsius, e escreve o valor em Fahrenheit.

### Exercício 3 — Calculadora de idade com `afirmar`

Usa uma `constante ANO_ATUAL`. Pede o ano de nascimento, e usa `afirmar` para garantir que não é maior que o ano atual (não pode ser no futuro). Calcula e escreve a idade.

## Parte 2 — Revisão da Aula 9

### Exercício 4 — Média de alunos com estrutura

Define uma `estrutura Aluno` com `nome` (`cadeia`) e `nota` (`decimal`). Pede quantos alunos há, lê os dados para um vetor de `Aluno`, e calcula a média das notas.

### Exercício 5 — Renomear por referência

Define uma `estrutura Pessoa` com `nome` e `idade`. Escreve um `procedimento renomear(ref pessoa:Pessoa, novoNome:cadeia)` que muda o nome. Testa mostrando o nome antes e depois.

## Parte 3 — Consolidação (Aulas 1 a 10)

### Exercício 6 — Catálogo com biblioteca de texto

Define uma `estrutura Produto` com `nome` (`cadeia`) e `preco` (`decimal`). Declara um vetor de produtos com um literal. Usa `importar Cadeia` para escrever cada nome em maiúsculas junto ao preço.

### Exercício 7 — Validador de idades de turma

Define uma `estrutura Aluno` com `nome` e `idade`. Pede os dados de vários alunos para um vetor, usando `afirmar` para garantir que cada idade está entre `0` e `120`. No fim, calcula a idade média.

### Exercício 8 — Calculadora de áreas com `incluir` e `afirmar`

Cria um ficheiro `biblioteca_formas.algo` com as funções `areaCirculo(raio)` e `areaRetangulo(base, altura)`, cada uma com um `afirmar` a garantir que os valores recebidos são positivos. Cria um `principal.algo` que os `incluir`, define uma `estrutura Forma` (`tipo:cadeia`, `area:decimal`), pede os dados de um círculo e de um retângulo, guarda os resultados num vetor de `Forma`, e escreve a lista final.
