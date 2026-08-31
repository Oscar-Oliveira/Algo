# -*- coding: utf-8 -*-
"""Executa um programa Algo de um estudante, de forma interativa
(suporta ler() a meio da execução, tal como a consola local), isolado
por processo próprio e por pasta temporária própria -- nunca bloqueia
o servidor (usa asyncio.create_subprocess_exec, não subprocess.run),
e nunca deixa um processo fugido consumir a máquina indefinidamente
(limites de tempo e memória).

Chama as primitivas do compilador diretamente (parse/verificar/
gerar_python), não o algo_lang.cli.compilar_ficheiro -- ver a nota em
compilar_codigo() sobre porquê. O compilador em si não é alterado."""
from __future__ import annotations

import asyncio
import os
import queue
import shutil
import sys
import tempfile
import threading
import time
import uuid
import xml.etree.ElementTree as ET

_NS_SVG = "http://www.w3.org/2000/svg"
_NS_XLINK = "http://www.w3.org/1999/xlink"
ET.register_namespace("", _NS_SVG)
ET.register_namespace("xlink", _NS_XLINK)

_RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ_PROJETO not in sys.path:
    sys.path.insert(0, _RAIZ_PROJETO)

from algo_lang.compilador.parser import parse, parse_biblioteca
from algo_lang.compilador.semantics import verificar, ErroSemantico
from algo_lang.compilador.lexer import ErroLexico
from algo_lang.compilador.parser import ErroSintatico
from algo_lang.compilador.codegen import gerar_python, gerar_python_com_mapa, ErroInternoCompilador
from algo_lang.compilador.inclusoes import mesclar_biblioteca_no_programa, ColisaoDeInclusao
from algo_lang.tools.flowchart import gerar_dot
from algo_lang.tools.tracer import gerar_trace, formatar_passo_debug
from algo_lang.tools import linter as linter_modulo

PASTA_EXECUCOES_POR_OMISSAO = os.path.join(tempfile.gettempdir(), "algo_online_execucoes")

LIMITE_TEMPO_SEGUNDOS = 10
LIMITE_MEMORIA_BYTES = 256 * 1024 * 1024  # 256 MB
LIMITE_INATIVIDADE_SEGUNDOS = 60  # janela por ler(), reiniciada a cada entrada enviada

# ON-04: a linguagem ALGO não tem forma de abrir ficheiros arbitrários
# -- este limite é generoso face ao que um programa legítimo precisa,
# só para conter uma exaustão de descritores de ficheiro caso o
# gerador de código alguma vez permita abrir ficheiros.
#
# Limite de número de PROCESSOS fica de fora daqui de propósito:
# RLIMIT_NPROC é, no Linux, um contador por UID do próprio kernel --
# partilhado por TODOS os processos desse utilizador, incluindo fora
# do contentor -- e confirmado nada fiável em testes (tanto afetado
# por processos não relacionados como, nalguns motores de contentores,
# nem sequer aplicado). O limite de processos é aplicado antes por
# `--pids-limit`/`pids_limit:` do Docker (cgroups, isolado por
# contentor) -- ver Dockerfile/docker-compose.yml e README.md.
LIMITE_DESCRITORES_FICHEIRO = 256

_BOOTSTRAP_LIMITES_RECURSOS = f"""\
import resource, os, sys
resource.setrlimit(resource.RLIMIT_CPU, ({LIMITE_TEMPO_SEGUNDOS}, {LIMITE_TEMPO_SEGUNDOS}))
resource.setrlimit(resource.RLIMIT_AS, ({LIMITE_MEMORIA_BYTES}, {LIMITE_MEMORIA_BYTES}))
resource.setrlimit(resource.RLIMIT_NOFILE, ({LIMITE_DESCRITORES_FICHEIRO}, {LIMITE_DESCRITORES_FICHEIRO}))
os.execv(sys.executable, [sys.executable, sys.argv[1]])
"""

# pastas de execução mais antigas do que isto são candidatas a limpeza em
# segundo plano -- generosamente acima do tempo de vida máximo de
# qualquer execução em curso (LIMITE_INATIVIDADE_SEGUNDOS renova-se a
# cada entrada enviada, mas nunca por mais de uma hora de sessão real),
# para nunca apagar a pasta de uma execução concorrente ainda em curso
IDADE_MINIMA_PARA_LIMPEZA_SEGUNDOS = 3600


class ErroCompilacao(Exception):
    """Erro de sintaxe/semântica -- não chega a executar nada."""
    pass


def _env_minimo() -> dict:
    """ON-05: o subprocesso que corre o programa do estudante não deve
    herdar as variáveis de ambiente do servidor -- em particular
    ONLINE_CHAVE_CIFRAGEM/ONLINE_CHAVE_SESSAO (ver main.py), que nunca
    deviam estar acessíveis a código escrito pelo estudante. Só o
    mínimo necessário para o Python arrancar corretamente."""
    minimo = {"PATH": os.environ.get("PATH", "")}
    if os.name == "nt":  # pragma: no cover -- produção corre sempre em Linux (ver Dockerfile)
        for chave in ("SYSTEMROOT", "SYSTEMDRIVE", "TEMP", "TMP"):
            if chave in os.environ:
                minimo[chave] = os.environ[chave]
    return minimo


def _limpar_pastas_antigas_em_fundo(pasta_pseudonimo: str) -> None:
    """Apaga pastas de execuções ANTIGAS (mais velhas que
    IDADE_MINIMA_PARA_LIMPEZA_SEGUNDOS) do mesmo estudante --
    best-effort, nunca bloqueia nem falha o pedido atual. Crucial: o
    critério é a IDADE de cada pasta, nunca "todas exceto a mais
    recente" -- uma execução concorrente ainda em curso (ex: duas abas
    do browser, ou o fluxograma pedido enquanto uma execução decorre)
    tem sempre uma pasta recente, por isso nunca é apagada por engano
    a meio. Corre fora do event loop quando há um a correr (não
    bloqueia o pedido que acabou de pedir uma pasta nova); corre já,
    de forma síncrona, quando chamada fora de um contexto assíncrono
    (ex: testes)."""
    def _limpar():
        agora = time.time()
        for nome in os.listdir(pasta_pseudonimo):
            caminho = os.path.join(pasta_pseudonimo, nome)
            try:
                idade = agora - os.path.getmtime(caminho)
            except OSError:
                continue
            if idade > IDADE_MINIMA_PARA_LIMPEZA_SEGUNDOS:
                shutil.rmtree(caminho, ignore_errors=True)
    try:
        asyncio.get_running_loop().run_in_executor(None, _limpar)
    except RuntimeError:
        _limpar()


def preparar_pasta_execucao(id_pseudonimo: str,
                             pasta_base: str = PASTA_EXECUCOES_POR_OMISSAO) -> str:
    """Uma pasta nova por EXECUÇÃO (não por estudante) -- nome único
    (UUID), para que pedidos concorrentes do mesmo estudante (duas
    abas do browser, ou o fluxograma pedido enquanto uma execução
    ainda está em curso) nunca colidam nem apaguem ficheiros uns dos
    outros a meio (ON-07/ARCH-11: antes, a mesma pasta por estudante
    era apagada com shutil.rmtree a cada novo pedido). Pastas antigas
    do mesmo estudante são limpas em segundo plano -- nunca guarda
    código entre visitas, por decisão explícita (sem persistência de
    programas)."""
    pasta_pseudonimo = os.path.join(pasta_base, id_pseudonimo)
    os.makedirs(pasta_pseudonimo, exist_ok=True)
    pasta = os.path.join(pasta_pseudonimo, uuid.uuid4().hex)
    os.makedirs(pasta)
    _limpar_pastas_antigas_em_fundo(pasta_pseudonimo)
    return pasta


def _resolver_inclusoes(programa, pasta_base) -> None:
    """Reimplementação de algo_lang.cli._resolver_inclusoes, sem os
    sys.exit(1) -- levanta ErroCompilacao em vez disso. A lógica em si
    (ler cada ficheiro incluído, juntar as suas funções/estruturas/
    declarações ao programa principal) é a mesma; só a forma de
    reportar erro muda. AL-36: suporta inclusões aninhadas (uma
    biblioteca incluir outra), tal como cli.py.

    ON-02: 'inc.caminho' vem do código do estudante -- um caminho
    absoluto ou com '../' permitiria ler qualquer ficheiro do servidor.
    Confinado a 'pasta_base' via os.path.realpath + verificação de
    prefixo (os.path.join já descarta pasta_base se inc.caminho for
    absoluto, por isso o realpath resolve para fora do prefixo em
    ambos os casos -- tratados da mesma forma, com a mesma mensagem de
    erro de 'não encontrado', para não revelar se o caminho existe
    fora da pasta permitida). As inclusões aninhadas continuam
    confinadas à MESMA 'pasta_base' (nunca à pasta do ficheiro incluído
    que as trouxe) -- o editor web não tem subpastas, todos os
    ficheiros do estudante vivem sempre lado a lado, por isso isto não
    muda o comportamento prático, só evita alargar por engano o
    perímetro de segurança se essa suposição alguma vez deixar de ser
    verdade."""
    ja_incluidos = {}
    pasta_base_real = os.path.realpath(pasta_base)
    _resolver_lista_de_inclusoes(programa, programa.inclusoes, pasta_base, pasta_base_real, ja_incluidos)


def _resolver_lista_de_inclusoes(programa, inclusoes, pasta_base, pasta_base_real, ja_incluidos) -> None:
    for inc in inclusoes:
        caminho_real = os.path.realpath(os.path.join(pasta_base, inc.caminho))
        try:
            dentro_da_pasta = os.path.commonpath([caminho_real, pasta_base_real]) == pasta_base_real
        except ValueError:  # caminhos em unidades/discos diferentes (Windows)
            dentro_da_pasta = False
        if caminho_real in ja_incluidos:
            alias_anterior = ja_incluidos[caminho_real]
            if inc.como != alias_anterior:
                descricao_anterior = f"com o alias '{alias_anterior}'" if alias_anterior else "sem alias"
                descricao_nova = f"com o alias '{inc.como}'" if inc.como else "sem alias"
                raise ErroCompilacao(
                    f"Erro na linha {inc.linha}: ficheiro incluído '{inc.caminho}' já foi "
                    f"incluído antes {descricao_anterior}; não pode ser incluído outra vez "
                    f"{descricao_nova}."
                )
            continue
        if not dentro_da_pasta or not os.path.isfile(caminho_real):
            raise ErroCompilacao(
                f"Erro na linha {inc.linha}: ficheiro incluído '{inc.caminho}' não encontrado "
                f"-- confirma que criaste esse ficheiro antes de o executares."
            )
        ja_incluidos[caminho_real] = inc.como
        with open(caminho_real, "r", encoding="utf-8") as f:
            codigo = f.read()
        try:
            declaracoes, funcoes, estruturas, inclusoes_aninhadas = parse_biblioteca(codigo)
        except (ErroLexico, ErroSintatico) as e:
            raise ErroCompilacao(f"Erro em '{inc.caminho}': {e}") from e

        try:
            mesclar_biblioteca_no_programa(
                programa, inc.caminho, declaracoes, funcoes, estruturas, alias=inc.como)
        except ColisaoDeInclusao as e:
            if e.tipo == "alias":
                raise ErroCompilacao(
                    f"O alias '{e.nome}' (usado em '{e.caminho_origem}') já está a ser "
                    f"usado por outra inclusão -- escolhe um alias diferente.") from e
            if e.tipo == "função":
                raise ErroCompilacao(
                    f"'{e.nome}' (incluído de '{e.caminho_origem}') colide com uma "
                    f"função já definida.") from e
            elif e.tipo == "variável global":
                raise ErroCompilacao(
                    f"A variável '{e.nome}' (incluída de '{e.caminho_origem}') colide "
                    f"com uma variável global já declarada.") from e
            else:
                raise ErroCompilacao(
                    f"A estrutura '{e.nome}' (incluída de '{e.caminho_origem}') colide "
                    f"com uma estrutura já definida.") from e

        _resolver_lista_de_inclusoes(
            programa, inclusoes_aninhadas, pasta_base, pasta_base_real, ja_incluidos)


def _validar_nome_ficheiro(nome: str, pasta_estudante: str) -> str:
    """ON-01: 'nome' vem do editor (controlado pelo estudante) e é usado
    para construir um caminho de escrita -- sem esta validação, um nome
    como '../../outra_pasta/ficheiro.py' ou um caminho absoluto escreve
    fora da pasta do estudante. Exige um nome simples (sem separadores
    de caminho nem '..') e confirma, com os.path.realpath, que o
    caminho final resolvido continua dentro de pasta_estudante -- dupla
    verificação, para não confiar só na whitelist de caracteres.
    Devolve o caminho absoluto já validado."""
    if not nome or nome in (".", "..") or "/" in nome or "\\" in nome:
        raise ErroCompilacao(f"Nome de ficheiro inválido: '{nome}'.")
    caminho = os.path.join(pasta_estudante, nome)
    pasta_real = os.path.realpath(pasta_estudante)
    caminho_real = os.path.realpath(caminho)
    if os.path.commonpath([caminho_real, pasta_real]) != pasta_real:
        raise ErroCompilacao(f"Nome de ficheiro inválido: '{nome}'.")
    return caminho


def _escrever_ficheiros_e_analisar(ficheiros: list[dict], nome_principal: str,
                                    pasta_estudante: str):
    """Escreve todos os ficheiros do estudante na pasta, analisa o
    principal e resolve 'incluir' contra os outros já escritos --
    partilhado por compilar_codigo, gerar_fluxograma_svg e
    gerar_rasto, para não repetir esta parte três vezes. Devolve
    (programa, caminho_principal) já com as inclusões resolvidas,
    ainda SEM verificar() -- cada chamador decide se/quando verificar."""
    nomes_vistos = set()
    caminho_principal = None
    for ficheiro in ficheiros:
        nome = ficheiro["nome"]
        if nome in nomes_vistos:
            raise ErroCompilacao(f"Tens dois ficheiros com o mesmo nome: '{nome}'.")
        nomes_vistos.add(nome)
        caminho = _validar_nome_ficheiro(nome, pasta_estudante)
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(ficheiro["conteudo"])
        if nome == nome_principal:
            caminho_principal = caminho

    if caminho_principal is None:
        raise ErroCompilacao(f"Não encontrei o ficheiro principal '{nome_principal}'.")

    try:
        with open(caminho_principal, "r", encoding="utf-8") as f:
            codigo_principal = f.read()
        programa = parse(codigo_principal)
        _resolver_inclusoes(programa, pasta_estudante)
    except (ErroLexico, ErroSintatico) as e:
        raise ErroCompilacao(str(e)) from e

    return programa, caminho_principal


def compilar_codigo(ficheiros: list[dict], nome_principal: str, pasta_estudante: str) -> str:
    """Escreve TODOS os ficheiros do estudante na sua pasta (o
    principal e quaisquer bibliotecas próprias que ele tenha criado),
    compila o principal, resolvendo 'incluir' contra os outros
    ficheiros já escritos na mesma pasta. Chama as primitivas do
    compilador diretamente (parse/verificar/gerar_python), não
    algo_lang.cli.compilar_ficheiro -- esse wrapper foi escrito para a
    consola e faz sys.exit(1) num erro, o que aqui terminaria o
    servidor inteiro, não só este pedido. O compilador em si
    (parser/semantics/codegen) não é tocado.

    'ficheiros' é uma lista de {"nome": str, "conteudo": str}.
    'nome_principal' tem de corresponder ao "nome" de um deles.
    Devolve o caminho do .py gerado. Levanta ErroCompilacao (mensagem
    já em português, pronta a mostrar ao estudante) em caso de erro."""
    programa, caminho_principal = _escrever_ficheiros_e_analisar(
        ficheiros, nome_principal, pasta_estudante)
    try:
        verificar(programa)
        codigo_py = gerar_python(programa)
    except ErroSemantico as e:
        raise ErroCompilacao(str(e)) from e
    except ErroInternoCompilador as e:  # pragma: no cover -- verificar() já garantiu que o programa é válido antes disto
        raise ErroCompilacao(
            f"{e} -- isto é um bug do próprio ALGO, não do teu programa."
        ) from e
    except RecursionError as e:  # pragma: no cover -- AUDITORIA_2026-08-19 bugs #7/#10:
        # rede de segurança, não a correção principal -- essa está no
        # parser (parser.py:LIMITE_PROFUNDIDADE_ARVORE), que já impede
        # uma AST demasiado profunda de sequer chegar aqui. Fica como
        # defesa em profundidade para qualquer OUTRA travessia recursiva
        # da AST (presente ou futura) que tenha o mesmo problema sem
        # passar pelo parser -- sem isto, um RecursionError propagava
        # até ao handler genérico do FastAPI (main.py), um 500 opaco em
        # vez do erro amigável que o resto do compilador tenta sempre dar.
        raise ErroCompilacao(
            "o teu programa tem uma expressão demasiado complexa (operadores/"
            "aninhamento a mais) para o compilador conseguir processar -- "
            "tenta simplificá-la, ex. dividindo em variáveis intermédias."
        ) from e

    caminho_py = caminho_principal.rsplit(".", 1)[0] + ".py"
    with open(caminho_py, "w", encoding="utf-8") as f:
        f.write(codigo_py)
    return caminho_py


class SaidaExcessiva(Exception):
    """ON-09: uma única linha de saída maior do que o buffer do
    StreamReader (64KB por omissão no asyncio) faz readline() levantar
    ValueError/LimitOverrunError em vez de devolver a linha -- sem
    isto, um programa "preso" a imprimir uma linha gigante sem quebra
    de linha derrubava a leitura inteira com uma exceção não tratada."""
    pass


class ExecucaoInterativa:
    """Envolve um processo de execução em curso -- criar, ler o que
    ele já escreveu, escrever-lhe entradas, terminar. Pensada para ser
    usada a partir de um WebSocket (ver main.py): cada mensagem
    recebida do browser vira uma chamada a `enviar_entrada`, e cada
    linha lida do processo é reencaminhada para o browser."""

    def __init__(self, caminho_py: str, pasta_estudante: str):
        self.caminho_py = caminho_py
        self.pasta_estudante = pasta_estudante
        self.processo: asyncio.subprocess.Process | None = None
        self.terminou = False
        self.codigo_saida: int | None = None
        self.tempo_limite: asyncio.Timeout | None = None

    async def iniciar(self) -> None:
        # ON-04/ON-06: os limites de CPU/memória/descritores de ficheiro
        # têm de ser aplicados DENTRO do processo filho, mas NUNCA via
        # preexec_fn -- a documentação do Python avisa
        # explicitamente que preexec_fn não é seguro na presença de
        # threads no processo pai (corre no intervalo entre fork() e
        # exec(), e pode bloquear o filho indefinidamente). Em vez
        # disso, o filho arranca já como um interpretador Python novo,
        # totalmente independente do processo pai (via -c), aplica os
        # limites com resource.setrlimit -- seguro aqui, porque este
        # código só corre DEPOIS de um exec(), num processo já
        # single-threaded, não no meio de um fork() -- e só depois
        # arranca o programa do estudante com um segundo exec()
        # (os.execv), tornando-se indistinguível de o ter corrido
        # diretamente.
        comando = [sys.executable, self.caminho_py]
        if os.name == "posix":  # pragma: no cover -- ambiente de desenvolvimento é sempre POSIX aqui, mas mantém o código correto para Windows
            comando = [sys.executable, "-c", _BOOTSTRAP_LIMITES_RECURSOS, self.caminho_py]
        self.processo = await asyncio.create_subprocess_exec(
            *comando,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=self.pasta_estudante,
            env=_env_minimo(),
        )

    async def ler_proxima_linha(self) -> str | None:
        """Devolve a próxima linha de saída do programa, ou None
        quando o programa termina. 'escrever()' termina sempre em
        newline (confirmado no codegen), por isso ler linha a linha
        não perde nenhum aviso/pedido de entrada."""
        assert self.processo is not None and self.processo.stdout is not None
        try:
            linha = await self.processo.stdout.readline()
        except (ValueError, asyncio.LimitOverrunError) as e:
            await self.terminar_a_forcar()
            raise SaidaExcessiva(
                "A saída do programa excedeu o limite de tamanho por linha."
            ) from e
        if not linha:
            self.codigo_saida = await self.processo.wait()
            self.terminou = True
            return None
        # rstrip("\r\n") -- em Windows, o processo filho escreve "\r\n"
        # (tradução de newline do próprio Python ao imprimir), não só "\n".
        return linha.decode("utf-8", errors="replace").rstrip("\r\n")

    async def enviar_entrada(self, texto: str) -> None:
        assert self.processo is not None and self.processo.stdin is not None
        self.processo.stdin.write((texto + "\n").encode("utf-8"))
        await self.processo.stdin.drain()
        if self.tempo_limite is not None:
            self.tempo_limite.reschedule(
                asyncio.get_running_loop().time() + LIMITE_INATIVIDADE_SEGUNDOS)

    async def terminar_a_forcar(self) -> None:
        if self.processo is not None and self.processo.returncode is None:
            self.processo.kill()
            await self.processo.wait()
        self.terminou = True


async def correr_com_limite_de_tempo(execucao: ExecucaoInterativa, callback_linha,
                                      limite_segundos: float = LIMITE_TEMPO_SEGUNDOS + 2) -> None:
    """Lê linhas da execução e chama callback_linha(linha) para cada
    uma, até o programa terminar. 'limite_segundos' cobre só o
    arranque (compilar → primeira saída, um pouco acima do limite de
    CPU do próprio processo, para dar folga a E/S bloqueante que não
    conta como tempo de CPU) -- a partir daí, cada entrada enviada por
    ExecucaoInterativa.enviar_entrada() reagenda o prazo para uma nova
    janela de LIMITE_INATIVIDADE_SEGUNDOS, para um programa com vários
    ler() não ficar com um orçamento único partilhado por todas as
    respostas do estudante."""
    try:
        async with asyncio.timeout(limite_segundos) as tempo_limite:
            execucao.tempo_limite = tempo_limite
            while True:
                linha = await execucao.ler_proxima_linha()
                if linha is None:
                    break
                await callback_linha(linha)
    except TimeoutError:
        await execucao.terminar_a_forcar()
        raise
    finally:
        execucao.tempo_limite = None


# ---------- fluxograma ----------

class ErroFluxograma(Exception):
    pass


NOME_PRINCIPAL_PARA_FLUXOGRAMA = "Principal"


def _remover_scripts(elemento: ET.Element) -> None:
    for filho in list(elemento):
        tag_local = filho.tag.rsplit("}", 1)[-1]
        if tag_local == "script":
            elemento.remove(filho)
        else:
            _remover_scripts(filho)


def _sanitizar_svg(svg: str) -> str:
    """ON-34: o SVG vem do graphviz, gerado a partir do código do
    estudante, e o frontend insere-o diretamente via innerHTML -- um
    <script> ou um atributo de evento (onload, onerror, ...) no SVG
    executaria no browser de quem o vir. Os rótulos que flowchart.py
    gera são sempre texto simples entre aspas (nunca rótulos HTML-like
    do graphviz), por isso já vêm devidamente escapados pelo próprio
    graphviz -- isto é defesa em profundidade, não a correção de um XSS
    já reproduzido. Remove qualquer <script> e qualquer atributo 'on*'
    ou 'href'/'xlink:href' com esquema javascript:, sem depender de
    nenhuma biblioteca de sanitização externa (só a stdlib)."""
    try:
        raiz = ET.fromstring(svg)
    except ET.ParseError as e:
        raise ErroFluxograma(f"O graphviz devolveu um SVG inválido: {e}") from e

    _remover_scripts(raiz)
    for elemento in raiz.iter():
        for nome_attr in list(elemento.attrib):
            nome_local = nome_attr.rsplit("}", 1)[-1].lower()
            valor = elemento.attrib[nome_attr]
            if nome_local.startswith("on"):
                del elemento.attrib[nome_attr]
            elif nome_local in ("href",) and valor.strip().lower().startswith("javascript:"):
                del elemento.attrib[nome_attr]

    return ET.tostring(raiz, encoding="unicode")


def gerar_fluxograma_svg(ficheiros: list[dict], nome_principal: str, pasta_estudante: str,
                          nome_rotina: str | None = None) -> dict:
    """Compila e gera o fluxograma em SVG (texto, fácil de embutir
    diretamente numa página -- ao contrário de PNG, não precisa de
    codificação base64) do programa principal OU de uma função/
    procedimento à escolha -- incluindo os que vêm de ficheiros
    incluídos via 'incluir', já que 'programa.funcoes' os já tem todos
    juntos depois de _escrever_ficheiros_e_analisar resolver as
    inclusões. Precisa do binário 'dot' do graphviz instalado no
    sistema (ver Dockerfile) -- sem ele, levanta ErroFluxograma com
    uma mensagem clara em vez de um erro confuso.

    Devolve {"svg": str, "rotinas": [nomes...], "rotina_atual": str} --
    'rotinas' é sempre "Principal" mais o nome de cada função/
    procedimento, para o frontend poder oferecer um seletor."""
    if shutil.which("dot") is None:
        raise ErroFluxograma(
            "O 'graphviz' não está instalado neste servidor -- "
            "o fluxograma não pode ser gerado."
        )

    programa, _ = _escrever_ficheiros_e_analisar(ficheiros, nome_principal, pasta_estudante)
    try:
        verificar(programa)
    except ErroSemantico as e:
        raise ErroCompilacao(str(e)) from e

    nomes_rotinas = {f.nome for f in programa.funcoes}
    rotinas_disponiveis = [NOME_PRINCIPAL_PARA_FLUXOGRAMA] + sorted(nomes_rotinas)

    if nome_rotina is None or nome_rotina == NOME_PRINCIPAL_PARA_FLUXOGRAMA:
        corpo_alvo = programa.corpo
        titulo = programa.nome
        rotina_atual = NOME_PRINCIPAL_PARA_FLUXOGRAMA
    else:
        alvo = next((f for f in programa.funcoes if f.nome == nome_rotina), None)
        if alvo is None:
            raise ErroCompilacao(
                f"Não existe nenhuma função/procedimento '{nome_rotina}' -- "
                f"disponíveis: {', '.join(rotinas_disponiveis)}."
            )
        corpo_alvo = alvo.corpo
        titulo = f"{programa.nome} — {alvo.nome}"
        rotina_atual = alvo.nome

    dot = gerar_dot(corpo_alvo, titulo, nomes_rotinas)

    nome_base = f"fluxograma_{uuid.uuid4().hex[:8]}"
    caminho_dot = os.path.join(pasta_estudante, nome_base + ".dot")
    caminho_svg = os.path.join(pasta_estudante, nome_base + ".svg")
    with open(caminho_dot, "w", encoding="utf-8") as f:
        f.write(dot)

    import subprocess
    resultado = subprocess.run(
        ["dot", "-Tsvg", caminho_dot, "-o", caminho_svg],
        capture_output=True, text=True, timeout=15)
    if resultado.returncode != 0:
        raise ErroFluxograma(f"O graphviz não conseguiu gerar o fluxograma: {resultado.stderr}")

    with open(caminho_svg, encoding="utf-8") as f:
        svg = f.read()
    svg = _sanitizar_svg(svg)

    return {"svg": svg, "rotinas": rotinas_disponiveis, "rotina_atual": rotina_atual}


# ---------- linter ----------

def analisar_linter(ficheiros: list[dict], nome_principal: str, pasta_estudante: str) -> list[dict]:
    """Corre o linter (algo_lang.tools.linter) sobre o programa do
    estudante logo que o parse tenha sucesso -- ao contrário de
    compilar_codigo, NÃO chama verificar(): o linter só percorre a
    AST, não precisa dela ser semanticamente válida, e os erros de
    compilação já são mostrados em separado pelo frontend (ver
    ErroCompilacao). Devolve uma lista de {"mensagem": str, "linha":
    int}, uma por aviso, na mesma ordem (por linha) que Linter.
    analisar() já garante."""
    programa, _ = _escrever_ficheiros_e_analisar(ficheiros, nome_principal, pasta_estudante)
    codigo_principal = next(f["conteudo"] for f in ficheiros if f["nome"] == nome_principal)
    try:
        avisos = linter_modulo.analisar(programa, codigo_principal)
    except RecursionError as e:  # pragma: no cover -- ver o mesmo catch em compilar_codigo:
        # este endpoint (/api/linter) salta verificar() de propósito, por
        # isso é o único caminho real do serviço web que chegava a um
        # RecursionError cru do próprio linter (bug #10) sem passar
        # primeiro por um limiar mais baixo em verificar(). A correção
        # principal está no parser; isto é só a rede de segurança.
        raise ErroCompilacao(
            "o teu programa tem uma expressão demasiado complexa (operadores/"
            "aninhamento a mais) para o compilador conseguir processar -- "
            "tenta simplificá-la, ex. dividindo em variáveis intermédias."
        ) from e
    return [{"mensagem": a.mensagem, "linha": a.linha} for a in avisos]


# ---------- rasto (tracer) ----------

class ErroRasto(Exception):
    pass


def gerar_rasto(ficheiros: list[dict], nome_principal: str, entradas: list[str],
                 pasta_estudante: str) -> dict:
    """Compila e corre o programa sob rasto (algo_lang.tools.tracer),
    com as entradas já indicadas antecipadamente (sem interatividade
    -- decisão explícita de âmbito para esta primeira versão: um
    programa a pedir mais entradas do que as fornecidas simplesmente
    para, tal como já acontece na ferramenta local). Devolve o
    resultado cru de gerar_trace() ACRESCIDO de titulo/ficheiro/
    codigoFonte -- os mesmos três campos que algo_lang.cli.
    cmd_executa_com_trace escreve no ficheiro '..._trace.json', e que
    o visualizador (visualizador/algo-trace-viewer.html) exige para
    aceitar o ficheiro. Mantém 'consolaFinal' (que o CLI não grava no
    .json) porque este dicionário também é devolvido diretamente pelo
    endpoint /api/rasto, e o frontend já o usa antes do download."""
    programa, _ = _escrever_ficheiros_e_analisar(ficheiros, nome_principal, pasta_estudante)
    try:
        verificar(programa)
    except ErroSemantico as e:
        raise ErroCompilacao(str(e)) from e

    dados = gerar_python_com_mapa(programa)
    nome_base = f"rasto_{uuid.uuid4().hex[:8]}"
    caminho_py = os.path.join(pasta_estudante, nome_base + ".py")
    with open(caminho_py, "w", encoding="utf-8") as f:
        f.write(dados["codigo"])

    try:
        resultado = gerar_trace(
            dados["codigo"], caminho_py, dados["mapa_linhas"],
            dados["nomes_globais"], dados["nomes_funcoes"], entradas=entradas,
            nomes_locais_por_funcao=dados["nomes_locais_por_funcao"])
    except Exception as e:
        raise ErroRasto(f"Não foi possível gerar o rasto: {e}") from e

    codigo_principal = next(f["conteudo"] for f in ficheiros if f["nome"] == nome_principal)
    return {
        **resultado,
        "titulo": programa.nome,
        "ficheiro": nome_principal,
        "codigoFonte": codigo_principal.splitlines(),
    }


# ---------- rasto AO VIVO (--debug interativo, via WebSocket) ----------
#
# Peça isolada de propósito -- ver online/main.py (rota /ws/debug) e o
# botão "Debug" no editor. Só esta secção, essas duas pontas em main.py/
# app.js/editor.html, e o parâmetro 'fluxo_entrada' em
# algo_lang/tools/tracer.py existem por causa disto -- retirar a
# funcionalidade é apagar essas peças, sem tocar em mais nada (gerar_rasto
# e ExecucaoInterativa acima não são usados nem alterados por isto).
#
# Ao contrário de ExecucaoInterativa (subprocesso isolado, com
# resource.setrlimit), isto corre o programa do estudante DENTRO do
# processo do servidor, numa thread própria -- sys.settrace só funciona
# no próprio processo, e gerar_trace() é síncrono. Por isso não há
# isolamento por processo aqui: a única rede de segurança contra um
# programa preso é MAX_PASSOS/LIMITE_TEMPO_SEGUNDOS do próprio tracer
# (tools/tracer.py), os mesmos já usados por gerar_rasto acima. Aceite
# de propósito para esta primeira versão, precisamente para ser fácil de
# avaliar e, se não compensar, de retirar.

class ErroDebugAoVivo(Exception):
    pass


def preparar_debug_ao_vivo(ficheiros: list[dict], nome_principal: str, pasta_estudante: str) -> dict:
    """Equivalente a compilar_codigo, mas devolve o que gerar_trace()
    precisa (código Python + mapa de linhas, tal como gerar_rasto usa)
    em vez de só o caminho do .py -- ExecucaoComDebugAoVivo (mais abaixo)
    usa isto para arrancar a thread de execução. Levanta ErroCompilacao,
    tal como compilar_codigo (mesmo tratamento de erro, repetido aqui em
    vez de partilhado, para esta secção poder ser removida sem mexer em
    compilar_codigo)."""
    programa, _ = _escrever_ficheiros_e_analisar(ficheiros, nome_principal, pasta_estudante)
    try:
        verificar(programa)
        dados = gerar_python_com_mapa(programa)
    except ErroSemantico as e:
        raise ErroCompilacao(str(e)) from e
    except ErroInternoCompilador as e:  # pragma: no cover -- verificar() já garantiu que o programa é válido antes disto
        raise ErroCompilacao(
            f"{e} -- isto é um bug do próprio ALGO, não do teu programa."
        ) from e
    except RecursionError as e:  # pragma: no cover -- ver o mesmo catch em compilar_codigo
        raise ErroCompilacao(
            "o teu programa tem uma expressão demasiado complexa (operadores/"
            "aninhamento a mais) para o compilador conseguir processar -- "
            "tenta simplificá-la, ex. dividindo em variáveis intermédias."
        ) from e

    nome_base = f"debug_{uuid.uuid4().hex[:8]}"
    caminho_py = os.path.join(pasta_estudante, nome_base + ".py")
    with open(caminho_py, "w", encoding="utf-8") as f:
        f.write(dados["codigo"])
    dados["caminho_py"] = caminho_py
    return dados


class _FluxoEntradaFilaEspera:
    """Um objeto tipo-stdin (só precisa de .readline()) que bloqueia até
    receber uma linha -- para o ler()/input() do programa do estudante
    (a correr na thread de ExecucaoComDebugAoVivo) esperar por uma
    resposta que o estudante ainda vai escrever no browser. Alimentado
    por enviar()/fechar(), chamados a partir do event loop -- queue.Queue
    já é thread-safe, por isso não precisa de nenhum lock à parte. None
    sinaliza fim de entrada (EOF, ver fechar())."""

    def __init__(self):
        self._fila = queue.Queue()

    def readline(self) -> str:
        linha = self._fila.get()
        return "" if linha is None else linha + "\n"

    def enviar(self, texto: str) -> None:
        self._fila.put(texto)

    def fechar(self) -> None:
        self._fila.put(None)


class ExecucaoComDebugAoVivo:
    """O equivalente, para o rasto AO VIVO, do que ExecucaoInterativa é
    para a execução normal -- mas em vez de um subprocesso lido linha a
    linha, corre gerar_trace() numa thread própria (ver o aviso de
    isolamento no topo desta secção) e traduz cada passo, já formatado
    por formatar_passo_debug (a mesma função que o --debug ao vivo da
    CLI usa -- ver tools/tracer.py:ImpressorDebugAoVivo, para as duas
    formas nunca divergirem), em eventos que main.py reencaminha para o
    WebSocket."""

    def __init__(self, dados_compilados: dict, pasta_estudante: str):
        self.dados = dados_compilados
        self.pasta_estudante = pasta_estudante
        self.entrada = _FluxoEntradaFilaEspera()
        self.eventos: asyncio.Queue = asyncio.Queue()
        self.terminou = False
        self._thread: threading.Thread | None = None

    def iniciar(self) -> None:
        loop = asyncio.get_running_loop()

        def publicar(evento: dict) -> None:
            # call_soon_threadsafe: 'correr' (mais abaixo) corre numa
            # thread à parte, mas self.eventos é um asyncio.Queue, só
            # seguro de mexer a partir do próprio event loop.
            loop.call_soon_threadsafe(self.eventos.put_nowait, evento)

        def correr() -> None:
            try:
                consola_vista = ""

                def on_passo(passo):
                    nonlocal consola_vista
                    linhas, consola_vista = formatar_passo_debug(passo, consola_vista)
                    # cada 'linha' pode conter '\n' embutidos (uma única
                    # diferença de consola a cobrir várias linhas reais de
                    # saída) -- divide sempre, para bater com o contrato
                    # de "saida" que o frontend já espera de /ws/executar
                    # (uma linha real do programa por mensagem).
                    for linha in linhas:
                        for sub_linha in linha.split("\n"):
                            publicar({"tipo": "saida", "texto": sub_linha})

                resultado = gerar_trace(
                    self.dados["codigo"], self.dados["caminho_py"], self.dados["mapa_linhas"],
                    self.dados["nomes_globais"], self.dados["nomes_funcoes"],
                    fluxo_entrada=self.entrada,
                    nomes_locais_por_funcao=self.dados["nomes_locais_por_funcao"],
                    on_passo=on_passo)

                # mesmo 'resto' que ImpressorDebugAoVivo.finalizar() trata na CLI
                resto = resultado["consolaFinal"][len(consola_vista):]
                if resto:
                    for sub_linha in resto.rstrip("\n").split("\n"):
                        publicar({"tipo": "saida", "texto": sub_linha})

                # "erro" é sempre um evento TERMINAL (tal como em /ws/executar) --
                # nunca seguido de "fim", para o frontend não mostrar as duas
                # mensagens (erro + "-- terminou --") uma a seguir à outra.
                if resultado["erro"]:
                    publicar({"tipo": "erro", "mensagem": resultado["erro"]["mensagem"]})
                elif resultado["limiteExcedido"]:
                    # UX-18: mesma mensagem que /ws/executar já usa para o limite do subprocesso
                    mensagem = (
                        "Execução interrompida: excedeu o tempo limite (possível ciclo infinito)."
                        if resultado.get("limiteTipo") == "tempo" else
                        "Execução interrompida: excedeu o limite de passos do rasto (possível ciclo infinito)."
                    )
                    publicar({"tipo": "erro", "mensagem": mensagem})
                else:
                    publicar({"tipo": "fim"})
            except Exception as e:  # pragma: no cover -- rede de segurança, não deve ocorrer
                publicar({"tipo": "erro", "mensagem": f"Erro interno a gerar o rasto: {e}"})
            finally:
                self.terminou = True

        self._thread = threading.Thread(target=correr, daemon=True)
        self._thread.start()

    async def proximo_evento(self) -> dict:
        return await self.eventos.get()

    def enviar_entrada(self, texto: str) -> None:
        self.entrada.enviar(texto)

    def terminar_a_forcar(self) -> None:
        """Não há processo para matar (ver o aviso de isolamento no topo
        desta secção) -- só desbloqueia um ler() pendente com EOF, para a
        thread não ficar presa para sempre à espera de uma entrada que já
        não vai chegar (ex.: o estudante fechou a aba a meio de um
        ler()). A partir daí a thread (daemon=True, nunca impede o
        processo do servidor de terminar) acaba por conta própria -- ou
        pelo EOFError que a entrada vazia provoca, ou pelos limites do
        próprio tracer se estiver presa por outro motivo."""
        self.entrada.fechar()
        self.terminou = True


