# -*- coding: utf-8 -*-
import pytest

import limitador_registo as lr


def test_ip_nao_bloqueado_por_omissao():
    lr.verificar_bloqueado(lr.hash_ip("1.2.3.4"))  # não deve levantar


def test_bloqueia_apos_limiar_de_falhas():
    ip_hash = lr.hash_ip("1.2.3.4")
    for _ in range(lr.LIMIAR_TENTATIVAS):
        lr.registar_falha(ip_hash)
    with pytest.raises(lr.ErroLimiteRegisto, match="Demasiadas tentativas"):
        lr.verificar_bloqueado(ip_hash)


def test_ips_diferentes_sao_independentes():
    ip1 = lr.hash_ip("1.2.3.4")
    ip2 = lr.hash_ip("5.6.7.8")
    for _ in range(lr.LIMIAR_TENTATIVAS):
        lr.registar_falha(ip1)
    lr.verificar_bloqueado(ip2)  # não deve levantar


def test_limpar_repoe_o_contador():
    ip_hash = lr.hash_ip("1.2.3.4")
    for _ in range(lr.LIMIAR_TENTATIVAS - 1):
        lr.registar_falha(ip_hash)
    lr.limpar(ip_hash)
    for _ in range(lr.LIMIAR_TENTATIVAS - 1):
        lr.registar_falha(ip_hash)
    lr.verificar_bloqueado(ip_hash)  # ainda não atingiu o limiar outra vez, não deve levantar


@pytest.mark.parametrize("tentativas,minimo,maximo", [
    (15, 60, 60),
    (16, 120, 120),
    (25, 3600, 3600),
])
def test_duracao_do_bloqueio_cresce_ate_um_teto(tentativas, minimo, maximo):
    duracao = lr._duracao_bloqueio_segundos(tentativas)
    assert minimo <= duracao <= maximo


def test_hash_ip_e_deterministico_e_nao_reversivel():
    h1 = lr.hash_ip("1.2.3.4")
    h2 = lr.hash_ip("1.2.3.4")
    assert h1 == h2
    assert "1.2.3.4" not in h1
