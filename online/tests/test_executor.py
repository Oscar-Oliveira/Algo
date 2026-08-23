# -*- coding: utf-8 -*-
import asyncio
import os

import pytest

import executor


def _correr(corrotina):
    return asyncio.run(corrotina)


def _um_ficheiro(codigo, nome="principal.algo"):
    """Atalho para os muitos testes de um só ficheiro -- devolve a
    lista de ficheiros e o nome do principal, no formato que
    executor.py agora espera em todo o lado."""
    return [{"nome": nome, "conteudo": codigo}], nome


# ---------- compilação ----------

def test_compilar_codigo_valido(tmp_path):
    ficheiros, principal = _um_ficheiro('algoritmo "T"\ninicio\n    escrever("ola")\n')
    caminho_py = executor.compilar_codigo(ficheiros, principal, str(tmp_path))
    assert caminho_py.endswith(".py")
    with open(caminho_py, encoding="utf-8") as f:
        assert "ola" in f.read()


def test_compilar_codigo_erro_de_sintaxe_nao_termina_o_processo(tmp_path):
    """O ponto central deste teste: reutilizar cli.compilar_ficheiro
    diretamente faria sys.exit(1) aqui -- confirma que isso já não
    acontece (o teste continua a correr depois desta linha)."""
    ficheiros, principal = _um_ficheiro("algoritmo sem aspas\ninicio\n    escrever(1)\n")
    with pytest.raises(executor.ErroCompilacao, match="sintaxe"):
        executor.compilar_codigo(ficheiros, principal, str(tmp_path))


def test_compilar_codigo_erro_semantico(tmp_path):
    ficheiros, principal = _um_ficheiro('algoritmo "T"\ninicio\n    escrever(x)\n')
    with pytest.raises(executor.ErroCompilacao, match="semântico"):
        executor.compilar_codigo(ficheiros, principal, str(tmp_path))


def test_ficheiro_principal_em_falta_da_erro_claro(tmp_path):
    with pytest.raises(executor.ErroCompilacao, match="principal"):
        executor.compilar_codigo(
            [{"nome": "a.algo", "conteudo": "x"}], "b.algo", str(tmp_path))


def test_compilar_codigo_recursion_error_vira_erro_compilacao_amigavel(tmp_path, monkeypatch):
    """AUDITORIA_2026-08-19 bugs #7/#10: rede de segurança adicional --
    a correção principal está no parser (algo_lang), que já impede uma
    AST demasiado profunda de sequer existir. Isto simula um
    RecursionError de qualquer OUTRA travessia recursiva (presente ou
    futura) que o escape, confirmando que vira um ErroCompilacao
    amigável em vez de propagar cru até ao handler genérico do
    FastAPI (que retornaria um 500 opaco)."""
    def _verificar_que_rebenta(programa):
        raise RecursionError("simulado")
    monkeypatch.setattr(executor, "verificar", _verificar_que_rebenta)
    ficheiros, principal = _um_ficheiro('algoritmo "T"\ninicio\n    escrever(1)\n')
    with pytest.raises(executor.ErroCompilacao, match="complexa"):
        executor.compilar_codigo(ficheiros, principal, str(tmp_path))


def test_dois_ficheiros_com_o_mesmo_nome_da_erro_claro(tmp_path):
    with pytest.raises(executor.ErroCompilacao, match="mesmo nome"):
        executor.compilar_codigo(
            [{"nome": "a.algo", "conteudo": "x"}, {"nome": "a.algo", "conteudo": "y"}],
            "a.algo", str(tmp_path))


# ---------- ON-01: nome de ficheiro não pode escrever fora da pasta ----------

def test_nome_de_ficheiro_com_travessia_de_caminho_e_rejeitado(tmp_path):
    import os
    marcador = tmp_path.parent / "pwned.txt"
    with pytest.raises(executor.ErroCompilacao, match="inválido"):
        executor.compilar_codigo(
            [{"nome": "../pwned.txt", "conteudo": "x"}], "../pwned.txt", str(tmp_path))
    assert not marcador.exists()


def test_nome_de_ficheiro_absoluto_e_rejeitado(tmp_path):
    import os
    alvo = str(tmp_path.parent / "pwned.txt")
    with pytest.raises(executor.ErroCompilacao, match="inválido"):
        executor.compilar_codigo(
            [{"nome": alvo, "conteudo": "x"}], alvo, str(tmp_path))
    assert not os.path.exists(alvo)


def test_nome_de_ficheiro_com_separador_e_rejeitado(tmp_path):
    with pytest.raises(executor.ErroCompilacao, match="inválido"):
        executor.compilar_codigo(
            [{"nome": "sub/ficheiro.algo", "conteudo": "x"}], "sub/ficheiro.algo", str(tmp_path))


# ---------- incluir (bibliotecas próprias) ----------

def test_incluir_resolve_funcao_de_outro_ficheiro(tmp_path):
    principal = 'algoritmo "T"\nincluir "biblioteca.algo"\ninicio\n    escrever(dobro(21))\n'
    biblioteca = "funcao dobro(n:inteiro):inteiro\n    retornar n * 2\n"
    caminho_py = executor.compilar_codigo(
        [{"nome": "principal.algo", "conteudo": principal},
         {"nome": "biblioteca.algo", "conteudo": biblioteca}],
        "principal.algo", str(tmp_path))
    with open(caminho_py, encoding="utf-8") as f:
        conteudo = f.read()
    assert "def dobro(n):" in conteudo


# ---------- AL-36: 'incluir' transitivo ----------

def test_incluir_transitivo_biblioteca_que_inclui_outra(tmp_path):
    principal = 'algoritmo "T"\nincluir "meio.algo"\ninicio\n    escrever(dobro(triplo(5)))\n'
    meio = 'incluir "fundo.algo"\nfuncao dobro(n:inteiro):inteiro\n    retornar n * 2\n'
    fundo = "funcao triplo(n:inteiro):inteiro\n    retornar n * 3\n"
    caminho_py = executor.compilar_codigo(
        [{"nome": "principal.algo", "conteudo": principal},
         {"nome": "meio.algo", "conteudo": meio},
         {"nome": "fundo.algo", "conteudo": fundo}],
        "principal.algo", str(tmp_path))
    with open(caminho_py, encoding="utf-8") as f:
        conteudo = f.read()
    assert "def dobro(n):" in conteudo
    assert "def triplo(n):" in conteudo


def test_incluir_transitivo_circular_nao_entra_em_ciclo_infinito(tmp_path):
    principal = 'algoritmo "T"\nincluir "a.algo"\ninicio\n    escrever(fA() + fB())\n'
    a = 'incluir "b.algo"\nfuncao fA():inteiro\n    retornar 1\n'
    b = 'incluir "a.algo"\nfuncao fB():inteiro\n    retornar 2\n'
    caminho_py = executor.compilar_codigo(
        [{"nome": "principal.algo", "conteudo": principal},
         {"nome": "a.algo", "conteudo": a},
         {"nome": "b.algo", "conteudo": b}],
        "principal.algo", str(tmp_path))
    with open(caminho_py, encoding="utf-8") as f:
        conteudo = f.read()
    assert "def fA():" in conteudo
    assert "def fB():" in conteudo


def test_incluir_ficheiro_em_falta_da_erro_claro(tmp_path):
    principal = 'algoritmo "T"\nincluir "nao_existe.algo"\ninicio\n    escrever(1)\n'
    with pytest.raises(executor.ErroCompilacao, match="não encontrado"):
        executor.compilar_codigo(
            [{"nome": "principal.algo", "conteudo": principal}], "principal.algo", str(tmp_path))


def test_incluir_caminho_absoluto_fora_da_pasta_e_rejeitado(tmp_path):
    """ON-02: um 'incluir' com caminho absoluto não pode ler ficheiros
    fora da pasta do estudante -- aqui, um ficheiro real que existe no
    sistema mas fora de tmp_path, para confirmar que não é a simples
    inexistência do ficheiro que está a ser apanhada."""
    alvo = tmp_path.parent / "segredo.algo"
    alvo.write_text("funcao f():inteiro\n    retornar 1\n", encoding="utf-8")
    principal = f'algoritmo "T"\nincluir "{alvo.as_posix()}"\ninicio\n    escrever(f())\n'
    with pytest.raises(executor.ErroCompilacao, match="não encontrado"):
        executor.compilar_codigo(
            [{"nome": "principal.algo", "conteudo": principal}], "principal.algo", str(tmp_path))


def test_incluir_travessia_de_caminho_fora_da_pasta_e_rejeitado(tmp_path):
    """ON-02: '../' não pode escapar da pasta do estudante para ler um
    ficheiro irmão de outra pasta."""
    alvo = tmp_path.parent / "outra_pasta_segredo.algo"
    alvo.write_text("funcao f():inteiro\n    retornar 1\n", encoding="utf-8")
    principal = f'algoritmo "T"\nincluir "../{alvo.name}"\ninicio\n    escrever(f())\n'
    with pytest.raises(executor.ErroCompilacao, match="não encontrado"):
        executor.compilar_codigo(
            [{"nome": "principal.algo", "conteudo": principal}], "principal.algo", str(tmp_path))


def test_incluir_colisao_de_funcao_da_erro_claro(tmp_path):
    principal = (
        'algoritmo "T"\nincluir "b.algo"\n'
        "funcao f():inteiro\n    retornar 1\n"
        "inicio\n    escrever(f())\n"
    )
    biblioteca = "funcao f():inteiro\n    retornar 2\n"
    with pytest.raises(executor.ErroCompilacao, match="colide"):
        executor.compilar_codigo(
            [{"nome": "principal.algo", "conteudo": principal},
             {"nome": "b.algo", "conteudo": biblioteca}],
            "principal.algo", str(tmp_path))


def test_incluir_colisao_de_estrutura_da_erro_claro(tmp_path):
    principal = (
        'algoritmo "T"\nincluir "b.algo"\n'
        "estrutura Ponto\n    x:inteiro\n"
        "inicio\n    escrever(1)\n"
    )
    biblioteca = "estrutura Ponto\n    y:inteiro\n"
    with pytest.raises(executor.ErroCompilacao, match="colide"):
        executor.compilar_codigo(
            [{"nome": "principal.algo", "conteudo": principal},
             {"nome": "b.algo", "conteudo": biblioteca}],
            "principal.algo", str(tmp_path))


# ---------- 'incluir ... como <alias>' -- namespace opcional ----------

def test_incluir_com_alias_gera_funcao_com_nome_mangled(tmp_path):
    principal = (
        'algoritmo "T"\nincluir "geometria.algo" como geometria\n'
        "inicio\n    escrever(geometria.dobro(21))\n"
    )
    biblioteca = "funcao dobro(n:inteiro):inteiro\n    retornar n * 2\n"
    caminho_py = executor.compilar_codigo(
        [{"nome": "principal.algo", "conteudo": principal},
         {"nome": "geometria.algo", "conteudo": biblioteca}],
        "principal.algo", str(tmp_path))
    with open(caminho_py, encoding="utf-8") as f:
        conteudo = f.read()
    assert "def geometria_dobro(n):" in conteudo


def test_incluir_alias_reutilizado_para_ficheiro_diferente_da_erro_claro(tmp_path):
    principal = (
        'algoritmo "T"\nincluir "a.algo" como m\nincluir "b.algo" como m\n'
        "inicio\n    escrever(1)\n"
    )
    a = "funcao fA():inteiro\n    retornar 1\n"
    b = "funcao fB():inteiro\n    retornar 2\n"
    with pytest.raises(executor.ErroCompilacao, match="alias"):
        executor.compilar_codigo(
            [{"nome": "principal.algo", "conteudo": principal},
             {"nome": "a.algo", "conteudo": a},
             {"nome": "b.algo", "conteudo": b}],
            "principal.algo", str(tmp_path))


def test_incluir_alias_colide_com_biblioteca_importada_da_erro_claro(tmp_path):
    principal = (
        'algoritmo "T"\nimportar Matematica\nincluir "lib.algo" como matematica\n'
        "inicio\n    escrever(1)\n"
    )
    biblioteca = "funcao f():inteiro\n    retornar 1\n"
    with pytest.raises(executor.ErroCompilacao, match="biblioteca"):
        executor.compilar_codigo(
            [{"nome": "principal.algo", "conteudo": principal},
             {"nome": "lib.algo", "conteudo": biblioteca}],
            "principal.algo", str(tmp_path))


def test_execucao_completa_com_incluir(tmp_path):
    async def cenario():
        principal = 'algoritmo "T"\nincluir "lib.algo"\ninicio\n    escrever(triplo(4))\n'
        biblioteca = "funcao triplo(n:inteiro):inteiro\n    retornar n * 3\n"
        caminho_py = executor.compilar_codigo(
            [{"nome": "principal.algo", "conteudo": principal},
             {"nome": "lib.algo", "conteudo": biblioteca}],
            "principal.algo", str(tmp_path))
        execucao = executor.ExecucaoInterativa(caminho_py, str(tmp_path))
        await execucao.iniciar()
        linha = await execucao.ler_proxima_linha()
        assert linha == "12"
        await execucao.terminar_a_forcar()
    _correr(cenario())


# ---------- pasta por execução (ON-07/ARCH-11) ----------

def test_preparar_pasta_execucao_devolve_pasta_nova_a_cada_chamada(tmp_path):
    """Ao contrário do comportamento antigo (mesma pasta por
    estudante, apagada e recriada a cada pedido), cada chamada agora
    devolve uma pasta distinta e sempre vazia -- não há "conteúdo
    anterior" a limpar porque nunca é a mesma pasta."""
    import os
    pasta1 = executor.preparar_pasta_execucao("pseudo-1", str(tmp_path))
    with open(os.path.join(pasta1, "trabalho.txt"), "w") as f:
        f.write("conteudo desta execucao")
    pasta2 = executor.preparar_pasta_execucao("pseudo-1", str(tmp_path))
    assert pasta1 != pasta2
    assert os.listdir(pasta2) == []


def test_pastas_de_estudantes_diferentes_sao_diferentes(tmp_path):
    pasta_a = executor.preparar_pasta_execucao("pseudo-a", str(tmp_path))
    pasta_b = executor.preparar_pasta_execucao("pseudo-b", str(tmp_path))
    assert pasta_a != pasta_b


def test_execucoes_concorrentes_do_mesmo_estudante_nao_se_apagam(tmp_path):
    """ON-07/ARCH-11: duas execuções concorrentes do mesmo estudante
    (ex: duas abas do browser, ou o fluxograma pedido enquanto uma
    execução ainda decorre) nunca podem apagar os ficheiros uma da
    outra -- a limpeza em segundo plano só apaga pastas antigas
    (ver test_pastas_antigas_sao_limpas...), nunca a mais recente."""
    import os
    pasta_a = executor.preparar_pasta_execucao("pseudo-concorrente", str(tmp_path))
    with open(os.path.join(pasta_a, "a.txt"), "w") as f:
        f.write("a")
    pasta_b = executor.preparar_pasta_execucao("pseudo-concorrente", str(tmp_path))
    with open(os.path.join(pasta_b, "b.txt"), "w") as f:
        f.write("b")
    assert pasta_a != pasta_b
    assert os.path.exists(os.path.join(pasta_a, "a.txt"))
    assert os.path.exists(os.path.join(pasta_b, "b.txt"))


def test_pastas_antigas_sao_limpas_pastas_recentes_sao_preservadas(tmp_path):
    import os
    import time
    pasta_pseudonimo = os.path.join(str(tmp_path), "pseudo-limpeza")
    os.makedirs(pasta_pseudonimo)
    pasta_antiga = os.path.join(pasta_pseudonimo, "antiga")
    os.makedirs(pasta_antiga)
    instante_antigo = time.time() - executor.IDADE_MINIMA_PARA_LIMPEZA_SEGUNDOS - 60
    os.utime(pasta_antiga, (instante_antigo, instante_antigo))

    pasta_nova = executor.preparar_pasta_execucao("pseudo-limpeza", str(tmp_path))

    assert not os.path.exists(pasta_antiga)
    assert os.path.isdir(pasta_nova)


# ---------- execução interativa ----------

def test_execucao_simples_sem_entrada(tmp_path):
    async def cenario():
        ficheiros, principal = _um_ficheiro('algoritmo "T"\ninicio\n    escrever("ola mundo")\n')
        caminho_py = executor.compilar_codigo(ficheiros, principal, str(tmp_path))
        execucao = executor.ExecucaoInterativa(caminho_py, str(tmp_path))
        await execucao.iniciar()
        linha = await execucao.ler_proxima_linha()
        assert linha == "ola mundo"
        fim = await execucao.ler_proxima_linha()
        assert fim is None
        assert execucao.terminou
        assert execucao.codigo_saida == 0
    _correr(cenario())


def test_subprocesso_nao_herda_variaveis_de_ambiente_do_servidor(tmp_path, monkeypatch):
    """ON-05: o subprocesso do estudante não pode ver segredos do
    servidor (ex.: ONLINE_CHAVE_CIFRAGEM/ONLINE_CHAVE_SESSAO)."""
    async def cenario():
        monkeypatch.setenv("SEGREDO_TESTE_ON05", "nao_deveria_aparecer")
        caminho_py = str(tmp_path / "prog.py")
        with open(caminho_py, "w") as f:
            f.write("import os\nprint(os.environ.get('SEGREDO_TESTE_ON05', 'AUSENTE'))\n")
        execucao = executor.ExecucaoInterativa(caminho_py, str(tmp_path))
        await execucao.iniciar()
        linha = await execucao.ler_proxima_linha()
        assert linha == "AUSENTE"
        await execucao.terminar_a_forcar()
    _correr(cenario())


def test_execucao_com_ler_interativo(tmp_path):
    async def cenario():
        codigo = (
            'algoritmo "Soma"\ninicio\n'
            '    a:inteiro\n    b:inteiro\n'
            '    ler(a)\n    ler(b)\n'
            '    escrever("Soma: ", a + b)\n'
        )
        ficheiros, principal = _um_ficheiro(codigo)
        caminho_py = executor.compilar_codigo(ficheiros, principal, str(tmp_path))
        execucao = executor.ExecucaoInterativa(caminho_py, str(tmp_path))
        await execucao.iniciar()
        await execucao.enviar_entrada("3")
        await execucao.enviar_entrada("4")
        linha = await execucao.ler_proxima_linha()
        assert linha == "Soma: 7"
        assert await execucao.ler_proxima_linha() is None
    _correr(cenario())


def test_terminar_a_forca_mata_processo_em_curso(tmp_path):
    async def cenario():
        ficheiros, principal = _um_ficheiro(
            'algoritmo "T"\ninicio\n    enquanto verdadeiro fazer\n        escrever("a")\n')
        caminho_py = executor.compilar_codigo(ficheiros, principal, str(tmp_path))
        execucao = executor.ExecucaoInterativa(caminho_py, str(tmp_path))
        await execucao.iniciar()
        await execucao.ler_proxima_linha()  # confirma que arrancou mesmo
        await execucao.terminar_a_forcar()
        assert execucao.terminou
        assert execucao.processo.returncode is not None
    _correr(cenario())


def test_limite_de_tempo_mata_ciclo_infinito(tmp_path):
    async def cenario():
        ficheiros, principal = _um_ficheiro(
            'algoritmo "T"\ninicio\n    enquanto verdadeiro fazer\n        escrever("a")\n')
        caminho_py = executor.compilar_codigo(ficheiros, principal, str(tmp_path))
        execucao = executor.ExecucaoInterativa(caminho_py, str(tmp_path))
        await execucao.iniciar()
        with pytest.raises(TimeoutError):
            async def ignorar(linha):
                pass
            await executor.correr_com_limite_de_tempo(execucao, ignorar, limite_segundos=2)
        assert execucao.processo.returncode is not None
    _correr(cenario())


def test_inatividade_reinicia_a_cada_entrada_enviada(tmp_path, monkeypatch):
    """Um programa com vários ler() não deve ficar preso a um único
    orçamento de tempo partilhado por todas as respostas -- cada
    enviar_entrada() tem de reabrir uma nova janela de inatividade."""
    monkeypatch.setattr(executor, "LIMITE_INATIVIDADE_SEGUNDOS", 1.5)

    async def cenario():
        ficheiros, principal = _um_ficheiro(
            'algoritmo "Soma"\ninicio\n'
            '    a:inteiro\n    b:inteiro\n'
            '    escrever("dá-me a")\n    ler(a)\n'
            '    escrever("dá-me b")\n    ler(b)\n'
            '    escrever("Soma: ", a + b)\n'
        )
        caminho_py = executor.compilar_codigo(ficheiros, principal, str(tmp_path))
        execucao = executor.ExecucaoInterativa(caminho_py, str(tmp_path))
        await execucao.iniciar()

        linhas = []
        respostas = iter(["3", "4"])

        async def responder(linha):
            linhas.append(linha)
            resposta = next(respostas, None)
            if resposta is not None:
                # atraso maior do que o orçamento de arranque original
                # (2s), mas dentro da janela de inatividade de cada turno
                await asyncio.sleep(1.0)
                await execucao.enviar_entrada(resposta)

        await executor.correr_com_limite_de_tempo(execucao, responder, limite_segundos=2)
        assert linhas == ["dá-me a", "dá-me b", "Soma: 7"]
    _correr(cenario())


def test_limite_de_memoria_trava_alocacao_excessiva(tmp_path):
    async def cenario():
        caminho_py = str(tmp_path / "memoria.py")
        with open(caminho_py, "w") as f:
            f.write('print("antes")\nx = [0] * (10**10)\nprint("depois")\n')
        execucao = executor.ExecucaoInterativa(caminho_py, str(tmp_path))
        await execucao.iniciar()
        linhas = []
        async def guardar(linha):
            linhas.append(linha)
        try:
            await executor.correr_com_limite_de_tempo(execucao, guardar, limite_segundos=5)
        except TimeoutError:
            pass
        assert "antes" in linhas
        assert "depois" not in linhas
    _correr(cenario())


def test_linha_de_saida_excessiva_da_erro_amigavel_em_vez_de_rebentar(tmp_path):
    """ON-09: uma única linha maior do que o buffer do StreamReader
    (64KB por omissão) fazia readline() levantar ValueError/
    LimitOverrunError não apanhado -- agora vira SaidaExcessiva, e o
    processo é terminado em vez de ficar pendurado."""
    async def cenario():
        caminho_py = str(tmp_path / "linhagigante.py")
        with open(caminho_py, "w") as f:
            f.write(
                "import sys\n"
                "sys.stdout.write('x' * (2 * 1024 * 1024))\n"
                "sys.stdout.flush()\n"
                "import time\n"
                "time.sleep(5)\n"
            )
        execucao = executor.ExecucaoInterativa(caminho_py, str(tmp_path))
        await execucao.iniciar()
        with pytest.raises(executor.SaidaExcessiva):
            await execucao.ler_proxima_linha()
        assert execucao.terminou
    _correr(cenario())


@pytest.mark.skipif(os.name != "posix", reason="RLIMIT_NOFILE só é aplicado em POSIX")
def test_limite_de_descritores_de_ficheiro_e_aplicado(tmp_path):
    """ON-04: sem RLIMIT_NOFILE, nada impedia um programa de esgotar os
    descritores de ficheiro disponíveis no servidor."""
    async def cenario():
        caminho_py = str(tmp_path / "muitosficheiros.py")
        with open(caminho_py, "w") as f:
            f.write(
                "abertos = 0\n"
                "try:\n"
                "    fds = []\n"
                "    while True:\n"
                "        fds.append(open('/dev/null'))\n"
                "        abertos += 1\n"
                "except OSError:\n"
                "    pass\n"
                "print(f'abertos={abertos}')\n"
            )
        execucao = executor.ExecucaoInterativa(caminho_py, str(tmp_path))
        await execucao.iniciar()
        linha = await execucao.ler_proxima_linha()
        await execucao.terminar_a_forcar()
        assert linha is not None
        abertos = int(linha.split("=")[1])
        assert 0 < abertos < executor.LIMITE_DESCRITORES_FICHEIRO
    _correr(cenario())


# ---------- fluxograma ----------

def test_gerar_fluxograma_svg(tmp_path):
    ficheiros, principal = _um_ficheiro('algoritmo "T"\ninicio\n    escrever("ola")\n')
    resultado = executor.gerar_fluxograma_svg(ficheiros, principal, str(tmp_path))
    assert "<svg" in resultado["svg"]
    assert resultado["rotinas"] == ["Principal"]
    assert resultado["rotina_atual"] == "Principal"


def test_fluxograma_erro_de_sintaxe(tmp_path):
    ficheiros, principal = _um_ficheiro("algoritmo sem aspas\n")
    with pytest.raises(executor.ErroCompilacao):
        executor.gerar_fluxograma_svg(ficheiros, principal, str(tmp_path))


# ---------- ON-34: sanitização do SVG antes de ser devolvido ----------

def test_sanitizar_svg_remove_elemento_script():
    svg_malicioso = (
        '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script>'
        '<circle cx="5" cy="5" r="4"/></svg>'
    )
    resultado = executor._sanitizar_svg(svg_malicioso)
    assert "<script" not in resultado
    assert "circle" in resultado


def test_sanitizar_svg_remove_atributos_de_evento():
    svg_malicioso = (
        '<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)">'
        '<rect onmouseover="alert(2)" width="1" height="1"/></svg>'
    )
    resultado = executor._sanitizar_svg(svg_malicioso)
    assert "onload" not in resultado
    assert "onmouseover" not in resultado
    assert "rect" in resultado


def test_sanitizar_svg_remove_href_javascript():
    svg_malicioso = (
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">'
        '<a xlink:href="javascript:alert(1)"><text>clica</text></a></svg>'
    )
    resultado = executor._sanitizar_svg(svg_malicioso)
    assert "javascript:" not in resultado


def test_gerar_fluxograma_svg_real_nunca_contem_script_nem_atributos_de_evento(tmp_path):
    ficheiros, principal = _um_ficheiro('algoritmo "T"\ninicio\n    escrever("ola")\n')
    resultado = executor.gerar_fluxograma_svg(ficheiros, principal, str(tmp_path))
    assert "<script" not in resultado["svg"]
    assert " onload=" not in resultado["svg"]
    assert " onerror=" not in resultado["svg"]


def test_fluxograma_com_condicoes_e_ciclos(tmp_path):
    codigo = '''algoritmo "T"
inicio
    n:inteiro
    ler(n)
    i:inteiro
    para i de 1 ate n fazer
        se i mod 2 == 0 entao
            escrever(i)
'''
    ficheiros, principal = _um_ficheiro(codigo)
    resultado = executor.gerar_fluxograma_svg(ficheiros, principal, str(tmp_path))
    assert "<svg" in resultado["svg"]


def test_fluxograma_com_incluir(tmp_path):
    principal = 'algoritmo "T"\nincluir "lib.algo"\ninicio\n    escrever(dobro(3))\n'
    biblioteca = "funcao dobro(n:inteiro):inteiro\n    retornar n * 2\n"
    resultado = executor.gerar_fluxograma_svg(
        [{"nome": "principal.algo", "conteudo": principal},
         {"nome": "lib.algo", "conteudo": biblioteca}],
        "principal.algo", str(tmp_path))
    assert "<svg" in resultado["svg"]


def test_fluxograma_lista_todas_as_rotinas_incluindo_de_bibliotecas(tmp_path):
    principal = (
        'algoritmo "T"\nincluir "lib.algo"\n'
        "funcao local():inteiro\n    retornar 1\n"
        "inicio\n    escrever(local())\n"
    )
    biblioteca = "funcao dobro(n:inteiro):inteiro\n    retornar n * 2\n"
    resultado = executor.gerar_fluxograma_svg(
        [{"nome": "principal.algo", "conteudo": principal},
         {"nome": "lib.algo", "conteudo": biblioteca}],
        "principal.algo", str(tmp_path))
    assert resultado["rotinas"] == ["Principal", "dobro", "local"]


def test_fluxograma_de_uma_rotina_especifica_de_biblioteca_incluida(tmp_path):
    principal = 'algoritmo "T"\nincluir "lib.algo"\ninicio\n    escrever(dobro(3))\n'
    biblioteca = "funcao dobro(n:inteiro):inteiro\n    retornar n * 2\n"
    resultado = executor.gerar_fluxograma_svg(
        [{"nome": "principal.algo", "conteudo": principal},
         {"nome": "lib.algo", "conteudo": biblioteca}],
        "principal.algo", str(tmp_path), nome_rotina="dobro")
    assert resultado["rotina_atual"] == "dobro"
    assert "<svg" in resultado["svg"]


def test_fluxograma_rotina_inexistente_da_erro_claro(tmp_path):
    ficheiros, principal = _um_ficheiro('algoritmo "T"\ninicio\n    escrever(1)\n')
    with pytest.raises(executor.ErroCompilacao, match="Não existe"):
        executor.gerar_fluxograma_svg(ficheiros, principal, str(tmp_path), nome_rotina="fantasma")


# ---------- rasto ----------

def test_gerar_rasto_simples(tmp_path):
    ficheiros, principal = _um_ficheiro(
        'algoritmo "T"\ninicio\n    a:inteiro\n    ler(a)\n    escrever(a*2)\n')
    rasto = executor.gerar_rasto(ficheiros, principal, ["5"], str(tmp_path))
    assert rasto["consolaFinal"] == "10\n"
    assert rasto["erro"] is None
    assert len(rasto["passos"]) > 0


def test_gerar_rasto_inclui_as_chaves_que_o_visualizador_exige(tmp_path):
    """O visualizador (visualizador/algo-trace-viewer.html) recusa
    ficheiros sem 'passos'/'codigoFonte' -- confirma que o envelope
    devolvido aqui tem exatamente as mesmas chaves que
    algo_lang.cli.cmd_executa_com_trace escreve no '..._trace.json'."""
    codigo = 'algoritmo "Dobro"\ninicio\n    a:inteiro\n    ler(a)\n    escrever(a*2)\n'
    ficheiros, principal = _um_ficheiro(codigo)
    rasto = executor.gerar_rasto(ficheiros, principal, ["5"], str(tmp_path))
    assert rasto["titulo"] == "Dobro"
    assert rasto["ficheiro"] == principal
    assert rasto["codigoFonte"] == codigo.splitlines()


def test_gerar_rasto_erro_de_compilacao(tmp_path):
    ficheiros, principal = _um_ficheiro("algoritmo sem aspas\n")
    with pytest.raises(executor.ErroCompilacao):
        executor.gerar_rasto(ficheiros, principal, [], str(tmp_path))


def test_gerar_rasto_sem_entradas_suficientes(tmp_path):
    ficheiros, principal = _um_ficheiro(
        'algoritmo "T"\ninicio\n    a:inteiro\n    ler(a)\n    escrever(a)\n')
    rasto = executor.gerar_rasto(ficheiros, principal, [], str(tmp_path))
    assert rasto["erro"] is not None


def test_gerar_rasto_variaveis_aparecem_na_pilha(tmp_path):
    ficheiros, principal = _um_ficheiro('algoritmo "T"\ninicio\n    a:inteiro = 42\n    escrever(a)\n')
    rasto = executor.gerar_rasto(ficheiros, principal, [], str(tmp_path))
    variaveis_vistas = [p["pilha"][0]["variaveis"] for p in rasto["passos"] if p["pilha"]]
    assert any(v.get("a") == 42 for v in variaveis_vistas)


def test_gerar_rasto_com_incluir(tmp_path):
    principal = 'algoritmo "T"\nincluir "lib.algo"\ninicio\n    escrever(dobro(5))\n'
    biblioteca = "funcao dobro(n:inteiro):inteiro\n    retornar n * 2\n"
    rasto = executor.gerar_rasto(
        [{"nome": "principal.algo", "conteudo": principal},
         {"nome": "lib.algo", "conteudo": biblioteca}],
        "principal.algo", [], str(tmp_path))
    assert rasto["consolaFinal"] == "10\n"


# ---------- linter ----------

def test_analisar_linter_sem_avisos(tmp_path):
    ficheiros, principal = _um_ficheiro('algoritmo "T"\ninicio\n    escrever("ola")\n')
    avisos = executor.analisar_linter(ficheiros, principal, str(tmp_path))
    assert avisos == []


def test_analisar_linter_variavel_nao_usada(tmp_path):
    ficheiros, principal = _um_ficheiro('algoritmo "T"\ninicio\n    a:inteiro = 1\n    escrever("ola")\n')
    avisos = executor.analisar_linter(ficheiros, principal, str(tmp_path))
    assert len(avisos) == 1
    assert "a" in avisos[0]["mensagem"]
    assert avisos[0]["linha"] == 3


def test_analisar_linter_erro_de_sintaxe(tmp_path):
    ficheiros, principal = _um_ficheiro("algoritmo sem aspas\n")
    with pytest.raises(executor.ErroCompilacao):
        executor.analisar_linter(ficheiros, principal, str(tmp_path))


def test_analisar_linter_corre_mesmo_com_erro_semantico(tmp_path):
    """Ao contrário de compilar_codigo, analisar_linter não chama
    verificar() -- um erro semântico (aqui, somar inteiro com texto)
    não deve impedir o linter de correr sobre a AST já obtida."""
    ficheiros, principal = _um_ficheiro(
        'algoritmo "T"\ninicio\n    a:inteiro = 1\n    escrever(a + "x")\n')
    avisos = executor.analisar_linter(ficheiros, principal, str(tmp_path))
    assert avisos == []


def test_analisar_linter_recursion_error_vira_erro_compilacao_amigavel(tmp_path, monkeypatch):
    """Mesma rede de segurança que test_compilar_codigo_recursion_error_...,
    mas para o endpoint /api/linter -- este é o caminho real do bug
    #10: analisar_linter salta verificar() de propósito, por isso é o
    único sítio do serviço web que chegava a um RecursionError cru do
    próprio linter sem passar primeiro por um limiar mais baixo em
    verificar()."""
    def _analisar_que_rebenta(programa, codigo):
        raise RecursionError("simulado")
    monkeypatch.setattr(executor.linter_modulo, "analisar", _analisar_que_rebenta)
    ficheiros, principal = _um_ficheiro('algoritmo "T"\ninicio\n    escrever(1)\n')
    with pytest.raises(executor.ErroCompilacao, match="complexa"):
        executor.analisar_linter(ficheiros, principal, str(tmp_path))


def test_analisar_linter_com_incluir(tmp_path):
    principal = 'algoritmo "T"\nincluir "lib.algo"\ninicio\n    escrever(dobro(5))\n'
    biblioteca = "funcao dobro(n:inteiro):inteiro\n    retornar n * 2\n"
    avisos = executor.analisar_linter(
        [{"nome": "principal.algo", "conteudo": principal},
         {"nome": "lib.algo", "conteudo": biblioteca}],
        "principal.algo", str(tmp_path))
    assert avisos == []


