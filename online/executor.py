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
import resource
import shutil
import sys
import tempfile
import uuid

_RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ_PROJETO not in sys.path:
    sys.path.insert(0, _RAIZ_PROJETO)

from algo_lang.compilador.parser import parse, parse_biblioteca
from algo_lang.compilador.semantics import verificar, ErroSemantico
from algo_lang.compilador.lexer import ErroLexico
from algo_lang.compilador.parser import ErroSintatico
from algo_lang.compilador.codegen import gerar_python, gerar_python_com_mapa
from algo_lang.tools.flowchart import gerar_dot
from algo_lang.tools.tracer import gerar_trace

PASTA_EXECUCOES_POR_OMISSAO = os.path.join(tempfile.gettempdir(), "algo_online_execucoes")

LIMITE_TEMPO_SEGUNDOS = 10
LIMITE_MEMORIA_BYTES = 256 * 1024 * 1024  # 256 MB


class ErroCompilacao(Exception):
    """Erro de sintaxe/semântica -- não chega a executar nada."""
    pass


def _limitar_recursos():  # pragma: no cover -- só corre DENTRO do processo filho, após o fork
    """Chamada via preexec_fn, já dentro do processo filho, antes de
    executar o Python do programa do estudante -- limita CPU e memória
    ao nível do sistema operativo (Linux). Um programa preso num ciclo
    infinito ou a alocar memória sem controlo é travado pelo próprio
    SO, não por um temporizador do lado do servidor sozinho."""
    resource.setrlimit(resource.RLIMIT_CPU, (LIMITE_TEMPO_SEGUNDOS, LIMITE_TEMPO_SEGUNDOS))
    resource.setrlimit(resource.RLIMIT_AS, (LIMITE_MEMORIA_BYTES, LIMITE_MEMORIA_BYTES))


def preparar_pasta_estudante(id_pseudonimo: str,
                              pasta_base: str = PASTA_EXECUCOES_POR_OMISSAO) -> str:
    """Uma pasta própria por estudante (pelo pseudónimo, nunca pelo
    email), limpa a cada nova execução -- nunca guarda código entre
    visitas, por decisão explícita (sem persistência de programas)."""
    pasta = os.path.join(pasta_base, id_pseudonimo)
    if os.path.isdir(pasta):
        shutil.rmtree(pasta)
    os.makedirs(pasta)
    return pasta


def _resolver_inclusoes(programa, pasta_base) -> None:
    """Reimplementação de algo_lang.cli._resolver_inclusoes, sem os
    sys.exit(1) -- levanta ErroCompilacao em vez disso. A lógica em si
    (ler cada ficheiro incluído, juntar as suas funções/estruturas/
    declarações ao programa principal) é a mesma; só a forma de
    reportar erro muda. Não suporta inclusões aninhadas (uma
    biblioteca incluir outra) -- o próprio compilador também não: 
    parse_biblioteca() não trata 'incluir', é uma limitação da
    linguagem em si, não desta reimplementação."""
    ja_incluidos = set()
    for inc in programa.inclusoes:
        caminho = inc.caminho
        if not os.path.isabs(caminho):
            caminho = os.path.join(pasta_base, caminho)
        caminho = os.path.normpath(caminho)
        if caminho in ja_incluidos:
            continue
        ja_incluidos.add(caminho)
        if not os.path.isfile(caminho):
            raise ErroCompilacao(
                f"Erro na linha {inc.linha}: ficheiro incluído '{inc.caminho}' não encontrado "
                f"-- confirma que criaste esse ficheiro antes de o executares."
            )
        with open(caminho, "r", encoding="utf-8") as f:
            codigo = f.read()
        try:
            declaracoes, funcoes, estruturas = parse_biblioteca(codigo)
        except (ErroLexico, ErroSintatico) as e:
            raise ErroCompilacao(f"Erro em '{inc.caminho}': {e}") from e

        nomes_estruturas_existentes = {e.nome for e in programa.estruturas}
        for e in estruturas:
            if e.nome in nomes_estruturas_existentes:
                raise ErroCompilacao(
                    f"A estrutura '{e.nome}' (incluída de '{inc.caminho}') colide "
                    f"com uma estrutura já definida.")
            programa.estruturas.append(e)
            nomes_estruturas_existentes.add(e.nome)

        nomes_existentes = {f.nome for f in programa.funcoes}
        for f in funcoes:
            if f.nome in nomes_existentes:
                raise ErroCompilacao(
                    f"'{f.nome}' (incluído de '{inc.caminho}') colide com uma "
                    f"função já definida.")
            programa.funcoes.append(f)
            nomes_existentes.add(f.nome)

        nomes_decl_existentes = {d.nome for d in programa.declaracoes}
        for d in declaracoes:
            if d.nome in nomes_decl_existentes:
                raise ErroCompilacao(
                    f"A variável '{d.nome}' (incluída de '{inc.caminho}') colide "
                    f"com uma variável global já declarada.")
            programa.declaracoes.append(d)
            nomes_decl_existentes.add(d.nome)


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
        caminho = os.path.join(pasta_estudante, nome)
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

    caminho_py = caminho_principal.rsplit(".", 1)[0] + ".py"
    with open(caminho_py, "w", encoding="utf-8") as f:
        f.write(codigo_py)
    return caminho_py


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

    async def iniciar(self) -> None:
        kwargs = {}
        if os.name == "posix":  # pragma: no cover -- ambiente de desenvolvimento é sempre POSIX aqui, mas mantém o código correto para Windows
            kwargs["preexec_fn"] = _limitar_recursos
        self.processo = await asyncio.create_subprocess_exec(
            sys.executable, self.caminho_py,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=self.pasta_estudante,
            **kwargs,
        )

    async def ler_proxima_linha(self) -> str | None:
        """Devolve a próxima linha de saída do programa, ou None
        quando o programa termina. 'escrever()' termina sempre em
        newline (confirmado no codegen), por isso ler linha a linha
        não perde nenhum aviso/pedido de entrada."""
        assert self.processo is not None and self.processo.stdout is not None
        linha = await self.processo.stdout.readline()
        if not linha:
            self.codigo_saida = await self.processo.wait()
            self.terminou = True
            return None
        return linha.decode("utf-8", errors="replace").rstrip("\n")

    async def enviar_entrada(self, texto: str) -> None:
        assert self.processo is not None and self.processo.stdin is not None
        self.processo.stdin.write((texto + "\n").encode("utf-8"))
        await self.processo.stdin.drain()

    async def terminar_a_forcar(self) -> None:
        if self.processo is not None and self.processo.returncode is None:
            self.processo.kill()
            await self.processo.wait()
        self.terminou = True


async def correr_com_limite_de_tempo(execucao: ExecucaoInterativa, callback_linha,
                                      limite_segundos: float = LIMITE_TEMPO_SEGUNDOS + 2) -> None:
    """Lê linhas da execução e chama callback_linha(linha) para cada
    uma, até o programa terminar -- com um limite de tempo total de
    parede (um pouco acima do limite de CPU do próprio processo, para
    dar folga a E/S bloqueante que não conta como tempo de CPU)."""
    try:
        async with asyncio.timeout(limite_segundos):
            while True:
                linha = await execucao.ler_proxima_linha()
                if linha is None:
                    break
                await callback_linha(linha)
    except TimeoutError:
        await execucao.terminar_a_forcar()
        raise


# ---------- fluxograma ----------

class ErroFluxograma(Exception):
    pass


NOME_PRINCIPAL_PARA_FLUXOGRAMA = "Principal"


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

    return {"svg": svg, "rotinas": rotinas_disponiveis, "rotina_atual": rotina_atual}


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
            dados["nomes_globais"], dados["nomes_funcoes"], entradas=entradas)
    except Exception as e:
        raise ErroRasto(f"Não foi possível gerar o rasto: {e}") from e

    codigo_principal = next(f["conteudo"] for f in ficheiros if f["nome"] == nome_principal)
    return {
        **resultado,
        "titulo": programa.nome,
        "ficheiro": nome_principal,
        "codigoFonte": codigo_principal.splitlines(),
    }


