# Avaliação Contínua 3 — Aulas 10 a 11 (Bibliotecas, `incluir`, Tratamento de Erros)

## Antes de começares

- Duração sugerida: 90 minutos.
- Teste individual — resolve sozinho/a, sem consultar colegas.
- Cada exercício pede um programa `.algo` completo e independente (o Exercício 2 precisa de **dois** ficheiros — uma "biblioteca" e um "principal", na mesma pasta).
- Testa sempre o teu programa a correr antes de o entregar.
- Cotação total: 20 valores (indicada em cada exercício).

### Exercício 1 — Gerador de iniciais (4 valores)

Usa `importar Cadeia`. Pede o nome completo de uma pessoa (nome próprio e apelido, separados por um espaço). Usa `cadeia.dividir` para separar as duas palavras, e escreve as iniciais de cada uma em maiúsculas (ex.: "Maria Silva" → "M. S.").

### Exercício 2 — Conversor de unidades com `incluir` (5 valores)

Cria um ficheiro `biblioteca_unidades.algo` com as funções `metrosParaPes(metros:decimal):decimal` (1 m = 3.28084 pés) e `kgParaLibras(kg:decimal):decimal` (1 kg = 2.20462 libras). Cria um ficheiro `principal.algo` que os `incluir`, pede um valor em metros e um valor em quilogramas, e escreve os dois convertidos.

### Exercício 3 — Validador de reserva de voo (3 valores)

Usa uma `constante CAPACIDADE_AVIAO` (`inteiro`) com o número de lugares do avião. Pede o número de lugares a reservar (`inteiro`), e usa `afirmar` para garantir que o valor é positivo e não ultrapassa a capacidade. Escreve uma confirmação da reserva.

### Exercício 4 — Encomendas por entregar (4 valores)

Define uma `estrutura Encomenda` com os campos `cliente` (`cadeia`), `valor` (`decimal`) e `entregue` (`booleano`). Pede os dados de 3 encomendas para um vetor. Escreve uma `funcao totalEntregues(encomendas:Encomenda[], tamanho:inteiro):inteiro` que conta quantas já foram entregues, e usa-a para escrever o resultado.

### Exercício 5 — Validador de código postal (4 valores)

Usa `importar Cadeia`. Pede um código postal (`cadeia`) no formato `NNNN-NNN` (7 carateres, incluindo o hífen). Usa `cadeia.comprimento` e `afirmar` para garantir que tem exatamente 7 carateres, e `cadeia.caracter` com `afirmar` para garantir que o caráter no índice 4 é `'-'`. Se passar nas duas validações, escreve "Código postal válido".
