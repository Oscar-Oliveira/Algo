# -*- coding: utf-8 -*-
"""Gera um "trace" completo da execução de um programa ALGO: a cada linha
executada, regista a linha .algo correspondente, a pilha de chamadas com
todas as variáveis visíveis, e a consola acumulada até esse ponto.

Corre o Python REAL gerado pelo compilador (via sys.settrace), em vez de
reimplementar a linguagem -- por isso suporta tudo o que o compilador
suporta (estruturas, ref, recursividade, bibliotecas, ...), sem
divergências.
"""
import sys
import io
import builtins
import contextlib

MAX_PASSOS = 4000
NOME_FUNCAO_PRINCIPAL = "_algo_programa"


class LimiteDePassosExcedido(Exception):
    pass


class _redirect_stdin:
    """contextlib não tem um redirect_stdin -- implementação equivalente."""
    def __init__(self, novo_stdin):
        self._novo = novo_stdin
        self._antigo = None

    def __enter__(self):
        self._antigo = sys.stdin
        sys.stdin = self._novo
        return self._novo

    def __exit__(self, *exc):
        sys.stdin = self._antigo
        return False


def _valor_serializavel(v):
    """Converte um valor Python num valor pronto para JSON, mantendo os
    tipos nativos quando possível (para a página web poder formatar como
    quiser) em vez de os transformar já em texto."""
    if isinstance(v, (int, float, bool, str)) or v is None:
        return v
    if isinstance(v, list):
        return [_valor_serializavel(e) for e in v]
    if hasattr(v, "__dict__"):  # instância de uma 'estrutura'
        return {k: _valor_serializavel(val) for k, val in vars(v).items()}
    return repr(v)


def _fmt_debug(v):
    if isinstance(v, bool):
        return "verdadeiro" if v else "falso"
    if isinstance(v, list):
        return "[" + ", ".join(_fmt_debug(e) for e in v) + "]"
    if isinstance(v, dict):
        return "{" + ", ".join(f"{k}: {_fmt_debug(x)}" for k, x in v.items()) + "}"
    return str(v)


def formatar_consola_com_debug(resultado):
    """Reconstrói a consola tal como apareceria com o antigo --debug: a
    saída real do programa intercalada com uma anotação '[debug linha N]'
    a cada passo, mostrando as variáveis visíveis nesse momento (todas as
    frames da pilha fundidas, da mais externa para a mais interna, tal
    como a resolução de nomes normal). Isto é construído inteiramente
    aqui a partir do trace já recolhido -- o compilador não sabe nada
    disto, não gerou nenhum código extra para o tornar possível."""
    linhas_saida = []
    consola_vista = ""
    for passo in resultado["passos"]:
        novo_texto = passo["consola"][len(consola_vista):]
        if novo_texto:
            linhas_saida.append(novo_texto.rstrip("\n"))
        consola_vista = passo["consola"]

        variaveis = {}
        for frame in passo["pilha"]:
            variaveis.update(frame["variaveis"])
        if variaveis:
            partes = ", ".join(f"{k}={_fmt_debug(v)}" for k, v in variaveis.items())
            linhas_saida.append(f"    [debug linha {passo['linha']}] {partes}")

    resto = resultado["consolaFinal"][len(consola_vista):]
    if resto:
        linhas_saida.append(resto.rstrip("\n"))
    return "\n".join(linhas_saida) + ("\n" if linhas_saida else "")


def gerar_trace(codigo_py: str, caminho_py: str, mapa_linhas: dict,
                 nomes_globais: list, nomes_funcoes: list, entradas=None):
    """Executa 'codigo_py' (o Python gerado a partir de um .algo) sob
    sys.settrace(), devolvendo um dicionário pronto a converter em JSON:
    {
        "passos": [ {"linha": int, "evento": str, "consola": str,
                      "pilha": [ {"nome": str, "variaveis": {...}}, ... ]} ],
        "consolaFinal": str,
        "erro": None | {"mensagem": str, "linha": int},
        "limiteExcedido": bool,
    }

    'entradas': lista de strings para alimentar ler(), ou None para usar
    o stdin real do processo (permite entrada interativa).
    """
    nomes_funcoes_conhecidas = set(nomes_funcoes) | {NOME_FUNCAO_PRINCIPAL}
    passos = []
    limite_excedido = {"valor": False}
    resultado_erro = {"valor": None}

    def construir_pilha(frame):
        pilha = []
        f = frame
        while f is not None:
            nome = f.f_code.co_name
            if f.f_code.co_filename != caminho_py:
                f = f.f_back
                continue
            if nome == NOME_FUNCAO_PRINCIPAL:
                variaveis = {k: _valor_serializavel(v) for k, v in f.f_globals.items()
                             if k in nomes_globais}
                pilha.append({"nome": "Principal", "variaveis": variaveis})
            elif nome in nomes_funcoes_conhecidas:
                variaveis = {k: _valor_serializavel(v) for k, v in f.f_locals.items()
                             if not k.startswith("_")}
                pilha.append({"nome": nome, "variaveis": variaveis})
            # frames de funções auxiliares internas (_algo_...) não entram na pilha visível
            f = f.f_back
        pilha.reverse()
        return pilha

    def tracer(frame, evento, arg):
        if evento == "return":
            # a função principal terminou -- o 'line' da sua última instrução
            # só regista o estado ANTES dela correr, por isso o efeito dessa
            # última linha (consola/variáveis) nunca aparecia em nenhum
            # passo. Aqui, no retorno, já correu -- atualiza o último passo
            # em vez de acrescentar um novo, para não violar "um passo por
            # linha executada".
            if (passos and frame.f_code.co_filename == caminho_py
                    and frame.f_code.co_name == NOME_FUNCAO_PRINCIPAL):
                pilha_final = construir_pilha(frame)
                if pilha_final:
                    passos[-1] = {
                        "linha": passos[-1]["linha"],
                        "consola": buffer_saida.getvalue(),
                        "pilha": pilha_final,
                    }
            return tracer
        if evento != "line":
            return tracer
        if frame.f_code.co_filename != caminho_py:
            return tracer
        linha_algo = mapa_linhas.get(frame.f_lineno)
        if linha_algo is None:
            return tracer
        pilha = construir_pilha(frame)
        if not pilha:
            # execução ainda ao nível do módulo (ex: a definir 'class Ponto' ou
            # 'def dobro' antes do programa entrar em _algo_programa) -- não é
            # um passo relevante para mostrar ao aluno
            return tracer
        if len(passos) >= MAX_PASSOS:
            limite_excedido["valor"] = True
            raise LimiteDePassosExcedido()
        passos.append({
            "linha": linha_algo,
            "consola": buffer_saida.getvalue(),
            "pilha": pilha,
        })
        return tracer

    buffer_saida = io.StringIO()
    entrada_stream = io.StringIO("\n".join(entradas)) if entradas is not None else None

    namespace = {"__name__": "__main__", "__file__": caminho_py}
    codigo_compilado = compile(codigo_py, caminho_py, "exec")

    gestor_stdin = _redirect_stdin(entrada_stream) if entrada_stream is not None \
        else contextlib.nullcontext()

    # A PARTIR DAQUI e até ao 'finally' mais abaixo, sys.settrace(tracer)
    # está ativo -- nenhum código que corra neste intervalo (incluindo
    # construir_pilha, tracer(), _valor_serializavel, e até o __enter__/
    # __exit__ de _redirect_stdin) é visível à medição de cobertura, já
    # que o próprio coverage.py também usa sys.settrace() para se medir
    # a si próprio -- só um pode estar ativo de cada vez. Confirmado
    # manualmente que todo este código corre (--debug/--json têm dezenas
    # de testes), só não fica registado nas métricas.
    tracer_anterior = sys.gettrace()
    sys.settrace(tracer)
    try:
        with contextlib.redirect_stdout(buffer_saida), gestor_stdin:
            exec(codigo_compilado, namespace)
    except LimiteDePassosExcedido:
        pass
    except SystemExit:
        pass
    except Exception as e:  # pragma: no cover -- rede de segurança, não deve ocorrer
        resultado_erro["valor"] = {"mensagem": str(e), "linha": None}
    finally:
        sys.settrace(tracer_anterior)

    consola_final = buffer_saida.getvalue()

    # AL-23/AL-24: o próprio runtime já apanha os erros de execução comuns
    # (e falhas de 'afirmar') e regista a mensagem/linha em
    # _ALGO_ERRO_RUNTIME antes de sys.exit(1) (ver
    # codegen.py:_algo_registar_erro_runtime) -- lido diretamente do
    # namespace da execução, em vez de inferir a partir do texto impresso
    # na consola. A deteção antiga (endswith de frases fixas) cobria só 3
    # dos 4 tipos de erro (faltava ValueError, AL-23) e corria o risco de
    # um escrever() legítimo do próprio estudante coincidir por acaso com
    # uma dessas frases (AL-24) -- este canal não depende de texto nenhum.
    erro_runtime = namespace.get("_ALGO_ERRO_RUNTIME")
    if resultado_erro["valor"] is None and erro_runtime is not None:
        linha_erro = erro_runtime["linha"]
        if linha_erro is None:
            linha_erro = passos[-1]["linha"] if passos else None
        resultado_erro["valor"] = {"mensagem": erro_runtime["mensagem"], "linha": linha_erro}

    return {
        "passos": passos,
        "consolaFinal": consola_final,
        "erro": resultado_erro["valor"],
        "limiteExcedido": limite_excedido["valor"],
    }
