# Achados durante a escrita do manual

Melhorias conceptuais, inconsistências e bugs encontrados ao escrever
`docs/manual/`, por capítulo. Cada achado é reportado aqui (não no
próprio capítulo) para que um achado que obrigue a rever conteúdo já
escrito não fique perdido a meio de outro ficheiro.

Estado de cada achado: 🟢 confirmado só por leitura do código · 🟡
confirmado a correr o compilador · ⚪ por decidir (só uma observação,
pode ser intencional).

---

## Capítulo 1 — Introdução e tipos

### 1. Valor por omissão de `caracter` viola a invariante "exatamente 1 símbolo" — ✅ corrigido

`DEFAULT_POR_TIPO["caracter"]` (`algo_lang/compilador/gerador_base.py:29`)
é `""` (cadeia vazia), não um símbolo. Confirmado gerando código para
`c:caracter` sem valor inicial: gera `c = ""`.

Em todos os outros pontos da linguagem, `caracter` é garantidamente 1
símbolo: o lexer rejeita um literal `'...'` com 0 ou 2+ símbolos
(`lexer.py:274`), e `ler()` para `caracter` só aceita input com
`len(resp) == 1`. Só o valor por omissão de uma declaração sem
inicializador quebra essa garantia — um programa que declara
`c:caracter` e o lê (`escrever(c)`) antes de o atribuir mostra uma cadeia
vazia, não um erro nem um símbolo válido.

Impacto prático baixo (o padrão pedagógico é sempre `ler()` logo a
seguir a declarar), mas era uma inconsistência de tipo real: um valor
`caracter` que nunca deveria poder existir, existia.

**Corrigido**: `DEFAULT_POR_TIPO["caracter"]`
(`algo_lang/compilador/gerador_base.py:30`) passou de `'""'` para
`'" "'` (um espaço) — decisão confirmada com o maintainer. Um `c:caracter`
sem valor inicial fica agora `' '`, satisfazendo a invariante em todo o
resto da linguagem.

Efeito colateral encontrado e corrigido: `algo_lang/tests/test_biblioteca_conversao.py::test_para_ascii_de_caracter_por_omissao_vazio_da_erro_nosso_nao_traceback`
dependia especificamente do valor por omissão vazio para exercitar a
verificação defensiva `len(c) != 1` de `conversao.paraAscii` — essa
verificação existia precisamente por causa deste buraco (evidência de
que já tinha sido notado antes, mas nunca corrigido na origem). Teste
reescrito como `test_para_ascii_de_caracter_por_omissao_e_um_espaco_valido`,
a documentar o novo comportamento em vez do antigo. A verificação
`len(c) != 1` em `conversao.py` foi deixada tal como estava (defesa em
profundidade — nenhum caminho da linguagem consegue hoje produzir um
`caracter` vazio, mas não custa manter a rede de segurança). Suite
completa corrida depois da alteração (`pytest algo_lang/tests/ -m "not
slow"`): mesmas 44 falhas pré-existentes de ambiente (subprocessos de
CLI/symlink que já falhavam antes desta alteração, confirmado com `git
stash`), nenhuma nova.

### 2. `bin/ReferenciaCompletaCLI.md` diz que a indentação usa só espaços — mas o lexer aceita tabs — 🟢

`docs/bin/ReferenciaCompletaCLI.md:232` ("Os blocos são delimitados por
**indentação** — usa sempre espaços, não tabs.") contradiz
`lexer.py:_medir_indentacao`, que trata tabs como um estilo de
indentação de primeira classe, tão válido como grupos de 4 espaços — só
proíbe MISTURAR os dois estilos dentro do mesmo ficheiro. Um ficheiro
indentado inteiramente com tabs compila normalmente.

Isto é uma imprecisão de documentação existente (não deste manual novo),
a corrigir separadamente nesse ficheiro quando fizer sentido.

### 3. `codegen_minimo.py` foi apagado mas continua citado como existente — ✅ corrigido

Ao investigar o achado 1 (`DEFAULT_POR_TIPO`, partilhado entre os dois
geradores segundo o cabeçalho de `gerador_base.py`), `algo_lang/compilador/codegen_minimo.py`
não existe no repositório (`git log --diff-filter=D` confirma que foi
apagado no commit `cc78b3d`, o commit mais recente). Ficaram por
atualizar:

- `context/project-overview.md` — secção "Compiler pipeline" descreve
  `codegen_minimo.py` como o caminho de código de `compila --minimo`,
  incluindo comportamento específico (`afirmar`→`assert`,
  `matematica.raiz`→`math.sqrt`); `algo_lang/cli.py` não tem nenhuma
  flag `--minimo`.
- `algo_lang/compilador/gerador_base.py` (docstring do módulo) e
  `algo_lang/compilador/codegen.py:812,852` — comentários que continuam
  a explicar decisões "para dar suporte a `codegen_minimo.py`"/"--minimo".
- Referências em `algo_lang/tests/test_correcoes_auditoria.py` e
  `algo_lang/tests/test_fuzzing_e_propriedades.py` (não verificado se são
  testes ainda a exercitar algo real ou só comentários/nomes de teste
  órfãos).

Não era um bug de comportamento (o compilador não afirma ter `--minimo`
nalgum sítio executável), só documentação/comentários desatualizados —
mas `context/project-overview.md` é lido automaticamente como instrução
de projeto (`CLAUDE.md`), por isso uma descrição errada da pipeline ali
tinha mais impacto do que um comentário solto.

**Corrigido**: `context/project-overview.md` já não descreve
`codegen_minimo.py`/`--minimo` como existentes — passou a mencionar
`gerador_base.py`/`GeradorCodigoBase` como o resto real dessa divisão
(hoje com uma só subclasse, `GeradorCodigo`). Comentários/docstrings em
`gerador_base.py` (cabeçalho do módulo, `ErroInternoCompilador`,
`_coagir_decimal`, `_gerar_atribuicao`, `_gerar_funcao`), `codegen.py`
(`_gerar_atribuicao`, dois pontos) e `semantics.py`
(`verificar_nomes_python`) atualizados para não descrever a estrutura
atual do código em termos de um ficheiro/flag que já não existe. Ao
corrigir o comentário de `gerador_base.py:_gerar_atribuicao` confirmou-se
que o ramo `A.EstruturaLiteral` aí (linhas ~155-160) é hoje código morto
de facto — `codegen.py` (única subclasse) intercepta sempre esse caso
antes de chamar `super()`; deixado no lugar com o comentário a
documentar isso (não é bug — código morto assinalado, não apagado,
seguindo a instrução de projeto em `CLAUDE.md`).
Referências a `--minimo`/`codegen_minimo.py` que sobraram em
`test_correcoes_auditoria.py` e `test_fuzzing_e_propriedades.py` foram
inspecionadas e são narrativa histórica válida (notas de auditoria sobre
um bug já corrigido, ou justificação de uma regra que se manteve) em
testes que continuam a exercitar comportamento real — não precisam de
alteração. Suite completa corrida depois da alteração
(`pytest algo_lang/tests/ -m "not slow"`): mesmas 44 falhas
pré-existentes de ambiente (idênticas às do achado 1), nenhuma nova —
consistente com esta correção ser só documentação/comentários.

---

## Capítulo 2 — Operadores

### 4. `2^3^2` tipa como `decimal` (`512.0`), não `inteiro`, apesar de todo o expoente ser literal — ✅ corrigido

Confirmado a correr o compilador: `escrever(2^3^2)` imprime `512.0`, não
`512`. Causa: `^` é associativo à direita, por isso isto é `2^(3^2)`; o
tipo do `^` exterior só é `inteiro` se `_expoente_estaticamente_nao_negativo`
(`semantics.py:1335`) conseguir provar que o expoente (aqui, a
subexpressão `3^2`) nunca é negativo, e essa função só sabe "dobrar" em
compilação expressões feitas de `+`/`-`/`*` sobre literais/`constante`
(a mesma limitação já documentada em
`docs/DecisoesELimitacoesConhecidas.md` para tamanhos de vetor
constantes) — `^` dentro do próprio expoente não é reconhecido, mesmo
sendo só literais e o valor mais interno sendo claramente `9` (positivo).
O mesmo já acontecia (e está documentado) para o caso mais óbvio,
`2^n` com `n` variável — mas o caso `2^3^2` é mais surpreendente porque
não envolve nenhuma variável: é um valor 100% conhecido em compilação
que mesmo assim não é reconhecido como não-negativo.

Efeito prático: `x:inteiro = 2^3^2` é erro de compilação ("'decimal' não
cabe em 'inteiro'"), obrigando a `x:decimal = 2^3^2` ou a
`conversao.paraInteiro(2^3^2)` para um valor que já se sabe, só de olhar
para o código, que é inteiro exato.

Impacto muito baixo na prática (potências encadeadas com `^` são raras
em código pedagógico), mas era uma inconsistência de tipo real, e
`x:inteiro = 2^3^2` sendo erro de compilação para um valor 100%
conhecido como inteiro era surpreendente.

**Corrigido**: `_resolver_constante` (`semantics.py`) passou a "dobrar"
também `^` (além de `+`/`-`/`*`) — devolve `None` se o expoente
resolvido for negativo (dobrar isso daria um valor fracionário, fora do
que a função promete devolver), caso contrário `esq ** dire`. Efeito em
cadeia previsto (e pretendido pelo maintainer): `_expoente_estaticamente_nao_negativo`
reaproveita `_resolver_constante`, por isso passa a reconhecer `2^3^2`
(exponente `3^2` agora dobrável) como não-negativo, tipando a expressão
`inteiro`; e tamanhos de vetor definidos com `^` encadeado (ex.:
`constante N:inteiro = 2^3^2; v:inteiro[N]`) também passam a ser
resolvidos estaticamente pelas mesmas verificações que já usam
`_resolver_constante` (`_validar_dims`, valor inicial de `constante`).
Teste `test_cadeia_de_potencia_moderada_continua_a_funcionar`
(`test_correcoes_auditoria.py`) atualizado: `2^2^2` passa a imprimir
`"16"` (inteiro), não `"16.0"`. Suite completa corrida depois da
alteração (`pytest algo_lang/tests/ -m "not slow"`): mesmas 44 falhas
pré-existentes de ambiente, nenhuma nova.

### 8. `docs/manual/02-Operadores.md`, secção 2.4, continuava a descrever o bug do achado 4 como se estivesse por corrigir — ✅ corrigido

Encontrado numa segunda passagem de auditoria ao manual (posterior à
correção do achado 4 no compilador): o próprio texto do capítulo 2
nunca foi atualizado depois de `_resolver_constante` passar a dobrar
`^`. `docs/manual/02-Operadores.md:113` mostrava
`escrever(2^3^2)         // 512.0     (decimal! -- ver nota abaixo)` —
confirmado a correr o compilador que o resultado real hoje é `512`
(inteiro), não `512.0`. A caixa "**Nota / achado**" logo a seguir
(linhas 121-128) repetia a descrição do bug como atual e ligava para
`ACHADOS.md`, onde o mesmo achado 4 já estava marcado "✅ corrigido" —
uma contradição direta entre dois documentos do próprio manual. A
frase de contexto ("Isto só acontece quando o expoente é um literal
não-negativo ou uma expressão feita só de literais/`constante`
combinados com `+`/`-`/`*`") também ficou incompleta, sem `^` na lista
de operadores dobráveis.

Causa-raiz do processo: ao resolver o achado 4, a correção foi feita em
`ACHADOS.md` e `DecisoesELimitacoesConhecidas.md`, mas não se verificou
se o capítulo do manual que originou o achado também citava o exemplo
como texto normal (não só numa caixa de nota) — nesse caso ficou,
porque a caixa "Nota/achado" não é a ÚNICA menção ao bug no capítulo, é
só a mais óbvia.

**Corrigido**: linha 113 atualizada para `512` (sem o "decimal!"); caixa
"Nota/achado" removida (mesmo padrão já seguido no achado 6, capítulo
7); frase de contexto atualizada para incluir `^` na lista de
operadores que `_resolver_constante` sabe dobrar. Confirmado a correr
o compilador que o exemplo agora bate certo com o texto.

---

## Capítulo 5 — Vetores e matrizes

### 5. `DecisoesELimitacoesConhecidas.md` diz que "atribuição, declaração" copiam vetor por valor — falso, as duas são erro de compilação para vetor — ✅ corrigido

`docs/DecisoesELimitacoesConhecidas.md`, secção "Cópia por valor e
`ref`": *"Atribuição, declaração, `retornar`, e literais `{...}`
copiam structs/vetores por valor (...) Só `ref` cria aliasing"*.

Confirmado a correr o compilador que isto é verdade para `estrutura`
(`p2:Ponto = p1` copia por valor, mutar `p2` não afeta `p1`), mas
**não** para vetor:

```algo
v1:inteiro[3] = {1, 2, 3}
v2:inteiro[3]
v2 = v1                    // ErroSemantico: 'v2' é um vetor; não pode
                            // ser atribuído diretamente
v3:inteiro[3] = v1         // ErroSemantico: 'v1' é um vetor; falta
                            // indexá-lo (ex: v1[i])
```

As duas formas de "cópia" que a frase atribui a vetor e struct por
igual (`atribuição`, `declaração` a partir de uma variável) na verdade
nunca chegam a copiar nada para um vetor — são rejeitadas em
compilação antes disso (`semantics.py`: `_tipo_expr` recusa um vetor
"nu" fora de `permitir_vetor` — só argumento de chamada e `retornar`
passam essa flag; a verificação de alvo de atribuição em
`_verificar_stmt`/`A.Atribuicao` rejeita `dims_alvo > 0`
incondicionalmente). Só `retornar`, literal `{...}`, e passar como
argumento normal (sem `ref`) a uma função — todos já cobertos pela
mesma flag `permitir_vetor` — de facto copiam um vetor por valor.

Impacto: um leitor de `DecisoesELimitacoesConhecidas.md` que confiasse
literalmente na frase escreveria `v2 = v1` à espera de uma cópia e
levaria um erro de compilação (não um bug silencioso — o compilador
protege corretamente, só a documentação está desalinhada com o que o
compilador realmente aceita).

**Corrigido**: a entrada "Cópia por valor e `ref`" em
`DecisoesELimitacoesConhecidas.md` passou a separar os dois casos —
`estrutura` (atribuição, declaração, `retornar`, literais copiam por
valor) de `vetor` (só `retornar`, literais, e passagem como argumento
copiam por valor; atribuição/declaração a partir doutra variável são
`ErroSemantico` em compilação, não aliasing nem cópia silenciosa), com
a referência concreta a `semantics.py` (`_tipo_expr`/`permitir_vetor`,
verificação de `dims_alvo` no alvo de atribuição) que já estava
descrita aqui no achado. Não havia código para corrigir — só a
documentação.

### 9. `escrever(a, b)` concatena sem separador — dois exemplos (capítulos 5 e 6) mostravam um `// resultado` que implicava um espaço — ✅ corrigido

Confirmado a correr o compilador: `_algo_escrever` (`codegen.py`, gera
`print("".join(_algo_fmt(v) for v in valores))`) junta os argumentos de
`escrever(...)` com `""`, não com espaço — `escrever(2, 3)` imprime
`"23"`, nunca `"2 3"`. Isto não é bug de comportamento (é a decisão de
design de sempre, `escrever` não insere separador nenhum por conta
própria — quem quiser um espaço tem de o passar como argumento de
texto explícito, `escrever(a, " ", b)`, padrão já seguido
corretamente na esmagadora maioria dos exemplos do manual, capítulo 7
incluído).

Dois exemplos esqueceram esse `" "` explícito e mostravam um comentário
`// resultado` que só faz sentido com um espaço:
- `docs/manual/05-Vetores-e-Matrizes.md:86` —
  `escrever(m[0][1], m[1][0])     // 2 3` produzia de facto `"23"`.
- `docs/manual/06-Funcoes-e-Procedimentos.md:64` —
  `escrever(x, y)        // 2 1` produzia de facto `"21"`.

**Corrigido**: `" "` acrescentado como argumento extra em ambos
(`escrever(m[0][1], " ", m[1][0])` e `escrever(x, " ", y)`), verificado
a correr o compilador que agora produzem exatamente `"2 3"`/`"2 1"`.
Varrida a totalidade do manual à procura de mais ocorrências do mesmo
padrão (`escrever` com vários argumentos e um `//` a seguir) — todas as
outras já usavam `" "`/`", "` explícito.

---

## Capítulo 7 — Estruturas

### 6. "Idioma de percurso de uma lista ligada" (comentário em `semantics.py`) não deixa claro que só serve para percorrer, não para construir por mutação — ✅ corrigido

`semantics.py` (perto de `_tipos_comparaveis`) comenta que `nulo`
comparar com qualquer `estrutura` existe para suportar "o idioma de
percurso de uma lista ligada" (`enquanto no <> nulo fazer ...`).
Confirmado que a leitura/percurso funciona bem (`imprimir` percorrendo
com `enquanto n <> nulo`), mas o comentário não avisa que, como
`estrutura` copia por valor em TODO lado — incluindo ao atribuir a um
campo (`no.seguinte = outroNo` copia `outroNo` para dentro do campo) —
o padrão imperativo clássico de "criar um nó, ligá-lo a outro já
existente, e mutar esse nó mais tarde" **não propaga** através do
campo já copiado:

```algo
b:No = {valor: 2, seguinte: nulo}
a:No = {valor: 1, seguinte: b}
b.valor = 99
escrever(a.seguinte.valor)   // 2, não 99 -- a.seguinte já era uma cópia de 'b'
```

Confirmado a correr o compilador. Não é um bug (é a consequência direta
e consistente de "estrutura copia por valor sempre", já documentada em
`DecisoesELimitacoesConhecidas.md` para outros contextos) — mas é um
efeito surpreendente especificamente para quem já viu listas ligadas
com referências reais em Java/C/Python, e o comentário que menciona o
"idioma" não avisa da limitação. A construção correta (recursiva/
funcional, de baixo para cima, nunca mutando um nó já devolvido) FOI
testada e funciona (ver capítulo 7 do manual, secção 7.5).

**Corrigido, mas não como sugerido inicialmente**: em vez de acrescentar
uma entrada em `DecisoesELimitacoesConhecidas.md` (documento interno de
decisões de arquitetura, não material dirigido a quem aprende a
linguagem), decidiu-se com o maintainer que o sítio certo para esta
explicação já era o capítulo 7 do manual — e, ao verificar, já lá
estava, com o mesmo exemplo `b`/`a` deste achado, a explicação de
porquê falha, a construção correta (7.5, de baixo para cima) e a
alternativa de vetor indexado por `inteiro` para identidade partilhada
mutável. A caixa "Nota / achado" nessa secção (que apontava para este
achado e sugeria a entrada em `DecisoesELimitacoesConhecidas.md`) foi
removida, por estar resolvida. Só o comentário em `semantics.py`
(`_tipos_comparaveis`, perto de `'nulo' compara-se com qualquer tipo de
estrutura`) precisava mesmo de correção — atualizado para qualificar
que o "idioma" é só de percurso, com uma referência cruzada à secção
7.5 do manual.

---

## Capítulo 8 — Bibliotecas

### 7. `conversao.paraBooleano("0")` dá `verdadeiro`, não `falso` — ✅ corrigido

Confirmado a correr o compilador: `conversao.paraBooleano("0")` →
`verdadeiro`, enquanto `conversao.paraBooleano(0)` (inteiro) →
`falso`. Causa: só a lista fixa `"falso"/"f"/"false"/"não"/"nao"/"n"`
converte texto para `falso` (`bibliotecas/conversao.py`); qualquer
outro texto não vazio, incluindo `"0"`, segue a truthiness nativa do
Python (`bool(x)`), e uma cadeia não vazia é sempre truthy
independentemente do que lá está escrito.

Não era bug de comportamento inconsistente com o resto da linguagem —
era uma lacuna na lista fixa (que já existia deliberadamente para
"não"/"nao", evitar que a própria palavra portuguesa para "não" virasse
`verdadeiro` por ser texto não vazio) que não cobria `"0"`, uma
armadilha igualmente plausível para quem vier de outras
linguagens/formatos onde `"0"` textual costuma significar falso (JSON,
variáveis de ambiente, CSV).

**Corrigido**: `"0"` (com espaços/maiúsculas à volta, como os outros)
adicionado à lista fixa em `conversao.py` (`conversao_paraBooleano`),
com o comentário do código atualizado a justificar o porquê. Casos de
teste `('"0"', "falso")` e `('"1"', "verdadeiro")` adicionados a
`test_para_booleano` (`test_biblioteca_conversao.py`). Suite completa
corrida depois da alteração (`pytest algo_lang/tests/ -m "not slow"`):
mesmas 44 falhas pré-existentes de ambiente, nenhuma nova.

---

## Capítulo 10 — `afirmar` e tratamento de erros

### 10. Números de linha citados nas mensagens de erro dos exemplos estavam errados — ✅ corrigido

Confirmado a correr os três exemplos como ficheiros `.algo` reais
(cabeçalho `algoritmo "..."` + o bloco exatamente como mostrado no
manual — os blocos, à semelhança do resto do manual, omitem esse
cabeçalho por brevidade). Nenhum dos três batia com o `(linha N)`
citado:
- `docs/manual/10-Afirmar-e-Tratamento-de-Erros.md:19` (exemplo
  `afirmar` com mensagem) citava `linha 3`; real é `linha 4`.
- `docs/manual/10-Afirmar-e-Tratamento-de-Erros.md:31` (exemplo
  `afirmar` sem mensagem) citava `linha 3`; real também é `linha 4`.
- `docs/manual/10-Afirmar-e-Tratamento-de-Erros.md:69` (exemplo divisão
  por zero) citava `linha 3`; real é `linha 5`.

O texto da própria mensagem (formato, separador ` — `, `❌ Afirmação
falhou (linha N): ...`, `Erro em tempo de execução: divisão por
zero.`) estava exato — só o número. Causa provável: os números foram
escritos a contar as linhas visíveis no bloco (sem o cabeçalho
`algoritmo` que o capítulo 1 exige mas este capítulo omite nos
exemplos), sem confirmar contra uma execução real com esse cabeçalho
incluído — nenhum outro capítulo do manual cita um número de linha
concreto na saída, precisamente porque essa contagem depende de um
cabeçalho que o próprio bloco não mostra.

**Corrigido**: os três números concretos substituídos por `N`
genérico, com uma frase a esclarecer que `N` é a linha real no
ficheiro completo (incluindo o cabeçalho `algoritmo` omitido no
excerto) — evita citar um número que só está certo para uma escolha
específica, não mostrada, de onde o cabeçalho fica.

---

## Índice / meta

### 11. `00-Indice.md` subcontava quantos achados mudaram comportamento real do compilador — ✅ corrigido

`docs/manual/00-Indice.md`, secção "Estado geral", dizia: *"7 achados
registados... 1 corrigido no compilador (valor por omissão de
`caracter`), 6 são notas de documentação/conceito a rever (nenhum bug
de comportamento novo por corrigir no compilador)"*. Falso a partir do
momento em que os achados 4 e 7 foram corrigidos nesta sessão: ambos
mudaram comportamento real do compilador/runtime (tipagem de `^`
encadeado em `semantics.py`; `conversao.paraBooleano("0")` em
`conversao.py`) — a frase ficou desatualizada assim que essas duas
correções aconteceram, contradizendo o texto "Corrigido" dos próprios
achados 4 e 7 mais abaixo no mesmo `ACHADOS.md`. Também misturava, sob
a mesma etiqueta "a rever", achados já corrigidos (3, 5, 6) com o único
que continua deliberadamente por corrigir (achado 2, fora do âmbito
deste manual).

**Corrigido**: reescrito para contar corretamente 6 achados já
corrigidos (3 com mudança real de comportamento do compilador: achados
1, 4, 7; os outros 3 só documentação/comentários: achados 3, 5, 6) e 1
deliberadamente adiado (achado 2). Confirmado só por leitura cruzada
com o resto de `ACHADOS.md` — não precisa de correr o compilador.
