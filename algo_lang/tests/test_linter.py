# -*- coding: utf-8 -*-
"""Testes para o linter (avisos de estilo, não impedem a compilação)."""
import textwrap

import pytest

from algo_lang.compilador.parser import parse
from algo_lang.compilador.semantics import verificar, ErroSemantico
from algo_lang.tools.linter import analisar


def _avisos(codigo_algo):
    programa = parse(textwrap.dedent(codigo_algo))
    verificar(programa)
    return analisar(programa)


def test_programa_limpo_nao_tem_avisos():
    avisos = _avisos("""
        algoritmo "T"
        funcao dobro(x:inteiro):inteiro
            devolver x * 2
        inicio
            n:inteiro = 5
            escrever(dobro(n))
    """)
    assert avisos == []


def test_variavel_de_ciclo_para_nunca_e_assinalada():
    """'para i de 1 ate 5 fazer' sem usar 'i' no corpo é um idioma comum
    (contar iterações) e não deve gerar aviso."""
    avisos = _avisos("""
        algoritmo "T"
        inicio
            i:inteiro = 0
            para i de 1 ate 5 fazer
                escrever("oi")
    """)
    assert avisos == []


def test_variavel_nunca_usada_no_programa_principal():
    avisos = _avisos("""
        algoritmo "T"
        inicio
            x:inteiro = 5
            escrever("ola")
    """)
    assert len(avisos) == 1
    assert "x" in avisos[0].mensagem
    assert "nunca é usada" in avisos[0].mensagem


def test_variavel_usada_so_do_lado_esquerdo_de_atribuicoes_e_assinalada():
    avisos = _avisos("""
        algoritmo "T"
        inicio
            x:inteiro = 5
            x = 10
            x = 20
            escrever("nunca lê x")
    """)
    assert any("x" in a.mensagem and "nunca é usada" in a.mensagem for a in avisos)


def test_variavel_usada_como_indice_nao_e_assinalada():
    avisos = _avisos("""
        algoritmo "T"
        inicio
            v:inteiro[3]
            i:inteiro = 1
            v[i] = 10
            escrever(v[1])
    """)
    assert avisos == []


def test_parametro_nao_usado():
    avisos = _avisos("""
        algoritmo "T"
        funcao f(a:inteiro, b:inteiro):inteiro
            devolver a
        inicio
            escrever(f(1, 2))
    """)
    assert len(avisos) == 1
    assert "b" in avisos[0].mensagem
    assert "nunca é usado" in avisos[0].mensagem


def test_funcao_nunca_chamada():
    avisos = _avisos("""
        algoritmo "T"
        funcao nuncaChamada(x:inteiro):inteiro
            devolver x
        inicio
            escrever("ola")
    """)
    assert len(avisos) == 1
    assert "nuncaChamada" in avisos[0].mensagem
    assert "nunca é chamada" in avisos[0].mensagem


def test_procedimento_nunca_chamado_usa_genero_correto():
    avisos = _avisos("""
        algoritmo "T"
        procedimento nuncaChamado()
            escrever("ola")
        inicio
            escrever("adeus")
    """)
    assert len(avisos) == 1
    assert "nunca é chamado" in avisos[0].mensagem


def test_funcao_chamada_por_outra_funcao_nao_e_assinalada():
    avisos = _avisos("""
        algoritmo "T"
        funcao auxiliar(x:inteiro):inteiro
            devolver x * 2
        funcao principal(x:inteiro):inteiro
            devolver auxiliar(x) + 1
        inicio
            escrever(principal(5))
    """)
    assert avisos == []


def test_parametro_sombreia_global_da_aviso():
    avisos = _avisos("""
        algoritmo "T"
        total:inteiro = 0
        procedimento mostra(total:inteiro)
            escrever(total)
        inicio
            mostra(5)
    """)
    assert any("total" in a.mensagem and "mesmo nome" in a.mensagem for a in avisos)


def test_variavel_local_sombreia_global_da_aviso():
    avisos = _avisos("""
        algoritmo "T"
        total:inteiro = 0
        procedimento f()
            total:inteiro = 5
            escrever(total)
        inicio
            f()
    """)
    assert any("total" in a.mensagem and "mesmo nome" in a.mensagem for a in avisos)


def test_escrita_em_global_mutavel_da_aviso():
    avisos = _avisos("""
        algoritmo "T"
        total:inteiro = 0
        procedimento acumular(x:inteiro)
            total = total + x
        inicio
            acumular(5)
    """)
    assert any("total" in a.mensagem and "acede diretamente" in a.mensagem for a in avisos)


def test_leitura_em_global_mutavel_da_aviso():
    avisos = _avisos("""
        algoritmo "T"
        total:inteiro = 42
        funcao mostraTotal():inteiro
            devolver total
        inicio
            escrever(mostraTotal())
    """)
    assert any("total" in a.mensagem and "acede diretamente" in a.mensagem for a in avisos)


def test_varias_globais_usadas_aparecem_juntas_num_so_aviso():
    avisos = _avisos("""
        algoritmo "T"
        a:inteiro = 0
        b:inteiro = 0
        procedimento soma()
            a = a + b
        inicio
            soma()
    """)
    relevantes = [a for a in avisos if "acede diretamente" in a.mensagem]
    assert len(relevantes) == 1
    assert "'a'" in relevantes[0].mensagem and "'b'" in relevantes[0].mensagem
    assert "variáveis globais" in relevantes[0].mensagem  # plural correto


def test_constante_global_nao_da_aviso_de_uso_de_globais():
    """Aceder a uma 'constante' global não é o mesmo problema que aceder
    a uma variável global mutável -- não deve ser assinalado."""
    avisos = _avisos("""
        algoritmo "T"
        constante IVA:decimal = 1.23
        funcao precoComIva(preco:decimal):decimal
            devolver preco * IVA
        inicio
            escrever(precoComIva(10.0))
    """)
    assert not any("acede diretamente" in a.mensagem for a in avisos)


def test_parametro_que_sombreia_global_nao_conta_como_uso():
    """Se o parâmetro tem o mesmo nome da global, dentro da função é o
    parâmetro que está a ser usado, não a global -- não deve gerar o
    aviso de 'acede diretamente', só o aviso de sombra (já testado)."""
    avisos = _avisos("""
        algoritmo "T"
        total:inteiro = 0
        procedimento naoUsaGlobal(total:inteiro)
            escrever(total)
        inicio
            naoUsaGlobal(5)
    """)
    assert not any("acede diretamente" in a.mensagem for a in avisos)


def test_divisao_por_zero_literal():
    avisos = _avisos("""
        algoritmo "T"
        inicio
            x:inteiro = 5
            escrever(x / 0)
    """)
    assert any("divisão por zero" in a.mensagem for a in avisos)


def test_divisao_por_variavel_zero_nao_e_assinalada():
    """Só deteta o caso óbvio (literal 0); não tenta analisar se uma
    variável pode vir a valer zero em tempo de execução."""
    avisos = _avisos("""
        algoritmo "T"
        inicio
            x:inteiro = 5
            y:inteiro = 0
            escrever(x / y)
    """)
    assert not any("divisão por zero" in a.mensagem for a in avisos)


def test_comparacao_variavel_consigo_mesma():
    avisos = _avisos("""
        algoritmo "T"
        inicio
            x:inteiro = 5
            se x == x entao
                escrever("sempre")
    """)
    assert any("sempre verdadeira" in a.mensagem for a in avisos)


def test_comparacao_diferente_variavel_consigo_mesma():
    avisos = _avisos("""
        algoritmo "T"
        inicio
            x:inteiro = 5
            se x <> x entao
                escrever("nunca")
    """)
    assert any("sempre falsa" in a.mensagem for a in avisos)


def test_comparacao_de_elementos_diferentes_de_vetor_nao_e_assinalada():
    avisos = _avisos("""
        algoritmo "T"
        inicio
            v:inteiro[3] = {1, 2, 3}
            i:inteiro = 1
            j:inteiro = 2
            se v[i] == v[j] entao
                escrever("iguais")
    """)
    assert not any("sempre verdadeira" in a.mensagem for a in avisos)


def test_cli_verifica_sem_avisos(tmp_path):
    import subprocess
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text('algoritmo "T"\ninicio\n    escrever("ok")\n', encoding="utf-8")
    resultado = subprocess.run(["algo", "verifica", str(algo_path)], capture_output=True, text=True)
    assert resultado.returncode == 0
    assert "Nenhum aviso" in resultado.stdout


def test_cli_verifica_com_avisos(tmp_path):
    import subprocess
    algo_path = tmp_path / "prog.algo"
    algo_path.write_text(
        'algoritmo "T"\ninicio\n    x:inteiro = 5\n    escrever("ok")\n', encoding="utf-8")
    resultado = subprocess.run(["algo", "verifica", str(algo_path)], capture_output=True, text=True)
    assert resultado.returncode == 0
    assert "aviso" in resultado.stdout
    assert "x" in resultado.stdout


def test_comparacao_entre_variaveis_diferentes_nao_e_assinalada():
    """Confirma o caminho de sucesso: nomes diferentes ('x' vs 'y') não
    podem ser tratados como 'a mesma variável', por isso não há aviso de
    'comparação sempre verdadeira'."""
    avisos = _avisos("""
        algoritmo "T"
        inicio
            x:inteiro = 5
            y:inteiro = 5
            se x == y entao
                escrever("iguais")
    """)
    assert not any("sempre" in a.mensagem for a in avisos)


def test_comparacao_entre_indices_diferentes_nao_e_assinalada():
    """v[i] == v[i + 1] -- mesma base, índices com formas diferentes
    (LValue vs BinOp) -- não pode ser tratado como 'a mesma variável'."""
    avisos = _avisos("""
        algoritmo "T"
        inicio
            v:inteiro[5]
            i:inteiro = 0
            se v[i] == v[i + 1] entao
                escrever("iguais")
    """)
    assert not any("sempre" in a.mensagem for a in avisos)


def test_inclusao_duplicada_da_aviso():
    avisos = _avisos("""
        algoritmo "T"
        incluir "biblioteca.algo"
        incluir "biblioteca.algo"
        inicio
            escrever("ok")
    """)
    relevantes = [a for a in avisos if "já tinha sido incluído" in a.mensagem]
    assert len(relevantes) == 1
    assert "biblioteca.algo" in relevantes[0].mensagem


def test_inclusao_duplicada_com_caminhos_equivalentes_da_aviso():
    """'./biblioteca.algo' e 'biblioteca.algo' resolvem para o mesmo
    ficheiro -- deve ser detetado apesar do texto literal ser diferente."""
    avisos = _avisos("""
        algoritmo "T"
        incluir "biblioteca.algo"
        incluir "./biblioteca.algo"
        inicio
            escrever("ok")
    """)
    assert any("já tinha sido incluído" in a.mensagem for a in avisos)


def test_inclusoes_diferentes_nao_dao_aviso():
    avisos = _avisos("""
        algoritmo "T"
        incluir "a.algo"
        incluir "b.algo"
        inicio
            escrever("ok")
    """)
    assert not any("já tinha sido incluído" in a.mensagem for a in avisos)


def test_importar_duplicado_da_aviso():
    avisos = _avisos("""
        algoritmo "T"
        importar matematica
        importar matematica
        inicio
            escrever("ok")
    """)
    relevantes = [a for a in avisos if "já tinha sido importada" in a.mensagem]
    assert len(relevantes) == 1
    assert "matematica" in relevantes[0].mensagem


def test_importar_duplicado_ignora_maiusculas_minusculas():
    avisos = _avisos("""
        algoritmo "T"
        importar matematica
        importar Matematica
        inicio
            escrever("ok")
    """)
    assert any("já tinha sido importada" in a.mensagem for a in avisos)


def test_importares_diferentes_nao_dao_aviso():
    avisos = _avisos("""
        algoritmo "T"
        importar matematica
        importar cadeia
        inicio
            escrever("ok")
    """)
    assert not any("já tinha sido importada" in a.mensagem for a in avisos)


def test_caso_repetido_em_escolha_da_aviso():
    # AL-56/B15 (algo_lang/AUDITORIA_PROGRESSO.md): um 'caso' repetido com
    # um LITERAL direto (ex.: 'caso 1' duas vezes) passou a ser um ERRO de
    # compilação em semantics.py, não só um aviso -- por isso este teste
    # usa a mesma VARIÁVEL como valor de 'caso' duas vezes (não coberto
    # pela verificação nova, que só olha para literais diretos), para
    # continuar a exercitar o aviso do próprio linter.
    avisos = _avisos("""
        algoritmo "T"
        inicio
            x:inteiro = 1
            y:inteiro = 1
            escolher x
                caso y
                    escrever("um")
                caso y
                    escrever("também um")
    """)
    relevantes = [a for a in avisos if "já apareceu na linha" in a.mensagem]
    assert len(relevantes) == 1


def test_caso_repetido_em_escolha_com_literal_direto_e_erro_de_compilacao():
    """AL-56/B15: o caso mais comum (literal repetido) passou a ser
    apanhado em compilação, não só pelo linter."""
    with pytest.raises(ErroSemantico, match="já apareceu"):
        _avisos("""
            algoritmo "T"
            inicio
                x:inteiro = 1
                escolher x
                    caso 1
                        escrever("um")
                    caso 1
                        escrever("também um")
        """)


def test_casos_diferentes_em_escolha_nao_dao_aviso():
    avisos = _avisos("""
        algoritmo "T"
        inicio
            x:inteiro = 1
            escolher x
                caso 1
                    escrever("um")
                caso 2
                    escrever("dois")
    """)
    assert not any("já apareceu na linha" in a.mensagem for a in avisos)


def test_codigo_depois_de_devolver_da_aviso():
    avisos = _avisos("""
        algoritmo "T"
        funcao f(x:inteiro):inteiro
            devolver x
            escrever("nunca corre")
        inicio
            escrever(f(1))
    """)
    assert any("nunca são executadas" in a.mensagem for a in avisos)


def test_devolver_no_fim_do_bloco_nao_da_aviso():
    avisos = _avisos("""
        algoritmo "T"
        funcao f(x:inteiro):inteiro
            devolver x
        inicio
            escrever(f(1))
    """)
    assert not any("nunca são executadas" in a.mensagem for a in avisos)


def test_atribuicao_a_parametro_por_valor_da_aviso():
    avisos = _avisos("""
        algoritmo "T"
        procedimento incrementa(x:inteiro)
            x = x + 1
        inicio
            n:inteiro = 5
            incrementa(n)
            escrever(n)
    """)
    assert any("não é 'por referência'" in a.mensagem for a in avisos)


def test_atribuicao_a_parametro_por_referencia_nao_da_aviso():
    avisos = _avisos("""
        algoritmo "T"
        procedimento incrementa(ref x:inteiro)
            x = x + 1
        inicio
            n:inteiro = 5
            incrementa(n)
            escrever(n)
    """)
    assert not any("não é 'por referência'" in a.mensagem for a in avisos)


def test_resultado_de_funcao_descartado_da_aviso():
    avisos = _avisos("""
        algoritmo "T"
        funcao dobro(x:inteiro):inteiro
            devolver x * 2
        inicio
            dobro(5)
    """)
    assert any("é descartado aqui" in a.mensagem for a in avisos)


def test_resultado_de_funcao_usado_nao_da_aviso():
    avisos = _avisos("""
        algoritmo "T"
        funcao dobro(x:inteiro):inteiro
            devolver x * 2
        inicio
            escrever(dobro(5))
    """)
    assert not any("é descartado aqui" in a.mensagem for a in avisos)


def test_chamada_a_procedimento_nao_da_aviso_de_resultado_descartado():
    avisos = _avisos("""
        algoritmo "T"
        procedimento mostra(x:inteiro)
            escrever(x)
        inicio
            mostra(5)
    """)
    assert not any("é descartado aqui" in a.mensagem for a in avisos)


def test_ciclo_enquanto_verdadeiro_sem_devolver_da_aviso():
    avisos = _avisos("""
        algoritmo "T"
        inicio
            enquanto verdadeiro fazer
                escrever("para sempre")
    """)
    assert any("nunca termina" in a.mensagem for a in avisos)


def test_ciclo_enquanto_verdadeiro_com_devolver_nao_da_aviso():
    avisos = _avisos("""
        algoritmo "T"
        funcao f():inteiro
            enquanto verdadeiro fazer
                devolver 1
        inicio
            escrever(f())
    """)
    assert not any("nunca termina" in a.mensagem for a in avisos)


def test_ciclo_enquanto_com_condicao_normal_nao_da_aviso():
    avisos = _avisos("""
        algoritmo "T"
        inicio
            i:inteiro = 0
            enquanto i < 5 fazer
                i = i + 1
    """)
    assert not any("nunca termina" in a.mensagem for a in avisos)


def test_indice_literal_fora_dos_limites_da_aviso():
    avisos = _avisos("""
        algoritmo "T"
        inicio
            v:inteiro[3] = {1, 2, 3}
            escrever(v[5])
    """)
    assert any("fora dos limites" in a.mensagem for a in avisos)


def test_indice_literal_dentro_dos_limites_nao_da_aviso():
    avisos = _avisos("""
        algoritmo "T"
        inicio
            v:inteiro[3] = {1, 2, 3}
            escrever(v[2])
    """)
    assert not any("fora dos limites" in a.mensagem for a in avisos)


def test_indice_variavel_nao_da_aviso():
    """Só deteta o caso óbvio (índice literal); não tenta analisar valores
    de variáveis em tempo de execução."""
    avisos = _avisos("""
        algoritmo "T"
        inicio
            v:inteiro[3] = {1, 2, 3}
            i:inteiro = 5
            escrever(v[i])
    """)
    assert not any("fora dos limites" in a.mensagem for a in avisos)


def test_campo_em_falta_em_literal_de_estrutura_da_aviso():
    avisos = _avisos("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
            y:inteiro
        inicio
            p:Ponto = {x: 1}
            escrever(p.x, p.y)
    """)
    relevantes = [a for a in avisos if "não define o(s) campo(s)" in a.mensagem]
    assert len(relevantes) == 1
    assert "'y'" in relevantes[0].mensagem


def test_literal_de_estrutura_com_todos_os_campos_nao_da_aviso():
    avisos = _avisos("""
        algoritmo "T"
        estrutura Ponto
            x:inteiro
            y:inteiro
        inicio
            p:Ponto = {x: 1, y: 2}
            escrever(p.x, p.y)
    """)
    assert not any("não define o(s) campo(s)" in a.mensagem for a in avisos)


def test_comparacao_com_literal_nao_e_assinalada():
    """x == 5 -- um dos lados não é sequer uma variável simples (é um
    literal), por isso nunca pode ser tratado como 'a mesma variável'."""
    avisos = _avisos("""
        algoritmo "T"
        inicio
            x:inteiro = 5
            se x == 5 entao
                escrever("cinco")
    """)
    assert not any("sempre" in a.mensagem for a in avisos)


def test_ciclo_enquanto_bandeira_nunca_alterada_da_aviso():
    avisos = _avisos("""
        algoritmo "T"
        inicio
            continuar:booleano = verdadeiro
            enquanto continuar fazer
                escrever("ola")
    """)
    relevantes = [a for a in avisos if "nunca termina" in a.mensagem]
    assert len(relevantes) == 1
    assert "continuar" in relevantes[0].mensagem


def test_ciclo_faz_enquanto_bandeira_nunca_alterada_da_aviso():
    avisos = _avisos("""
        algoritmo "T"
        inicio
            continuar:booleano = verdadeiro
            fazer
                escrever("ola")
            enquanto continuar
    """)
    assert any("nunca termina" in a.mensagem and "continuar" in a.mensagem for a in avisos)


def test_ciclo_enquanto_bandeira_alterada_no_corpo_nao_da_aviso():
    avisos = _avisos("""
        algoritmo "T"
        inicio
            continuar:booleano = verdadeiro
            x:inteiro = 0
            enquanto continuar fazer
                x = x + 1
                se x > 10 entao
                    continuar = falso
    """)
    assert not any("nunca termina" in a.mensagem for a in avisos)


def test_ciclo_enquanto_bandeira_alterada_por_ler_no_corpo_nao_da_aviso():
    avisos = _avisos("""
        algoritmo "T"
        inicio
            continuar:booleano = verdadeiro
            enquanto continuar fazer
                ler(continuar)
    """)
    assert not any("nunca termina" in a.mensagem for a in avisos)


def test_ciclo_enquanto_bandeira_passada_a_chamada_nao_da_aviso():
    """A bandeira pode ser alterada dentro de uma chamada com um
    parâmetro 'ref' -- o linter não sabe se é 'ref' ou não, por isso
    prefere não avisar (falso negativo) a arriscar um falso positivo."""
    avisos = _avisos("""
        algoritmo "T"
        procedimento atualizar(ref c:booleano)
            c = falso
        inicio
            continuar:booleano = verdadeiro
            enquanto continuar fazer
                atualizar(continuar)
    """)
    assert not any("nunca termina" in a.mensagem for a in avisos)


def test_ciclo_enquanto_dentro_de_funcao_com_devolver_nao_da_aviso_de_bandeira():
    """Um 'devolver' algures no corpo já é uma forma válida de sair,
    mesmo sem a bandeira ser alterada -- não deve empilhar os dois
    avisos."""
    avisos = _avisos("""
        algoritmo "T"
        funcao f():inteiro
            continuar:booleano = verdadeiro
            enquanto continuar fazer
                devolver 1
            devolver 0
        inicio
            escrever(f())
    """)
    assert not any("nunca termina" in a.mensagem for a in avisos)


def test_recursao_sem_condicao_da_aviso():
    avisos = _avisos("""
        algoritmo "T"
        funcao f(n:inteiro):inteiro
            devolver f(n - 1)
        inicio
            escrever(f(5))
    """)
    relevantes = [a for a in avisos if "nunca termina" in a.mensagem]
    assert len(relevantes) == 1
    assert "'f'" in relevantes[0].mensagem


def test_recursao_com_caso_base_nao_da_aviso():
    avisos = _avisos("""
        algoritmo "T"
        funcao fatorial(n:inteiro):inteiro
            se n <= 1 entao
                devolver 1
            devolver n * fatorial(n - 1)
        inicio
            escrever(fatorial(5))
    """)
    assert not any("controlo de fluxo" in a.mensagem for a in avisos)


def test_procedimento_recursivo_sem_condicao_da_aviso():
    avisos = _avisos("""
        algoritmo "T"
        procedimento contar(n:inteiro)
            escrever(n)
            contar(n + 1)
        inicio
            contar(0)
    """)
    assert any("'contar'" in a.mensagem and "controlo de fluxo" in a.mensagem for a in avisos)


def test_comparacao_de_decimais_com_igualdade_da_aviso():
    avisos = _avisos("""
        algoritmo "T"
        inicio
            a:decimal = 0.1 + 0.2
            b:decimal = 0.3
            se a == b entao
                escrever("iguais")
    """)
    assert any("vírgula flutuante" in a.mensagem for a in avisos)


def test_comparacao_de_decimal_com_inteiro_nao_da_aviso_de_flutuante():
    avisos = _avisos("""
        algoritmo "T"
        inicio
            a:inteiro = 3
            b:inteiro = 3
            se a == b entao
                escrever("iguais")
    """)
    assert not any("vírgula flutuante" in a.mensagem for a in avisos)


def test_comparacao_da_mesma_variavel_decimal_nao_da_aviso_de_flutuante():
    """x == x já tem o aviso mais específico (comparação sempre
    verdadeira) -- não deve duplicar com o aviso de vírgula flutuante."""
    avisos = _avisos("""
        algoritmo "T"
        inicio
            a:decimal = 0.1
            se a == a entao
                escrever("iguais")
    """)
    assert not any("vírgula flutuante" in a.mensagem for a in avisos)
    assert any("sempre verdadeira" in a.mensagem for a in avisos)
