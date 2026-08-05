# ============================================================
#  Ficheiro gerado automaticamente pelo compilador ALGO
#  NAO EDITAR A MAO -- edita o ficheiro .algo original
# ============================================================

import sys

sys.setrecursionlimit(10000)


def _algo_fmt(v):
    """Formata valores para exibicao (escrever) ao estilo portugues."""
    if isinstance(v, bool):
        return "verdadeiro" if v else "falso"
    return str(v)


def _algo_escrever(*valores):
    print("".join(_algo_fmt(v) for v in valores))


def _algo_ler_inteiro(prompt=""):
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print("Valor invalido. Introduza um numero inteiro.")


def _algo_ler_decimal(prompt=""):
    while True:
        try:
            return float(input(prompt))
        except ValueError:
            print("Valor invalido. Introduza um numero decimal.")


def _algo_ler_booleano(prompt=""):
    while True:
        resp = input(prompt).strip().lower()
        if resp in ("verdadeiro", "v", "true"):
            return True
        if resp in ("falso", "f", "false"):
            return False
        print("Valor invalido. Introduza 'verdadeiro' ou 'falso'.")


def _algo_ler_texto(prompt=""):
    return input(prompt)


def _algo_ler_caracter(prompt=""):
    while True:
        resp = input(prompt)
        if len(resp) == 1:
            return resp
        print("Valor invalido. Introduza exatamente 1 caracter.")


def _algo_programa():
    global n, soma, numeros, i, media
    n = 5
    soma = 0
    numeros = [0 for _ in range(10)]
    for i in range(0, ((n - 1)) + (1 if (1) > 0 else -1), 1):
        numeros[i] = ((i + 1) * 10)
        soma = (soma + numeros[i])
    media = (soma / n)
    if (media > 20):
        _algo_escrever("Média alta: ", media)
    else:
        _algo_escrever("Média baixa: ", media)

if __name__ == "__main__":
    try:
        _algo_programa()
    except IndexError:
        print("Erro em tempo de execução: tentaste aceder a uma posição de array que não existe (índice fora dos limites).")
        sys.exit(1)
    except ZeroDivisionError:
        print("Erro em tempo de execução: divisão por zero.")
        sys.exit(1)
    except RecursionError:
        print("Erro em tempo de execução: recursão infinita (a função nunca chega ao caso base).")
        sys.exit(1)
    except ValueError as _algo_erro:
        print(f"Erro em tempo de execução: valor inválido ({_algo_erro}).")
        sys.exit(1)
