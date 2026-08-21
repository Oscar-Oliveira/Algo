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
# AUDITORIA_2026-08-19 bug #36-bis (ronda 13): "Principal" sozinho é um
# identificador ALGO válido -- um estudante podia legalmente chamar uma
# função sua "Principal" (a palavra até faz sentido nesse contexto) e
# ficar com duas entradas indistinguíveis na pilha do trace. Parênteses
# nunca são válidos num identificador (ver lexer.py: um ID só aceita
# letra/'_' seguido de alfanumérico/'_'), por isso este rótulo nunca
# pode colidir com o nome de nenhuma função do estudante.
NOME_VISIVEL_PRINCIPAL = "(Principal)"


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

    # AUDITORIA_2026-08-19 bug #17: 'pilha_frames'/'pilha_incremental'
    # mantêm a pilha de frames VISÍVEIS (mesmo filtro que
    # construir_pilha) incrementalmente, empurrada/retirada só nos
    # eventos 'call'/'return' -- em vez de reconstruir a cadeia
    # completa (frame.f_back) a CADA linha traçada, que tornava o
    # custo total O(profundidade²) numa recursão profunda (medido:
    # profundidade 1990 a demorar ~9.5s). A cada evento 'line', só a
    # entrada do TOPO (o frame atualmente a executar) é recalculada --
    # as entradas das frames ANCESTRAIS mantêm-se tal como estavam na
    # ÚLTIMA vez que cada uma foi o frame "atual" (não podem ter mudado
    # entretanto: Python é de execução única, uma frame ancestral fica
    # inerte enquanto uma frame mais funda está a correr). Cada entrada
    # é sempre SUBSTITUÍDA (nunca mutada) ao ser atualizada, para o
    # 'list(pilha_incremental)' de um passo já registado nunca ficar
    # corrompido por uma atualização posterior a essa MESMA lista viva.
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
                # AL-67/B27: o lexer permite explicitamente identificadores
                # ALGO começados por '_' (ex.: 'funcao f(_x:inteiro)') --
                # filtrar por "começa com '_'" escondia essas variáveis
                # REAIS do estudante do trace, não só os temporários
                # internos do compilador (que usam sempre o prefixo
                # '_algo_'). '_' sozinho é o único outro nome interno
                # gerado sem esse prefixo (destino descartado do valor de
                # retorno principal de uma chamada com 'ref' usada como
                # instrução solta -- ver _gerar_chamada_stmt).
                variaveis = {k: _valor_serializavel(v) for k, v in f.f_locals.items()
                             if not k.startswith("_algo_") and k != "_"}
                pilha.append({"nome": nome, "variaveis": variaveis})
            # frames de funções auxiliares internas (_algo_...) não entram na pilha visível
            f = f.f_back
        pilha.reverse()
        return pilha

    def _indice_do_ultimo_passo_em_principal(linha_alvo):
        """AL-71/AL-97(B25): encontra o último passo cuja pilha estava
        diretamente em _algo_programa (só "Principal", sem nenhuma função
        aninhada) E cuja linha é a da própria instrução final (linha_alvo)
        -- NÃO presumir que é sempre 'passos[-1]', nem que basta filtrar
        pela forma da pilha. Se a ÚLTIMA instrução do 'inicio' for (ou
        terminar n)a ÚNICA chamada a uma função/procedimento do
        utilizador em todo o programa, o passo "só Principal" mais
        recente por FORMA fica na posição 0 (a primeira e única vez que
        esse padrão apareceu em todo o trace, não perto do fim) -- sem o
        filtro adicional por linha, sobrescrever esse índice corrompia o
        PRIMEIRO passo do trace com o estado FINAL do programa, fazendo a
        consola "andar para trás" ao avançar passo a passo. Filtrar
        também por linha_alvo (a linha ALGO da própria instrução que está
        a retornar, não das linhas dentro da função chamada) garante que
        encontramos sempre o passo certo, mesmo que o mesmo padrão "só
        Principal" já tenha aparecido antes para outra instrução. Devolve
        None se não encontrar nenhum (não deve acontecer -- a própria
        instrução que levou a esta chamada tem de ter gerado um passo em
        _algo_programa antes de entrar em qualquer função)."""
        for i in range(len(passos) - 1, -1, -1):
            passo = passos[i]
            pilha = passo["pilha"]
            if (len(pilha) == 1 and pilha[0]["nome"] == NOME_VISIVEL_PRINCIPAL
                    and passo["linha"] == linha_alvo):
                return i
        return None  # pragma: no cover -- defensivo, ver docstring

    def _nome_visivel_ou_none(frame):
        """bug #17: mesmo filtro que construir_pilha usa para decidir se
        uma frame conta para a pilha visível (a função principal, ou uma
        função/procedimento do próprio estudante) -- devolve o nome a
        mostrar, ou None se a frame não for visível (ex.: um frame
        interno _algo_..., de uma biblioteca, ou fora do ficheiro
        gerado)."""
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
                        # AL-97/B25: a última instrução não entrou em
                        # nenhuma função do utilizador -- o seu próprio
                        # passo já é o último da lista, por isso
                        # atualizá-lo em vez de acrescentar mantém "um
                        # passo por linha executada" sem reordenar nada.
                        passos[indice] = passo_final
                    else:
                        # AL-97/B25: a última instrução ENTROU numa
                        # função do utilizador (ex.: 'escrever(f(10))'),
                        # que já acrescentou passos a seguir ao seu
                        # próprio (dentro de 'f'). Sobrescrever esse
                        # passo mais antigo, como antes, corrompia a
                        # ORDEM CRONOLÓGICA da lista -- ficava com o
                        # estado FINAL do programa (consola completa)
                        # numa posição anterior a passos que na
                        # realidade aconteceram primeiro, fazendo a
                        # consola "andar para trás" ao avançar no trace.
                        # Acrescentar um passo novo no fim preserva a
                        # ordem; o passo antigo mantém-se tal como
                        # estava (o estado ANTES de entrar em 'f').
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
        # bug #17: só a entrada do TOPO (a frame atual) precisa de ser
        # recalculada -- as ancestrais mantêm o valor da última vez que
        # cada uma foi a frame atual (ver comentário mais acima).
        # SUBSTITUÍDA (não mutada), para não corromper um 'list(...)'
        # já guardado num passo anterior.
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
            raise LimiteDePassosExcedido()
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
        # bug #36: ao contrário do exec() mais abaixo (já protegido por um
        # 'except Exception' de rede de segurança), este compile() estava
        # completamente desprotegido -- se o Python gerado for
        # sintaticamente inválido (ex.: bug #24, um bug de codegen
        # gerando 'else' sem 'if'), a exceção propagava crua até
        # cli.py, e dentro da consola interativa (cmd_consola) chegava a
        # fechar a sessão inteira, já que o ciclo de comandos só apanhava
        # SystemExit/KeyboardInterrupt. Devolve o mesmo formato de erro
        # que qualquer outra falha, sem tentar traçar nada (não há nada
        # de executável para traçar).
        return {
            "passos": [],
            "consolaFinal": "",
            "erro": {"mensagem": f"erro interno do compilador: {e}", "linha": None},
            "limiteExcedido": False,
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
