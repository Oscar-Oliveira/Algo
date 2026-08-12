# -*- coding: utf-8 -*-
"""Testes da integração do Alguem na consola do ALGO ('?'). O HTTP é
sempre simulado (o sandbox não tem acesso de rede à OpenRouter/Gemini)
-- o que se confirma aqui é a integração em si: importação preguiçosa,
passagem do último ficheiro como contexto, visibilidade de ficheiros
incluídos, e que um erro do Alguem nunca fecha a consola do ALGO.

Todos os mocks de urllib.request.urlopen usados aqui reconhecem um
pedido de classificação do guardião (procuram o marcador do prompt de
classificação no corpo do pedido) e respondem sempre "SAFE" a esses --
sem isto, o guardião rejeitaria a resposta simulada "ok" (que não bate
com nenhuma categoria) e cairia sempre para a recusa segura fixa,
mascarando o que estes testes querem mesmo confirmar."""
import pathlib
import shutil
import subprocess
import sys

import pytest

RAIZ_PROJETO = pathlib.Path(__file__).resolve().parent.parent.parent

# Função auxiliar Python, embutida como texto em cada script de teste
# (cada teste corre num subprocesso Python limpo) -- reconhece um
# pedido de classificação do guardião e responde SAFE a esses, para
# não interferir com o que cada teste está mesmo a verificar.
_URLOPEN_INTELIGENTE = '''
import json
from unittest.mock import MagicMock

def _resposta_json(texto):
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps(
        {"choices": [{"message": {"content": texto}}]}).encode()
    return cm

def fazer_urlopen_falso(resposta_normal="ok", capturar_em=None):
    """Devolve uma função para usar com patch('urllib.request.urlopen',
    side_effect=...). 'capturar_em' é um dict onde o último pedido
    NORMAL (não de classificação) fica guardado, se for dado."""
    def urlopen_falso(pedido, timeout=None):
        corpo = json.loads(pedido.data.decode())
        eh_classificacao = any(
            "Categoria (uma palavra só, maiúsculas):" in m.get("content", "")
            for m in corpo["messages"])
        if eh_classificacao:
            return _resposta_json("SAFE")
        if capturar_em is not None:
            capturar_em["corpo"] = corpo
        return _resposta_json(resposta_normal)
    return urlopen_falso
'''


def _script_com_mock(entradas, resposta="Boa pergunta! O que precisas de saber primeiro?"):
    """Gera um script Python que corre cmd_consola com urllib simulado
    (já ciente do guardião) e uma sequência de 'linhas digitadas'
    pré-definida -- correr isto como subprocesso evita qualquer
    contaminação de estado entre testes (cada um arranca um processo
    Python limpo)."""
    entradas_repr = repr(entradas)
    return f"""
import sys, json, os
from unittest.mock import patch
{_URLOPEN_INTELIGENTE}

entradas = iter({entradas_repr})
def input_falso(prompt):
    return next(entradas)

import algo_lang.cli as cli_mod
from algo_lang.cli import cmd_consola
import argparse

parser = argparse.ArgumentParser(prog="algo")
sub = parser.add_subparsers(dest="comando")
p = sub.add_parser("executa"); p.add_argument("ficheiro")
p.add_argument("--mostrar-python", action="store_true")
p.add_argument("--debug", action="store_true")
p.add_argument("--json", action="store_true")
p.add_argument("--entradas")
p.set_defaults(func=cli_mod.cmd_executa)

with patch("urllib.request.urlopen", side_effect=fazer_urlopen_falso({resposta!r})):
    with patch.object(cli_mod, "_ler_linha_prompt", side_effect=lambda pr: input_falso(pr)):
        cmd_consola(parser)
"""


def _correr(script, timeout=15):
    """Corre o script num subprocesso Python limpo -- a partir de uma
    CÓPIA completa do projeto (algo_lang/ + alguem/), numa pasta
    temporária, para que qualquer chamada ao Alguem escreva logs só
    nessa cópia, nunca na pasta real do pacote. Sem variáveis de
    ambiente: o isolamento vem só de inserir a cópia no início do
    sys.path do próprio script, antes de mais nada."""
    import tempfile
    with tempfile.TemporaryDirectory() as pasta_temp:
        raiz_copia = pathlib.Path(pasta_temp) / "projeto"
        shutil.copytree(
            RAIZ_PROJETO / "algo_lang", raiz_copia / "algo_lang",
            ignore=shutil.ignore_patterns("__pycache__", "tests"))
        shutil.copytree(
            RAIZ_PROJETO / "alguem", raiz_copia / "alguem",
            ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.jsonl"))
        script_isolado = f"import sys; sys.path.insert(0, {str(raiz_copia)!r})\n" + script
        return subprocess.run(
            [sys.executable, "-c", script_isolado], cwd=str(raiz_copia),
            capture_output=True, text=True, timeout=timeout)


def test_interrogacao_sozinha_chama_o_alguem_e_espera_mensagem():
    script = _script_com_mock(["?", "não sei como fazer isto", "sair", "sair"])
    resultado = _correr(script)
    assert resultado.returncode == 0, resultado.stderr
    assert "Olá! Sou o Alguem" in resultado.stdout
    assert "Boa pergunta!" in resultado.stdout
    assert "Até já!" in resultado.stdout
    assert "Até à próxima!" in resultado.stdout  # a consola do ALGO fechou depois, corretamente


def test_interrogacao_com_pergunta_inline_responde_logo():
    script = _script_com_mock(["sair"])
    # substituímos a entrada por '? pergunta' diretamente na linha da consola
    script = script.replace(
        'entradas = iter([\'sair\'])',
        'entradas = iter(["? não sei os ciclos", "sair", "sair"])')
    resultado = _correr(script)
    assert resultado.returncode == 0, resultado.stderr
    assert "Boa pergunta!" in resultado.stdout


def test_alguem_recebe_o_ultimo_ficheiro_como_contexto(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text(
        'algoritmo "T"\ninicio\n    escrever("procura-me no contexto")\n', encoding="utf-8")
    script = f"""
import sys, json, os
from unittest.mock import patch
{_URLOPEN_INTELIGENTE}

capturado = {{}}
import algo_lang.cli as cli_mod

with patch("urllib.request.urlopen", side_effect=fazer_urlopen_falso(capturar_em=capturado)):
    cli_mod._chamar_alguem({str(algo_path)!r}, mensagem_inicial="ola")

mensagens = capturado["corpo"]["messages"]
tem_contexto = any("procura-me no contexto" in m["content"] for m in mensagens)
print("CONTEXTO_ENVIADO=" + str(tem_contexto))
"""
    resultado = _correr(script)
    assert "CONTEXTO_ENVIADO=True" in resultado.stdout, resultado.stdout + resultado.stderr


def test_alguem_sem_ficheiro_anterior_nao_envia_contexto():
    script = f"""
import sys, json, os
from unittest.mock import patch
{_URLOPEN_INTELIGENTE}

capturado = {{}}
import algo_lang.cli as cli_mod

with patch("urllib.request.urlopen", side_effect=fazer_urlopen_falso(capturar_em=capturado)):
    cli_mod._chamar_alguem(None, mensagem_inicial="ola")

n_mensagens_sistema = sum(1 for m in capturado["corpo"]["messages"] if m["role"] == "system")
print("MENSAGENS_SISTEMA=" + str(n_mensagens_sistema))
"""
    resultado = _correr(script)
    # só 1 mensagem de sistema (o próprio prompt do Alguem) -- sem a
    # segunda mensagem de contexto de exercício
    assert "MENSAGENS_SISTEMA=1" in resultado.stdout, resultado.stdout + resultado.stderr


def test_erro_do_fornecedor_llm_nao_fecha_a_consola_do_algo():
    """Erro real (ex: sem acesso de rede, credenciais inválidas) tem
    de mostrar uma mensagem amigável e devolver ao prompt 'tu>', sem
    nunca deixar a consola inteira do ALGO abaixo."""
    script = """
import sys
from unittest.mock import patch
import urllib.error

erro = urllib.error.URLError("sem ligação")

entradas = iter(["?", "ola", "sair", "sair"])
def input_falso(prompt):
    return next(entradas)

import algo_lang.cli as cli_mod
from algo_lang.cli import cmd_consola
import argparse

parser = argparse.ArgumentParser(prog="algo")
sub = parser.add_subparsers(dest="comando")
p = sub.add_parser("executa"); p.add_argument("ficheiro")
p.set_defaults(func=cli_mod.cmd_executa)

with patch("urllib.request.urlopen", side_effect=erro):
    with patch.object(cli_mod, "_ler_linha_prompt", side_effect=lambda pr: input_falso(pr)):
        cmd_consola(parser)
"""
    resultado = _correr(script)
    assert resultado.returncode == 0, resultado.stderr
    assert "❌" in resultado.stdout
    assert "Até à próxima!" in resultado.stdout


def test_alguem_sem_pasta_disponivel_da_erro_amigavel(tmp_path, monkeypatch):
    """Se a pasta alguem/ não existir (cópia só do algo_lang), o '?' não
    deve rebentar a consola -- só avisar que o Alguem não está
    disponível."""
    import algo_lang.cli as cli_mod
    import builtins
    import sys as sys_mod
    real_import = builtins.__import__

    # se algum teste anterior já importou 'alguem' com sucesso, fica em
    # cache -- sem isto, o 'import alguem' nem chegaria a chamar
    # __import__ de novo, e o bloqueio simulado não teria efeito nenhum
    for nome_modulo in list(sys_mod.modules):
        if nome_modulo == "alguem" or nome_modulo.startswith("alguem."):
            del sys_mod.modules[nome_modulo]

    def import_bloqueado(nome, *a, **kw):
        if nome == "alguem":
            raise ImportError("simulado: sem pasta alguem/")
        return real_import(nome, *a, **kw)

    import io
    import contextlib
    buffer = io.StringIO()
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(builtins, "__import__", import_bloqueado)
        with contextlib.redirect_stdout(buffer):
            cli_mod._chamar_alguem(None)
    assert "Não encontrei a pasta 'alguem/'" in buffer.getvalue()


def test_ficheiro_e_enviado_com_o_nome_no_prompt(tmp_path):
    algo_path = tmp_path / "exercicio.algo"
    algo_path.write_text(
        'algoritmo "T"\ninicio\n    escrever("conteudo unico xyz")\n', encoding="utf-8")
    script = f"""
import sys, json, os
from unittest.mock import patch
{_URLOPEN_INTELIGENTE}

capturado = {{}}
import algo_lang.cli as cli_mod

with patch("urllib.request.urlopen", side_effect=fazer_urlopen_falso(capturar_em=capturado)):
    cli_mod._chamar_alguem({str(algo_path)!r}, mensagem_inicial="ola")

textos = [m["content"] for m in capturado["corpo"]["messages"]]
tem_nome = any("exercicio.algo" in t for t in textos)
tem_conteudo = any("conteudo unico xyz" in t for t in textos)
print("NOME=" + str(tem_nome))
print("CONTEUDO=" + str(tem_conteudo))
"""
    resultado = _correr(script)
    assert "NOME=True" in resultado.stdout, resultado.stdout + resultado.stderr
    assert "CONTEUDO=True" in resultado.stdout


def test_ficheiro_incluido_tambem_e_enviado_ao_alguem(tmp_path):
    (tmp_path / "biblioteca.algo").write_text(
        "funcao dobro(n:inteiro):inteiro\n    devolver n * 2\n", encoding="utf-8")
    principal = tmp_path / "principal.algo"
    principal.write_text(
        'algoritmo "T"\nincluir "biblioteca.algo"\ninicio\n    escrever(dobro(5))\n',
        encoding="utf-8")
    script = f"""
import sys, json
from unittest.mock import patch
{_URLOPEN_INTELIGENTE}

capturado = {{}}
import algo_lang.cli as cli_mod
with patch("urllib.request.urlopen", side_effect=fazer_urlopen_falso(capturar_em=capturado)):
    cli_mod._chamar_alguem({str(principal)!r}, mensagem_inicial="ola")

textos = [m["content"] for m in capturado["corpo"]["messages"]]
print("PRINCIPAL=" + str(any("principal.algo" in t for t in textos)))
print("BIBLIOTECA_NOME=" + str(any("biblioteca.algo" in t for t in textos)))
print("BIBLIOTECA_CONTEUDO=" + str(any("dobro" in t for t in textos)))
"""
    resultado = _correr(script)
    assert "PRINCIPAL=True" in resultado.stdout, resultado.stdout + resultado.stderr
    assert "BIBLIOTECA_NOME=True" in resultado.stdout
    assert "BIBLIOTECA_CONTEUDO=True" in resultado.stdout


def test_comando_ficheiros_lista_visibilidade_atual(tmp_path):
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text('algoritmo "T"\ninicio\n    escrever(1)\n', encoding="utf-8")
    script = f"""
import sys, json
from unittest.mock import patch
{_URLOPEN_INTELIGENTE}

entradas = iter(["ficheiros", "sair"])
def input_falso(prompt):
    return next(entradas)

import algo_lang.cli as cli_mod
with patch("urllib.request.urlopen", side_effect=fazer_urlopen_falso()):
    with patch.object(cli_mod, "_ler_linha_prompt", side_effect=lambda p: input_falso(p)):
        cli_mod._chamar_alguem({str(algo_path)!r})
"""
    resultado = _correr(script)
    assert "Tenho visibilidade de: prog.algo" in resultado.stdout, resultado.stdout + resultado.stderr


def test_comando_ficheiro_nome_troca_o_ficheiro_ativo(tmp_path):
    (tmp_path / "outro.algo").write_text(
        'algoritmo "Outro"\ninicio\n    escrever("sou o outro")\n', encoding="utf-8")
    primeiro = tmp_path / "primeiro.algo"
    primeiro.write_text('algoritmo "T"\ninicio\n    escrever(1)\n', encoding="utf-8")

    script = f"""
import sys, json
from unittest.mock import patch
{_URLOPEN_INTELIGENTE}

entradas = iter(["ficheiro outro.algo", "ficheiros", "sair"])
def input_falso(prompt):
    return next(entradas)

import algo_lang.cli as cli_mod
with patch("urllib.request.urlopen", side_effect=fazer_urlopen_falso()):
    with patch.object(cli_mod, "_ler_linha_prompt", side_effect=lambda p: input_falso(p)):
        cli_mod._chamar_alguem({str(primeiro)!r})
"""
    resultado = _correr(script)
    assert "Tenho visibilidade de: outro.algo" in resultado.stdout, resultado.stdout + resultado.stderr


def test_comando_ficheiro_nome_inexistente_da_erro_sem_rebentar():
    script = f"""
import sys, json
from unittest.mock import patch
{_URLOPEN_INTELIGENTE}

entradas = iter(["ficheiro nao_existe_de_todo.algo", "sair"])
def input_falso(prompt):
    return next(entradas)

import algo_lang.cli as cli_mod
with patch("urllib.request.urlopen", side_effect=fazer_urlopen_falso()):
    with patch.object(cli_mod, "_ler_linha_prompt", side_effect=lambda p: input_falso(p)):
        cli_mod._chamar_alguem(None)
"""
    resultado = _correr(script)
    assert resultado.returncode == 0, resultado.stderr
    assert "❌ Não encontrei" in resultado.stdout


def test_guardiao_intercepta_resposta_com_codigo_atraves_da_consola():
    """Confirma a integração completa: o guardião ativo por omissão
    intercepta uma resposta com código vinda da consola do ALGO, e o
    estudante nunca a vê -- só a versão regenerada."""
    script = """
import sys, json
from unittest.mock import patch, MagicMock

respostas = iter([
    "```algo\\nescrever(x)\\n```",
    "O que precisas de fazer a cada número que lês?",
    "SAFE",
])
def urlopen_falso(pedido, timeout=None):
    texto = next(respostas)
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps(
        {"choices": [{"message": {"content": texto}}]}).encode()
    return cm

entradas = iter(["? como calculo a média?", "sair", "sair"])
def input_falso(prompt):
    return next(entradas)

import algo_lang.cli as cli_mod
from algo_lang.cli import cmd_consola
import argparse

parser = argparse.ArgumentParser(prog="algo")
sub = parser.add_subparsers(dest="comando")
p = sub.add_parser("executa"); p.add_argument("ficheiro")
p.set_defaults(func=cli_mod.cmd_executa)

with patch("urllib.request.urlopen", side_effect=urlopen_falso):
    with patch.object(cli_mod, "_ler_linha_prompt", side_effect=lambda pr: input_falso(pr)):
        cmd_consola(parser)
"""
    resultado = _correr(script)
    assert resultado.returncode == 0, resultado.stderr
    assert "```" not in resultado.stdout
    assert "O que precisas de fazer a cada número que lês?" in resultado.stdout
