# -*- coding: utf-8 -*-
"""Interface de linha de comandos do compilador ALGO."""

import sys
import os
import json
import shutil
import subprocess
import argparse

from .compilador.lexer import ErroLexico
from .compilador.parser import parse, parse_biblioteca, ErroSintatico
from .compilador.semantics import verificar, verificar_nomes_python, ErroSemantico
from .compilador.codegen import gerar_python
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
        # AL-33: os.makedirs(..., exist_ok=True) só tolera a pasta já
        # existir -- se já houver um FICHEIRO com este nome, levanta
        # FileExistsError/NotADirectoryError não tratado.
        print(f"❌ Erro: não é possível criar a pasta '{pasta}' -- já existe um "
              f"ficheiro com esse nome. Renomeia ou remove esse ficheiro e tenta outra vez.")
        sys.exit(1)
    os.makedirs(pasta, exist_ok=True)
    return pasta, nome_base


def _resolver_inclusoes(programa, pasta_base, ja_incluidos=None):
    """Lê os ficheiros de 'incluir' e junta as suas funções/declarações
    ao programa principal."""
    if ja_incluidos is None:
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
            print(f"❌ Erro na linha {inc.linha}: ficheiro incluído '{inc.caminho}' não encontrado")
            sys.exit(1)
        with open(caminho, "r", encoding="utf-8") as f:
            codigo = f.read()
        declaracoes, funcoes, estruturas = parse_biblioteca(codigo)

        nomes_estruturas_existentes = {e.nome for e in programa.estruturas}
        for e in estruturas:
            if e.nome in nomes_estruturas_existentes:
                print(f"❌ Erro: estrutura '{e.nome}' (incluída de '{inc.caminho}') colide "
                      f"com uma estrutura já definida")
                sys.exit(1)
            programa.estruturas.append(e)
            nomes_estruturas_existentes.add(e.nome)

        nomes_existentes = {f.nome for f in programa.funcoes}
        for f in funcoes:
            if f.nome in nomes_existentes:
                print(f"❌ Erro: '{f.nome}' (incluído de '{inc.caminho}') colide com uma "
                      f"função já definida")
                sys.exit(1)
            programa.funcoes.append(f)
            nomes_existentes.add(f.nome)

        nomes_decl_existentes = {d.nome for d in programa.declaracoes}
        for d in declaracoes:
            if d.nome in nomes_decl_existentes:
                print(f"❌ Erro: variável '{d.nome}' (incluída de '{inc.caminho}') colide "
                      f"com uma variável global já declarada")
                sys.exit(1)
            programa.declaracoes.append(d)
            nomes_decl_existentes.add(d.nome)


def _carregar_e_resolver_inclusoes(caminho_algo: str):
    """Lê e faz parsing de um .algo, resolve 'incluir', devolve a AST --
    sem verificar tipos. Usado por ambos os modos de compilação; o modo
    normal chama verificar() a seguir, o modo --minimo propositadamente
    não chama."""
    if not os.path.isfile(caminho_algo):
        print(f"Erro: ficheiro '{caminho_algo}' não encontrado.")
        sys.exit(1)
    with open(caminho_algo, "r", encoding="utf-8") as f:
        codigo = f.read()
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


def compilar_ficheiro(caminho_algo: str, minimo: bool = False) -> str:
    """Compila um .algo e devolve o caminho do .py gerado.

    Modo normal (minimo=False): compilação pura, com verificação de
    tipos -- sem qualquer noção de debug/trace (ver cmd_executa_com_trace
    e algo_lang.tools.tracer para isso).

    Modo --minimo: SALTA a verificação de tipos e gera o Python mais
    direto possível (ver compilador/codegen_minimo.py). Um programa com
    um erro de tipos ainda compila neste modo -- só falha ao correr, com
    o erro nativo do Python."""
    if minimo:
        programa = _carregar_e_resolver_inclusoes(caminho_algo)
        from .compilador.codegen_minimo import gerar_python_minimo
        try:
            verificar_nomes_python(programa)
            codigo_py = gerar_python_minimo(programa)
        except (ErroLexico, ErroSintatico, ErroSemantico) as e:
            print(f"❌ {e}")
            sys.exit(1)
    else:
        programa = _carregar_e_verificar(caminho_algo)
        try:
            codigo_py = gerar_python(programa)
        except ErroSemantico as e:  # pragma: no cover -- verificar() já garantiu que o programa é válido antes disto
            print(f"❌ {e}")
            sys.exit(1)
    pasta, nome_base = _pasta_saida(caminho_algo)
    sufixo = "_min" if minimo else ""
    caminho_py = os.path.join(pasta, nome_base + sufixo + ".py")
    with open(caminho_py, "w", encoding="utf-8") as f:
        f.write(codigo_py)
    return caminho_py


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
    resultado = subprocess.run([sys.executable, caminho_py])
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
    except ErroSemantico as e:  # pragma: no cover -- verificar() já garantiu que o programa é válido antes disto
        print(f"❌ {e}")
        sys.exit(1)

    pasta, nome_base = _pasta_saida(args.ficheiro)
    caminho_py = os.path.join(pasta, nome_base + ".py")
    with open(caminho_py, "w", encoding="utf-8") as f:
        f.write(dados["codigo"])
    print(f"✔ Compilado para: {caminho_py}")

    entradas = None
    if args.entradas:
        if not os.path.isfile(args.entradas):
            print(f"❌ Erro: ficheiro de entradas '{args.entradas}' não encontrado")
            sys.exit(1)
        with open(args.entradas, "r", encoding="utf-8") as f:
            entradas = [linha.rstrip("\n") for linha in f]
    # se não houver ficheiro de entradas, gerar_trace() usa o stdin real
    # do processo -- podes escrever os valores interativamente

    print("----- A gerar o trace -----")
    resultado = gerar_trace(
        dados["codigo"], caminho_py, dados["mapa_linhas"],
        dados["nomes_globais"], dados["nomes_funcoes"], entradas=entradas,
    )

    print("\n----- Execução -----")
    if args.debug:
        print(formatar_consola_com_debug(resultado), end="")
    else:
        print(resultado["consolaFinal"], end="")
    if resultado["erro"]:
        print(f"❌ {resultado['erro']['mensagem']}")
    if resultado["limiteExcedido"]:
        print("⚠ Limite de passos do trace atingido (possível ciclo infinito) — "
              "o programa foi interrompido só para efeitos do trace.")

    if args.json:
        with open(args.ficheiro, "r", encoding="utf-8") as f:
            codigo_fonte = f.read()
        trace_final = {
            "titulo": programa.nome,
            "ficheiro": os.path.basename(args.ficheiro),
            "codigoFonte": codigo_fonte.splitlines(),
            "passos": resultado["passos"],
            "erro": resultado["erro"],
            "limiteExcedido": resultado["limiteExcedido"],
        }
        caminho_json = os.path.join(pasta, nome_base + "_trace.json")
        with open(caminho_json, "w", encoding="utf-8") as f:
            json.dump(trace_final, f, ensure_ascii=False, indent=1)
        print(f"\n✔ Trace gerado: {caminho_json} ({len(resultado['passos'])} passo(s))")
        print("  Abre o visualizador web e carrega este ficheiro para navegar passo a passo.")


def cmd_compila(args):
    caminho_py = compilar_ficheiro(args.ficheiro, minimo=args.minimo)
    print(f"✔ Compilado para: {caminho_py}")
    if args.minimo:
        print("  (modo --minimo: sem verificação de tipos prévia -- um erro de "
              "tipos só aparece ao correr o .py, como erro nativo do Python)")


def cmd_fluxograma(args):
    programa = _carregar_e_verificar(args.ficheiro)
    pasta, nome_base = _pasta_saida(args.ficheiro)
    nomes_rotinas = {f.nome for f in programa.funcoes}

    if args.funcao:
        alvo = next((f for f in programa.funcoes if f.nome == args.funcao), None)
        if alvo is None:
            print(f"❌ Erro: não existe nenhuma função/procedimento '{args.funcao}'")
            sys.exit(1)
        alvos = [(alvo.corpo, f"{programa.nome} — {alvo.nome}", f"{nome_base}_{alvo.nome}")]
    else:
        # por omissão: o fluxograma principal MAIS um fluxograma para cada
        # função/procedimento -- as chamadas a rotinas no principal (e nas
        # próprias rotinas) ficam com contorno duplo e remetem para o
        # ficheiro correspondente, em vez de tentar meter tudo num só
        # diagrama (o que ficaria ilegível, sobretudo com recursividade)
        alvos = [(programa.corpo, programa.nome, nome_base)]
        for f in programa.funcoes:
            alvos.append((f.corpo, f"{programa.nome} — {f.nome}", f"{nome_base}_{f.nome}"))

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
                ["dot", f"-T{args.formato}", caminho_dot, "-o", caminho_img])
            if resultado.returncode == 0:
                print(f"✔ Imagem gerada: {caminho_img}")

    if not graphviz_disponivel:
        print("  (Graphviz 'dot' não encontrado no sistema — instala-o para gerar "
              "automaticamente as imagens, ou abre os .dot num visualizador online)")



def cmd_lint(args):
    programa = _carregar_e_verificar(args.ficheiro)
    with open(args.ficheiro, "r", encoding="utf-8") as f:
        codigo_fonte = f.read()
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
    "compila": set(),
    "fluxograma": {"--funcao", "--formato"},
    "lint": set(),
}

# Atalhos de uma letra para os comandos mais usados na consola -- '?' fica
# de fora de propósito, reservado para outra coisa no futuro.
ATALHOS_CONSOLA = {
    "e": "executa",
    "c": "compila",
    "l": "lint",
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
            i += 2 if tok in flags_com_valor else 1
            continue
        tem_ficheiro = True
        break
    if tem_ficheiro:
        return resto
    if ultimo_ficheiro is None:
        raise ValueError(
            "ainda não usaste nenhum ficheiro nesta sessão -- indica um "
            f"nome, ex: '{comando} programa.algo'")
    return resto + [ultimo_ficheiro]


LINHA = "-" * 62


def _mostrar_banner():
    print(LINHA)
    print("  Consola ALGO")
    print(LINHA)
    print()
    print("  Escreve um comando e prime Enter -- sem escrever \"algo\" à frente.")
    print("  Cada um tem também um atalho de uma letra (entre parêntesis).")
    print()
    print("    executa <ficheiro.algo>  (e)   compila e corre o programa")
    print("    compila <ficheiro.algo>  (c)   só compila (gera o ficheiro .py)")
    print("    lint <ficheiro.algo>     (l)   avisos de possíveis enganos")
    print("    fluxograma <ficheiro.algo> (f) gera um diagrama do programa")
    print()
    print("    ajuda  (a)                     esta lista, com mais detalhe e exemplos")
    print("    sair                           termina a consola")
    print()
    print("    ?                              chama o Alguem, o teu tutor de algoritmia")
    print("    ? <pergunta>                   chama o Alguem já com uma pergunta")
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
    print("  compila <ficheiro.algo> [opções]   (atalho: c)")
    print(LINHA)
    print("  Só compila -- gera o ficheiro .py ao lado do .algo, não o corre.")
    print()
    print("    --minimo   gera Python mínimo: sem verificação de tipos prévia e")
    print("               sem funções de apoio (afirmar vira assert, math.raiz")
    print("               vira math.sqrt, etc.) -- útil para veres o Python \"a")
    print("               seco\" por trás do ALGO. Por ser Python nativo, mostra")
    print("               'True'/'False' em vez de 'verdadeiro'/'falso' -- é")
    print("               esperado, não é um bug")
    print()
    print("  Exemplos:")
    print("    compila soma.algo")
    print("    c soma.algo --minimo")
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
    print("  lint <ficheiro.algo>   (atalho: l)")
    print(LINHA)
    print("  Avisa sobre enganos comuns (variáveis nunca usadas, comparações")
    print("  sempre verdadeiras, etc.) sem impedir a compilação.")
    print()
    print("  Exemplo:")
    print("    l soma.algo")
    print()

    print(LINHA)
    print("  ? [pergunta]")
    print(LINHA)
    print("  Chama o Alguem, o teu tutor de algoritmia -- uma conversa, não um")
    print("  comando. Ajuda-te a pensar no problema, mas não escreve código nem")
    print("  dá a solução. Se já usaste um ficheiro nesta sessão, mostra-lho")
    print("  automaticamente ao Alguem, com o nome, e também qualquer ficheiro")
    print("  que ele inclua (via 'incluir') -- para ele poder responder a")
    print("  perguntas sobre o código específico que estás a fazer.")
    print()
    print("  Dentro da conversa:")
    print("    ficheiros             mostra que ficheiros o Alguem tem visíveis")
    print("    ficheiro nome.algo    troca o ficheiro em que o Alguem se baseia")
    print()
    print("  Exemplos:")
    print("    ?")
    print("    ? não sei como calcular a média de vários números")
    print()

    print(LINHA)
    print("  outros comandos")
    print(LINHA)
    print("    ajuda    (atalho: a)   mostra esta mensagem")
    print("    sair     termina a consola (também funcionam: exit, quit, Ctrl+D)")
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


def _resolver_caminho_por_nome(nome, ficheiro_base):
    """Encontra um ficheiro a partir de um nome que o estudante escreveu
    à mão dentro da conversa com o Alguem -- tenta o caminho tal e qual
    (relativo à pasta atual), e depois relativo à pasta do ficheiro que
    já estava ativo (para 'ficheiro outro.algo' funcionar mesmo estando
    a trabalhar dentro de uma subpasta)."""
    candidatos = [nome]
    if ficheiro_base:
        candidatos.append(os.path.join(os.path.dirname(os.path.abspath(ficheiro_base)), nome))
    for candidato in candidatos:
        if os.path.isfile(candidato):
            return candidato
    return None


def _chamar_alguem(ultimo_ficheiro, mensagem_inicial=None):
    """Chama o Alguem a partir da consola do ALGO ('?') -- é a ÚNICA
    forma de o chamar (não há script de arranque próprio). Importação
    preguiçosa de propósito -- a consola do ALGO continua a funcionar
    normalmente mesmo que a pasta alguem/ não exista, ou não esteja
    configurada (config.json em falta/incompleto): mostra-se um erro
    amigável e volta-se ao prompt do 'algo>', sem fechar nada."""
    try:
        import alguem
    except ImportError:
        # alguem/ vive ao lado de algo_lang/ (não dentro) -- em instalações
        # editáveis (o caso normal deste projeto, via algo.sh/algo.bat)
        # __file__ aponta para a árvore de código-fonte original, por isso
        # subir um nível a partir daqui chega à pasta onde ambas vivem.
        raiz_projeto = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if raiz_projeto not in sys.path:
            sys.path.insert(0, raiz_projeto)
        try:
            import alguem
        except ImportError:
            print("❌ Não encontrei a pasta 'alguem/' ao lado desta -- o Alguem "
                  "só está disponível se a tiveres também.")
            return

    ficheiro_ativo = ultimo_ficheiro
    ficheiros_visiveis = []
    if ficheiro_ativo:
        ficheiros_visiveis = alguem.resolver_ficheiros_visiveis(ficheiro_ativo)

    try:
        tutor = alguem.criar_alguem(ficheiros_visiveis=ficheiros_visiveis)
    except alguem.ErroConfiguracao as e:
        print(f"❌ {e}")
        return

    print(LINHA)
    print("A chamar o Alguem...")
    print("Olá! Sou o Alguem, o teu tutor de algoritmia.")
    if ficheiros_visiveis:
        nomes = ", ".join(nome for nome, _ in ficheiros_visiveis)
        print(f"(tenho visibilidade de: {nomes})")
    else:
        print("(ainda não tenho nenhum ficheiro visível -- escreve "
              "'ficheiro nome.algo' para me mostrares um)")
    print("(escreve 'sair' para voltares à consola do ALGO, 'ficheiros' para "
          "veres o que tenho visível, ou 'ficheiro nome.algo' para trocares)")
    print(LINHA)

    mensagem = mensagem_inicial
    try:
        while True:
            if mensagem is None:
                try:
                    mensagem = _ler_linha_prompt("\ntu> ").strip()
                except (EOFError, KeyboardInterrupt):
                    print()
                    break
            if not mensagem:
                mensagem = None
                continue
            if mensagem.lower() in ("sair", "exit", "quit"):
                print("Alguem> Até já!")
                break
            if mensagem.lower() in ("ficheiros", "ficheiro?"):
                if ficheiros_visiveis:
                    nomes = ", ".join(nome for nome, _ in ficheiros_visiveis)
                    print(f"Tenho visibilidade de: {nomes}")
                else:
                    print("Ainda não tenho nenhum ficheiro visível.")
                mensagem = None
                continue
            if mensagem.lower().startswith("ficheiro "):
                nome_pedido = mensagem[len("ficheiro "):].strip()
                caminho = _resolver_caminho_por_nome(nome_pedido, ficheiro_ativo)
                if caminho is None:
                    print(f"❌ Não encontrei '{nome_pedido}'.")
                else:
                    ficheiro_ativo = caminho
                    ficheiros_visiveis = alguem.resolver_ficheiros_visiveis(caminho)
                    tutor.considerar_ficheiros(ficheiros_visiveis)
                    nomes = ", ".join(nome for nome, _ in ficheiros_visiveis)
                    print(f"OK -- agora tenho visibilidade de: {nomes}")
                mensagem = None
                continue

            try:
                resposta = tutor.conversar(mensagem)
            except alguem.ErroFornecedorLLM as e:
                print(f"❌ {e}")
            else:
                print(f"\nAlguem> {resposta}")
            mensagem = None
    finally:
        # garante que a sessão fica sempre corretamente fechada no log,
        # seja qual for a forma como se saiu da conversa (sair/exit/
        # quit, EOF, Ctrl+C, ou um erro inesperado qualquer)
        tutor.fechar_sessao()

    print(LINHA)


def cmd_consola(parser):
    """Consola interativa: cada linha é um dos comandos normais
    (executa/compila/fluxograma/lint) sem o 'algo' à frente, sem teres de
    reabrir o programa a cada vez. Um comando com erro só mostra o erro e
    volta ao prompt -- não fecha a consola."""
    import shlex

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
        if linha in ("sair", "exit", "quit"):
            print("Até à próxima!")
            break
        if linha in ("ajuda", "help", "a"):
            _mostrar_ajuda(ultimo_ficheiro)
            continue
        if linha == "?" or linha.startswith("? "):
            _chamar_alguem(ultimo_ficheiro, mensagem_inicial=linha[2:].strip() or None)
            continue

        try:
            partes = shlex.split(linha)
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
                print("(escreve 'ajuda' para veres os comandos disponíveis e as suas opções)")
            continue

        if getattr(args, "ficheiro", None):
            ultimo_ficheiro = args.ficheiro

        try:
            args.func(args)
        except SystemExit:
            # os comandos usam sys.exit(1) para reportar erro numa
            # invocação única -- aqui isso só deve voltar ao prompt
            pass
        except KeyboardInterrupt:
            print("\n(interrompido)")


def main():
    parser = argparse.ArgumentParser(
        prog="algo",
        description="Compilador da linguagem algorítmica ALGO -> Python",
    )
    subparsers = parser.add_subparsers(dest="comando", required=True)

    p_executa = subparsers.add_parser("executa", help="compila e executa um ficheiro .algo")
    p_executa.add_argument("ficheiro", help="caminho para o ficheiro .algo")
    p_executa.add_argument(
        "--mostrar-python", action="store_true",
        help="mostra o código Python gerado antes de o executar",
    )
    p_executa.add_argument(
        "--debug", action="store_true",
        help="mostra na consola o valor das variáveis a cada passo da execução",
    )
    p_executa.add_argument(
        "--json", action="store_true",
        help="gera um ficheiro .json com o trace completo (linha a linha, pilha de "
             "chamadas, consola), para abrir no visualizador web",
    )
    p_executa.add_argument(
        "--entradas", default=None, metavar="FICHEIRO",
        help="ficheiro de texto com os valores para ler() (um por linha), usado com "
             "--debug/--json; sem isto, usa o stdin normal (podes escrever à mão)",
    )
    p_executa.set_defaults(func=cmd_executa)

    p_compila = subparsers.add_parser("compila", help="apenas compila (não executa)")
    p_compila.add_argument("ficheiro", help="caminho para o ficheiro .algo")
    p_compila.add_argument(
        "--minimo", action="store_true",
        help="gera o Python mais direto possível (sem funções de apoio, sem "
             "verificação de tipos prévia) -- math./cadeia. viram chamadas "
             "nativas do Python, afirmar vira assert",
    )
    p_compila.set_defaults(func=cmd_compila)

    p_fluxo = subparsers.add_parser("fluxograma", help="gera um fluxograma (.dot) do programa")
    p_fluxo.add_argument("ficheiro", help="caminho para o ficheiro .algo")
    p_fluxo.add_argument(
        "--funcao", default=None,
        help="gera só o fluxograma desta função/procedimento (por omissão, gera o "
             "principal MAIS um para cada função/procedimento do programa)",
    )
    p_fluxo.add_argument(
        "--formato", default="png", choices=["png", "svg", "pdf"],
        help="formato da imagem gerada, se o Graphviz estiver instalado (por omissão: png)",
    )
    p_fluxo.set_defaults(func=cmd_fluxograma)

    p_lint = subparsers.add_parser(
        "lint", help="analisa o programa em busca de possíveis enganos (avisos de estilo)")
    p_lint.add_argument("ficheiro", help="caminho para o ficheiro .algo")
    p_lint.set_defaults(func=cmd_lint)

    if len(sys.argv) == 1:
        cmd_consola(parser)
        return

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
