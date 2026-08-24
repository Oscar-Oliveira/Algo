# ============================================================
#  Ficheiro gerado automaticamente pelo compilador ALGO
#  NAO EDITAR A MAO -- edita o ficheiro .algo original
# ============================================================

import sys
import copy

sys.setrecursionlimit(10000)

# Sem isto, 'escrever' de um acento/emoji fora do codepage do ambiente
# rebentava com UnicodeEncodeError. Relevante em produção: online/
# executor.py limpa as variáveis de ambiente do subprocesso do estudante,
# por isso a codificação não pode ficar ao critério do ambiente.
# 'hasattr' porque sys.stdout nem sempre tem '.reconfigure()' -- ex.: sob
# tools/tracer.py, este ficheiro gerado corre com sys.stdout redirecionado
# para um io.StringIO() em memória, que não tem esse método.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


class _AlgoIndiceCadeiaInvalido(IndexError):
    """Subclasse de IndexError, para as bibliotecas de texto (ex.
    cadeia.caracter) distinguirem um índice fora dos limites de TEXTO de
    um índice fora dos limites de VETOR -- apanhada antes do 'except
    IndexError' genérico, mais abaixo neste ficheiro."""
    pass


class _AlgoErroAmigavel(ValueError):
    """Uma biblioteca (ex. cadeia.subcadeia, matematica.aleatorio) que já
    escreve a sua PRÓPRIA mensagem em português levanta esta classe, não
    ValueError direto -- apanhada ANTES do 'except ValueError' genérico,
    mostrada tal-e-qual (sem passar por _algo_traduzir_valueerro). Mesmo
    padrão que _AlgoIndiceCadeiaInvalido usa para o mesmo tipo de
    problema. Ver bibliotecas/cadeia.py, matematica.py, conversao.py para
    exemplos."""
    pass


def _algo_fmt(v):
    """Formata valores para exibicao (escrever) ao estilo portugues."""
    if isinstance(v, bool):
        return "verdadeiro" if v else "falso"
    if v is None:
        return "nulo"
    if isinstance(v, float):
        # Arredondar para 12 casas decimais esconde o ruido de
        # representacao binaria ("0.1 + 0.2" mostra "0.3", nao
        # "0.30000000000000004"), mantendo o ".0" que distingue 'decimal'
        # de 'inteiro'. "-0.0" e normalizado para "0.0" -- DEPOIS do
        # arredondamento, nao antes, porque um valor que arredonda para
        # -0.0 (ex.: -1e-13) só fica exatamente -0.0 depois de arredondar.
        # Notacao cientifica (ex.: 10.0^20 -> "1e+20") nao e traduzida.
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
    """float() do Python aceita "nan"/"inf"/"-inf"/"Infinity" e
    separadores '_' de milhar -- nenhum dos dois é um número decimal
    válido em ALGO. Usado só por '_algo_ler_decimal' (abaixo);
    'conversao.paraDecimal' aceita 'nan'/'inf' DE PROPÓSITO e por isso tem
    a sua PRÓPRIA verificação, mais permissiva, só para separadores '_' --
    não reaproveita este helper."""
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
    """Traduz as causas mais comuns de ValueError para portugues, em vez
    de mostrar sempre a mensagem crua do Python -- mantem o generico
    (mensagem original entre parenteses) como recurso para causas nao
    mapeadas."""
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
        # 'passo' literal igual a 0 já é rejeitado em compilação
        # (semantics.py); isto apanha um 'passo' calculado em runtime.
        return "o 'passo' do ciclo 'para' não pode ser zero (o ciclo nunca avançaria)."
    if "cannot convert float infinity to integer" in msg_min:
        return "não é possível converter 'infinito' para um número inteiro."
    if "int too large to convert to float" in msg_min:
        return "este número é grande demais para ser convertido para decimal."
    if "exceeds the limit" in msg_min and "integer string conversion" in msg_min:
        # Proteção do próprio Python (3.11+) contra a conversão
        # inteiro->texto de um número com dígitos a mais -- a mensagem
        # nativa cita 'sys.set_int_max_str_digits()', que não significa
        # nada para um estudante. O CÁLCULO em si não tem limite; só
        # mostrá-lo é que tem.
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
    """Rede de segurança -- a correção principal é em semantics.py
    (_globais_lidas_transitivamente), apanhada em compilação; isto cobre
    qualquer caso que essa análise (que só cobre o valor inicial de uma
    DECLARAÇÃO) não apanhe, ex.: uma atribuição normal ou uma chamada
    solta que leia uma global ainda não declarada nesse ponto."""
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
    """Canal de erro em runtime que não depende de nenhuma frase
    específica (evita a deteção frágil por texto que existia em
    tools/tracer.py). Chamada como função (não atribuição direta) de
    propósito -- funciona seja qual for o scope de onde é chamada, sem
    precisar de 'global' em cada local de chamada."""
    global _ALGO_ERRO_RUNTIME
    _ALGO_ERRO_RUNTIME = {"mensagem": mensagem, "linha": linha}


def _algo_pot(a, b):
    """O '**' nativo do Python 3 nunca levanta ValueError para base
    negativa com expoente fracionário -- devolve silenciosamente um
    número complexo (ex.: (-8.0) ** 0.5). matematica.raiz(-1) já tem uma
    mensagem amigável equivalente para esse domínio inválido; este é o
    caminho gémeo para o operador '^'."""
    if a < 0 and not float(b).is_integer():
        raise ValueError("negative number cannot be raised to a fractional power")
    return a ** b


def _algo_indice(i):
    """Índices negativos (ex.: 'v[-1]') são sempre rejeitados -- o Python
    nativo aceita índices negativos (conta a partir do fim), o que
    devolveria/escreveria silenciosamente o ÚLTIMO elemento em vez de dar
    o erro que um estudante esperaria. Chamado em toda leitura/escrita
    indexada (ver gerador_base.py:_lvalue), 1D e 2D+."""
    if i < 0:
        raise IndexError("índice negativo")
    return i


_ALGO_LIMITE_TAMANHO_VETOR = 10_000_000


def _algo_verificar_tamanho_vetor(tam):
    """Um tamanho de vetor calculado em runtime que fosse negativo
    silenciosamente produzia um vetor vazio -- range(negativo) do Python
    não levanta erro nenhum. Este é o único sítio onde QUALQUER dimensão
    de vetor passa antes de ser usada em range(), por isso não é preciso
    duplicar esta verificação em semantics.py. 10 milhões por dimensão --
    ver _algo_verificar_tamanho_vetor_agregado, a seguir, para o limite
    sobre o PRODUTO entre dimensões de um vetor 2D+.
    _AlgoErroAmigavel (não ValueError direto) evita que as mensagens
    fiquem reembrulhadas em "valor inválido (...)" pelo 'except
    ValueError' genérico."""
    if tam < 0:
        raise _AlgoErroAmigavel(f"tamanho de vetor não pode ser negativo (é {tam})")
    if tam > _ALGO_LIMITE_TAMANHO_VETOR:
        raise _AlgoErroAmigavel(
            f"o tamanho pedido ({tam}) é maior do que o limite permitido "
            f"({_ALGO_LIMITE_TAMANHO_VETOR})")
    return tam


def _algo_verificar_tamanho_vetor_agregado(*dims):
    """Cada dimensão individual já passa por _algo_verificar_tamanho_vetor,
    mas isso não impede um vetor tecnicamente enorme com todas as
    dimensões individualmente abaixo do limite (ex.: 'inteiro[9999][9999]
    [9999]', ~10^12 elementos) -- sem isto, a construção só falharia a
    meio (ou nem isso: esgotava memória sem erro nenhum apanhado) muito
    depois de já ter começado a alocar. Chamado UMA VEZ, com todas as
    dimensões já resolvidas, ANTES de começar a construir o vetor
    aninhado -- falha rápido, sem alocar nada. Usa o MESMO limite que
    cada dimensão individual usa sozinha (_ALGO_LIMITE_TAMANHO_VETOR),
    agora sobre o produto, não a soma nem cada eixo à parte -- para um
    vetor 1D isto é equivalente ao guarda de cima, sem mudar nada."""
    produto = 1
    for d in dims:
        produto *= max(d, 0)
    if produto > _ALGO_LIMITE_TAMANHO_VETOR:
        raise _AlgoErroAmigavel(
            f"o vetor pedido tem {produto} elementos no total, mais do que "
            f"o limite permitido ({_ALGO_LIMITE_TAMANHO_VETOR})")


def _algo_verificar_tamanho_vetor_resultado(lista, tamanho_esperado):
    """Uma função (biblioteca, ex. cadeia.dividir, ou do próprio programa)
    que devolve um vetor para inicializar uma declaração de tamanho fixo
    (ex.: 'partes:cadeia[3] = cadeia.dividir(...)') só tem o tamanho REAL
    conhecido em runtime -- ao contrário de um literal '{...}', cujo
    tamanho semantics.py já valida em compilação. Sem isto, um resultado
    maior do que o declarado ficava silenciosamente legível além do
    tamanho declarado, e um resultado menor só falhava (com a mensagem
    genérica de índice fora dos limites) quando de facto se tentasse ler
    além dele, nunca já na própria inicialização."""
    if len(lista) != tamanho_esperado:
        raise _AlgoErroAmigavel(
            f"esta chamada devolveu um vetor com {len(lista)} elemento(s), "
            f"mas a declaração espera {tamanho_esperado}")
    return lista


def adcionais(primos, n):
    _algo_dim0 = (n + 1)
    _algo_verificar_tamanho_vetor_agregado(_algo_dim0)
    primos2 = [0 for _ in range(_algo_verificar_tamanho_vetor(_algo_dim0))]
    i = 0
    for i in range(0, ((n - 1)) + (1 if (1) > 0 else -1), 1):
        primos2[_algo_indice(i)] = primos[_algo_indice(i)]
    return copy.deepcopy(primos2)

def _algo_programa():
    global primos, i, primos2
    primos = [[1, 2, 3, 4, 5], [6, 7, 8, 9, 10], [11, 12, 13, 14, 15], [16, 17, 18, 19, 20], [21, 22, 23, 24, 25]]
    i = 0
    for i in range(0, (4) + (1 if (1) > 0 else -1), 1):
        _algo_escrever(primos[_algo_indice(0)][_algo_indice(i)])
    primos2 = _algo_verificar_tamanho_vetor_resultado(copy.deepcopy(adcionais(copy.deepcopy(primos[_algo_indice(0)]), 5)), 6)
    primos2[_algo_indice(5)] = 6
    for i in range(0, (5) + (1 if (1) > 0 else -1), 1):
        _algo_escrever(primos2[_algo_indice(1)])
    _algo_escrever('ola')

_ALGO_MAPA_LINHAS = {324: 3, 325: 4, 326: 4, 327: 4, 328: 6, 329: 7, 330: 8, 331: 10, 335: 13, 336: 15, 337: 16, 338: 17, 339: 20, 340: 21, 341: 23, 342: 24, 343: 26}

if __name__ == "__main__":
    try:
        _algo_programa()
    except _AlgoIndiceCadeiaInvalido as _algo_erro:
        _algo_msg = f"Erro em tempo de execução: tentaste aceder a uma posição de texto que não existe (índice fora dos limites).{_algo_sufixo_linha(_algo_erro)}"
        print(_algo_msg)
        _algo_registar_erro_runtime(_algo_msg, _algo_linha_do_erro(_algo_erro))
        sys.exit(1)
    except _AlgoErroAmigavel as _algo_erro:
        _algo_msg = f"Erro em tempo de execução: {_algo_erro}{_algo_sufixo_linha(_algo_erro)}"
        print(_algo_msg)
        _algo_registar_erro_runtime(_algo_msg, _algo_linha_do_erro(_algo_erro))
        sys.exit(1)
    except IndexError as _algo_erro:
        _algo_msg = f"Erro em tempo de execução: tentaste aceder a uma posição de vetor que não existe (índice fora dos limites).{_algo_sufixo_linha(_algo_erro)}"
        print(_algo_msg)
        _algo_registar_erro_runtime(_algo_msg, _algo_linha_do_erro(_algo_erro))
        sys.exit(1)
    except EOFError as _algo_erro:
        _algo_msg = f"Erro em tempo de execução: o programa tentou ler mais valores do que os que o ficheiro de entradas tinha.{_algo_sufixo_linha(_algo_erro)}"
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
    except MemoryError as _algo_erro:
        _algo_msg = f"Erro em tempo de execução: o programa ficou sem memória (o valor pedido é grande demais).{_algo_sufixo_linha(_algo_erro)}"
        print(_algo_msg)
        _algo_registar_erro_runtime(_algo_msg, _algo_linha_do_erro(_algo_erro))
        sys.exit(1)
    except AttributeError as _algo_erro:
        _algo_msg = f"Erro em tempo de execução: {_algo_traduzir_attributeerror(str(_algo_erro))}{_algo_sufixo_linha(_algo_erro)}"
        print(_algo_msg)
        _algo_registar_erro_runtime(_algo_msg, _algo_linha_do_erro(_algo_erro))
        sys.exit(1)
    except NameError as _algo_erro:
        _algo_msg = f"Erro em tempo de execução: {_algo_traduzir_nameerror(str(_algo_erro))}{_algo_sufixo_linha(_algo_erro)}"
        print(_algo_msg)
        _algo_registar_erro_runtime(_algo_msg, _algo_linha_do_erro(_algo_erro))
        sys.exit(1)
    except ValueError as _algo_erro:
        _algo_msg = f"Erro em tempo de execução: {_algo_traduzir_valueerro(str(_algo_erro))}{_algo_sufixo_linha(_algo_erro)}"
        print(_algo_msg)
        _algo_registar_erro_runtime(_algo_msg, _algo_linha_do_erro(_algo_erro))
        sys.exit(1)
