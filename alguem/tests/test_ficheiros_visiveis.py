# -*- coding: utf-8 -*-
"""Testes de alguem.nucleo.ficheiros_visiveis."""
from alguem.nucleo import ficheiros_visiveis as modulo_ficheiros_visiveis
from alguem.nucleo.ficheiros_visiveis import resolver_ficheiros_visiveis


def test_ficheiro_sem_inclusoes(tmp_path):
    caminho = tmp_path / "sozinho.algo"
    caminho.write_text('algoritmo "T"\ninicio\n    escrever("ok")\n', encoding="utf-8")
    resultado = resolver_ficheiros_visiveis(str(caminho))
    assert resultado == [("sozinho.algo", 'algoritmo "T"\ninicio\n    escrever("ok")\n')]


def test_ficheiro_com_uma_inclusao(tmp_path):
    (tmp_path / "biblioteca.algo").write_text(
        "funcao dobro(n:inteiro):inteiro\n    retornar n * 2\n", encoding="utf-8")
    principal = tmp_path / "principal.algo"
    principal.write_text(
        'algoritmo "T"\nincluir "biblioteca.algo"\ninicio\n    escrever(dobro(5))\n',
        encoding="utf-8")
    resultado = resolver_ficheiros_visiveis(str(principal))
    nomes = [n for n, _ in resultado]
    assert nomes == ["principal.algo", "biblioteca.algo"]


def test_inclusoes_aninhadas_recursivas(tmp_path):
    (tmp_path / "fundo.algo").write_text(
        "funcao triplo(n:inteiro):inteiro\n    retornar n * 3\n", encoding="utf-8")
    (tmp_path / "meio.algo").write_text(
        'incluir "fundo.algo"\nfuncao dobro(n:inteiro):inteiro\n    retornar n * 2\n',
        encoding="utf-8")
    principal = tmp_path / "principal.algo"
    principal.write_text(
        'algoritmo "T"\nincluir "meio.algo"\ninicio\n    escrever(dobro(5))\n',
        encoding="utf-8")
    resultado = resolver_ficheiros_visiveis(str(principal))
    nomes = [n for n, _ in resultado]
    assert nomes == ["principal.algo", "meio.algo", "fundo.algo"]


def test_nao_repete_ficheiro_incluido_duas_vezes(tmp_path):
    (tmp_path / "comum.algo").write_text(
        "funcao dobro(n:inteiro):inteiro\n    retornar n * 2\n", encoding="utf-8")
    (tmp_path / "a.algo").write_text('incluir "comum.algo"\n', encoding="utf-8")
    principal = tmp_path / "principal.algo"
    principal.write_text(
        'algoritmo "T"\nincluir "a.algo"\nincluir "comum.algo"\ninicio\n    escrever(1)\n',
        encoding="utf-8")
    resultado = resolver_ficheiros_visiveis(str(principal))
    nomes = [n for n, _ in resultado]
    assert nomes.count("comum.algo") == 1


def test_inclusao_circular_nao_causa_recursao_infinita(tmp_path):
    """A inclui B, B inclui A -- tem de terminar, não entrar em
    recursão infinita nem duplicar nenhum dos dois."""
    (tmp_path / "a.algo").write_text(
        'incluir "b.algo"\nfuncao f_a():inteiro\n    retornar 1\n', encoding="utf-8")
    (tmp_path / "b.algo").write_text(
        'incluir "a.algo"\nfuncao f_b():inteiro\n    retornar 2\n', encoding="utf-8")
    resultado = resolver_ficheiros_visiveis(str(tmp_path / "a.algo"))
    nomes = [n for n, _ in resultado]
    assert nomes == ["a.algo", "b.algo"]


def test_tolerante_a_erro_de_sintaxe_no_ficheiro_principal(tmp_path):
    """O motivo de existir esta função em vez de usar o parser
    verdadeiro: o estudante pode estar a pedir ajuda precisamente
    porque o ficheiro tem um erro -- ainda assim, a inclusão deve ser
    detetada."""
    (tmp_path / "biblioteca.algo").write_text(
        "funcao dobro(n:inteiro):inteiro\n    retornar n * 2\n", encoding="utf-8")
    quebrado = tmp_path / "quebrado.algo"
    quebrado.write_text(
        'algoritmo "T"\nincluir "biblioteca.algo"\ninicio\n    x = )))) erro\n',
        encoding="utf-8")
    resultado = resolver_ficheiros_visiveis(str(quebrado))
    nomes = [n for n, _ in resultado]
    assert nomes == ["quebrado.algo", "biblioteca.algo"]


def test_ficheiro_incluido_que_nao_existe_e_ignorado_sem_rebentar(tmp_path):
    principal = tmp_path / "principal.algo"
    principal.write_text(
        'algoritmo "T"\nincluir "nao_existe.algo"\ninicio\n    escrever(1)\n',
        encoding="utf-8")
    resultado = resolver_ficheiros_visiveis(str(principal))
    nomes = [n for n, _ in resultado]
    assert nomes == ["principal.algo"]


def test_ficheiro_principal_que_nao_existe_devolve_lista_vazia(tmp_path):
    resultado = resolver_ficheiros_visiveis(str(tmp_path / "nao_existe.algo"))
    assert resultado == []


def test_incluir_caminho_absoluto_fora_da_pasta_e_ignorado(tmp_path):
    """AG-27: um 'incluir' com caminho absoluto para fora da pasta do
    exercício não pode dar ao Alguem (e por extensão à resposta ao
    estudante) visibilidade sobre ficheiros arbitrários do servidor."""
    pasta_exercicio = tmp_path / "exercicio"
    pasta_exercicio.mkdir()
    segredo = tmp_path / "segredo.algo"
    segredo.write_text("CONTEUDO_SECRETO", encoding="utf-8")
    principal = pasta_exercicio / "principal.algo"
    principal.write_text(
        f'algoritmo "T"\nincluir "{segredo.as_posix()}"\ninicio\n    escrever(1)\n',
        encoding="utf-8")
    resultado = resolver_ficheiros_visiveis(str(principal))
    nomes = [n for n, _ in resultado]
    assert nomes == ["principal.algo"]
    assert not any("CONTEUDO_SECRETO" in c for _, c in resultado)


def test_incluir_travessia_de_caminho_fora_da_pasta_e_ignorado(tmp_path):
    """AG-27: '../' não pode escapar da pasta do exercício."""
    pasta_exercicio = tmp_path / "exercicio"
    pasta_exercicio.mkdir()
    segredo = tmp_path / "segredo.algo"
    segredo.write_text("CONTEUDO_SECRETO", encoding="utf-8")
    principal = pasta_exercicio / "principal.algo"
    principal.write_text(
        'algoritmo "T"\nincluir "../segredo.algo"\ninicio\n    escrever(1)\n',
        encoding="utf-8")
    resultado = resolver_ficheiros_visiveis(str(principal))
    nomes = [n for n, _ in resultado]
    assert nomes == ["principal.algo"]
    assert not any("CONTEUDO_SECRETO" in c for _, c in resultado)


# ---------- AG-28: limites de nº de ficheiros e bytes totais ----------

def test_cadeia_de_inclusoes_maior_que_o_limite_de_ficheiros_e_cortada(tmp_path, monkeypatch):
    monkeypatch.setattr(modulo_ficheiros_visiveis, "LIMITE_FICHEIROS", 3)
    anterior = None
    for i in range(6):
        caminho = tmp_path / f"f{i}.algo"
        linha_incluir = f'incluir "f{i - 1}.algo"\n' if anterior else ""
        caminho.write_text(f"{linha_incluir}CONTEUDO_{i}", encoding="utf-8")
        anterior = caminho
    resultado = resolver_ficheiros_visiveis(str(tmp_path / "f5.algo"))
    assert len(resultado) == 3


def test_ficheiro_maior_que_o_limite_de_bytes_e_truncado(tmp_path, monkeypatch):
    monkeypatch.setattr(modulo_ficheiros_visiveis, "LIMITE_BYTES_TOTAL", 100)
    caminho = tmp_path / "grande.algo"
    caminho.write_text("x" * 1000, encoding="utf-8")
    resultado = resolver_ficheiros_visiveis(str(caminho))
    assert len(resultado) == 1
    nome, conteudo = resultado[0]
    assert len(conteudo.encode("utf-8")) <= 100 + len(
        "\n\n[... ficheiro truncado, excede o limite de tamanho total permitido ...]")
    assert "truncado" in conteudo


def test_soma_de_varios_ficheiros_acima_do_limite_de_bytes_para_de_incluir(tmp_path, monkeypatch):
    monkeypatch.setattr(modulo_ficheiros_visiveis, "LIMITE_BYTES_TOTAL", 50)
    (tmp_path / "b.algo").write_text("y" * 40, encoding="utf-8")
    principal = tmp_path / "principal.algo"
    principal.write_text('incluir "b.algo"\n' + "x" * 40, encoding="utf-8")
    resultado = resolver_ficheiros_visiveis(str(principal))
    nomes = [n for n, _ in resultado]
    # o principal (40 bytes + a linha de incluir) já quase esgota o
    # limite de 50 -- o segundo ficheiro não deve entrar de todo
    assert nomes == ["principal.algo"]


def test_conteudo_de_cada_ficheiro_esta_correto(tmp_path):
    (tmp_path / "biblioteca.algo").write_text("CONTEUDO_DA_BIBLIOTECA", encoding="utf-8")
    principal = tmp_path / "principal.algo"
    principal.write_text('incluir "biblioteca.algo"\nCONTEUDO_PRINCIPAL', encoding="utf-8")
    resultado = dict(resolver_ficheiros_visiveis(str(principal)))
    assert "CONTEUDO_PRINCIPAL" in resultado["principal.algo"]
    assert resultado["biblioteca.algo"] == "CONTEUDO_DA_BIBLIOTECA"
