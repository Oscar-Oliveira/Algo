# -*- coding: utf-8 -*-
"""Lexer para a linguagem algorítmica ALGO (baseada em português)."""

PALAVRAS_CHAVE = {
    "algoritmo", "inicio", "estrutura",
    "escrever", "ler",
    "se", "entao", "senao",
    "para", "de", "ate", "passo", "fazer",
    "enquanto",
    "escolher", "caso", "contrario",
    "funcao", "procedimento", "devolver", "ref",
    "importar", "incluir",
    "verdadeiro", "falso", "nulo",
    "e", "ou", "nao",
    "div", "mod",
    "constante", "afirmar",
}


class Token:
    __slots__ = ("tipo", "valor", "linha")

    def __init__(self, tipo, valor, linha):
        self.tipo = tipo
        self.valor = valor
        self.linha = linha

    def __repr__(self):  # pragma: no cover -- só para depuração manual, nunca chamado em produção
        return f"Token({self.tipo}, {self.valor!r}, linha={self.linha})"


class ErroLexico(Exception):
    def __init__(self, mensagem, linha):
        super().__init__(f"Erro léxico na linha {linha}: {mensagem}")
        self.linha = linha


SIMBOLOS_MULTI = [
    ("==", "IGUAL"),
    ("<>", "DIFERENTE"),
    ("<=", "LE"),
    (">=", "GE"),
]
SIMBOLOS_SINGLE = {
    "+": "MAIS", "-": "MENOS", "*": "VEZES", "/": "DIVIDE",
    "^": "POTENCIA", "=": "ATRIB", "<": "MENOR", ">": "MAIOR",
    "(": "LPAREN", ")": "RPAREN", "[": "LBRACKET", "]": "RBRACKET",
    "{": "LBRACE", "}": "RBRACE",
    ":": "COLON", ",": "COMMA", ".": "DOT",
}


def _remover_comentarios_bloco(codigo: str) -> str:
    """Remove comentários /* ... */ do texto completo, preservando o número
    de linhas (substitui o conteúdo removido por quebras de linha) para que
    os números de linha nas mensagens de erro continuem corretos."""
    resultado = []
    i = 0
    n = len(codigo)
    dentro_str = False
    dentro_char = False
    while i < n:
        c = codigo[i]
        if (dentro_str or dentro_char) and c == "\\" and i + 1 < n:
            # AL-42: um '\"'/'\\' escapado dentro de uma string (ou um '\''
            # escapado dentro de um caracter) não pode alternar dentro_str/
            # dentro_char -- ao contrário do que este laço fazia antes,
            # tratando toda aspa como fecho real. Sem isto, uma string como
            # "say \" then // not a comment" fechava cedo demais no '\"', e
            # o '//' a seguir apagava o resto da linha como se fosse
            # comentário.
            resultado.append(codigo[i:i + 2])
            i += 2
            continue
        if not dentro_str and not dentro_char and c == "/" and i + 1 < n and codigo[i + 1] == "/":
            # AL-XX: um '//' de comentário de linha tem de "esconder" o
            # resto da linha desta passagem -- senão um '/*' que apareça
            # depois de um '//' na mesma linha (ex.: "// 2 / 4 * 3, nao
            # e um bloco") é lido como abertura real de comentário de
            # bloco. A remoção efetiva do '//' acontece mais tarde, em
            # _remover_comentario (linha a linha); aqui só avançamos até
            # à quebra de linha sem interpretar o conteúdo.
            j = i
            while j < n and codigo[j] != "\n":
                j += 1
            resultado.append(codigo[i:j])
            i = j
            continue
        if not dentro_str and not dentro_char and c == "/" and i + 1 < n and codigo[i + 1] == "*":
            j = i + 2
            while j + 1 < n and not (codigo[j] == "*" and codigo[j + 1] == "/"):
                j += 1
            if j + 1 >= n:
                linha_abertura = codigo[:i].count("\n") + 1
                raise ErroLexico(
                    "comentário de bloco '/*' nunca foi fechado com '*/'", linha_abertura)
            trecho = codigo[i:j + 2]
            n_newlines = trecho.count("\n")
            # AL-41: um comentário de bloco numa só linha (sem newline
            # nenhum) tem de deixar um separador -- substituí-lo por ""
            # fundia os tokens dos dois lados (ex.: "a/*c*/b" virava o
            # identificador único "ab"). Só quando o comentário TEM
            # newlines é que os preservamos tal-e-qual, para os números de
            # linha a seguir continuarem corretos.
            resultado.append("\n" * n_newlines if n_newlines else " ")
            i += len(trecho)
            continue
        if c == '"' and not dentro_char:
            dentro_str = not dentro_str
        elif c == "'" and not dentro_str:
            dentro_char = not dentro_char
        resultado.append(c)
        i += 1
    return "".join(resultado)


def _medir_indentacao(linha_sem_comentario, linha_num):
    """Devolve (nível, estilo) -- nível em 'unidades' (1 unidade = 1 tab
    OU um grupo de 4 espaços), estilo 'tab'/'espaco'/None (linha sem
    indentação, nível 0). A indentação de uma linha tem de ser feita
    inteiramente com tabs OU inteiramente com espaços em grupos de 4 --
    nunca uma mistura dos dois na mesma linha, nem espaços que não sejam
    múltiplos de 4."""
    sem_indent = linha_sem_comentario.lstrip(" \t")
    bruto = linha_sem_comentario[: len(linha_sem_comentario) - len(sem_indent)]
    if not bruto:
        return 0, None
    tem_tab = "\t" in bruto
    tem_espaco = " " in bruto
    if tem_tab and tem_espaco:
        raise ErroLexico(
            "a indentação mistura tabs e espaços na mesma linha -- usa só tabs "
            "ou só grupos de 4 espaços", linha_num)
    if tem_tab:
        return len(bruto), "tab"
    if len(bruto) % 4 != 0:
        raise ErroLexico(
            f"indentação inválida ({len(bruto)} espaço(s)) -- tem de ser tabs "
            f"ou um múltiplo de 4 espaços", linha_num)
    return len(bruto) // 4, "espaco"


def tokenizar(codigo: str):
    codigo = _remover_comentarios_bloco(codigo)
    linhas = codigo.split("\n")
    tokens = []
    pilha_indent = [0]
    linha_num = 0
    # AL-15: mistura de tabs/espaços entre LINHAS DIFERENTES do mesmo
    # ficheiro -- cada linha isolada pode ser válida (só tabs, ou só
    # grupos de 4 espaços), mas misturar os dois estilos ao longo do
    # ficheiro já era um erro de compilação dentro da mesma linha;
    # agora é consistentemente um erro também entre linhas.
    estilo_indentacao = None
    linha_primeiro_estilo = None

    for linha_num, linha_bruta in enumerate(linhas, start=1):
        linha_sem_comentario = _remover_comentario(linha_bruta)
        linha_stripped = linha_sem_comentario.strip()

        if linha_stripped == "":
            continue

        nivel, estilo = _medir_indentacao(linha_sem_comentario, linha_num)
        if estilo is not None:
            if estilo_indentacao is None:
                estilo_indentacao = estilo
                linha_primeiro_estilo = linha_num
            elif estilo != estilo_indentacao:
                nomes = {"tab": "tabs", "espaco": "espaços"}
                raise ErroLexico(
                    f"o ficheiro mistura indentação por {nomes[estilo]} nesta linha "
                    f"com {nomes[estilo_indentacao]} usados anteriormente (desde a "
                    f"linha {linha_primeiro_estilo}) -- escolhe só um dos dois estilos "
                    f"e usa-o em todo o ficheiro", linha_num)

        if nivel > pilha_indent[-1]:
            # AL-73: um bloco novo tem de aumentar exatamente 1 unidade em
            # relacao ao nivel envolvente -- sem isto, um salto de 2+
            # unidades de uma vez (ex. por engano ao copiar/colar) era
            # aceite em silencio, mascarando um erro de indentacao comum.
            if nivel != pilha_indent[-1] + 1:
                raise ErroLexico(
                    f"indentação avança {nivel - pilha_indent[-1]} níveis de uma vez "
                    f"-- cada bloco novo só pode aumentar 1 nível de indentação",
                    linha_num)
            pilha_indent.append(nivel)
            tokens.append(Token("INDENT", nivel, linha_num))
        while nivel < pilha_indent[-1]:
            pilha_indent.pop()
            tokens.append(Token("DEDENT", nivel, linha_num))
        if nivel != pilha_indent[-1]:  # pragma: no cover -- AL-73 garante pilha_indent contigua (0,1,...,profundidade), logo nivel corresponde sempre a um valor da pilha apos o loop de DEDENT acima; mantido como rede de seguranca defensiva.
            raise ErroLexico("indentação inconsistente", linha_num)

        tokens.extend(_tokenizar_linha(linha_stripped, linha_num))
        tokens.append(Token("NEWLINE", None, linha_num))

    while len(pilha_indent) > 1:
        pilha_indent.pop()
        tokens.append(Token("DEDENT", 0, linha_num))
    tokens.append(Token("EOF", None, linha_num))
    return tokens


def _remover_comentario(linha):
    dentro_str = False
    dentro_char = False
    i = 0
    while i < len(linha):
        c = linha[i]
        if (dentro_str or dentro_char) and c == "\\" and i + 1 < len(linha):
            # AL-42: mesma correção que _remover_comentarios_bloco -- uma
            # aspa escapada não fecha a string/caracter.
            i += 2
            continue
        if c == '"' and not dentro_char:
            dentro_str = not dentro_str
        elif c == "'" and not dentro_str:
            dentro_char = not dentro_char
        elif c == "/" and not dentro_str and not dentro_char and i + 1 < len(linha) and linha[i + 1] == "/":
            return linha[:i]
        i += 1
    return linha


def _tokenizar_linha(linha, linha_num):
    tokens = []
    i = 0
    n = len(linha)
    while i < n:
        c = linha[i]
        if c == " " or c == "\t":
            # AL-72: um tab a meio de uma linha (fora da indentacao, ex.
            # colado de um editor com tabs de alinhamento) e whitespace tal
            # como o espaco -- so a INDENTACAO exige um estilo consistente
            # (ver _medir_indentacao), nao o resto da linha.
            i += 1
            continue
        if c == '"':
            # AL-13: escapes reconhecidos dentro de literais de texto --
            # \" (aspa literal), \\ (barra invertida literal), \n (quebra
            # de linha). Um '\' seguido de outra coisa qualquer não é uma
            # sequência de escape reconhecida e fica tal-e-qual no valor.
            j = i + 1
            buf = []
            while j < n and linha[j] != '"':
                if linha[j] == "\\" and j + 1 < n and linha[j + 1] in ('"', "\\", "n"):
                    buf.append({'"': '"', "\\": "\\", "n": "\n"}[linha[j + 1]])
                    j += 2
                    continue
                buf.append(linha[j])
                j += 1
            if j >= n:
                raise ErroLexico("cadeia de texto não fechada com aspas duplas", linha_num)
            tokens.append(Token("STRING", "".join(buf), linha_num))
            i = j + 1
            continue
        if c == "'":
            # AL-43: mesmos escapes que STRING (\' aspa simples literal, \\
            # barra invertida literal) -- sem isto não havia forma nenhuma
            # de representar um caracter ''' (apóstrofo).
            j = i + 1
            buf = []
            while j < n and linha[j] != "'":
                if linha[j] == "\\" and j + 1 < n and linha[j + 1] in ("'", "\\", "n"):
                    buf.append({"'": "'", "\\": "\\", "n": "\n"}[linha[j + 1]])
                    j += 2
                    continue
                buf.append(linha[j])
                j += 1
            if j >= n:
                raise ErroLexico("carácter não fechado com aspa simples", linha_num)
            conteudo = "".join(buf)
            if len(conteudo) != 1:
                raise ErroLexico(
                    f"um caracter tem de ter exatamente 1 símbolo entre aspas simples "
                    f"(encontrado {conteudo!r}); usa aspas duplas para texto", linha_num)
            tokens.append(Token("CARACTER", conteudo, linha_num))
            i = j + 1
            continue
        if c.isdigit() or (c == "." and i + 1 < n and linha[i + 1].isdigit()):
            # AL-74: um decimal pode comecar por '.' sem digito antes
            # (ex. '.5'), nao so terminar sem digito depois (ex. '1.').
            j = i
            is_float = False
            while j < n and (linha[j].isdigit() or (linha[j] == "." and not is_float)):
                if linha[j] == ".":
                    is_float = True
                j += 1
            texto = linha[i:j]
            if is_float:
                tokens.append(Token("FLOAT", float(texto), linha_num))
            else:
                tokens.append(Token("INT", int(texto), linha_num))
            i = j
            continue
        if c.isalpha() or c == "_":
            j = i
            while j < n and (linha[j].isalnum() or linha[j] == "_"):
                j += 1
            palavra = linha[i:j]
            if palavra in PALAVRAS_CHAVE:
                tokens.append(Token(palavra.upper(), palavra, linha_num))
            else:
                tokens.append(Token("ID", palavra, linha_num))
            i = j
            continue
        achou = False
        for simb, tipo in SIMBOLOS_MULTI:
            if linha[i:i + len(simb)] == simb:
                tokens.append(Token(tipo, simb, linha_num))
                i += len(simb)
                achou = True
                break
        if achou:
            continue
        if c in SIMBOLOS_SINGLE:
            tokens.append(Token(SIMBOLOS_SINGLE[c], c, linha_num))
            i += 1
            continue
        raise ErroLexico(f"caractere inesperado {c!r}", linha_num)
    return tokens
