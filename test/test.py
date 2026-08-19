# ============================================================
#  Ficheiro gerado automaticamente pelo compilador ALGO
#  NAO EDITAR A MAO -- edita o ficheiro .algo original
# ============================================================

import sys
import copy

sys.setrecursionlimit(10000)


class _AlgoIndiceCadeiaInvalido(IndexError):
    """AL-09: subclasse de IndexError, para as bibliotecas de texto
    (ex. cadeia.caracter) distinguirem um índice fora dos limites de
    TEXTO de um índice fora dos limites de ARRAY -- apanhada antes do
    'except IndexError' genérico, mais abaixo neste ficheiro."""
    pass


def _algo_fmt(v):
    """Formata valores para exibicao (escrever) ao estilo portugues."""
    if isinstance(v, bool):
        return "verdadeiro" if v else "falso"
    if v is None:
        return "nulo"
    return str(v)


def _algo_escrever(*valores):
    print("".join(_algo_fmt(v) for v in valores))


def _algo_ler_inteiro(prompt=""):
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print("Valor inválido. Introduza um número inteiro.")


def _algo_ler_decimal(prompt=""):
    while True:
        try:
            return float(input(prompt))
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


def _algo_verificar_tamanho_array(tam):
    """Um tamanho de array calculado em runtime (nao um literal, ja
    apanhado em compilacao) que de negativo silenciosamente produzia
    um array vazio -- range(negativo) do Python nao levanta erro
    nenhum. ValueError e reaproveitado de propósito: ja ha um
    'except ValueError' no programa gerado que traduz para a mensagem
    amigavel de 'Erro em tempo de execucao: valor invalido (...)'."""
    if tam < 0:
        raise ValueError(f"tamanho de array não pode ser negativo (é {tam})")
    return tam


def adcionais(primos, n):
    _algo_dim0 = (n + 1)
    primos2 = [0 for _ in range(_algo_verificar_tamanho_array(_algo_dim0))]
    i = 0
    for i in range(0, ((n - 1)) + (1 if (1) > 0 else -1), 1):
        primos2[i] = primos[i]
    return primos2

def _algo_programa():
    global primos, i, primos2
    primos = [1, 2, 3, 4, 5]
    i = 0
    for i in range(0, (4) + (1 if (1) > 0 else -1), 1):
        _algo_escrever(primos[i])
    primos2 = adcionais(copy.deepcopy(primos), 5)
    primos2[5] = 6
    for i in range(0, (5) + (1 if (1) > 0 else -1), 1):
        _algo_escrever(primos2[i])
    _algo_escrever('ola')

_ALGO_MAPA_LINHAS = {197: 3, 198: 4, 199: 4, 200: 6, 201: 7, 202: 8, 203: 10, 207: 13, 208: 15, 209: 16, 210: 17, 211: 20, 212: 21, 213: 23, 214: 24, 215: 26}

if __name__ == "__main__":
    try:
        _algo_programa()
    except _AlgoIndiceCadeiaInvalido as _algo_erro:
        _algo_msg = f"Erro em tempo de execução: tentaste aceder a uma posição de texto que não existe (índice fora dos limites).{_algo_sufixo_linha(_algo_erro)}"
        print(_algo_msg)
        _algo_registar_erro_runtime(_algo_msg, _algo_linha_do_erro(_algo_erro))
        sys.exit(1)
    except IndexError as _algo_erro:
        _algo_msg = f"Erro em tempo de execução: tentaste aceder a uma posição de array que não existe (índice fora dos limites).{_algo_sufixo_linha(_algo_erro)}"
        print(_algo_msg)
        _algo_registar_erro_runtime(_algo_msg, _algo_linha_do_erro(_algo_erro))
        sys.exit(1)
    except ZeroDivisionError as _algo_erro:
        _algo_msg = f"Erro em tempo de execução: divisão por zero.{_algo_sufixo_linha(_algo_erro)}"
        print(_algo_msg)
        _algo_registar_erro_runtime(_algo_msg, _algo_linha_do_erro(_algo_erro))
        sys.exit(1)
    except OverflowError as _algo_erro:
        _algo_msg = f"Erro em tempo de execução: o resultado é grande demais para ser representado (overflow numérico).{_algo_sufixo_linha(_algo_erro)}"
        print(_algo_msg)
        _algo_registar_erro_runtime(_algo_msg, _algo_linha_do_erro(_algo_erro))
        sys.exit(1)
    except RecursionError as _algo_erro:
        _algo_msg = f"Erro em tempo de execução: recursão infinita (a função nunca chega ao caso base).{_algo_sufixo_linha(_algo_erro)}"
        print(_algo_msg)
        _algo_registar_erro_runtime(_algo_msg, _algo_linha_do_erro(_algo_erro))
        sys.exit(1)
    except AttributeError as _algo_erro:
        _algo_msg = f"Erro em tempo de execução: {_algo_traduzir_attributeerror(str(_algo_erro))}{_algo_sufixo_linha(_algo_erro)}"
        print(_algo_msg)
        _algo_registar_erro_runtime(_algo_msg, _algo_linha_do_erro(_algo_erro))
        sys.exit(1)
    except ValueError as _algo_erro:
        _algo_msg = f"Erro em tempo de execução: {_algo_traduzir_valueerro(str(_algo_erro))}{_algo_sufixo_linha(_algo_erro)}"
        print(_algo_msg)
        _algo_registar_erro_runtime(_algo_msg, _algo_linha_do_erro(_algo_erro))
        sys.exit(1)
