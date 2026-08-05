# -*- coding: utf-8 -*-
from .tutor import Alguem
from .politica_pedagogica import PoliticaPedagogica
from .guardiao import GuardiaoPedagogico, Classificacao
from .registador import Registador
from .identidade import obter_id_estudante

__all__ = [
    "Alguem", "PoliticaPedagogica", "GuardiaoPedagogico", "Classificacao",
    "Registador", "obter_id_estudante",
]
