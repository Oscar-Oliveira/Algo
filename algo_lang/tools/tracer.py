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
import time
import builtins
import contextlib

MAX_PASSOS = 4000
# Mesma ideia e mesmo valor que LIMITE_CPU_SEGUNDOS (cli.py) para o
# caminho sem trace -- MAX_PASSOS sozinho conta LINHAS executadas, não o
# custo de cada uma; um ciclo com poucas iterações mas caro por iteração
# (ex.: um passo que serializa uma estrutura/vetor grande para o trace)
# podia levar muito tempo sem nunca se aproximar de MAX_PASSOS. Usa
# time.process_time() (tempo de CPU, não de relógio) pela mesma razão que
# LIMITE_CPU_SEGUNDOS: nunca interromper um programa legitimamente
# bloqueado em ler() à espera do estudante.
LIMITE_TEMPO_SEGUNDOS = 10
NOME_FUNCAO_PRINCIPAL = "_algo_programa"
# Parênteses nunca são válidos num identificador ALGO, por isso este
# rótulo nunca colide com o nome de uma função do estudante (mesmo uma
# chamada "Principal").
NOME_VISIVEL_PRINCIPAL = "(Principal)"


class LimiteDePassosExcedido(Exception):
    pass


class LimiteDeTempoExcedido(Exception):
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


def _arredondar_decimal(v):
    """Espelha o arredondamento de codegen.py:_algo_fmt (12 casas decimais,
    '-0.0' normalizado para 0.0), para o inspetor de variáveis do
    --debug/--json mostrar o mesmo valor que 'escrever' mostraria."""
    v = round(v, 12)
    return 0.0 if v == 0.0 else v


def _valor_serializavel(v):
    """Converte um valor Python num valor pronto para JSON, mantendo os
    tipos nativos quando possível (para a página web poder formatar como
    quiser) em vez de os transformar já em texto."""
    if isinstance(v, float):
        return _arredondar_decimal(v)
    if isinstance(v, (int, bool, str)) or v is None:
        return v
    if isinstance(v, list):
        return [_valor_serializavel(e) for e in v]
    if hasattr(v, "__dict__"):  # instância de uma 'estrutura'
        return {k: _valor_serializavel(val) for k, val in vars(v).items()}
    return repr(v)


def _fmt_debug(v):
    if isinstance(v, bool):
        return "verdadeiro" if v else "falso"
    if isinstance(v, float):
        return repr(_arredondar_decimal(v))
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
        "limiteTipo": None | "passos" | "tempo",
    }

    'entradas': lista de strings para alimentar ler(), ou None para usar
    o stdin real do processo (permite entrada interativa).
    """
    nomes_funcoes_conhecidas = set(nomes_funcoes) | {NOME_FUNCAO_PRINCIPAL}
    passos = []
    limite_excedido = {"valor": False, "tipo": None}
    resultado_erro = {"valor": None}

    # 'pilha_frames'/'pilha_incremental' mantêm a pilha de frames visíveis
    # incrementalmente (empurrada/retirada só nos eventos 'call'/'return'),
    # em vez de reconstruir a cadeia completa a cada linha traçada, o que
    # seria O(profundidade²) numa recursão profunda. Cada entrada é sempre
    # SUBSTITUÍDA (nunca mutada) ao ser atualizada, para o
    # 'list(pilha_incremental)' de um passo já registado não ficar
    # corrompido por uma atualização posterior.
    pilha_frames = []
    pilha_incremental = []

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
                pilha.append({"nome": NOME_VISIVEL_PRINCIPAL, "variaveis": variaveis})
            elif nome in nomes_funcoes_conhecidas:
                # O lexer permite identificadores ALGO começados por '_' --
                # filtrar variáveis por "começa com '_'" esconderia essas
                # variáveis reais do estudante. Só '_algo_'-prefixados e o
                # nome '_' sozinho (destino descartado de um 'ref' usado
                # como instrução solta -- ver _gerar_chamada_stmt) são
                # internos do compilador.
                variaveis = {k: _valor_serializavel(v) for k, v in f.f_locals.items()
                             if not k.startswith("_algo_") and k != "_"}
                pilha.append({"nome": nome, "variaveis": variaveis})
            # frames de funções auxiliares internas (_algo_...) não entram na pilha visível
            f = f.f_back
        pilha.reverse()
        return pilha

    def _indice_do_ultimo_passo_em_principal(linha_alvo):
        """Encontra o último passo cuja pilha estava só em _algo_programa
        (sem função aninhada) E cuja linha é a da própria instrução
        (linha_alvo) -- filtrar só pela forma da pilha pode escolher a
        ocorrência errada quando o mesmo padrão "só Principal" já apareceu
        antes, noutra instrução. Devolve None se não encontrar (não deve
        acontecer)."""
        for i in range(len(passos) - 1, -1, -1):
            passo = passos[i]
            pilha = passo["pilha"]
            if (len(pilha) == 1 and pilha[0]["nome"] == NOME_VISIVEL_PRINCIPAL
                    and passo["linha"] == linha_alvo):
                return i
        return None  # pragma: no cover -- defensivo, ver docstring

    def _nome_visivel_ou_none(frame):
        """Mesmo filtro que construir_pilha usa para decidir se uma frame
        conta para a pilha visível -- devolve o nome a mostrar, ou None se
        a frame não for visível (ex.: um frame interno _algo_..., de uma
        biblioteca, ou fora do ficheiro gerado)."""
        if frame.f_code.co_filename != caminho_py:
            return None
        nome = frame.f_code.co_name
        if nome == NOME_FUNCAO_PRINCIPAL:
            return NOME_VISIVEL_PRINCIPAL
        if nome in nomes_funcoes_conhecidas:
            return nome
        return None

    def tracer(frame, evento, arg):
        if evento == "call":
            nome_visivel = _nome_visivel_ou_none(frame)
            if nome_visivel is not None:
                pilha_frames.append(frame)
                pilha_incremental.append({"nome": nome_visivel, "variaveis": {}})
            return tracer
        if evento == "return":
            if pilha_frames and frame is pilha_frames[-1]:
                pilha_frames.pop()
                pilha_incremental.pop()
            # a função principal terminou -- o 'line' da sua última instrução
            # só regista o estado ANTES dela correr, por isso o efeito dessa
            # última linha (consola/variáveis) nunca aparecia em nenhum
            # passo. Aqui, no retorno, já correu -- atualiza esse passo
            # em vez de acrescentar um novo, para não violar "um passo por
            # linha executada".
            if (passos and frame.f_code.co_filename == caminho_py
                    and frame.f_code.co_name == NOME_FUNCAO_PRINCIPAL):
                linha_alvo = mapa_linhas.get(frame.f_lineno)
                pilha_final = construir_pilha(frame)
                indice = (_indice_do_ultimo_passo_em_principal(linha_alvo)
                          if linha_alvo is not None else None)
                if pilha_final and indice is not None:
                    passo_final = {
                        "linha": passos[indice]["linha"],
                        "consola": buffer_saida.getvalue(),
                        "pilha": pilha_final,
                    }
                    if indice == len(passos) - 1:
                        # A última instrução não entrou em nenhuma função
                        # do utilizador -- o seu próprio passo já é o
                        # último da lista, por isso atualizá-lo mantém "um
                        # passo por linha executada".
                        passos[indice] = passo_final
                    else:
                        # A última instrução ENTROU numa função do
                        # utilizador (ex.: 'escrever(f(10))'), que já
                        # acrescentou passos a seguir ao seu. Sobrescrever
                        # esse passo mais antigo corromperia a ordem
                        # cronológica; acrescentar um passo novo no fim
                        # preserva-a.
                        passos.append(passo_final)
            return tracer
        if evento != "line":
            return tracer
        if frame.f_code.co_filename != caminho_py:
            return tracer
        linha_algo = mapa_linhas.get(frame.f_lineno)
        if linha_algo is None:
            return tracer
        if not pilha_incremental:
            # execução ainda ao nível do módulo (ex: a definir 'class Ponto' ou
            # 'def dobro' antes do programa entrar em _algo_programa) -- não é
            # um passo relevante para mostrar ao aluno
            return tracer
        # Só a entrada do TOPO (a frame atual) precisa de ser recalculada
        # -- as ancestrais mantêm o valor da última vez que cada uma foi a
        # frame atual (ver comentário mais acima). SUBSTITUÍDA (não
        # mutada), para não corromper um 'list(...)' já guardado num passo
        # anterior.
        nome_atual = pilha_incremental[-1]["nome"]
        if nome_atual == NOME_VISIVEL_PRINCIPAL:
            variaveis_atuais = {k: _valor_serializavel(v) for k, v in frame.f_globals.items()
                                 if k in nomes_globais}
        else:
            variaveis_atuais = {k: _valor_serializavel(v) for k, v in frame.f_locals.items()
                                 if not k.startswith("_algo_") and k != "_"}
        pilha_incremental[-1] = {"nome": nome_atual, "variaveis": variaveis_atuais}
        if len(passos) >= MAX_PASSOS:
            limite_excedido["valor"] = True
            limite_excedido["tipo"] = "passos"
            raise LimiteDePassosExcedido()
        if time.process_time() - tempo_inicio > LIMITE_TEMPO_SEGUNDOS:
            limite_excedido["valor"] = True
            limite_excedido["tipo"] = "tempo"
            raise LimiteDeTempoExcedido()
        passos.append({
            "linha": linha_algo,
            "consola": buffer_saida.getvalue(),
            "pilha": list(pilha_incremental),
        })
        return tracer

    buffer_saida = io.StringIO()
    entrada_stream = io.StringIO("\n".join(entradas)) if entradas is not None else None

    namespace = {"__name__": "__main__", "__file__": caminho_py}
    try:
        codigo_compilado = compile(codigo_py, caminho_py, "exec")
    except SyntaxError as e:
        # Se o Python gerado for sintaticamente inválido, esta exceção não
        # pode propagar crua até cli.py -- dentro da consola interativa
        # (cmd_consola) isso fecharia a sessão inteira, já que o ciclo de
        # comandos só apanha SystemExit/KeyboardInterrupt. Devolve o mesmo
        # formato de erro que qualquer outra falha.
        return {
            "passos": [],
            "consolaFinal": "",
            "erro": {"mensagem": f"erro interno do compilador: {e}", "linha": None},
            "limiteExcedido": False,
            "limiteTipo": None,
        }

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
    tempo_inicio = time.process_time()
    tracer_anterior = sys.gettrace()
    sys.settrace(tracer)
    try:
        with contextlib.redirect_stdout(buffer_saida), gestor_stdin:
            exec(codigo_compilado, namespace)
    except LimiteDePassosExcedido:
        pass
    except LimiteDeTempoExcedido:
        pass
    except SystemExit:
        pass
    except Exception as e:  # pragma: no cover -- rede de segurança, não deve ocorrer
        resultado_erro["valor"] = {"mensagem": str(e), "linha": None}
    finally:
        sys.settrace(tracer_anterior)

    consola_final = buffer_saida.getvalue()

    # O runtime já regista a mensagem/linha do erro em _ALGO_ERRO_RUNTIME
    # antes de sys.exit(1) (ver codegen.py:_algo_registar_erro_runtime) --
    # lido diretamente do namespace da execução, em vez de inferir a partir
    # do texto impresso na consola.
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
        "limiteTipo": limite_excedido["tipo"],
    }
