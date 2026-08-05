# -*- coding: utf-8 -*-
"""O que o Alguem sabe sobre a sintaxe do ALGO, para as suas pistas e
exemplos (nível 5, pseudocódigo parcial) usarem sempre a sintaxe
verdadeira -- 'devolver', não 'retorna'; 'fazer', não 'faz'; arrays a
começar em 0; etc.

A lista de palavras-chave vem diretamente de algo_lang.compilador.lexer
-- não é uma cópia escrita à mão que possa desatualizar-se se a
linguagem mudar. Se algo_lang não estiver acessível (o Alguem também
tem de funcionar copiado sozinho, sem a pasta do ALGO ao lado), cai
para uma lista de reserva e avisa uma vez, em vez de rebentar."""
import os
import sys
import warnings

_RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _RAIZ_PROJETO not in sys.path:
    sys.path.insert(0, _RAIZ_PROJETO)

try:
    from algo_lang.compilador.lexer import PALAVRAS_CHAVE
    from algo_lang.compilador.semantics import NUMERICOS, TEXTUAIS
    _TIPOS_PRIMITIVOS = sorted(NUMERICOS | TEXTUAIS | {"booleano"})
    _PALAVRAS_CHAVE = sorted(PALAVRAS_CHAVE)
    _FONTE = "algo_lang (importado diretamente do compilador)"
except ImportError:  # pragma: no cover -- testado por subprocesso isolado (test_conhecimento_algo.py), a medição de cobertura não segue por processos separados com cwd diferente
    warnings.warn(
        "Não consegui importar algo_lang -- o Alguem vai usar uma lista de "
        "palavras-chave de reserva, que pode não estar atualizada. Corre o "
        "Alguem a partir da pasta do ALGO (como sibling de algo_lang/) para "
        "usar sempre a lista verdadeira.", stacklevel=2)
    _PALAVRAS_CHAVE = sorted([
        "algoritmo", "inicio", "estrutura", "escrever", "ler", "se", "entao",
        "senao", "para", "de", "ate", "passo", "fazer", "enquanto", "escolher",
        "caso", "contrario", "funcao", "procedimento", "devolver", "ref",
        "importar", "incluir", "verdadeiro", "falso", "e", "ou", "nao", "div",
        "mod", "constante", "afirmar",
    ])
    _TIPOS_PRIMITIVOS = sorted(["inteiro", "decimal", "cadeia", "caracter", "booleano"])
    _FONTE = "lista de reserva (algo_lang não estava acessível)"


REFERENCIA_SINTAXE = """\
Referência rápida da sintaxe do ALGO (usa SEMPRE esta sintaxe exata \
nas tuas pistas e exemplos -- nunca inventes palavras-chave nem uses \
sintaxe de outra linguagem, como Python ou pseudocódigo genérico):

- Estrutura: `algoritmo "Nome"`, corpo principal depois de `inicio`.
- Declarar uma variável: `nome:tipo` (ex: `total:inteiro`), com valor \
inicial opcional: `total:inteiro = 0`.
- Tipos primitivos: {tipos}.
- Verbos das palavras-chave de ação estão sempre no INFINITIVO: \
`escrever`, `ler`, `devolver`, `fazer`, `escolher`, `importar`, \
`incluir`, `afirmar` -- nunca "escreve", "retorna", "faz" isolado, \
"escolha".
- Decisão: `se condicao entao` / `senao se condicao entao` / `senao`, \
sem dois pontos no fim da linha.
- Decisão múltipla: `escolher expr` / `caso valor1, valor2` / \
`contrario`.
- Ciclo contado: `para i de inicio ate fim fazer` (opcionalmente \
`passo N`).
- Ciclo condicional: `enquanto condicao fazer`.
- Ciclo com teste no fim: `fazer` ... `enquanto condicao` (executa \
sempre pelo menos uma vez).
- Funções: `funcao nome(param:tipo):tipo_de_retorno`, terminam sempre \
com `devolver valor`. Procedimentos: `procedimento nome(param:tipo)`, \
não devolvem valor.
- Parâmetros por referência: `ref nome:tipo` (só faz sentido em \
funções/procedimentos).
- Arrays começam em 0: `v:inteiro[5]`, primeiro elemento é `v[0]`.
- Operadores: `==`, `<>` (diferente), `<=`, `>=`, `e`, `ou`, `nao`, \
`div` (divisão inteira), `mod` (resto).
- Estruturas: `estrutura Nome` com campos `nome:tipo`, um por linha.
- Comentários: `//` até ao fim da linha, ou `/* ... */`.
- NÃO há chavetas `{{}}` para blocos -- a indentação (tabs OU grupos \
de 4 espaços, nunca misturados) é o que define o bloco.

Todas as palavras-chave da linguagem: {palavras}.
""".format(
    tipos=", ".join(_TIPOS_PRIMITIVOS),
    palavras=", ".join(_PALAVRAS_CHAVE),
)
