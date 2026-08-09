# -*- coding: utf-8 -*-
"""Política pedagógica: os parâmetros que definem QUANTO e COMO o
Alguem ajuda. É dados estruturados, não código -- por isso dá para
trocar de política só editando o config.json, sem tocar em nada mais,
e é o que permite comparar experimentalmente estratégias diferentes
(um dos objetivos da investigação: Configuração A/B/C do documento)."""
from dataclasses import dataclass


@dataclass
class PoliticaPedagogica:
    modo: str = "socratic"
    nivel_maximo_ajuda: int = 5
    permite_gerar_codigo: bool = False
    permite_solucoes_completas: bool = False
    prefere_perguntas: bool = True
    pistas_progressivas: bool = True
    usar_guardiao: bool = True

    def __post_init__(self):
        # AG-15: sem isto, um nivel_maximo_ajuda negativo ou acima do
        # topo da escada (7) passava sem erro -- e, no caso negativo,
        # excluía até o nível 0 (Autonomia) do prompt (AG-16), que se
        # resolve sozinho ao validar aqui.
        if not (0 <= self.nivel_maximo_ajuda <= 7):
            raise ValueError(
                f"nivel_maximo_ajuda tem de estar entre 0 e 7 (os níveis "
                f"da escada de ajuda), recebido: {self.nivel_maximo_ajuda}"
            )

    @classmethod
    def a_partir_de_dict(cls, dados: dict) -> "PoliticaPedagogica":
        """Constrói a política a partir do dicionário 'politica_pedagogica'
        do config.json. Campos em falta ficam com o valor por omissão
        (acima) -- um config.json pode indicar só o que quer mudar."""
        campos_validos = {f for f in cls.__dataclass_fields__}
        desconhecidos = set(dados) - campos_validos
        if desconhecidos:
            raise ValueError(
                f"'politica_pedagogica' no config.json tem campo(s) "
                f"desconhecido(s): {', '.join(sorted(desconhecidos))}. "
                f"Campos válidos: {', '.join(sorted(campos_validos))}."
            )
        return cls(**dados)
