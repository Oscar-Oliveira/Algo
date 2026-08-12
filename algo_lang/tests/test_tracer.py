# -*- coding: utf-8 -*-
"""Testes para o gerador de trace JSON (algo_lang.tools.tracer) usado
pelo modo 'algo executa --debug --json'."""
import json
import os
import subprocess
import sys
import textwrap

import pytest

from algo_lang.compilador.parser import parse
from algo_lang.compilador.semantics import verificar
from algo_lang.compilador.codegen import gerar_python_com_mapa
from algo_lang.tools.tracer import gerar_trace


def _trace(codigo_algo, entradas=None, tmp_path=None):
    codigo_algo = textwrap.dedent(codigo_algo).lstrip("\n")
    programa = parse(codigo_algo)
    verificar(programa)
    dados = gerar_python_com_mapa(programa)
    caminho_py = os.path.join(str(tmp_path), "prog.py") if tmp_path else "/tmp/_trace_teste.py"
    with open(caminho_py, "w", encoding="utf-8") as f:
        f.write(dados["codigo"])
    return gerar_trace(dados["codigo"], caminho_py, dados["mapa_linhas"],
                        dados["nomes_globais"], dados["nomes_funcoes"], entradas=entradas)


def test_trace_basico_tem_um_passo_por_linha_executada(tmp_path):
    resultado = _trace("""
        algoritmo "T"
        inicio
            x:inteiro = 1
            y:inteiro = 2
            escrever(x + y)
    """, tmp_path=tmp_path)
    assert resultado["erro"] is None
    assert resultado["consolaFinal"].strip() == "3"
    linhas_vistas = [p["linha"] for p in resultado["passos"]]
    assert linhas_vistas == [3, 4, 5]


def test_trace_regista_variaveis_da_pilha_principal(tmp_path):
    resultado = _trace("""
        algoritmo "T"
        inicio
            x:inteiro = 42
            escrever(x)
    """, tmp_path=tmp_path)
    ultimo = resultado["passos"][-1]
    assert ultimo["pilha"][0]["nome"] == "Principal"
    assert ultimo["pilha"][0]["variaveis"]["x"] == 42


def test_trace_recursividade_mostra_pilha_a_crescer(tmp_path):
    resultado = _trace("""
        algoritmo "T"
        funcao fatorial(n:inteiro):inteiro
            se n <= 1 entao
                devolver 1
            senao
                devolver n * fatorial(n - 1)
        inicio
            escrever(fatorial(4))
    """, tmp_path=tmp_path)
    assert resultado["erro"] is None
    assert resultado["consolaFinal"].strip() == "24"
    profundidade_maxima = max(len(p["pilha"]) for p in resultado["passos"])
    assert profundidade_maxima == 5  # Principal + 4 chamadas recursivas (n=4,3,2,1)
    passo_fundo = next(p for p in resultado["passos"] if len(p["pilha"]) == 5)
    assert passo_fundo["pilha"][-1]["nome"] == "fatorial"
    assert passo_fundo["pilha"][-1]["variaveis"]["n"] == 1


def test_trace_ref_mostra_variavel_alterada_apos_chamada(tmp_path):
    resultado = _trace("""
        algoritmo "T"
        procedimento trocar(ref a:inteiro, ref b:inteiro)
            temp:inteiro = a
            a = b
            b = temp
        inicio
            p:inteiro = 3
            q:inteiro = 9
            trocar(p, q)
            escrever(p, " ", q)
    """, tmp_path=tmp_path)
    assert resultado["consolaFinal"].strip() == "9 3"
    ultimo = resultado["passos"][-1]
    variaveis = ultimo["pilha"][0]["variaveis"]
    assert variaveis["p"] == 9
    assert variaveis["q"] == 3


def test_trace_estrutura_serializa_como_objeto(tmp_path):
    resultado = _trace("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
            y:inteiro
        inicio
            p:Ponto = {x: 3, y: 4}
            escrever(p.x)
    """, tmp_path=tmp_path)
    ultimo = resultado["passos"][-1]
    assert ultimo["pilha"][0]["variaveis"]["p"] == {"x": 3, "y": 4}


def test_trace_array_serializa_como_lista(tmp_path):
    resultado = _trace("""
        algoritmo "T"
        inicio
            v:inteiro[3] = {10, 20, 30}
            escrever(v[0])
    """, tmp_path=tmp_path)
    ultimo = resultado["passos"][-1]
    assert ultimo["pilha"][0]["variaveis"]["v"] == [10, 20, 30]


def test_trace_ler_consome_entradas_fornecidas(tmp_path):
    resultado = _trace("""
        algoritmo "T"
        inicio
            nome:cadeia
            ler(nome)
            escrever("ola ", nome)
    """, entradas=["Rita"], tmp_path=tmp_path)
    assert resultado["consolaFinal"].strip() == "ola Rita"


def test_trace_deteta_indice_fora_dos_limites(tmp_path):
    resultado = _trace("""
        algoritmo "T"
        inicio
            v:inteiro[3] = {1, 2, 3}
            escrever(v[10])
    """, tmp_path=tmp_path)
    assert resultado["erro"] is not None
    assert "índice fora dos limites" in resultado["erro"]["mensagem"]
    assert resultado["erro"]["linha"] == 4


def test_trace_deteta_divisao_por_zero(tmp_path):
    resultado = _trace("""
        algoritmo "T"
        inicio
            x:inteiro = 5
            y:inteiro = 0
            escrever(x / y)
    """, tmp_path=tmp_path)
    assert resultado["erro"] is not None
    assert "divisão por zero" in resultado["erro"]["mensagem"]


def test_trace_deteta_valueerror(tmp_path):
    """AL-23: o tracer não cobria ValueError -- confirma que agora
    também fica marcado como erro, com mensagem e linha."""
    resultado = _trace("""
        algoritmo "T"
        importar Matematica
        inicio
            escrever(matematica.raiz(-4))
    """, tmp_path=tmp_path)
    assert resultado["erro"] is not None
    assert "domínio válido" in resultado["erro"]["mensagem"]
    assert resultado["erro"]["linha"] == 4


def test_trace_nao_confunde_escrever_legitimo_com_uma_frase_de_erro(tmp_path):
    """AL-24: a deteção antiga por endswith() de frases fixas dava falso
    positivo se um escrever() legítimo terminasse com uma dessas frases
    -- agora não depende de texto nenhum, só do canal _ALGO_ERRO_RUNTIME,
    que só um erro real preenche."""
    resultado = _trace("""
        algoritmo "T"
        inicio
            escrever("o resultado é: divisão por zero.")
    """, tmp_path=tmp_path)
    assert resultado["erro"] is None


def test_trace_senao_se_mapeia_para_a_sua_propria_linha(tmp_path):
    """Regressão: os ramos de 'senao se' têm de apontar para a sua
    própria linha, não para a linha do 'se' inicial."""
    resultado = _trace("""
        algoritmo "T"
        inicio
            nota:inteiro = 12
            se nota >= 18 entao
                escrever("Excelente")
            senao se nota >= 10 entao
                escrever("Aprovado")
            senao
                escrever("Reprovado")
    """, tmp_path=tmp_path)
    linhas = [p["linha"] for p in resultado["passos"]]
    assert 6 in linhas  # a linha do 'senao se nota >= 10 entao:'


def test_trace_escolha_mapeia_cada_caso_para_a_sua_linha(tmp_path):
    resultado = _trace("""
        algoritmo "T"
        inicio
            n:inteiro = 3
            escolher n
                caso 1
                    escrever("um")
                caso 2, 3
                    escrever("dois ou tres")
                contrario
                    escrever("outro")
    """, tmp_path=tmp_path)
    linhas = [p["linha"] for p in resultado["passos"]]
    assert 7 in linhas  # a linha do 'caso 2, 3:'


# ---------- integração via CLI ----------

def test_cli_json_sozinho_ja_nao_exige_debug(tmp_path):
    """--json deixou de depender de --debug: cada flag agora é independente
    (--debug mostra na consola, --json escreve o ficheiro; usam-se juntas
    ou em separado)."""
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text('algoritmo "T"\ninicio\n    escrever("ok")\n', encoding="utf-8")
    resultado = subprocess.run(
        ["algo", "executa", str(algo_path), "--json"], capture_output=True, text=True)
    assert resultado.returncode == 0, resultado.stderr
    assert (tmp_path / "prog" / "prog_trace.json").exists()


def test_cli_gera_ficheiro_trace_json(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text(textwrap.dedent("""
        algoritmo "T"
        inicio
            x:inteiro = 5
            escrever(x)
    """).lstrip("\n"), encoding="utf-8")
    resultado = subprocess.run(
        ["algo", "executa", str(algo_path), "--debug", "--json"],
        capture_output=True, text=True, timeout=15)
    assert resultado.returncode == 0, resultado.stderr
    caminho_json = tmp_path / "prog" / "prog_trace.json"
    assert caminho_json.exists()
    with open(caminho_json, encoding="utf-8") as f:
        dados = json.load(f)
    assert dados["titulo"] == "T"
    assert dados["codigoFonte"][0] == 'algoritmo "T"'
    assert len(dados["passos"]) > 0


def test_cli_entradas_por_ficheiro(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text(textwrap.dedent("""
        algoritmo "T"
        inicio
            nome:cadeia
            ler(nome)
            escrever("ola ", nome)
    """), encoding="utf-8")
    entradas_path = tmp_path / "entradas.txt"
    entradas_path.write_text("Rita\n", encoding="utf-8")
    resultado = subprocess.run(
        ["algo", "executa", str(algo_path), "--debug", "--json",
         "--entradas", str(entradas_path)],
        capture_output=True, text=True, timeout=15)
    assert resultado.returncode == 0, resultado.stderr
    assert "ola Rita" in resultado.stdout


# ---------- formatar_consola_com_debug (o --debug na consola) ----------

def test_debug_nao_mostra_variavel_antes_de_atribuida(tmp_path):
    """Regressão relatada pelo utilizador: 'media' era declarada depois do
    ciclo 'para' -- o antigo --debug (embutido no compilador) tentava
    lê-la durante o ciclo e rebentava com NameError. Com o trace, isto é
    estruturalmente impossível: cada passo só tem as variáveis que já
    foram mesmo atribuídas nesse ponto da execução real."""
    from algo_lang.tools.tracer import formatar_consola_com_debug
    resultado = _trace("""
        algoritmo "T"
        inicio
            soma:inteiro = 0
            i:inteiro = 0
            para i de 0 ate 2 fazer
                soma = soma + i
            media:decimal = soma / 3
            escrever(media)
    """, tmp_path=tmp_path)
    texto = formatar_consola_com_debug(resultado)
    linhas_com_media = [l for l in texto.split("\n") if "media" in l]
    assert linhas_com_media, "esperava-se pelo menos uma linha de debug com 'media'"
    # sempre que 'media' aparece, já tem o valor final -- nunca aparece
    # antes de ser atribuída (ao contrário do antigo bug)
    assert all("1.0" in l for l in linhas_com_media)


def test_debug_mostra_globais_e_locais_dentro_de_funcao(tmp_path):
    from algo_lang.tools.tracer import formatar_consola_com_debug
    resultado = _trace("""
        algoritmo "T"
        total:inteiro = 0
        funcao soma(a:inteiro, b:inteiro):inteiro
            resultado:inteiro = 0
            k:inteiro = 0
            para k de a ate b fazer
                resultado = resultado + k
            devolver resultado
        inicio
            total = soma(1, 3)
            escrever(total)
    """, tmp_path=tmp_path)
    texto = formatar_consola_com_debug(resultado)
    assert "a=1, b=3" in texto     # parâmetros
    assert "resultado=" in texto  # local
    assert "total=" in texto      # global visível dentro da função


def test_cli_debug_mostra_trace_na_consola(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text(textwrap.dedent("""
        algoritmo "T"
        inicio
            x:inteiro = 5
            escrever(x)
    """).lstrip("\n"), encoding="utf-8")
    resultado = subprocess.run(
        ["algo", "executa", str(algo_path), "--debug"],
        capture_output=True, text=True, timeout=15)
    assert resultado.returncode == 0, resultado.stderr
    assert "[debug linha" in resultado.stdout
    assert "x=5" in resultado.stdout
    assert not (tmp_path / "prog" / "prog_trace.json").exists()  # --debug sozinho não gera json


def test_debug_formata_arrays_e_estruturas_e_intercala_saida_real(tmp_path):
    """Fecha os últimos pontos de cobertura de formatar_consola_com_debug:
    _fmt_debug com uma lista e com um dicionário (estrutura), e o texto
    real produzido por escrever() intercalado entre as anotações de
    debug (não só as próprias anotações)."""
    from algo_lang.tools.tracer import formatar_consola_com_debug
    resultado = _trace("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
        inicio
            v:inteiro[2] = {1, 2}
            p:Ponto = {x: 5}
            flag:booleano = verdadeiro
            escrever(v[0])
            escrever(p.x)
    """, tmp_path=tmp_path)
    texto = formatar_consola_com_debug(resultado)
    assert "v=[1, 2]" in texto
    assert "p={x: 5}" in texto
    assert "flag=verdadeiro" in texto
    # a saída real (não só as linhas de debug) tem de aparecer intercalada
    linhas = texto.split("\n")
    assert "1" in linhas
    assert "5" in linhas
