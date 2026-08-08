# -*- coding: utf-8 -*-
import asyncio

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


def test_dois_ficheiros_com_o_mesmo_nome_da_erro_claro(tmp_path):
    with pytest.raises(executor.ErroCompilacao, match="mesmo nome"):
        executor.compilar_codigo(
            [{"nome": "a.algo", "conteudo": "x"}, {"nome": "a.algo", "conteudo": "y"}],
            "a.algo", str(tmp_path))


# ---------- incluir (bibliotecas próprias) ----------

def test_incluir_resolve_funcao_de_outro_ficheiro(tmp_path):
    principal = 'algoritmo "T"\nincluir "biblioteca.algo"\ninicio\n    escrever(dobro(21))\n'
    biblioteca = "funcao dobro(n:inteiro):inteiro\n    devolver n * 2\n"
    caminho_py = executor.compilar_codigo(
        [{"nome": "principal.algo", "conteudo": principal},
         {"nome": "biblioteca.algo", "conteudo": biblioteca}],
        "principal.algo", str(tmp_path))
    with open(caminho_py, encoding="utf-8") as f:
        conteudo = f.read()
    assert "def dobro(n):" in conteudo


def test_incluir_ficheiro_em_falta_da_erro_claro(tmp_path):
    principal = 'algoritmo "T"\nincluir "nao_existe.algo"\ninicio\n    escrever(1)\n'
    with pytest.raises(executor.ErroCompilacao, match="não encontrado"):
        executor.compilar_codigo(
            [{"nome": "principal.algo", "conteudo": principal}], "principal.algo", str(tmp_path))


def test_incluir_colisao_de_funcao_da_erro_claro(tmp_path):
    principal = (
        'algoritmo "T"\nincluir "b.algo"\n'
        "funcao f():inteiro\n    devolver 1\n"
        "inicio\n    escrever(f())\n"
    )
    biblioteca = "funcao f():inteiro\n    devolver 2\n"
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


def test_execucao_completa_com_incluir(tmp_path):
    async def cenario():
        principal = 'algoritmo "T"\nincluir "lib.algo"\ninicio\n    escrever(triplo(4))\n'
        biblioteca = "funcao triplo(n:inteiro):inteiro\n    devolver n * 3\n"
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


# ---------- pasta por estudante ----------

def test_preparar_pasta_estudante_limpa_conteudo_anterior(tmp_path):
    pasta = executor.preparar_pasta_estudante("pseudo-1", str(tmp_path))
    with open(f"{pasta}/lixo.txt", "w") as f:
        f.write("resto de uma execucao anterior")
    pasta2 = executor.preparar_pasta_estudante("pseudo-1", str(tmp_path))
    assert pasta == pasta2
    import os
    assert not os.path.exists(f"{pasta2}/lixo.txt")


def test_pastas_de_estudantes_diferentes_sao_diferentes(tmp_path):
    pasta_a = executor.preparar_pasta_estudante("pseudo-a", str(tmp_path))
    pasta_b = executor.preparar_pasta_estudante("pseudo-b", str(tmp_path))
    assert pasta_a != pasta_b


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
    biblioteca = "funcao dobro(n:inteiro):inteiro\n    devolver n * 2\n"
    resultado = executor.gerar_fluxograma_svg(
        [{"nome": "principal.algo", "conteudo": principal},
         {"nome": "lib.algo", "conteudo": biblioteca}],
        "principal.algo", str(tmp_path))
    assert "<svg" in resultado["svg"]


def test_fluxograma_lista_todas_as_rotinas_incluindo_de_bibliotecas(tmp_path):
    principal = (
        'algoritmo "T"\nincluir "lib.algo"\n'
        "funcao local():inteiro\n    devolver 1\n"
        "inicio\n    escrever(local())\n"
    )
    biblioteca = "funcao dobro(n:inteiro):inteiro\n    devolver n * 2\n"
    resultado = executor.gerar_fluxograma_svg(
        [{"nome": "principal.algo", "conteudo": principal},
         {"nome": "lib.algo", "conteudo": biblioteca}],
        "principal.algo", str(tmp_path))
    assert resultado["rotinas"] == ["Principal", "dobro", "local"]


def test_fluxograma_de_uma_rotina_especifica_de_biblioteca_incluida(tmp_path):
    principal = 'algoritmo "T"\nincluir "lib.algo"\ninicio\n    escrever(dobro(3))\n'
    biblioteca = "funcao dobro(n:inteiro):inteiro\n    devolver n * 2\n"
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
    biblioteca = "funcao dobro(n:inteiro):inteiro\n    devolver n * 2\n"
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


def test_analisar_linter_com_incluir(tmp_path):
    principal = 'algoritmo "T"\nincluir "lib.algo"\ninicio\n    escrever(dobro(5))\n'
    biblioteca = "funcao dobro(n:inteiro):inteiro\n    devolver n * 2\n"
    avisos = executor.analisar_linter(
        [{"nome": "principal.algo", "conteudo": principal},
         {"nome": "lib.algo", "conteudo": biblioteca}],
        "principal.algo", str(tmp_path))
    assert avisos == []


