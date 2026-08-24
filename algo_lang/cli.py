# -*- coding: utf-8 -*-
"""Interface de linha de comandos do compilador ALGO."""

import sys
import os
import json
import shutil
import shlex
import signal
import subprocess
import argparse

from .compilador.lexer import ErroLexico
from .compilador.parser import parse, parse_biblioteca, ErroSintatico
from .compilador.semantics import verificar, ErroSemantico
from .compilador.codegen import gerar_python, ErroInternoCompilador
from .compilador.inclusoes import mesclar_biblioteca_no_programa, ColisaoDeInclusao
from .tools.flowchart import gerar_dot
from .tools import linter as linter_modulo


def _pasta_saida(caminho_algo: str):
    """Devolve (pasta, nome_base): uma subpasta com o nome do próprio
    algoritmo, ao lado do ficheiro .algo, onde ficam todos os artefactos
    gerados (.py, .dot, imagens, ...) em vez de se misturarem com o
    código-fonte."""
    pasta_base = os.path.dirname(os.path.abspath(caminho_algo))
    nome_base = os.path.splitext(os.path.basename(caminho_algo))[0]
    pasta = os.path.join(pasta_base, nome_base)
    if os.path.isfile(pasta):
        print(
            f"❌ Erro: não é possível criar a pasta '{pasta}' -- já existe um "
            f"ficheiro com esse nome. Renomeia ou remove esse ficheiro e tenta outra vez."
        )
        sys.exit(1)
    try:
        os.makedirs(pasta, exist_ok=True)
    except OSError as e:
        print(
            f"❌ Erro: não consegui criar a pasta de saída '{pasta}' ({e}) -- "
            f"o caminho pode ser demasiado longo para o Windows; tenta mover o "
            f"ficheiro para uma pasta com um caminho mais curto."
        )
        sys.exit(1)
    return pasta, nome_base


def _ler_ficheiro_algo(caminho: str) -> str:
    """Lê um .algo como UTF-8. Usa 'utf-8-sig' (não 'utf-8') porque vários
    editores no Windows (incluindo o Bloco de Notas) escrevem um BOM no
    início do ficheiro; 'utf-8-sig' remove-o se existir e é um no-op
    seguro quando não há BOM nenhum."""
    try:
        with open(caminho, "r", encoding="utf-8-sig") as f:
            return f.read()
    except UnicodeDecodeError as e:
        print(
            f"❌ Erro: não consegui ler '{caminho}' como texto UTF-8 ({e}) -- "
            f"confirma a codificação do ficheiro (grava-o como UTF-8 no teu editor)."
        )
        sys.exit(1)


def _resolver_inclusoes(programa, pasta_base, ja_incluidos=None):
    """Lê os ficheiros de 'incluir' e junta as suas funções/declarações
    ao programa principal -- recursivamente (uma biblioteca incluída
    também pode ter 'incluir'), com deduplicação por caminho
    absoluto partilhada por toda a árvore de inclusões, para nunca
    processar o mesmo ficheiro duas vezes nem entrar em ciclo infinito
    (ex.: A inclui B, B inclui A)."""
    if ja_incluidos is None:
        ja_incluidos = {}
    _resolver_lista_de_inclusoes(programa, programa.inclusoes, pasta_base, ja_incluidos)


def _resolver_lista_de_inclusoes(programa, inclusoes, pasta_base, ja_incluidos):
    for inc in inclusoes:
        caminho = inc.caminho
        if not os.path.isabs(caminho):
            caminho = os.path.join(pasta_base, caminho)
        # os.path.normcase, não só normpath -- em sistemas de ficheiros
        # case-insensitive (Windows/macOS), "lib.algo" e "LIB.algo" são o
        # MESMO ficheiro, mas normpath sozinho não normaliza capitalização.
        caminho = os.path.normcase(os.path.normpath(caminho))
        if caminho in ja_incluidos:
            alias_anterior = ja_incluidos[caminho]
            if inc.como != alias_anterior:
                descricao_anterior = f"com o alias '{alias_anterior}'" if alias_anterior else "sem alias"
                descricao_nova = f"com o alias '{inc.como}'" if inc.como else "sem alias"
                print(
                    f"❌ Erro na linha {inc.linha}: ficheiro incluído '{inc.caminho}' já foi "
                    f"incluído antes {descricao_anterior}; não pode ser incluído outra vez "
                    f"{descricao_nova}"
                )
                sys.exit(1)
            continue
        ja_incluidos[caminho] = inc.como
        if not os.path.isfile(caminho):
            print(
                f"❌ Erro na linha {inc.linha}: ficheiro incluído '{inc.caminho}' não encontrado"
            )
            sys.exit(1)
        codigo = _ler_ficheiro_algo(caminho)
        try:
            declaracoes, funcoes, estruturas, inclusoes_aninhadas = parse_biblioteca(codigo)
        except (ErroLexico, ErroSintatico) as e:
            print(f"❌ Erro em '{inc.caminho}': {e}")
            sys.exit(1)

        try:
            mesclar_biblioteca_no_programa(
                programa, inc.caminho, declaracoes, funcoes, estruturas, alias=inc.como
            )
        except ColisaoDeInclusao as e:
            if e.tipo == "alias":
                print(
                    f"❌ Erro: o alias '{e.nome}' (usado em '{e.caminho_origem}') já está a "
                    f"ser usado por outra inclusão -- escolhe um alias diferente"
                )
                sys.exit(1)
            if e.tipo_existente == e.tipo:
                if e.tipo == "função":
                    print(
                        f"❌ Erro: '{e.nome}' (incluído de '{e.caminho_origem}') colide com uma "
                        f"função já definida"
                    )
                elif e.tipo == "variável global":
                    print(
                        f"❌ Erro: variável '{e.nome}' (incluída de '{e.caminho_origem}') colide "
                        f"com uma variável global já declarada"
                    )
                else:
                    print(
                        f"❌ Erro: estrutura '{e.nome}' (incluída de '{e.caminho_origem}') colide "
                        f"com uma estrutura já definida"
                    )
            else:
                # Colisão ENTRE categorias diferentes (ex.: uma função
                # incluída com o mesmo nome de uma estrutura já definida) --
                # mensagem dedicada que nomeia as duas categorias, em vez de
                # deixar cair no erro genérico e sem contexto de
                # semantics.py mais tarde.
                verbo = (
                    "declarada" if e.tipo_existente == "variável global" else "definida"
                )
                print(
                    f"❌ Erro: {e.tipo} '{e.nome}' (incluída de '{e.caminho_origem}') colide "
                    f"com uma {e.tipo_existente} já {verbo}"
                )
            sys.exit(1)

        # As inclusões desta biblioteca resolvem-se relativas à PRÓPRIA
        # pasta dela, não a pasta_base original -- um 'incluir "x.algo"'
        # dentro de lib/a.algo procura lib/x.algo, não a pasta do
        # ficheiro principal.
        _resolver_lista_de_inclusoes(
            programa, inclusoes_aninhadas, os.path.dirname(caminho), ja_incluidos
        )


def _carregar_e_resolver_inclusoes(caminho_algo: str):
    """Lê e faz parsing de um .algo, resolve 'incluir', devolve a AST --
    sem verificar tipos (ver _carregar_e_verificar, que chama verificar()
    a seguir)."""
    if not os.path.isfile(caminho_algo):
        print(f"❌ Erro: ficheiro '{caminho_algo}' não encontrado.")
        sys.exit(1)
    codigo = _ler_ficheiro_algo(caminho_algo)
    pasta_base = os.path.dirname(os.path.abspath(caminho_algo))
    try:
        programa = parse(codigo)
        _resolver_inclusoes(programa, pasta_base)
    except (ErroLexico, ErroSintatico) as e:
        print(f"❌ {e}")
        sys.exit(1)
    return programa


def _carregar_e_verificar(caminho_algo: str):
    """Lê, faz parsing, resolve inclusões e verifica tipos. Devolve a AST."""
    programa = _carregar_e_resolver_inclusoes(caminho_algo)
    try:
        verificar(programa)
    except ErroSemantico as e:
        print(f"❌ {e}")
        sys.exit(1)
    return programa


def compilar_ficheiro(caminho_algo: str) -> str:
    """Compila um .algo (com verificação de tipos) e devolve o caminho do
    .py gerado -- sem qualquer noção de debug/trace (ver
    cmd_executa_com_trace e algo_lang.tools.tracer para isso)."""
    programa = _carregar_e_verificar(caminho_algo)
    try:
        codigo_py = gerar_python(programa)
    except ErroInternoCompilador as e:  # pragma: no cover -- verificar() já garantiu que o programa é válido antes disto
        print(
            f"❌ {e} -- isto é um bug do próprio ALGO, não do teu programa. Por favor reporta-o."
        )
        sys.exit(1)
    pasta, nome_base = _pasta_saida(caminho_algo)
    caminho_py = os.path.join(pasta, nome_base + ".py")
    with open(caminho_py, "w", encoding="utf-8") as f:
        f.write(codigo_py)
    return caminho_py


LIMITE_CPU_SEGUNDOS = 10

# Limite de TEMPO DE CPU (não de relógio): ao contrário de um 'timeout='
# de parede, nunca interrompe um programa legitimamente bloqueado em
# ler() à espera do estudante -- E/S bloqueante não consome CPU. Mesma
# técnica que online/executor.py usa para o serviço web. 'resource' é
# só-POSIX -- no Windows (algo.bat), o programa corre sem este guarda.
def _bootstrap_limite_cpu() -> str:
    """Construído a cada chamada (não pré-calculado num literal de módulo)
    para ler sempre o valor ATUAL de LIMITE_CPU_SEGUNDOS -- permite a um
    teste baixar o limite via monkeypatch e confirmar o comportamento
    real do 'resource.setrlimit' de ponta a ponta, sem esperar os 10s do
    valor por omissão."""
    return (
        "import resource, os, sys\n"
        f"resource.setrlimit(resource.RLIMIT_CPU, ({LIMITE_CPU_SEGUNDOS}, {LIMITE_CPU_SEGUNDOS}))\n"
        "os.execv(sys.executable, [sys.executable, sys.argv[1]])\n"
    )


def _comando_com_limite_cpu(caminho_py: str) -> list:
    if os.name == "posix":
        return [sys.executable, "-c", _bootstrap_limite_cpu(), caminho_py]
    return [sys.executable, caminho_py]  # pragma: no cover -- ambiente de desenvolvimento é sempre Windows aqui, mas mantém o código correto para POSIX


def cmd_executa(args):
    if args.debug or args.json:
        cmd_executa_com_trace(args)
        return

    caminho_py = compilar_ficheiro(args.ficheiro)
    print(f"✔ Compilado para: {caminho_py}\n")
    if args.mostrar_python:
        print("----- Código Python gerado -----")
        with open(caminho_py, "r", encoding="utf-8") as f:
            print(f.read())
        print("---------------------------------\n")
    print("----- Execução -----")
    sys.stdout.flush()
    resultado = subprocess.run(_comando_com_limite_cpu(caminho_py))
    if os.name == "posix" and resultado.returncode == -signal.SIGXCPU:
        print(
            f"\n⚠ O programa foi interrompido por exceder {LIMITE_CPU_SEGUNDOS}s de "
            "tempo de CPU (possível ciclo infinito ou recursão sem fim)."
        )
    if resultado.returncode != 0:
        # Só sai com o código de erro em INSUCESSO -- cmd_consola só
        # atualiza 'ultimo_ficheiro' depois de args.func(args) terminar
        # SEM SystemExit.
        sys.exit(resultado.returncode)


def cmd_executa_com_trace(args):
    """Gera o trace completo da execução (linha a linha, pilha de
    chamadas com todas as variáveis, consola) -- via algo_lang.tools.tracer,
    que corre o Python REAL gerado pelo compilador sob sys.settrace(). O
    compilador (gerar_python_com_mapa) só devolve código puro mais um
    mapa de linhas; é este módulo que "adiciona" o debug, não o
    compilador. Usa --debug para veres o trace na consola, --json para
    gerares o ficheiro para o visualizador web (podes usar os dois)."""
    from .compilador.codegen import gerar_python_com_mapa
    from .tools.tracer import gerar_trace, formatar_consola_com_debug

    programa = _carregar_e_verificar(args.ficheiro)
    try:
        dados = gerar_python_com_mapa(programa)
    except ErroInternoCompilador as e:  # pragma: no cover -- verificar() já garantiu que o programa é válido antes disto
        print(
            f"❌ {e} -- isto é um bug do próprio ALGO, não do teu programa. Por favor reporta-o."
        )
        sys.exit(1)

    pasta, nome_base = _pasta_saida(args.ficheiro)
    caminho_py = os.path.join(pasta, nome_base + ".py")
    with open(caminho_py, "w", encoding="utf-8") as f:
        f.write(dados["codigo"])
    print(f"✔ Compilado para: {caminho_py}")
    if args.mostrar_python:
        print("----- Código Python gerado -----")
        print(dados["codigo"])
        print("---------------------------------\n")

    entradas = None
    if args.entradas:
        if not os.path.isfile(args.entradas):
            print(f"❌ Erro: ficheiro de entradas '{args.entradas}' não encontrado")
            sys.exit(1)
        # Reaproveita _ler_ficheiro_algo (mesmo tratamento de
        # UnicodeDecodeError que já existe para o .algo principal).
        entradas = _ler_ficheiro_algo(args.entradas).splitlines()
    # se não houver ficheiro de entradas, gerar_trace() usa o stdin real
    # do processo -- podes escrever os valores interativamente

    print("----- A gerar o trace -----")
    resultado = gerar_trace(
        dados["codigo"],
        caminho_py,
        dados["mapa_linhas"],
        dados["nomes_globais"],
        dados["nomes_funcoes"],
        entradas=entradas,
    )

    print("\n----- Execução -----")
    if args.debug:
        print(formatar_consola_com_debug(resultado), end="")
    else:
        print(resultado["consolaFinal"], end="")
    if resultado["erro"]:
        print(f"❌ {resultado['erro']['mensagem']}")
    if resultado["limiteExcedido"]:
        if resultado.get("limiteTipo") == "tempo":
            print(
                "⚠ Limite de tempo do trace atingido (execução demasiado longa) — "
                "o programa foi interrompido só para efeitos do trace."
            )
        else:
            print(
                "⚠ Limite de passos do trace atingido (possível ciclo infinito) — "
                "o programa foi interrompido só para efeitos do trace."
            )

    if args.json:
        # Reaproveita _ler_ficheiro_algo em vez de reabrir o ficheiro à
        # mão, para ter o mesmo tratamento de UnicodeDecodeError.
        codigo_fonte = _ler_ficheiro_algo(args.ficheiro)
        trace_final = {
            "titulo": programa.nome,
            "ficheiro": os.path.basename(args.ficheiro),
            "codigoFonte": codigo_fonte.splitlines(),
            "passos": resultado["passos"],
            "erro": resultado["erro"],
            "limiteExcedido": resultado["limiteExcedido"],
            "limiteTipo": resultado.get("limiteTipo"),
        }
        caminho_json = os.path.join(pasta, nome_base + "_trace.json")
        with open(caminho_json, "w", encoding="utf-8") as f:
            json.dump(trace_final, f, ensure_ascii=False, indent=1)
        print(f"\n✔ Trace gerado: {caminho_json} ({len(resultado['passos'])} passo(s))")
        print(
            "  Abre o visualizador web e carrega este ficheiro para navegar passo a passo."
        )

    if resultado["erro"] or resultado["limiteExcedido"]:
        # cmd_executa (sem --debug/--json) propaga o código de saída real
        # do subprocesso; este caminho precisa do mesmo comportamento para
        # um script/CI/corretor automático que confie no código de saída.
        sys.exit(1)


def cmd_fluxograma(args):
    programa = _carregar_e_verificar(args.ficheiro)
    pasta, nome_base = _pasta_saida(args.ficheiro)
    nomes_rotinas = {f.nome for f in programa.funcoes}

    if args.funcao:
        alvo = next((f for f in programa.funcoes if f.nome == args.funcao), None)
        if alvo is None:
            print(f"❌ Erro: não existe nenhuma função/procedimento '{args.funcao}'")
            sys.exit(1)
        alvos = [
            (alvo.corpo, f"{programa.nome} — {alvo.nome}", f"{nome_base}_{alvo.nome}")
        ]
    else:
        # por omissão: o fluxograma principal MAIS um fluxograma para cada
        # função/procedimento -- as chamadas a rotinas no principal (e nas
        # próprias rotinas) ficam com contorno duplo e remetem para o
        # ficheiro correspondente, em vez de tentar meter tudo num só
        # diagrama (o que ficaria ilegível, sobretudo com recursividade)
        alvos = [(programa.corpo, programa.nome, nome_base)]
        for f in programa.funcoes:
            alvos.append(
                (f.corpo, f"{programa.nome} — {f.nome}", f"{nome_base}_{f.nome}")
            )

    graphviz_disponivel = shutil.which("dot") is not None
    for corpo, titulo, nome_ficheiro in alvos:
        dot = gerar_dot(corpo, titulo, nomes_rotinas)
        caminho_dot = os.path.join(pasta, nome_ficheiro + ".dot")
        with open(caminho_dot, "w", encoding="utf-8") as f:
            f.write(dot)
        print(f"✔ Fluxograma gerado: {caminho_dot}")

        if graphviz_disponivel:
            caminho_img = os.path.join(pasta, nome_ficheiro + "." + args.formato)
            sys.stdout.flush()
            resultado = subprocess.run(
                ["dot", f"-T{args.formato}", caminho_dot, "-o", caminho_img]
            )
            if resultado.returncode == 0:
                print(f"✔ Imagem gerada: {caminho_img}")

    if not graphviz_disponivel:
        print(
            "  (Graphviz 'dot' não encontrado no sistema — instala-o para gerar "
            "automaticamente as imagens, ou abre os .dot num visualizador online)"
        )


def cmd_verifica(args):
    programa = _carregar_e_verificar(args.ficheiro)
    codigo_fonte = _ler_ficheiro_algo(args.ficheiro)
    avisos = linter_modulo.analisar(programa, codigo_fonte)
    if not avisos:
        print("✔ Nenhum aviso — o linter não encontrou nada a assinalar.")
        return
    print(f"{len(avisos)} aviso(s):\n")
    for aviso in avisos:
        print(f"  ⚠ {aviso}")


# Para cada comando que tem um 'ficheiro' posicional, as flags que consomem
# um valor a seguir (para a consola saber distinguir "--formato png" de um
# nome de ficheiro solto, ao decidir se falta um ficheiro na linha).
COMANDOS_COM_FICHEIRO = {
    "executa": {"--entradas"},
    "fluxograma": {"--funcao", "--formato"},
    "verifica": set(),
}

# Atalhos de uma letra para os comandos mais usados na consola.
ATALHOS_CONSOLA = {
    "e": "executa",
    "v": "verifica",
    "f": "fluxograma",
}


def _linha_com_ficheiro_por_omissao(comando, resto, ultimo_ficheiro):
    """Se a linha não tiver um nome de ficheiro solto (só flags), usa o
    último ficheiro da sessão. Devolve o 'resto' já completo, ou levanta
    ValueError com uma mensagem amigável se não houver ficheiro nenhum
    para usar por omissão."""
    flags_com_valor = COMANDOS_COM_FICHEIRO[comando]
    i = 0
    tem_ficheiro = False
    while i < len(resto):
        tok = resto[i]
        if tok.startswith("--"):
            if tok in flags_com_valor:
                if i + 1 >= len(resto):
                    raise ValueError(
                        f"a opção '{tok}' precisa de um valor a seguir "
                        f"(ex.: '{tok} nome_do_ficheiro')"
                    )
                i += 2
            else:
                i += 1
            continue
        tem_ficheiro = True
        break
    if tem_ficheiro:
        return resto
    if ultimo_ficheiro is None:
        raise ValueError(
            "ainda não usaste nenhum ficheiro nesta sessão -- indica um "
            f"nome, ex: '{comando} programa.algo'"
        )
    return resto + [ultimo_ficheiro]


LINHA = "-" * 62


_LOGO_ASCII = r"""
                        _    _     ____   ___
       ####            / \  | |   / ___| / _ \
     ########         / _ \ | |  | |  _ | | | |
   ############      / ___ \| |__| |_| || |_| |
 ################   /_/   \_\_____\____| \___/
"""


def _mostrar_banner():
    print(_LOGO_ASCII)
    print(LINHA)
    print()
    print('  Escreve um comando e prime Enter -- sem escrever "algo" à frente.')
    print("  Cada um tem também um atalho de uma letra (entre parêntesis).")
    print()
    print("    executa <ficheiro.algo>  (e)   compila e corre o programa")
    print("    verifica <ficheiro.algo> (v)   avisos de possíveis enganos")
    print("    fluxograma <ficheiro.algo> (f) gera um diagrama do programa")
    print()
    print("    ajuda  (a)                     esta lista, com mais detalhe e exemplos")
    print("    sair   (s)                     termina a consola")
    print()
    print("  Depois de usares um ficheiro uma vez, os comandos seguintes")
    print("  reutilizam-no -- não precisas de repetir o nome.")
    print(LINHA)


def _mostrar_ajuda(ultimo_ficheiro):
    print(LINHA)
    print("  executa <ficheiro.algo> [opções]   (atalho: e)")
    print(LINHA)
    print("  Compila e corre o programa.")
    print()
    print("    --mostrar-python        mostra o código Python gerado antes de correr")
    print("    --debug                 mostra o valor das variáveis a cada passo")
    print("    --json                  gera um .json com o trace completo, para o")
    print("                            visualizador web")
    print("    --entradas <ficheiro>   lê os valores de ler() de um ficheiro de")
    print("                            texto, em vez de perguntares um a um")
    print()
    print("  Exemplos:")
    print("    executa soma.algo")
    print("    e soma.algo --debug")
    print("    e soma.algo --json --entradas valores.txt")
    print()

    print(LINHA)
    print("  fluxograma <ficheiro.algo> [opções]   (atalho: f)")
    print(LINHA)
    print("  Gera um diagrama (.dot + imagem) do programa.")
    print()
    print("    --funcao <nome>    só gera o fluxograma dessa função/procedimento")
    print("                       (por omissão: o principal + um por cada função)")
    print("    --formato <tipo>   png (por omissão), svg ou pdf")
    print()
    print("  Exemplos:")
    print("    fluxograma soma.algo")
    print("    f soma.algo --formato svg")
    print("    f soma.algo --funcao calcularMedia")
    print()

    print(LINHA)
    print("  verifica <ficheiro.algo>   (atalho: v)")
    print(LINHA)
    print("  Avisa sobre enganos comuns (variáveis nunca usadas, comparações")
    print("  sempre verdadeiras, etc.) sem impedir a compilação.")
    print()
    print("  Exemplo:")
    print("    v soma.algo")
    print()

    print(LINHA)
    print("  outros comandos")
    print(LINHA)
    print("    ajuda    (atalho: a)   mostra esta mensagem")
    print(
        "    sair     (atalho: s)   termina a consola (também funcionam: exit, quit, Ctrl+D)"
    )
    print()
    if ultimo_ficheiro:
        print(f"  Ficheiro atual desta sessão: {ultimo_ficheiro}")
    else:
        print("  Ainda não usaste nenhum ficheiro nesta sessão.")
    print(LINHA)


def _ler_linha_prompt(prompt):
    """Como input(prompt), mas sem qualquer leitura antecipada do stdin.

    input() (e sys.stdin normal) lê por blocos: quando o stdin não é um
    terminal (por exemplo, com 'algo' a ser testado ou usado dentro de um
    pipe), um único input() pode consumir do sistema operativo bytes que
    já pertencem às linhas seguintes -- incluindo as que um 'executa'
    devia poder passar ao ler() do PRÓPRIO PROGRAMA que vai correr a
    seguir, num subprocesso que herda este stdin. Lendo um byte de cada
    vez, a posição do stdin fica sempre exatamente a seguir ao NEWLINE
    desta linha, e o subprocesso recebe o resto tal e qual."""
    sys.stdout.write(prompt)
    sys.stdout.flush()
    bytes_linha = bytearray()
    fd = sys.stdin.fileno()
    while True:
        b = os.read(fd, 1)
        if not b:
            if not bytes_linha:
                raise EOFError
            break
        if b == b"\n":
            break
        bytes_linha.extend(b)
    return bytes_linha.decode("utf-8", errors="replace")


def _shlex_split_sem_escape(linha):
    """Como shlex.split(linha), mas sem tratar '\\' como caráter de escape
    nem '#' como início de comentário -- um caminho Windows colado sem
    aspas (ex.: 'C:\\Users\\aluno\\prog.algo') ou um nome de ficheiro com
    '#' devem chegar intactos. Aspas simples/duplas continuam a funcionar
    normalmente, para nomes de ficheiro com espaços."""
    lexer = shlex.shlex(linha, posix=True)
    lexer.whitespace_split = True
    lexer.escape = ""
    lexer.commenters = ""
    return list(lexer)


def cmd_consola(parser):
    """Consola interativa: cada linha é um dos comandos normais
    (executa/fluxograma/verifica) sem o 'algo' à frente, sem teres de
    reabrir o programa a cada vez. Um comando com erro só mostra o erro e
    volta ao prompt -- não fecha a consola."""
    _mostrar_banner()
    ultimo_ficheiro = None

    while True:
        try:
            linha = _ler_linha_prompt("\nalgo> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        linha = linha.strip()
        if not linha:
            continue
        if linha in ("sair", "exit", "quit", "s"):
            print("Até à próxima!")
            break
        if linha in ("ajuda", "help", "a"):
            _mostrar_ajuda(ultimo_ficheiro)
            continue

        try:
            partes = _shlex_split_sem_escape(linha)
        except ValueError as e:
            print(f"❌ {e}")
            continue

        comando, resto = partes[0], partes[1:]
        comando = ATALHOS_CONSOLA.get(comando, comando)
        if comando in COMANDOS_COM_FICHEIRO:
            try:
                resto = _linha_com_ficheiro_por_omissao(comando, resto, ultimo_ficheiro)
            except ValueError as e:
                print(f"❌ {e}")
                continue

        try:
            args = parser.parse_args([comando] + resto)
        except SystemExit:
            # o argparse já escreveu a mensagem de erro/ajuda -- só não
            # deixamos que feche a consola
            if comando not in ("-h", "--help"):
                print(
                    "(escreve 'ajuda' para veres os comandos disponíveis e as suas opções)"
                )
            continue

        try:
            args.func(args)
        except SystemExit:
            # os comandos usam sys.exit(1) para reportar erro numa
            # invocação única -- aqui isso só deve voltar ao prompt.
            # Um ficheiro que NÃO existe não deve substituir
            # 'ultimo_ficheiro'; um ficheiro que EXISTE mas falhou por
            # outra razão (erro léxico/sintático/semântico) fica na mesma
            # como 'ultimo_ficheiro', para o fluxo normal ser corrigir e
            # voltar a correr só com 'e'.
            ficheiro = getattr(args, "ficheiro", None)
            if ficheiro and os.path.isfile(ficheiro):
                ultimo_ficheiro = ficheiro
            continue
        except KeyboardInterrupt:
            print("\n(interrompido)")
            continue
        except Exception as e:
            # Rede de segurança: o contrato desta consola (docstring
            # acima) é que um comando com erro só mostra o erro e volta ao
            # prompt, nunca fecha a consola.
            print(f"❌ erro interno do compilador: {e}")
            continue

        if getattr(args, "ficheiro", None):
            ultimo_ficheiro = args.ficheiro


def main():
    # algo.bat/algo.sh mitigam isto só para quem invoca sempre através do
    # script de arranque -- mas 'python -m algo_lang.cli' e o comando
    # 'algo' instalado por pip (venv ativado manualmente) não passam por
    # eles. Sem isto, a consola do Windows (code page 1252/850 por
    # omissão, não UTF-8) crasha com UnicodeEncodeError ao imprimir
    # '✔'/'❌'.
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        prog="algo",
        description="Compilador da linguagem algorítmica ALGO -> Python",
    )
    subparsers = parser.add_subparsers(dest="comando", required=True)

    p_executa = subparsers.add_parser(
        "executa", help="compila e executa um ficheiro .algo"
    )
    p_executa.add_argument("ficheiro", help="caminho para o ficheiro .algo")
    p_executa.add_argument(
        "--mostrar-python",
        action="store_true",
        help="mostra o código Python gerado antes de o executar",
    )
    p_executa.add_argument(
        "--debug",
        action="store_true",
        help="mostra na consola o valor das variáveis a cada passo da execução",
    )
    p_executa.add_argument(
        "--json",
        action="store_true",
        help="gera um ficheiro .json com o trace completo (linha a linha, pilha de "
        "chamadas, consola), para abrir no visualizador web",
    )
    p_executa.add_argument(
        "--entradas",
        default=None,
        metavar="FICHEIRO",
        help="ficheiro de texto com os valores para ler() (um por linha), usado com "
        "--debug/--json; sem isto, usa o stdin normal (podes escrever à mão)",
    )
    p_executa.set_defaults(func=cmd_executa)

    p_fluxo = subparsers.add_parser(
        "fluxograma", help="gera um fluxograma (.dot) do programa"
    )
    p_fluxo.add_argument("ficheiro", help="caminho para o ficheiro .algo")
    p_fluxo.add_argument(
        "--funcao",
        default=None,
        help="gera só o fluxograma desta função/procedimento (por omissão, gera o "
        "principal MAIS um para cada função/procedimento do programa)",
    )
    p_fluxo.add_argument(
        "--formato",
        default="png",
        choices=["png", "svg", "pdf"],
        help="formato da imagem gerada, se o Graphviz estiver instalado (por omissão: png)",
    )
    p_fluxo.set_defaults(func=cmd_fluxograma)

    p_verifica = subparsers.add_parser(
        "verifica",
        help="analisa o programa em busca de possíveis enganos (avisos de estilo)",
    )
    p_verifica.add_argument("ficheiro", help="caminho para o ficheiro .algo")
    p_verifica.set_defaults(func=cmd_verifica)

    if len(sys.argv) == 1:
        cmd_consola(parser)
        return

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
