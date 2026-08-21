# -*- coding: utf-8 -*-
"""Gerador de código Python a partir da AST da linguagem ALGO."""

from . import ast_nodes as A
from .. import bibliotecas
from .ast_nodes import texto_expr
from .gerador_base import GeradorCodigoBase, DEFAULT_POR_TIPO, ErroInternoCompilador


CABECALHO_RUNTIME = '''\
# ============================================================
#  Ficheiro gerado automaticamente pelo compilador ALGO
#  NAO EDITAR A MAO -- edita o ficheiro .algo original
# ============================================================

import sys
import copy

sys.setrecursionlimit(10000)

# AUDITORIA_2026-08-19 bug #25: sem isto, 'escrever' de um acento ou
# emoji fora do codepage do ambiente (ex.: cp1252 no Windows) rebentava
# com UnicodeEncodeError -- subclasse de ValueError, por isso caía no
# 'except ValueError' mais abaixo, relabelled como "valor inválido
# ('charmap' codec can't encode character...)", uma mensagem sem
# relação nenhuma com o problema real (o código do estudante estava
# correto). Relevante em produção: online/executor.py limpa as
# variáveis de ambiente do subprocesso do estudante (LANG/LC_ALL/
# PYTHONIOENCODING incluídas), por isso a codificação não pode ficar
# ao critério do ambiente. 'hasattr' porque sys.stdout nem sempre tem
# '.reconfigure()' -- ex.: sob tools/tracer.py (--debug/--json), este
# mesmo ficheiro gerado corre com sys.stdout redirecionado para um
# io.StringIO() em memória (contextlib.redirect_stdout), que não tem
# esse método.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


class _AlgoIndiceCadeiaInvalido(IndexError):
    """AL-09: subclasse de IndexError, para as bibliotecas de texto
    (ex. cadeia.caracter) distinguirem um índice fora dos limites de
    TEXTO de um índice fora dos limites de VETOR -- apanhada antes do
    'except IndexError' genérico, mais abaixo neste ficheiro."""
    pass


def _algo_fmt(v):
    """Formata valores para exibicao (escrever) ao estilo portugues."""
    if isinstance(v, bool):
        return "verdadeiro" if v else "falso"
    if v is None:
        return "nulo"
    if isinstance(v, float):
        # AUDITORIA_2026-08-19 bug #18: str(float) do Python mostra o
        # valor exato guardado em binario -- "0.1 + 0.2" imprimia
        # "0.30000000000000004" em vez de "0.3". Arredondar para 12
        # casas decimais esconde o ruido de representacao binaria em
        # praticamente todo o codigo de ensino, mantendo o ".0" para um
        # 'decimal' de valor inteiro (distingue de 'inteiro' na saida).
        # "-0.0" (atingivel por aritmetica normal, ex.: 0.0 * -1.0) e
        # normalizado para "0.0" -- zero negativo nao tem valor
        # pedagogico nenhum e só confunde. Notacao cientifica
        # (ex.: 10.0^20 -> "1e+20") fica deliberadamente por resolver --
        # fora do alcance razoavel de "arredondar ruido", ver bug #18 em
        # docs/AuditoriaCompilador_2026-08-19.md.
        # AUDITORIA_2026-08-19 bug #18-bis (ronda 13): a normalizacao de
        # "-0.0" tem de correr DEPOIS do arredondamento, nao antes -- um
        # valor que nao e exatamente 0.0 mas ARREDONDA para -0.0 (ex.:
        # -1e-13) continuava a escapar a normalizacao, mostrando "-0.0"
        # na mesma.
        v = round(v, 12)
        if v == 0.0:
            v = 0.0
        return repr(v)
    return str(v)


def _algo_escrever(*valores):
    print("".join(_algo_fmt(v) for v in valores))


def _algo_ler_inteiro(prompt=""):
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print("Valor inválido. Introduza um número inteiro.")


def _algo_texto_para_decimal(texto):
    """AUDITORIA_2026-08-19 bug #19: float() do Python aceita
    "nan"/"inf"/"-inf"/"Infinity" (case-insensitive) e separadores '_' de
    milhar -- nenhum dos dois e um numero decimal valido em ALGO (o
    lexer nao suporta '_' em literais numericos, e nao ha forma de o
    estudante escrever um 'nan'/'inf' literal no codigo-fonte). Usado só
    por '_algo_ler_decimal' (abaixo) -- ao contrário de 'ler()' (entrada
    interativa, onde "nan" é quase sempre um erro de digitação),
    'conversao.paraDecimal' aceita 'nan'/'inf' DE PROPÓSITO (bug #40,
    investigado na ronda 12: é o único ponto de todo o ALGO por onde um
    programa consegue construir esses valores deliberadamente) e por
    isso tem a sua PRÓPRIA verificação, mais permissiva, só para
    separadores '_' -- não reaproveita este helper."""
    t = texto.strip()
    if "_" in t or t.lstrip("+-").lower() in ("nan", "inf", "infinity"):
        raise ValueError(f"'{texto}' não é um número decimal válido")
    return float(t)


def _algo_ler_decimal(prompt=""):
    while True:
        try:
            return _algo_texto_para_decimal(input(prompt))
        except ValueError:
            print("Valor inválido. Introduza um número decimal.")


def _algo_ler_booleano(prompt=""):
    """Deliberadamente mais estrito que conversao.paraBooleano: 'ler' é
    entrada interativa e pode voltar a pedir até o estudante escrever algo
    válido, por isso vale a pena recusar texto ambíguo (ex.: um erro de
    digitação) em vez de o aceitar como 'verdadeiro' por omissão.
    conversao.paraBooleano é uma função de conversão pura (não pode voltar
    a pedir nada) sobre um valor já existente, por isso segue a
    truthiness nativa do Python para qualquer texto não reconhecido --
    são dois contextos diferentes de propósito, não uma inconsistência a
    corrigir."""
    while True:
        resp = input(prompt).strip().lower()
        if resp in ("verdadeiro", "v", "true"):
            return True
        if resp in ("falso", "f", "false"):
            return False
        print("Valor inválido. Introduza 'verdadeiro' ou 'falso'.")


def _algo_ler_texto(prompt=""):
    return input(prompt)


def _algo_ler_caracter(prompt=""):
    while True:
        resp = input(prompt)
        if len(resp) == 1:
            return resp
        print("Valor inválido. Introduza exatamente 1 caracter.")


def _algo_div(a, b):
    """div: divisao INTEIRA TRUNCADA (arredonda em direcao a zero, como
    a maioria das linguagens ensinadas em programacao introdutoria) --
    ao contrario do // nativo do Python, que arredonda para -infinito
    (ex: -7 // 2 = -4, mas -7 div 2 = -3)."""
    q, r = divmod(a, b)
    if r != 0 and (a < 0) != (b < 0):
        q += 1
    return q


def _algo_mod(a, b):
    """mod: resto da divisao truncada (_algo_div) -- sinal igual ao do
    primeiro operando, ao contrario do % nativo do Python."""
    return a - _algo_div(a, b) * b


def _algo_traduzir_valueerro(msg):
    """AL-08/UX-01: traduz as causas mais comuns de ValueError para
    portugues, em vez de mostrar sempre a mensagem crua do Python --
    mantem o generico (mensagem original entre parenteses) como
    recurso para causas nao mapeadas."""
    msg_min = msg.lower()
    if "math domain error" in msg_min:
        return ("o valor está fora do domínio válido desta operação "
                 "(ex: raiz quadrada de um número negativo).")
    if "negative number cannot be raised to a fractional power" in msg_min:
        return "não é possível elevar um número negativo a um expoente fracionário."
    if "invalid literal for int()" in msg_min:
        return "o texto não pode ser convertido para um número inteiro."
    if "could not convert string to float" in msg_min:
        return "o texto não pode ser convertido para um número decimal."
    if "range() arg 3 must not be zero" in msg_min:
        # AUDITORIA_2026-08-19 bug #5: 'passo' só é rejeitado em
        # compilação quando é um LITERAL igual a 0 (semantics.py) -- um
        # 'passo' calculado em runtime (ex.: vindo de uma variável) só
        # é apanhado aqui.
        return "o 'passo' do ciclo 'para' não pode ser zero (o ciclo nunca avançaria)."
    if "cannot convert float infinity to integer" in msg_min:
        # bug #8: conversao.paraInteiro(x) com x = 'infinito'.
        return "não é possível converter 'infinito' para um número inteiro."
    if "int too large to convert to float" in msg_min:
        # bug #8: conversao.paraDecimal(x) com x um inteiro demasiado
        # grande para caber num número decimal.
        return "este número é grande demais para ser convertido para decimal."
    if "exceeds the limit" in msg_min and "integer string conversion" in msg_min:
        # bug #33: proteção do próprio Python (3.11+) contra a conversão
        # inteiro->texto de um número com dígitos a mais (ex.: 'escrever'
        # de 2^100000) -- a mensagem nativa cita
        # 'sys.set_int_max_str_digits()', que não significa nada para um
        # estudante. O CÁLCULO em si não tem limite (inteiro de precisão
        # arbitrária); só mostrá-lo é que tem.
        return "este número tem dígitos a mais para conseguir ser mostrado."
    return f"valor inválido ({msg})."


def _algo_traduzir_attributeerror(msg):
    """Num programa ALGO válido, um AttributeError só pode acontecer ao
    aceder a um campo de um valor 'nulo' -- semantics.py já garante em
    compilação que todos os outros acessos a campos existem e têm o
    tipo certo. Tenta extrair o nome do campo da mensagem nativa do
    Python (ex.: "'NoneType' object has no attribute 'seguinte'") para
    uma mensagem mais específica; sem isso, cai num genérico."""
    prefixo, sufixo = "'NoneType' object has no attribute '", "'"
    if msg.startswith(prefixo) and msg.endswith(sufixo):
        campo = msg[len(prefixo):-len(sufixo)]
        return f"tentaste aceder ao campo '{campo}' de um valor nulo."
    return "tentaste aceder a um campo de um valor nulo."  # pragma: no cover -- defensivo


def _algo_traduzir_nameerror(msg):
    """AUDITORIA_2026-08-19 bug #26: rede de segurança -- a correção
    principal é em semantics.py (_globais_lidas_transitivamente),
    apanhada em compilação; isto cobre qualquer caso que essa análise
    (que só cobre o valor inicial de uma DECLARAÇÃO) não apanhe, ex.:
    uma atribuição normal ou uma chamada solta que leia uma global
    ainda não declarada nesse ponto do programa."""
    prefixo, sufixo = "name '", "' is not defined"
    if msg.startswith(prefixo) and msg.endswith(sufixo):
        nome = msg[len(prefixo):-len(sufixo)]
        return f"a variável '{nome}' foi usada antes de existir um valor nela."
    return "uma variável foi usada antes de existir um valor nela."  # pragma: no cover -- defensivo


def _algo_linha_do_erro(erro):
    """UX-04: percorre o traceback da excecao à procura do frame mais
    profundo que ainda corresponda a uma linha ALGO conhecida (via
    _ALGO_MAPA_LINHAS, definido mais abaixo neste ficheiro, ja que so
    fica completo depois de todo o codigo ser gerado) -- nao basta o
    frame mais profundo de todos, que costuma estar DENTRO de uma
    biblioteca (ex: matematica_raiz -> _math.sqrt), sem linha ALGO
    correspondente; fica sempre com o último frame mapeado antes de
    'descer' para código interno. Devolve None se não encontrar
    nenhum."""
    tb = erro.__traceback__
    linha_algo = None
    while tb is not None:
        candidato = _ALGO_MAPA_LINHAS.get(tb.tb_lineno)
        if candidato is not None:
            linha_algo = candidato
        tb = tb.tb_next
    return linha_algo


def _algo_sufixo_linha(erro):
    linha_algo = _algo_linha_do_erro(erro)
    return f" (linha {linha_algo})" if linha_algo else ""


_ALGO_ERRO_RUNTIME = None


def _algo_registar_erro_runtime(mensagem, linha):
    """AL-23/AL-24: substitui a deteção frágil por texto (endswith de
    frases fixas) que existia em tools/tracer.py -- cada ponto do
    runtime que apanha um erro e termina o programa regista aqui a
    mensagem e a linha, um canal que não depende de nenhuma frase
    específica nem corre o risco de um escrever() legítimo do próprio
    estudante coincidir por acaso com uma dessas frases. Chamada como
    função (não atribuição direta) de propósito -- funciona
    corretamente seja qual for o scope de onde é chamada (corpo
    principal ou dentro de uma função/procedimento), sem precisar de
    'global' em cada local de chamada."""
    global _ALGO_ERRO_RUNTIME
    _ALGO_ERRO_RUNTIME = {"mensagem": mensagem, "linha": linha}


def _algo_pot(a, b):
    """AL-57/B16: ao contrário do Python 2 (de onde a mensagem já
    traduzida em _algo_traduzir_valueerro parece ter sido portada), o
    '**' nativo do Python 3 nunca levanta ValueError para base negativa
    com expoente fracionário -- devolve silenciosamente um número
    complexo (ex.: (-8.0) ** 0.5). matematica.raiz(-1) já tinha uma
    mensagem amigável equivalente para esse domínio inválido; este é o
    caminho gémeo para o operador '^'."""
    if a < 0 and not float(b).is_integer():
        raise ValueError("negative number cannot be raised to a fractional power")
    return a ** b


def _algo_indice(i):
    """Bug #31: um índice negativo (ex.: 'v[-1]') nunca era validado --
    o Python nativo aceita índices negativos (conta a partir do fim),
    por isso 'v[-1]' silenciosamente devolvia/escrevia o ÚLTIMO
    elemento em vez de dar o erro de 'índice fora dos limites' que um
    estudante esperaria. Chamado em toda leitura/escrita indexada (ver
    gerador_base.py:_lvalue), 1D e 2D+ (cada nível de indexação passa
    por aqui). Levanta o mesmo IndexError nativo que já é apanhado e
    traduzido no rodapé do programa gerado -- nenhuma mensagem nova
    precisa de ser adicionada."""
    if i < 0:
        raise IndexError("índice negativo")
    return i


_ALGO_LIMITE_TAMANHO_VETOR = 10_000_000


def _algo_verificar_tamanho_vetor(tam):
    """Um tamanho de vetor calculado em runtime (nao um literal, ja
    apanhado em compilacao) que de negativo silenciosamente produzia
    um vetor vazio -- range(negativo) do Python nao levanta erro
    nenhum. ValueError e reaproveitado de propósito: ja ha um
    'except ValueError' no programa gerado que traduz para a mensagem
    amigavel de 'Erro em tempo de execucao: valor invalido (...)'.

    AUDITORIA_2026-08-19 bug #32: também não havia limite SUPERIOR --
    um tamanho suficientemente grande (literal ou calculado) deixava o
    programa "pendurado" a alocar memória durante segundos, sem
    nenhuma mensagem, em vez de falhar rápido e de forma amigável.
    Este é o único sítio onde QUALQUER dimensão de vetor passa antes
    de ser usada em range() -- tanto para um tamanho literal como
    calculado, e para cada dimensão de um vetor 2D+ (chamado uma vez
    por dimensão) -- por isso não é preciso duplicar esta verificação
    em semantics.py. 10 milhões por dimensão (não o produto entre
    dimensões, que continua sem limite agregado -- fora do âmbito
    desta correção, ver PLANO_CORRECOES_AUDITORIA.md), medido a
    demorar cerca de 1 segundo (100 milhões já demora ~13s)."""
    if tam < 0:
        raise ValueError(f"tamanho de vetor não pode ser negativo (é {tam})")
    if tam > _ALGO_LIMITE_TAMANHO_VETOR:
        raise ValueError(
            f"o tamanho pedido ({tam}) é maior do que o limite permitido "
            f"({_ALGO_LIMITE_TAMANHO_VETOR})")
    return tam

'''

OPS_BIN = {
    "+": "+", "-": "-", "*": "*", "/": "/",
    "==": "==", "<>": "!=", "<": "<", ">": ">", "<=": "<=", ">=": ">=",
    "e": "and", "ou": "or",
}

LEITORES_POR_TIPO = {
    "inteiro": "_algo_ler_inteiro",
    "decimal": "_algo_ler_decimal",
    "booleano": "_algo_ler_booleano",
    "cadeia": "_algo_ler_texto",
    "caracter": "_algo_ler_caracter",
}


class GeradorCodigo(GeradorCodigoBase):
    def __init__(self, programa: A.Programa):
        super().__init__(programa)
        self.registo_bibliotecas = bibliotecas.obter_registo()

    # -------- ponto de entrada --------
    def gerar(self) -> str:
        self.linhas = CABECALHO_RUNTIME.split("\n")

        self.estruturas = {}
        for e in self.programa.estruturas:
            campos = {}
            for c in e.campos:
                dims_n = 0 if c.dims is None else len(c.dims)
                campos[c.nome] = (c.tipo, dims_n)
            self.estruturas[e.nome] = campos

        for imp in self.programa.importares:
            info = self.registo_bibliotecas.get(imp.nome.lower())
            if info is None:  # pragma: no cover -- semantics.py já validou que a biblioteca existe
                continue
            if info["cabecalho"]:
                self.linhas.extend(info["cabecalho"].split("\n"))
            for _nome_metodo, (_cats, _tipo, codigo_py) in info["funcoes"].items():
                self.linhas.extend(codigo_py.split("\n"))

        for e in self.programa.estruturas:
            self._gerar_estrutura(e)

        # tabela de globais = declarações de topo + tudo o que é declarado dentro de 'inicio'
        for d in self.programa.declaracoes:
            self.tabela_tipos_globais[d.nome] = d.tipo
        A.coletar_declaracoes_tipadas(self.programa.corpo, self.tabela_tipos_globais)

        # as funções são geradas antes das globais: o corpo de uma função só
        # é executado quando é chamada, por isso é seguro defini-la aqui
        # mesmo que só venha a ser usada no inicializador de uma global a seguir
        for f in self.programa.funcoes:
            self._gerar_funcao(f)

        for d in self.programa.declaracoes:
            self._linha_algo_atual = d.linha
            self._gerar_declaracao(d, 0, self.tabela_tipos_globais)
        self._linha_algo_atual = None
        if self.programa.declaracoes:
            self.linhas.append("")

        self.emit("def _algo_programa():", 0)
        if self.tabela_tipos_globais:
            self.emit(f"global {', '.join(self.tabela_tipos_globais)}", 1)
        corpo_vazio = not self.programa.corpo
        if corpo_vazio:  # pragma: no cover -- o parser exige >=1 instrução após 'inicio'
            self.emit("pass", 1)
        tipos = dict(self.tabela_tipos_globais)
        for stmt in self.programa.corpo:
            self._gerar_stmt(stmt, 1, tipos)
        self._linha_algo_atual = None
        self.linhas.append("")

        # UX-04: o mapa de linhas (.py gerado -> linha ALGO original) já
        # é sempre construído durante a geração (ver emit()) -- embutido
        # aqui como dados simples no próprio ficheiro gerado, para os
        # handlers de erro em runtime logo a seguir conseguirem mostrar
        # a que linha ALGO corresponde um erro, mesmo fora do modo
        # --debug (que usa este mesmo mapa de forma independente, via
        # tools/tracer.py, correndo o programa sob sys.settrace()).
        self.linhas.append(f"_ALGO_MAPA_LINHAS = {self.mapa_linhas!r}")
        self.linhas.append("")

        self.emit('if __name__ == "__main__":', 0)
        self.emit("try:", 1)
        self.emit("_algo_programa()", 2)
        self.emit("except _AlgoIndiceCadeiaInvalido as _algo_erro:", 1)
        self.emit(
            '_algo_msg = f"Erro em tempo de execução: tentaste aceder a uma posição de '
            'texto que não existe (índice fora dos limites).{_algo_sufixo_linha(_algo_erro)}"', 2)
        self.emit("print(_algo_msg)", 2)
        self.emit("_algo_registar_erro_runtime(_algo_msg, _algo_linha_do_erro(_algo_erro))", 2)
        self.emit("sys.exit(1)", 2)
        self.emit("except IndexError as _algo_erro:", 1)
        self.emit(
            '_algo_msg = f"Erro em tempo de execução: tentaste aceder a uma posição de '
            'vetor que não existe (índice fora dos limites).{_algo_sufixo_linha(_algo_erro)}"', 2)
        self.emit("print(_algo_msg)", 2)
        self.emit("_algo_registar_erro_runtime(_algo_msg, _algo_linha_do_erro(_algo_erro))", 2)
        self.emit("sys.exit(1)", 2)
        # AUDITORIA_2026-08-19 bug #4: 'ler()' a mais depois de
        # '--entradas' esgotar o ficheiro levanta EOFError nativo --
        # sem isto, caía no 'except Exception' genérico do tracer
        # ("não deve ocorrer" -- mas ocorre).
        self.emit("except EOFError as _algo_erro:", 1)
        self.emit(
            '_algo_msg = f"Erro em tempo de execução: o programa tentou ler mais valores '
            'do que os que o ficheiro de entradas tinha.{_algo_sufixo_linha(_algo_erro)}"', 2)
        self.emit("print(_algo_msg)", 2)
        self.emit("_algo_registar_erro_runtime(_algo_msg, _algo_linha_do_erro(_algo_erro))", 2)
        self.emit("sys.exit(1)", 2)
        self.emit("except ZeroDivisionError as _algo_erro:", 1)
        self.emit(
            '_algo_msg = f"Erro em tempo de execução: divisão por zero.{_algo_sufixo_linha(_algo_erro)}"', 2)
        self.emit("print(_algo_msg)", 2)
        self.emit("_algo_registar_erro_runtime(_algo_msg, _algo_linha_do_erro(_algo_erro))", 2)
        self.emit("sys.exit(1)", 2)
        # AL-68/B28: sem isto, um OverflowError (ex.: 'x:decimal =
        # 2.0 ^ 2000.0') propagava como traceback Python cru -- não
        # estava entre as exceções traduzidas, mesmo fora do tracer.
        self.emit("except OverflowError as _algo_erro:", 1)
        self.emit(
            '_algo_msg = f"Erro em tempo de execução: o resultado é grande demais para ser '
            'representado (overflow numérico).{_algo_sufixo_linha(_algo_erro)}"', 2)
        self.emit("print(_algo_msg)", 2)
        self.emit("_algo_registar_erro_runtime(_algo_msg, _algo_linha_do_erro(_algo_erro))", 2)
        self.emit("sys.exit(1)", 2)
        self.emit("except RecursionError as _algo_erro:", 1)
        self.emit(
            '_algo_msg = f"Erro em tempo de execução: recursão infinita '
            '(a função nunca chega ao caso base).{_algo_sufixo_linha(_algo_erro)}"', 2)
        self.emit("print(_algo_msg)", 2)
        self.emit("_algo_registar_erro_runtime(_algo_msg, _algo_linha_do_erro(_algo_erro))", 2)
        self.emit("sys.exit(1)", 2)
        self.emit("except AttributeError as _algo_erro:", 1)
        self.emit(
            '_algo_msg = f"Erro em tempo de execução: '
            '{_algo_traduzir_attributeerror(str(_algo_erro))}{_algo_sufixo_linha(_algo_erro)}"', 2)
        self.emit("print(_algo_msg)", 2)
        self.emit("_algo_registar_erro_runtime(_algo_msg, _algo_linha_do_erro(_algo_erro))", 2)
        self.emit("sys.exit(1)", 2)
        # AUDITORIA_2026-08-19 bug #26: rede de segurança -- ver
        # _algo_traduzir_nameerror.
        self.emit("except NameError as _algo_erro:", 1)
        self.emit(
            '_algo_msg = f"Erro em tempo de execução: '
            '{_algo_traduzir_nameerror(str(_algo_erro))}{_algo_sufixo_linha(_algo_erro)}"', 2)
        self.emit("print(_algo_msg)", 2)
        self.emit("_algo_registar_erro_runtime(_algo_msg, _algo_linha_do_erro(_algo_erro))", 2)
        self.emit("sys.exit(1)", 2)
        self.emit("except ValueError as _algo_erro:", 1)
        self.emit(
            '_algo_msg = f"Erro em tempo de execução: '
            '{_algo_traduzir_valueerro(str(_algo_erro))}{_algo_sufixo_linha(_algo_erro)}"', 2)
        self.emit("print(_algo_msg)", 2)
        self.emit("_algo_registar_erro_runtime(_algo_msg, _algo_linha_do_erro(_algo_erro))", 2)
        self.emit("sys.exit(1)", 2)
        self.linhas.append("")
        return "\n".join(self.linhas)

    def _gerar_estrutura(self, e: A.EstruturaDef):
        # AL-89/B16: propositadamente NÃO associado a 'e.linha' (a linha da
        # definição 'estrutura X') -- ao contrário de uma instrução normal,
        # o corpo de '__init__'/'__eq__' só corre em RUNTIME, sempre que
        # uma instância é criada ou comparada, nunca na linha da própria
        # definição. Mapeá-lo para 'e.linha' fazia o tracer (--debug/--json)
        # injetar passos espúrios (linha da definição, pilha do chamador)
        # sempre que uma estrutura era construída/comparada. Deixando
        # '_linha_algo_atual' em None aqui, 'emit()' não regista nenhuma
        # entrada em mapa_linhas para estas linhas -- tracer.py já ignora
        # de propósito qualquer linha sem entrada (ver 'if linha_algo is
        # None: return tracer').
        recursivas = self._estruturas_recursivas()
        params_kwargs = []
        for c in e.campos:
            if c.dims is not None or c.tipo not in DEFAULT_POR_TIPO:
                # vetor OU campo de tipo estrutura: o valor por omissão tem
                # de ser construído dentro do __init__, nunca como valor
                # por omissão direto do parâmetro -- um valor por omissão
                # de parâmetro só é avaliado UMA VEZ (quando a classe é
                # definida), por isso todas as instâncias partilhariam o
                # mesmo objeto ("mutable default argument", um erro
                # clássico do Python) em vez de cada uma ter o seu próprio
                params_kwargs.append(f"{c.nome}=None")
            else:
                params_kwargs.append(f"{c.nome}={self._valor_default(c.tipo)}")
        assinatura = ", ".join(["self"] + params_kwargs)
        self.emit(f"class {e.nome}:", 0)
        self.emit(f"def __init__({assinatura}):", 1)
        if not e.campos:  # pragma: no cover -- o parser exige >=1 campo em 'estrutura'
            self.emit("pass", 2)
        for c in e.campos:
            if c.dims is not None:
                self.emit(f"if {c.nome} is None:", 2)
                valor_default = self._construir_vetor_aninhado(c.tipo, c.dims, {}, 3)
                self.emit(f"{c.nome} = {valor_default}", 3)
                self.emit(f"self.{c.nome} = {c.nome}", 2)
            elif c.tipo not in DEFAULT_POR_TIPO:
                # AL-39: se 'c.tipo' é (direta ou mutuamente) recursivo,
                # construir a instância por omissão nunca terminaria --
                # fica 'None' (nulo), tal como o estudante teria de
                # escrever explicitamente para terminar uma lista ligada.
                valor_default = "None" if c.tipo in recursivas else self._valor_default(c.tipo)
                self.emit(f"self.{c.nome} = {c.nome} if {c.nome} is not None else {valor_default}", 2)
            else:
                self.emit(f"self.{c.nome} = {c.nome}", 2)
        self.emit("def __eq__(self, outro):", 1)
        self.emit(f"if not isinstance(outro, {e.nome}):", 2)
        self.emit("return NotImplemented", 3)
        if e.campos:
            condicoes = " and ".join(f"self.{c.nome} == outro.{c.nome}" for c in e.campos)
        else:  # pragma: no cover -- o parser exige >=1 campo em 'estrutura'
            condicoes = "True"
        self.emit(f"return {condicoes}", 2)
        self._linha_algo_atual = None
        self.linhas.append("")

    # -------- declarações --------
    def _gerar_lista_args(self, args, f_def, tipos) -> str:
        """AL-16: um argumento pode ser um literal de estrutura (ex.:
        f({x: 1, y: 2})) -- precisa do tipo do PARÂMETRO correspondente
        para saber que classe Python construir (o literal em si não sabe
        o seu próprio tipo). Partilhado entre chamadas usadas como
        expressão e chamadas usadas como instrução solta (esta última
        com o seu próprio caminho de geração para parâmetros 'ref')."""
        args_py = []
        for i, a in enumerate(args):
            param = f_def.parametros[i] if f_def is not None and i < len(f_def.parametros) else None
            if isinstance(a, A.EstruturaLiteral) and param is not None:
                args_py.append(self._expr_estrutura_literal(a, param.tipo, tipos))
            elif isinstance(a, A.VetorLiteral) and param is not None:
                # Mesma ideia que A.EstruturaLiteral acima: um literal de
                # vetor ({...}) passado diretamente como argumento não tem
                # tipo próprio, semantics.py já validou a forma contra
                # 'param.dims' -- é sempre uma instância nova, não precisa
                # de cópia.
                args_py.append(self._expr_vetor_literal(a, param.tipo, tipos))
            elif param is not None:
                expr_py = self._coagir_decimal(self._expr(a, tipos), param.tipo, a)
                if not param.por_referencia and (param.dims > 0 or param.tipo in self.estruturas):
                    # AL-52/B11: um parâmetro de tipo 'estrutura' (ou,
                    # agora, um vetor) sem 'ref' é por VALOR -- semantics.py
                    # já garante todo o contrato de 'ref' (778-820), mas o
                    # Python gerado nunca copiava o objeto/lista, só passava
                    # a MESMA referência. Uma mutação dentro da função (ex.:
                    # 'p.x = 99' ou 'v[0] = 99') vazava silenciosamente para
                    # quem chamou. Um literal ({...}, tratado nos 'if'
                    # acima) já é uma instância nova -- não precisa de
                    # cópia. Uma única condição (não duas) para não fazer
                    # deepcopy em dobro num vetor de estruturas.
                    expr_py = f"copy.deepcopy({expr_py})"
                args_py.append(expr_py)
            else:
                args_py.append(self._expr(a, tipos))
        return ", ".join(args_py)

    def _hoistear_indices_ref(self, f_def, args, tipos, nivel):
        """Bug #34: um argumento 'ref' cujo alvo usa um índice computado
        (ex.: 'ref v[f()]') era avaliado duas vezes -- uma para o LER
        como argumento da chamada, outra para o ESCREVER-DE-VOLTA no
        unpacking do valor de retorno -- porque cada emissão corre
        self._expr()/self._lvalue() de forma independente sobre o
        MESMO nó da AST. Se a expressão do índice tiver efeito lateral
        (ou apenas calhar a dar valores diferentes de cada vez), a
        leitura e a escrita acabam em índices diferentes. Eleva cada
        índice de um argumento 'ref' para uma variável temporária,
        avaliada uma única vez antes da chamada, devolvendo uma cópia
        do LValue que refere essa temporária em vez do índice
        original -- tanto a leitura (args_str) como a escrita
        (out_vars) passam a usar exatamente o mesmo texto Python,
        gerado a partir do mesmo nó já hasteado. Eleva SEMPRE, mesmo
        quando o índice já é uma variável simples ou um literal --
        mais simples de justificar como correto do que distinguir os
        casos 'seguros' dos 'arriscados'. Não mexe em acessos '.campo'
        (nomes estáticos, sem expressão para avaliar) nem em
        argumentos que não sejam 'ref'."""
        contador = 0
        novos = []
        for p, a in zip(f_def.parametros, args):
            if not p.por_referencia or not isinstance(a, A.LValue) or not any(
                    tag == "indice" for tag, _ in a.acessos):
                novos.append(a)
                continue
            novos_acessos = []
            for tag, valor in a.acessos:
                if tag == "indice":
                    nome_tmp = f"_algo_tmp_idx_{contador}"
                    contador += 1
                    self.emit(f"{nome_tmp} = {self._expr(valor, tipos)}", nivel)
                    novos_acessos.append(("indice", A.LValue(nome_tmp, [], a.linha)))
                else:
                    novos_acessos.append((tag, valor))
            novos.append(A.LValue(a.nome, novos_acessos, a.linha))
        return novos

    def _expr_estrutura_literal(self, lit: A.EstruturaLiteral, tipo_nome: str, tipos) -> str:
        """AL-16: um A.EstruturaLiteral não sabe o seu próprio tipo (só os
        campos) -- quem chama tem sempre de indicar 'tipo_nome' a partir
        do contexto (o tipo declarado, ou o tipo do parâmetro que recebe
        o literal numa chamada)."""
        campos_decl = self.estruturas.get(tipo_nome, {})
        partes = []
        for nome, valor in lit.campos:
            tipo_campo = campos_decl.get(nome, ("", 0))[0]
            if isinstance(valor, A.EstruturaLiteral):
                # AL-78/B8: literal de estrutura aninhado dentro doutro --
                # 'valor' não tem 'self._expr()' próprio (só faz sentido
                # com o tipo do campo, já conhecido aqui), por isso
                # recursão direta em vez de _expr()/_coagir_decimal (que só
                # tratam valores primitivos).
                expr_py = self._expr_estrutura_literal(valor, tipo_campo, tipos)
            else:
                expr_py = self._coagir_decimal(self._expr(valor, tipos), tipo_campo, valor)
                # bug#1 (caminhos 8/10): campo de literal de struct a
                # partir de uma variável existente (ex.: '{canto: p1}').
                expr_py = self._copiar_se_necessario(expr_py, tipo_campo, 0)
            partes.append(f"{nome}={expr_py}")
        return f"{tipo_nome}({', '.join(partes)})"

    def _expr_vetor_literal(self, lit: A.VetorLiteral, tipo_elemento: str, tipos) -> str:
        """AL-58/B18: coage cada elemento individualmente para o tipo
        alvo (ex.: inteiro -> decimal), tal como _expr_estrutura_literal
        já faz para campos de estrutura -- o dispatcher genérico de
        _expr() para A.VetorLiteral não sabe o tipo alvo, por isso nunca
        coagia nada (v:decimal[3] = {1, 2, 3} imprimia '1 2 3', não
        '1.0 2.0 3.0'). Recursivo para suportar vetores aninhados
        (multidimensionais)."""
        partes = []
        for elem in lit.elementos:
            if isinstance(elem, A.VetorLiteral):
                partes.append(self._expr_vetor_literal(elem, tipo_elemento, tipos))
            elif isinstance(elem, A.EstruturaLiteral):
                # AL-78/B8: elemento de vetor que é ele próprio um literal
                # de estrutura (ex.: vetor de estruturas).
                partes.append(self._expr_estrutura_literal(elem, tipo_elemento, tipos))
            else:
                expr_py = self._coagir_decimal(self._expr(elem, tipos), tipo_elemento, elem)
                # bug#1 (caminhos 5/9): elemento de literal de vetor a
                # partir de uma variável existente (ex.: '{p1, p2}').
                partes.append(self._copiar_se_necessario(expr_py, tipo_elemento, 0))
        return f"[{', '.join(partes)}]"

    def _gerar_declaracao(self, d: A.Declaracao, nivel, tipos):
        if d.inicial is not None and isinstance(d.inicial, A.VetorLiteral):
            self.emit(f"{d.nome} = {self._expr_vetor_literal(d.inicial, d.tipo, tipos)}", nivel)
            return
        if d.inicial is not None and isinstance(d.inicial, A.EstruturaLiteral):
            if d.dims is not None:
                # AL-45/B5: '{}' vazio inicializando um vetor -- semantics.py
                # já garantiu que só chega aqui com campos vazios.
                self.emit(f"{d.nome} = []", nivel)
                return
            self.emit(f"{d.nome} = {self._expr_estrutura_literal(d.inicial, d.tipo, tipos)}", nivel)
            return
        if d.inicial is not None and isinstance(d.inicial, A.Chamada):
            f_def = self._encontrar_funcao(d.inicial.nome)
            if f_def and any(p.por_referencia for p in f_def.parametros):
                args_hoisted = self._hoistear_indices_ref(f_def, d.inicial.args, tipos, nivel)
                out_vars = [
                    self._lvalue_de_expr(a, tipos)
                    for p, a in zip(f_def.parametros, args_hoisted)
                    if p.por_referencia
                ]
                args_str = self._gerar_lista_args(args_hoisted, f_def, tipos)
                self.emit(f"{d.nome}, {', '.join(out_vars)} = {d.inicial.nome}({args_str})", nivel)
                # AL-51/B17: o valor de retorno principal nunca passava por
                # _coagir_decimal neste caminho -- 'y:decimal = f(x)' com
                # 'f' a devolver 'inteiro' ficava com o inteiro cru.
                valor_coagido = self._coagir_decimal(d.nome, d.tipo, d.inicial)
                if valor_coagido != d.nome:
                    self.emit(f"{d.nome} = {valor_coagido}", nivel)
                return
        if d.inicial is not None:
            expr_py = self._coagir_decimal(self._expr(d.inicial, tipos), d.tipo, d.inicial)
            dims_n = 0 if d.dims is None else len(d.dims)
            expr_py = self._copiar_se_necessario(expr_py, d.tipo, dims_n)
            self.emit(f"{d.nome} = {expr_py}", nivel)
        elif d.dims is None:
            self.emit(f"{d.nome} = {self._valor_default(d.tipo)}", nivel)
        else:
            expr = self._construir_vetor_aninhado(d.tipo, d.dims, tipos, nivel)
            self.emit(f"{d.nome} = {expr}", nivel)

    def _gerar_atribuicao(self, stmt: A.Atribuicao, nivel, tipos):
        """AL-51/B17: sobrepõe gerador_base.py só para o caminho de chamada
        com parâmetros 'ref' -- precisa de _gerar_lista_args (coerção
        inteiro->decimal nos argumentos, cópia de estruturas por valor --
        AL-52/B11) e de coagir o valor de retorno principal; nenhum dos
        dois existe em codegen_minimo.py (fica com o comportamento cru da
        base partilhada, de propósito -- ver a mesma duplicação já
        existente em _gerar_chamada_stmt)."""
        if isinstance(stmt.expr, A.Chamada):
            f_def = self._encontrar_funcao(stmt.expr.nome)
            if f_def and any(p.por_referencia for p in f_def.parametros):
                args_hoisted = self._hoistear_indices_ref(f_def, stmt.expr.args, tipos, nivel)
                out_vars = [
                    self._lvalue_de_expr(a, tipos)
                    for p, a in zip(f_def.parametros, args_hoisted)
                    if p.por_referencia
                ]
                args_str = self._gerar_lista_args(args_hoisted, f_def, tipos)
                alvo = self._lvalue(stmt.alvo, tipos)
                self.emit(f"{alvo}, {', '.join(out_vars)} = {stmt.expr.nome}({args_str})", nivel)
                tipo_alvo = self._tipo_final_lvalue(stmt.alvo, tipos)
                valor_coagido = self._coagir_decimal(alvo, tipo_alvo, stmt.expr)
                if valor_coagido != alvo:
                    self.emit(f"{alvo} = {valor_coagido}", nivel)
                return
        if isinstance(stmt.expr, A.EstruturaLiteral):
            # Literal de estrutura como valor de uma atribuição (não só de
            # uma declaração ou argumento de chamada) -- agora alcançável
            # em modo normal (semantics.py passou a propagar o tipo
            # esperado também aqui). gerador_base.py já tem um caminho
            # para este caso (construído para dar suporte a --minimo, que
            # salta verificar()), mas é uma versão simplificada sem
            # coerção decimal nem suporte a literais aninhados -- usa-se
            # aqui a mesma _expr_estrutura_literal já usada por
            # declaração/argumento de chamada, para os três caminhos
            # terem exatamente o mesmo comportamento.
            alvo = self._lvalue(stmt.alvo, tipos)
            tipo_alvo = self._tipo_final_lvalue(stmt.alvo, tipos)
            self.emit(f"{alvo} = {self._expr_estrutura_literal(stmt.expr, tipo_alvo, tipos)}", nivel)
            return
        super()._gerar_atribuicao(stmt, nivel, tipos)

    def _construir_vetor_aninhado(self, tipo, dims_exprs, tipos, nivel):
        """Constrói a expressão Python de um vetor com N dimensões, ex:
        [[0 for _ in range(c)] for _ in range(l)] para 2D.

        AL-88/B15: cada dimensão é avaliada UMA VEZ, para uma variável
        temporária emitida antes da expressão, em vez de inline -- sem
        isto, a dimensão INTERIOR de um vetor multidimensional era
        reavaliada uma vez por iteração da dimensão exterior (a
        compreensão de listas aninhada do Python reavalia o 'range()'
        interior a cada volta), duplicando o efeito de uma expressão de
        dimensão com efeitos laterais (ex.: uma chamada de função). Mesmo
        princípio que _gerar_para já aplica a 'passo'. 'nivel' é onde as
        atribuições temporárias são emitidas -- tem de ser o mesmo nível
        de indentação de quem usa a expressão devolvida logo a seguir."""
        if not dims_exprs:
            return self._valor_default(tipo)
        temps = []
        for i, dim_expr in enumerate(dims_exprs):
            nome_temp = f"_algo_dim{i}"
            self.emit(f"{nome_temp} = {self._expr(dim_expr, tipos)}", nivel)
            temps.append(nome_temp)
        expr = self._valor_default(tipo)
        for nome_temp in reversed(temps):
            expr = f"[{expr} for _ in range(_algo_verificar_tamanho_vetor({nome_temp}))]"
        return expr

    # -------- statements --------
    def _gerar_stmt(self, stmt, nivel, tipos):
        if getattr(stmt, "linha", None) is not None:
            self._linha_algo_atual = stmt.linha
        if isinstance(stmt, A.Declaracao):
            tipos[stmt.nome] = stmt.tipo
            self._gerar_declaracao(stmt, nivel, tipos)
        elif isinstance(stmt, A.Atribuicao):
            self._gerar_atribuicao(stmt, nivel, tipos)
        elif isinstance(stmt, A.Ler):
            self._gerar_ler(stmt, nivel, tipos)
        elif isinstance(stmt, A.Escrever):
            args = ", ".join(self._expr(e, tipos) for e in stmt.exprs)
            self.emit(f"_algo_escrever({args})", nivel)
        elif isinstance(stmt, A.Se):
            self._gerar_se(stmt, nivel, tipos)
        elif isinstance(stmt, A.Para):
            self._gerar_para(stmt, nivel, tipos)
        elif isinstance(stmt, A.Enquanto):
            self.emit(f"while {self._expr(stmt.condicao, tipos)}:", nivel)
            self._gerar_corpo(stmt.corpo, nivel + 1, tipos)
        elif isinstance(stmt, A.FazEnquanto):
            self.emit("while True:", nivel)
            self._gerar_corpo(stmt.corpo, nivel + 1, tipos)
            self.emit(f"if not ({self._expr(stmt.condicao, tipos)}):", nivel + 1)
            self.emit("break", nivel + 2)
        elif isinstance(stmt, A.Escolha):
            self._gerar_escolha(stmt, nivel, tipos)
        elif isinstance(stmt, A.Devolver):
            if isinstance(stmt.expr, A.EstruturaLiteral):
                # Literal de estrutura devolvido diretamente -- semantics.py
                # já validou a forma contra o tipo de retorno da função.
                # Usa-se _expr_estrutura_literal (coerção decimal + literais
                # aninhados) em vez do _expr() genérico, que não tem ramo
                # nenhum para A.EstruturaLiteral (só sabe construir a partir
                # do tipo esperado, que aqui já se conhece).
                valor = self._expr_estrutura_literal(stmt.expr, self.tipo_retorno_atual, tipos)
            elif isinstance(stmt.expr, A.VetorLiteral):
                # Mesma ideia para um literal de vetor -- _expr_vetor_literal
                # coage cada elemento (ex.: inteiro -> decimal), ao contrário
                # do ramo genérico de A.VetorLiteral em _expr(), que apenas
                # monta a lista sem coagir nada.
                valor = self._expr_vetor_literal(stmt.expr, self.tipo_retorno_atual, tipos)
            else:
                valor = self._coagir_decimal(self._expr(stmt.expr, tipos), self.tipo_retorno_atual, stmt.expr)
                valor = self._copiar_se_necessario(valor, self.tipo_retorno_atual, self.dims_retorno_atual)
            if self.refs_atuais:
                self.emit(f"return {valor}, {', '.join(self.refs_atuais)}", nivel)
            else:
                self.emit(f"return {valor}", nivel)
        elif isinstance(stmt, A.ChamadaStmt):
            self._gerar_chamada_stmt(stmt, nivel, tipos)
        elif isinstance(stmt, A.Afirmar):
            self._gerar_afirmar(stmt, nivel, tipos)
        else:  # pragma: no cover -- todos os tipos de instrução da AST são tratados acima
            raise ErroInternoCompilador(
                f"instrução não suportada: {type(stmt).__name__} (linha {getattr(stmt, 'linha', 0)})")

    def _gerar_afirmar(self, stmt: A.Afirmar, nivel, tipos):
        cond_py = self._expr(stmt.condicao, tipos)
        # texto_expr() devolve texto não escapado (pode conter aspas/chavetas/backslash
        # vindos de literais do próprio código do estudante). repr() gera um literal
        # Python seguro para esse texto — nunca é reavaliado como f-string/código no
        # programa gerado, ao contrário de o interpolar diretamente numa f-string.
        prefixo_literal = repr(f"❌ Afirmação falhou (linha {stmt.linha}): {texto_expr(stmt.condicao)}")
        self.emit(f"if not ({cond_py}):", nivel)
        if stmt.mensagem is not None:
            msg_py = self._expr(stmt.mensagem, tipos)
            self.emit(f'_algo_msg = {prefixo_literal} + " — " + str({msg_py})', nivel + 1)
        else:
            self.emit(f'_algo_msg = {prefixo_literal}', nivel + 1)
        self.emit("print(_algo_msg)", nivel + 1)
        self.emit(f"_algo_registar_erro_runtime(_algo_msg, {stmt.linha})", nivel + 1)
        self.emit("sys.exit(1)", nivel + 1)

    def _gerar_ler(self, stmt: A.Ler, nivel, tipos):
        for alvo in stmt.alvos:
            tipo = self._tipo_final_lvalue(alvo, tipos)
            leitor = LEITORES_POR_TIPO.get(tipo, "_algo_ler_texto")
            destino = self._lvalue(alvo, tipos)
            self.emit(f"{destino} = {leitor}()", nivel)

    def _gerar_chamada_stmt(self, stmt: A.ChamadaStmt, nivel, tipos):
        chamada = stmt.chamada
        f_def = self._encontrar_funcao(chamada.nome)
        if f_def and any(p.por_referencia for p in f_def.parametros):
            args_hoisted = self._hoistear_indices_ref(f_def, chamada.args, tipos, nivel)
            out_vars = [
                self._lvalue_de_expr(a, tipos)
                for p, a in zip(f_def.parametros, args_hoisted)
                if p.por_referencia
            ]
            args_str = self._gerar_lista_args(args_hoisted, f_def, tipos)
            if f_def.eh_procedimento:
                self.emit(f"{', '.join(out_vars)} = {chamada.nome}({args_str})", nivel)
            else:
                self.emit(f"_, {', '.join(out_vars)} = {chamada.nome}({args_str})", nivel)
        else:
            self.emit(self._expr(chamada, tipos), nivel)

    def _lvalue_de_expr(self, expr, tipos):
        if isinstance(expr, A.LValue):
            return self._lvalue(expr, tipos)
        raise ErroInternoCompilador(  # pragma: no cover -- semantics.py já valida isto antes
            "argumentos passados por referência têm de ser uma variável, um "
            "elemento de vetor ou um campo")

    # -------- lvalue / expressões --------
    def _expr(self, expr, tipos):
        if expr is None:  # pragma: no cover -- nenhum chamador passa None (todos são guardados)
            return ""
        if isinstance(expr, A.Literal):
            if expr.tipo in ("cadeia", "caracter"):
                # AL-13: repr() em vez de escapar à mão -- desde que o
                # lexer passou a suportar \n dentro de literais, o valor
                # pode conter uma quebra de linha real, que um simples
                # '"..."' não representa em Python; repr() trata sempre
                # corretamente aspas, backslash e quebras de linha.
                return repr(expr.valor)
            if expr.tipo == "booleano":
                return "True" if expr.valor else "False"
            return repr(expr.valor)
        if isinstance(expr, A.LValue):
            return self._lvalue(expr, tipos)
        if isinstance(expr, A.BinOp):
            if expr.op in ("div", "mod"):
                # AL-05: divisão truncada, não a floor division nativa do
                # Python -- ver _algo_div/_algo_mod no cabeçalho.
                funcao = "_algo_div" if expr.op == "div" else "_algo_mod"
                return f"{funcao}({self._expr(expr.esq, tipos)}, {self._expr(expr.dire, tipos)})"
            if expr.op == "^":
                # AL-57/B16: ver _algo_pot no cabeçalho -- '**' nativo do
                # Python devolve complex silenciosamente para base
                # negativa com expoente fracionário.
                chamada = f"_algo_pot({self._expr(expr.esq, tipos)}, {self._expr(expr.dire, tipos)})"
                # Etapa 12 da 4ª auditoria (achado da segunda passagem
                # independente): semantics.py tipa 'inteiro ^ inteiro'
                # como 'decimal' sempre que não consegue provar em
                # compilação que o expoente nunca é negativo (ver
                # _expoente_estaticamente_nao_negativo) -- mas se o
                # expoente calculado em runtime acabar não-negativo, o
                # '**' nativo do Python devolve int, não float, porque
                # os dois operandos são int. Sem isto, uma variável
                # 'decimal' ficava silenciosamente com um int (ex.:
                # 'y:decimal = 2^n' imprimia '8' em vez de '8.0').
                if (expr._tipo_inferido == "decimal"
                        and expr.esq._tipo_inferido == "inteiro"
                        and expr.dire._tipo_inferido == "inteiro"):
                    return f"float({chamada})"
                return chamada
            op = OPS_BIN[expr.op]
            return f"({self._expr(expr.esq, tipos)} {op} {self._expr(expr.dire, tipos)})"
        if isinstance(expr, A.UnOp):
            if expr.op == "nao":
                return f"(not {self._expr(expr.operando, tipos)})"
            if expr.op == "-":
                return f"(-{self._expr(expr.operando, tipos)})"
        if isinstance(expr, A.Chamada):
            args = self._gerar_lista_args(expr.args, self._encontrar_funcao(expr.nome), tipos)
            nome_py = expr.nome.replace(".", "_") if "." in expr.nome else expr.nome
            return f"{nome_py}({args})"
        if isinstance(expr, A.VetorLiteral):  # pragma: no cover -- semantics.py (_tipo_expr, AL-16) já rejeita um VetorLiteral fora dos dois contextos tratados por _gerar_declaracao/_expr_vetor_literal e _expr_estrutura_literal antes de chegar aqui
            elementos = ", ".join(self._expr(e, tipos) for e in expr.elementos)
            return f"[{elementos}]"
        raise ErroInternoCompilador(  # pragma: no cover -- todos os tipos de expressão da AST são tratados acima
            f"expressão não suportada: {type(expr).__name__} (linha {getattr(expr, 'linha', 0)})")


def gerar_python(programa: A.Programa) -> str:
    return GeradorCodigo(programa).gerar()


def gerar_python_com_mapa(programa: A.Programa):
    """Como gerar_python(), mas devolve também o mapa de linhas (linha do
    .py -> linha do .algo original) e os nomes globais/funções -- usado
    pela ferramenta de trace (algo_lang.tools.tracer) para conseguir
    mostrar, a cada passo da execução real, a que linha do .algo
    corresponde e quais são as variáveis globais visíveis. O compilador
    em si não sabe nada de debug/trace -- só devolve esta informação de
    correspondência de linhas, que é sempre gerada (é meta-informação
    inofensiva, não código extra dentro do programa)."""
    gerador = GeradorCodigo(programa)
    codigo = gerador.gerar()
    return {
        "codigo": codigo,
        "mapa_linhas": dict(gerador.mapa_linhas),
        "nomes_globais": list(gerador.tabela_tipos_globais.keys()),
        "nomes_funcoes": [f.nome for f in programa.funcoes],
    }
