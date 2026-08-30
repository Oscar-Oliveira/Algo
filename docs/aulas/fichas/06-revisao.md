# Ficha de Trabalho — Aula 6: Revisão (Aulas 1 a 5)

## Antes de começares

Esta aula não tem matéria nova — é só para consolidar. Os exercícios combinam livremente tudo o que já viste: tipos, `constante`, operadores, `se`/`senao se`/`escolher`, `para`/`enquanto`/`fazer ... enquanto`, `sair`/`continuar`, e os padrões de acumulador/contador. Testa sempre o teu programa a correr, não só a lê-lo.

### Exercício 1 — Calculadora de IMC repetida

Usa `fazer ... enquanto` para calcular o IMC de várias pessoas seguidas: pede peso e altura, calcula e classifica o IMC (como na Aula 4/5), e no fim de cada cálculo pergunta se o utilizador quer calcular outro. Repete enquanto a resposta for `verdadeiro`.

### Exercício 2 — Números primos até N

Pede um número `n` (`inteiro`). Usa um `para` de 2 até `n` para percorrer cada número; para cada um, usa outro `para` interior a testar se algum valor entre 2 e ele-menos-1 o divide sem resto (`mod`) — se dividir, não é primo. Escreve só os números primos encontrados.

### Exercício 3 — Sistema de senha com tentativas limitadas

Usa duas `constante` (a senha correta e o número máximo de tentativas). Usa `para` para dar ao utilizador um número limitado de tentativas de acertar a senha, usando `sair` assim que acertar. No fim, escreve se o acesso foi permitido ou bloqueado.

### Exercício 4 — Médias de uma turma

Pede quantos alunos há numa turma. Usa `para` para ler a nota de cada aluno, somando-as (acumulador) e contando quantos têm nota positiva (contador, `>= 9.5`). No fim, calcula e escreve a média da turma, quantos aprovados houve, e classifica a turma como "positiva" ou "negativa".

### Exercício 5 — Jogo de adivinhar um número

Usa uma `constante` com um número secreto. Usa `fazer ... enquanto` para pedir palpites, dizendo "Mais alto!" ou "Mais baixo!" consoante o palpite, e conta quantas tentativas foram precisas até acertar.

### Exercício 6 — Menu com repetição

Usa `fazer ... enquanto` para mostrar repetidamente um menu com 3 opções (por exemplo: somar dois números, multiplicar dois números, sair), lidas com `escolher`/`caso`/`contrario`. O programa só termina quando o utilizador escolhe a opção de sair.
