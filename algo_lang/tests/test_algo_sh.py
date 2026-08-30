# -*- coding: utf-8 -*-
"""Testes do script de arranque algo.sh (Linux/macOS -- algo.command tem
o mesmo conteúdo, byte a byte, por isso estes testes também dão
confiança nesse). O algo.bat (Windows) não é testável neste ambiente
(só Linux disponível) -- foi revisto manualmente com o mesmo cuidado."""
import os
import pathlib
import shutil
import subprocess
import pytest

RAIZ_PROJETO = pathlib.Path(__file__).resolve().parent.parent.parent

# Achado 1 revisto (docs/interno/PlanoAuditoria.md): não é um bug, é a própria
# natureza destes testes -- correm 'algo.sh' como processo real
# (Windows não sabe interpretar o shebang de um script bash, dá
# "%1 is not a valid Win32 application") e dois deles criam symlinks
# para simular um PATH mínimo (privilégio que o Windows exige e que
# esta conta não tem, ao contrário de Linux/macOS). Confirma o que o
# docstring do módulo já dizia: só faz sentido correr em POSIX.
_SO_NAO_SUPORTADO = pytest.mark.skipif(
    os.name != "posix",
    reason="algo.sh é um script bash, testado como processo real -- só corre em POSIX "
    "(Windows usa algo.bat, sem testes automáticos, ver docstring do módulo)",
)


def _preparar_copia_do_projeto(tmp_path):
    """Copia só o necessário para o algo.sh conseguir instalar-se: o
    pacote, o pyproject.toml e o próprio script -- disposição igual à do
    pacote distribuído por empacotar.py (algo.sh solto na raiz, ao lado
    do pyproject.toml), não à do repositório (onde vive em instaladores/)."""
    destino = tmp_path / "projeto"
    destino.mkdir()
    shutil.copytree(RAIZ_PROJETO / "algo_lang", destino / "algo_lang",
                     ignore=shutil.ignore_patterns("__pycache__", "tests"))
    shutil.copy(RAIZ_PROJETO / "pyproject.toml", destino / "pyproject.toml")
    shutil.copy(RAIZ_PROJETO / "instaladores" / "algo.sh", destino / "algo.sh")
    os.chmod(destino / "algo.sh", 0o755)
    return destino


def _preparar_copia_do_repositorio(tmp_path):
    """Disposição igual à do repositório: algo.sh dentro de instaladores/,
    com o pyproject.toml um nível acima. Confirma o fallback do próprio
    algo.sh (que procura o pyproject.toml na sua própria pasta antes de
    subir um nível) para esta disposição, distinta da do pacote
    distribuído usada por _preparar_copia_do_projeto."""
    destino = tmp_path / "projeto"
    destino.mkdir()
    shutil.copytree(RAIZ_PROJETO / "algo_lang", destino / "algo_lang",
                     ignore=shutil.ignore_patterns("__pycache__", "tests"))
    shutil.copy(RAIZ_PROJETO / "pyproject.toml", destino / "pyproject.toml")
    (destino / "instaladores").mkdir()
    shutil.copy(RAIZ_PROJETO / "instaladores" / "algo.sh",
                destino / "instaladores" / "algo.sh")
    os.chmod(destino / "instaladores" / "algo.sh", 0o755)
    return destino


@_SO_NAO_SUPORTADO
@pytest.mark.slow
def test_algo_sh_a_partir_de_instaladores_usa_venv_na_raiz(tmp_path):
    projeto = _preparar_copia_do_repositorio(tmp_path)
    (projeto / "soma.algo").write_text(
        'algoritmo "T"\ninicio\n    escrever(2 + 3)\n', encoding="utf-8")

    resultado = subprocess.run(
        ["./instaladores/algo.sh", "executa", "soma.algo"], cwd=projeto,
        capture_output=True, text=True, timeout=120)
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert "5" in resultado.stdout
    assert (projeto / ".venv" / "bin" / "algo").exists()
    assert not (projeto / "instaladores" / ".venv").exists()


@_SO_NAO_SUPORTADO
@pytest.mark.slow
def test_algo_sh_primeira_execucao_cria_venv_e_funciona(tmp_path):
    projeto = _preparar_copia_do_projeto(tmp_path)
    algo_path = projeto / "soma.algo"
    algo_path.write_text(
        'algoritmo "T"\ninicio\n    escrever(2 + 3)\n', encoding="utf-8")

    assert not (projeto / ".venv").exists()
    resultado = subprocess.run(
        ["./algo.sh", "executa", "soma.algo"], cwd=projeto,
        capture_output=True, text=True, timeout=120)
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert "Primeira utilização" in resultado.stdout
    assert "5" in resultado.stdout
    assert (projeto / ".venv" / "bin" / "algo").exists()


@_SO_NAO_SUPORTADO
@pytest.mark.slow
def test_algo_sh_segunda_execucao_nao_reinstala(tmp_path):
    projeto = _preparar_copia_do_projeto(tmp_path)
    (projeto / "soma.algo").write_text(
        'algoritmo "T"\ninicio\n    escrever(2 + 3)\n', encoding="utf-8")
    subprocess.run(["./algo.sh", "executa", "soma.algo"], cwd=projeto,
                    capture_output=True, text=True, timeout=120)

    resultado = subprocess.run(
        ["./algo.sh", "verifica", "soma.algo"], cwd=projeto,
        capture_output=True, text=True, timeout=15)
    assert resultado.returncode == 0
    assert "Primeira utilização" not in resultado.stdout


@_SO_NAO_SUPORTADO
@pytest.mark.slow
def test_algo_sh_funciona_com_espacos_no_caminho(tmp_path):
    pasta_com_espacos = tmp_path / "pasta com espaços"
    pasta_com_espacos.mkdir()
    shutil.copytree(RAIZ_PROJETO / "algo_lang", pasta_com_espacos / "algo_lang",
                     ignore=shutil.ignore_patterns("__pycache__", "tests"))
    shutil.copy(RAIZ_PROJETO / "pyproject.toml", pasta_com_espacos / "pyproject.toml")
    shutil.copy(RAIZ_PROJETO / "instaladores" / "algo.sh", pasta_com_espacos / "algo.sh")
    os.chmod(pasta_com_espacos / "algo.sh", 0o755)
    (pasta_com_espacos / "soma.algo").write_text(
        'algoritmo "T"\ninicio\n    escrever(2 + 3)\n', encoding="utf-8")

    resultado = subprocess.run(
        ["./algo.sh", "executa", "soma.algo"], cwd=pasta_com_espacos,
        capture_output=True, text=True, timeout=120)
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert "5" in resultado.stdout


@_SO_NAO_SUPORTADO
def test_algo_sh_sem_python_da_erro_amigavel(tmp_path):
    projeto = _preparar_copia_do_projeto(tmp_path)
    bin_minimo = tmp_path / "bin_minimo"
    bin_minimo.mkdir()
    for cmd in ("bash", "sh", "cd", "command", "dirname", "pwd", "rm", "mkdir", "cat"):
        caminho = shutil.which(cmd)
        if caminho:
            (bin_minimo / cmd).symlink_to(caminho)

    resultado = subprocess.run(
        ["bash", "algo.sh"], cwd=projeto,
        capture_output=True, text=True, timeout=15,
        env={"HOME": os.environ.get("HOME", "/tmp"), "PATH": str(bin_minimo)})
    assert resultado.returncode != 0
    assert "Não encontrei o Python" in resultado.stderr
    assert not (projeto / ".venv").exists()


def test_algo_command_e_identico_ao_algo_sh():
    """algo.command (macOS, duplo-clique) tem de ter o mesmo conteúdo do
    algo.sh -- é literalmente o mesmo script, só muda a extensão para o
    Finder o reconhecer como executável."""
    conteudo_sh = (RAIZ_PROJETO / "instaladores" / "algo.sh").read_text(encoding="utf-8")
    conteudo_command = (RAIZ_PROJETO / "instaladores" / "algo.command").read_text(encoding="utf-8")
    assert conteudo_sh == conteudo_command


@_SO_NAO_SUPORTADO
def test_algo_sh_venv_sem_pip_da_erro_amigavel(tmp_path):
    """Cenário real em Debian/Ubuntu sem o pacote 'python3-venv': o venv
    chega a ser criado, mas fica sem 'pip' lá dentro. Para simular isto
    de forma fiável, forjamos um 'python3' no PATH que, quando chamado
    com '-m venv', cria a estrutura mas sem pip -- exatamente o
    comportamento real do sistema nesse cenário."""
    projeto = _preparar_copia_do_projeto(tmp_path)

    python_real = shutil.which("python3")
    bin_falso = tmp_path / "bin_falso"
    bin_falso.mkdir()
    (bin_falso / "python3").write_text(f"""#!/usr/bin/env bash
if [ "$1" = "-m" ] && [ "$2" = "venv" ]; then
    "{python_real}" -m venv --without-pip "${{@:3}}"
else
    exec "{python_real}" "$@"
fi
""", encoding="utf-8")
    os.chmod(bin_falso / "python3", 0o755)

    ambiente = dict(os.environ)
    ambiente["PATH"] = f"{bin_falso}:{ambiente['PATH']}"
    resultado = subprocess.run(
        ["./algo.sh"], cwd=projeto, capture_output=True, text=True,
        timeout=30, env=ambiente)
    assert resultado.returncode != 0
    assert "python3-venv" in resultado.stderr
    assert not (projeto / ".venv").exists()
