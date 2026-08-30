# 06 — Funções e procedimentos

Assunto: `funcao` (devolve valor com `retornar`) vs `procedimento` (sem
valor de retorno), parâmetros por valor vs `ref`, âmbito (variáveis
locais vs globais), e recursão.

## `calculadora_geometria.algo`

Calcula áreas de um retângulo, um círculo e um triângulo.

Demonstra: `funcao` com vários parâmetros por valor, `constante` global
(`PI`) visível dentro das funções, `procedimento` que só produz efeito
(`escrever`) sem devolver nada, e chamadas de função livremente dentro de
outra expressão (`areaRetangulo(...) + areaCirculo(...) + ...`) —
permitido porque nenhuma tem parâmetro `ref`.

## `gestor_inventario.algo`

Processa um inventário guardado num vetor: soma, maior valor,
duplicação de quantidades, troca de dois valores.

Demonstra: parâmetro vetor usa colchetes **vazios**
(`v:inteiro[]` — aceita vetor de qualquer tamanho), sempre acompanhado de
um parâmetro `tamanho` à parte, porque a linguagem não tem forma de obter
o tamanho de um vetor dentro da função; `ref` num parâmetro vetor
(`duplicarValores`) para o mutar no próprio vetor do chamador, tal como
`ref` em dois escalares para a troca clássica (`trocar`).

## `recursao_fatorial_fibonacci.algo`

`fatorial` e `fibonacci`, ambas recursivas.

Demonstra: uma função a chamar-se a si própria com um caso base que não
recursa (sem isso seria recursão infinita — erro de execução), e
reaproveita `para` (assunto 04) para chamar `fibonacci` repetidamente e
imprimir os primeiros N termos.
