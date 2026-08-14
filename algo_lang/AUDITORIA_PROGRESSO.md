# Progresso da correção da AUDITORIA.md

Acompanha a correção dos 30 bugs (`B1`..`B30`) listados em `AUDITORIA.md`.
Âmbito desta passagem: só a secção "1. Bugs". As secções 2 (melhorias UX),
3 (conceptuais) e 4 (lixo) ficam de fora, salvo indicação em contrário.

Convenção: cada bug corrigido ganha um ID `AL-NN` sequencial (próximo
livre indicado abaixo), usado em comentários no código e, quando fizer
sentido, no nome do teste de regressão em
`algo_lang/tests/test_correcoes_auditoria.py`.

**Próximo ID livre: AL-44** (atualizar depois de cada correção)

Como retomar: ver qual é o primeiro bug com estado `[ ]` abaixo e
continuar a partir daí. Correr `python3 -m pytest algo_lang/tests/ -v`
antes de começar para confirmar que o estado atual está verde.

**Nota sobre a suite de testes neste ambiente (Windows):** ~89 testes já
falhavam no HEAD original, ANTES de qualquer correção desta auditoria --
todos por motivos de ambiente (encoding cp1252 do console Windows,
`FileNotFoundError` ao invocar subprocessos), não por bugs de lógica.
Lista completa guardada durante a sessão em
`/tmp/baseline_failed.txt` (fora do repositório, não persiste entre
sessões -- se precisares, regenera com
`python -m pytest algo_lang/tests/ -q -m "not slow" 2>&1 | grep "^FAILED" | sort`
no HEAD antes de mexer em nada). Ao verificar regressões, compara a
CONTAGEM (371 passed / 89 failed na baseline) e a lista de nomes, não
assumas que "algum teste falha" = regressão tua.

## Lexer (`compilador/lexer.py`)
- [x] B1 [ALTA] `/* */` sem espaço funde tokens adjacentes -- AL-41
- [x] B2 [ALTA] Aspas escapadas confundem remoção de comentários -- AL-42
- [x] B3 [BAIXA] `caracter` sem escape para apóstrofo -- AL-43

## Parser (`compilador/parser.py`)
- [x] B4 [ALTA] Sem limite de profundidade para blocos aninhados -- AL-44
- [x] B5 [MÉDIA] `{}` nunca interpretado como array literal vazio -- AL-45

## Semântica (`compilador/semantics.py`)
- [x] B6 [ALTA] Atribuição a array inteiro não rejeitada -- AL-46
- [x] B7 [ALTA] Tamanhos de arrays em campos de `estrutura` não validados -- AL-48
- [x] B8 [ALTA] `_contem_devolver` não verifica todos os caminhos -- AL-49
- [x] B9 [ALTA] `ler` aceita arrays/structs como alvo -- AL-47
- [x] B10 [ALTA] Parâmetros nunca verificados contra colisão de nomes -- AL-50
- [x] B11 [ALTA] Structs por valor não copiadas (cross-cutting semantics/codegen) -- AL-52
- [x] B12 [MÉDIA] Mensagens de `_tipo_lvalue` usam nome base, não sub-caminho -- AL-53
- [x] B13 [MÉDIA] Conflito de tipo em ramos irmãos não detetado -- AL-54
- [x] B14 [MÉDIA] `escrever` de struct inteira não rejeitado -- AL-55
- [x] B15 [BAIXA] `Escolha` não deteta `caso` duplicados -- AL-56

(B17, codegen, também corrigido nesta passagem -- AL-51 -- por partilhar
código com B11.)

## Codegen (`compilador/codegen.py` / `codegen_minimo.py` / `gerador_base.py`)
- [x] B16 [ALTA] `base ^ expoente` negativa/fracionária devolve `complex` -- AL-57
- [x] B17 [ALTA] Falta coerção inteiro→decimal em retorno de `ref` -- AL-51 (feito com B11)
- [x] B18 [MÉDIA-ALTA] Elementos de array literal não coagidos p/ decimal -- AL-58
- [x] B19 [MÉDIA] `codegen_minimo.py`: `div`/`mod` via `float` perdem precisão -- AL-59
- [x] B20 [MÉDIA] `codegen_minimo.py`: `matematica.potencia` perde tipo decimal -- AL-60

## CLI / inclusões / bibliotecas
- [x] B21 [ALTA] `--debug`/`--json` sai com código 0 mesmo com erro -- AL-61
- [x] B22 [ALTA] Dedup de `incluir` sensível a maiúsculas/minúsculas -- AL-62 (só `algo_lang/cli.py`; `online/executor.py` já usa `os.path.realpath`, que resolve capitalização real em Windows -- não tocado, fora do âmbito desta auditoria)
- [x] B23 [MÉDIA] Consola memoriza ficheiro falhado como "último ficheiro" -- AL-63
- [x] B24 [MÉDIA] `cadeia.caracter` inconsistente com `subcadeia` p/ índices negativos -- AL-64
- [x] B25 [MÉDIA] `conversao.paraInteiro` trunca decimal mas rejeita cadeia equivalente -- AL-65

## Tools (`tracer.py`, `flowchart.py`, `linter.py`)
- [x] B26 [ALTA] Linter: falso positivo p/ variáveis de `inicio` usadas só em funções -- AL-66
- [x] B27 [ALTA] Tracer: variáveis com `_` invisíveis no trace -- AL-67
- [x] B28 [ALTA] Tracer: linha salta para trás em procedimentos só com `ref`; `OverflowError` não traduzido -- AL-68
- [x] B29 [MÉDIA] Linter: campos em falta não cobre literais como argumento -- AL-69
- [x] B30 [MÉDIA] Linter: atribuição a parâmetro por valor não cobre `ler(...)` -- AL-70

---

## TODOS OS 30 BUGS (B1-B30) CORRIGIDOS -- 2026-08-14

Suite completa: `python -m pytest algo_lang/tests/ -q -m "not slow"` -- 419
passed / 89 failed (mesmos 89 da baseline original, todos falhas de
AMBIENTE Windows pré-existentes, não relacionadas com estas correções --
ver nota no topo deste ficheiro). Todas as correções têm teste de
regressão em `algo_lang/tests/test_correcoes_auditoria.py` (secção
"Segunda auditoria") ou em `test_linter.py`.

### Bug adicional encontrado (fora da lista B1-B30) -- CORRIGIDO -- AL-71

Ao escrever o teste de regressão de B27, descobri um bug distinto e
pré-existente em `tools/tracer.py:gerar_trace` (`tracer()`, o ramo do
evento `"return"` para `NOME_FUNCAO_PRINCIPAL`): quando a ÚLTIMA
instrução do bloco `inicio` é uma chamada a uma função/procedimento do
utilizador (ex.: `escrever(f(10))` como última linha), o código que
"corrige" o último passo ao `_algo_programa` terminar sobrescrevia
sempre `passos[-1]` -- mas nesse momento `passos[-1]` podia ser o
ÚLTIMO PASSO DENTRO DA FUNÇÃO CHAMADA (ex. 'f'), não o passo da própria
`_algo_programa`. O resultado: o último passo do trace de dentro da
função ficava com a pilha errada (só "Principal", perdendo o frame da
função) e com a consola já avançada demais; o passo real da última
instrução nunca era atualizado com o efeito de a ter executado.

Corrigido (2026-08-14, mesma sessão): `_indice_do_ultimo_passo_em_principal()`
procura o último passo com pilha só "Principal" (não presume
`passos[-1]`) antes de o sobrescrever. Teste de regressão:
`test_trace_nao_corrompe_passo_quando_ultima_instrucao_chama_funcao`
em `test_correcoes_auditoria.py`.

---

## Notas de progresso (append-only, mais recente no topo)

- 2026-08-14: Documento criado, início da correção sistemática por módulo.
