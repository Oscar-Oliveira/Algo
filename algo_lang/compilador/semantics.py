# -*- coding: utf-8 -*-
"""Verificador de tipos em tempo de compilação para a linguagem ALGO."""

import keyword
import re

from . import ast_nodes as A
from .. import bibliotecas

NUMERICOS = {"inteiro", "decimal"}
TEXTUAIS = {"cadeia", "caracter"}
PRIMITIVOS = NUMERICOS | TEXTUAIS | {"booleano"}

# Nomes que o PRÓPRIO código gerado usa sem qualificação, fora de
# qualquer 'global' do estudante -- uma global com um destes nomes rebate
# o import/builtin correspondente no módulo Python gerado. 'sys'/'copy'
# vêm do cabeçalho do próprio codegen.py (CABECALHO_RUNTIME); 'print'/
# 'input' são builtins que o código gerado chama diretamente. Fixo,
# porque está sempre presente, independente de bibliotecas ALGO
# importadas (ver _nomes_importados_no_cabecalho para essas).
NOMES_RESERVADOS_CODEGEN = {"sys", "copy", "print", "input"}


def _nomes_importados_no_cabecalho(cabecalho):
    """Cada biblioteca pode injetar 'import X as Y' no seu próprio
    CABECALHO (ex.: matematica.py -> '_math'/'_random') -- extrai os
    aliases automaticamente em vez de manter uma lista fixa à parte, que
    ficaria desatualizada sempre que uma biblioteca nova precisasse do
    seu próprio import."""
    nomes = set()
    for linha in cabecalho.splitlines():
        m = re.match(r"^\s*import\s+([\w.]+)(?:\s+as\s+(\w+))?\s*$", linha)
        if m:
            nomes.add(m.group(2) or m.group(1).split(".")[0])
    return nomes


def _nomes_lidos_em_expr(expr, nomes, chamadas, aliases=None):
    """Percorre uma expressão recolhendo todo nome de variável LIDO
    (A.LValue.nome) em 'nomes', e todo nome de função/procedimento do
    PRÓPRIO ficheiro chamado em 'chamadas' -- usado por
    _globais_lidas_transitivamente para saber que globais o CORPO de uma
    função lê, direta ou indiretamente. Uma chamada sem '.' é sempre do
    próprio ficheiro. Uma chamada 'alias.metodo' de um 'incluir ... como
    alias' TAMBÉM é (é uma função ALGO normal, só com nome mangled) --
    'aliases' (self.aliases_inclusao, alias -> {metodo: nome_mangled})
    resolve-a para essa chave em self.funcoes; None ou alias
    desconhecido (biblioteca real, nunca lê globais ALGO) não entra em
    'chamadas'. Espelha a forma de despacho já usada em
    codegen.py/tools/linter.py, mas não pode importar de tools/ (ver
    ARCH-02)."""
    if expr is None:
        return
    if isinstance(expr, A.LValue):
        nomes.add(expr.nome)
        for tag, valor in expr.acessos:
            if tag == "indice":
                _nomes_lidos_em_expr(valor, nomes, chamadas, aliases)
    elif isinstance(expr, A.BinOp):
        _nomes_lidos_em_expr(expr.esq, nomes, chamadas, aliases)
        _nomes_lidos_em_expr(expr.dire, nomes, chamadas, aliases)
    elif isinstance(expr, A.UnOp):
        _nomes_lidos_em_expr(expr.operando, nomes, chamadas, aliases)
    elif isinstance(expr, A.Chamada):
        if "." not in expr.nome:
            chamadas.add(expr.nome)
        elif aliases:
            alias, metodo = expr.nome.split(".", 1)
            mapa = aliases.get(alias)
            if mapa and metodo in mapa:
                chamadas.add(mapa[metodo])
        for a in expr.args:
            _nomes_lidos_em_expr(a, nomes, chamadas, aliases)
        for tag, valor in expr.acessos:
            if tag == "indice":
                _nomes_lidos_em_expr(valor, nomes, chamadas, aliases)
    elif isinstance(expr, A.VetorLiteral):
        for e in expr.elementos:
            _nomes_lidos_em_expr(e, nomes, chamadas, aliases)
    elif isinstance(expr, A.EstruturaLiteral):
        for _nome, valor in expr.campos:
            _nomes_lidos_em_expr(valor, nomes, chamadas, aliases)
    # A.Literal: nada a fazer (não lê nenhum nome)


def _nomes_lidos_em_stmts(stmts, nomes, chamadas, aliases=None):
    """Mesma ideia que _nomes_lidos_em_expr, para uma lista de
    instruções (incluindo dentro de blocos aninhados, via
    A.subblocos)."""
    for s in stmts:
        if isinstance(s, A.Declaracao):
            _nomes_lidos_em_expr(s.inicial, nomes, chamadas, aliases)
            if s.dims:
                for dim in s.dims:
                    _nomes_lidos_em_expr(dim, nomes, chamadas, aliases)
        elif isinstance(s, A.Atribuicao):
            for tag, valor in s.alvo.acessos:
                if tag == "indice":
                    _nomes_lidos_em_expr(valor, nomes, chamadas, aliases)
            _nomes_lidos_em_expr(s.expr, nomes, chamadas, aliases)
        elif isinstance(s, A.Ler):
            for alvo in s.alvos:
                for tag, valor in alvo.acessos:
                    if tag == "indice":
                        _nomes_lidos_em_expr(valor, nomes, chamadas, aliases)
        elif isinstance(s, A.Escrever):
            for e in s.exprs:
                _nomes_lidos_em_expr(e, nomes, chamadas, aliases)
        elif isinstance(s, A.Se):
            for cond, _corpo in s.ramos:
                _nomes_lidos_em_expr(cond, nomes, chamadas, aliases)
        elif isinstance(s, A.Para):
            _nomes_lidos_em_expr(s.ini, nomes, chamadas, aliases)
            _nomes_lidos_em_expr(s.fim, nomes, chamadas, aliases)
            _nomes_lidos_em_expr(s.passo, nomes, chamadas, aliases)
        elif isinstance(s, A.Enquanto):
            _nomes_lidos_em_expr(s.condicao, nomes, chamadas, aliases)
        elif isinstance(s, A.FazEnquanto):
            _nomes_lidos_em_expr(s.condicao, nomes, chamadas, aliases)
        elif isinstance(s, A.Escolha):
            _nomes_lidos_em_expr(s.expr, nomes, chamadas, aliases)
            for valores, _corpo in s.casos:
                for v in valores:
                    _nomes_lidos_em_expr(v, nomes, chamadas, aliases)
        elif isinstance(s, A.Retornar):
            if s.expr is not None:
                _nomes_lidos_em_expr(s.expr, nomes, chamadas, aliases)
        elif isinstance(s, A.ChamadaStmt):
            _nomes_lidos_em_expr(s.chamada, nomes, chamadas, aliases)
        elif isinstance(s, A.Afirmar):
            _nomes_lidos_em_expr(s.condicao, nomes, chamadas, aliases)
            _nomes_lidos_em_expr(s.mensagem, nomes, chamadas, aliases)
        for bloco in A.subblocos(s):
            _nomes_lidos_em_stmts(bloco, nomes, chamadas, aliases)


class ErroSemantico(Exception):
    def __init__(self, mensagem, linha):
        super().__init__(f"Erro semântico na linha {linha}: {mensagem}")
        self.linha = linha


def verificar_nomes_python(programa):
    """As palavras-chave do ALGO (se, para, fazer...) não têm nada a ver
    com as do Python -- por isso um identificador como 'class' ou
    'import' é perfeitamente válido em ALGO, mas geraria Python
    sintaticamente inválido (a variável seria traduzida diretamente para
    o mesmo nome). Chamada por verificar() -- não é sobre tipos, é sobre
    o nome sequer poder existir em Python."""
    for nome, linha in A.coletar_identificadores(programa):
        if keyword.iskeyword(nome):
            raise ErroSemantico(
                f"'{nome}' não pode ser usado como nome -- é uma palavra "
                f"reservada do Python (a linguagem que o ALGO gera por trás), "
                f"mesmo não sendo uma palavra reservada do ALGO", linha)


class Escopo:
    """Escopo aninhado (bloco, função, ou nível de topo): nomes locais
    próprios, com fallback de LEITURA para o escopo pai (Escopo ou dict).

    'raiz_funcao' marca a fronteira de uma função/procedimento (ou do
    corpo principal): é seguro sombrear para lá dela porque corresponde
    a um 'def' Python à parte, com o seu próprio namespace. Um Escopo
    de bloco comum (corpo de 'se'/'para'/'enquanto'/...) não é fronteira,
    porque em Python if/for/while NÃO criam namespace novo -- por isso
    '_registar_decl' não deixa redeclarar um nome já ativo num bloco
    aninhado dentro da mesma função, só reaproveitar o nome depois de o
    bloco onde foi declarado ter terminado."""

    def __init__(self, pai, raiz_funcao=False):
        self.pai = pai
        self.raiz_funcao = raiz_funcao
        self.locais = {}

    def __contains__(self, nome):
        return nome in self.locais or nome in self.pai

    def __getitem__(self, nome):
        if nome in self.locais:
            return self.locais[nome]
        return self.pai[nome]

    def __setitem__(self, nome, valor):
        self.locais[nome] = valor


class VerificadorTipos:
    def __init__(self, programa: A.Programa):
        self.programa = programa
        self.registo_bibliotecas = bibliotecas.obter_registo()
        self.bibliotecas_importadas = {}   # nome_minusculo -> info do registo
        for imp in programa.importares:
            chave = imp.nome.lower()
            if chave not in self.registo_bibliotecas:
                disponiveis = ", ".join(sorted(self.registo_bibliotecas)) or "(nenhuma)"
                raise ErroSemantico(
                    f"biblioteca '{imp.nome}' não existe. Bibliotecas disponíveis: "
                    f"{disponiveis}", imp.linha)
            self.bibliotecas_importadas[chave] = self.registo_bibliotecas[chave]

        # alias (de 'incluir "x.algo" como alias') -> {metodo_original:
        # nome_mangled} -- já populado por inclusoes.mesclar_biblioteca_no_programa
        # antes de semantics.py correr; aqui só se valida que nenhum alias
        # colide com uma biblioteca importada (uma colisão com
        # função/estrutura/variável já é apanhada no próprio merge, contra
        # o nome MANGLED -- ver inclusoes.py).
        self.aliases_inclusao = programa.aliases_inclusao
        for inc in programa.inclusoes:
            if inc.como.lower() in self.bibliotecas_importadas:
                raise ErroSemantico(
                    f"'{inc.como}' já é o nome de uma biblioteca importada; escolhe "
                    f"outro alias em 'incluir \"{inc.caminho}\" como {inc.como}'",
                    inc.linha)

        # nome_python_gerado (ex.: "matematica_raiz") -> "biblioteca.metodo"
        # (ex.: "matematica.raiz"), só para bibliotecas importadas -- uma
        # função/estrutura/variável do estudante com o MESMO nome que o
        # nome Python interno de uma função de biblioteca sobrepunha-se-lhe
        # silenciosamente no código gerado (a definição do estudante vem
        # depois no ficheiro), sem nenhum erro a avisar.
        self.nomes_internos_bibliotecas = {
            f"{nome_biblioteca}_{metodo}": f"{nome_biblioteca}.{metodo}"
            for nome_biblioteca, info in self.bibliotecas_importadas.items()
            for metodo in info["funcoes"]
        }

        # Mesma ideia que 'nomes_internos_bibliotecas', mas para funções
        # incluídas com alias: 'alias_metodo' (nome Python mangled já
        # atribuído por inclusoes.py) -> "alias.metodo" (para a mensagem
        # de erro em '_verificar_nome_disponivel').
        self.nomes_internos_aliases = {
            nome_mangled: f"{alias}.{metodo_original}"
            for alias, mapa in self.aliases_inclusao.items()
            for metodo_original, nome_mangled in mapa.items()
        }

        # bugs #23/#27: nomes reservados pelo próprio código gerado --
        # ver NOMES_RESERVADOS_CODEGEN (sempre presentes) e
        # _nomes_importados_no_cabecalho (por biblioteca, só quando
        # importada).
        self.nomes_reservados_codegen = set(NOMES_RESERVADOS_CODEGEN)
        for info in self.bibliotecas_importadas.values():
            self.nomes_reservados_codegen |= _nomes_importados_no_cabecalho(info["cabecalho"])

        self.funcoes = {}
        for f in programa.funcoes:
            if f.nome in self.funcoes:
                raise ErroSemantico(f"'{f.nome}' já foi definido anteriormente", f.linha)
            if f.nome in PRIMITIVOS:
                raise ErroSemantico(
                    f"'{f.nome}' é o nome de um tipo primitivo; escolhe outro "
                    f"nome para a função/procedimento", f.linha)
            if f.nome.lower() in self.bibliotecas_importadas:
                raise ErroSemantico(
                    f"'{f.nome}' já é o nome de uma biblioteca importada; "
                    f"escolhe outro nome para a função/procedimento", f.linha)
            if f.nome in self.nomes_reservados_codegen:
                raise ErroSemantico(
                    f"'{f.nome}' colide com um nome interno usado pelo código "
                    f"gerado; escolhe outro nome para a função/procedimento", f.linha)
            if f.nome in self.nomes_internos_bibliotecas:
                raise ErroSemantico(
                    f"'{f.nome}' colide com o nome interno gerado para "
                    f"'{self.nomes_internos_bibliotecas[f.nome]}' (biblioteca "
                    f"importada); escolhe outro nome para a função/procedimento",
                    f.linha)
            self.funcoes[f.nome] = f

        # Nomes de topo do corpo principal (variáveis/constantes globais) --
        # calculado aqui porque as estruturas são registadas ANTES de
        # 'self.globais' existir (ver verificar(), mais abaixo), só para
        # dar uma mensagem dedicada em _validar_dims quando um campo de
        # vetor de 'estrutura' referencia um destes nomes.
        self._nomes_globais_top_level = {d.nome for d in programa.declaracoes}

        # Só as declarações de TOPO (antes de 'inicio') chegam a ser
        # globais -- usado por _globais_lidas_transitivamente para
        # distinguir "nome que nunca vai ser global" de "nome que VAI ser
        # global, mas ainda não está disponível aqui" (referência
        # antecipada entre declarações de topo fora de ordem).
        self._nomes_globais_eventuais = self._nomes_globais_top_level

        self.estruturas = {}   # nome_estrutura -> {campo: (tipo, dims, dims_exprs, por_referencia)}
        linhas_dos_campos = {}   # (nome_estrutura, nome_campo) -> linha (só para mensagens de erro)
        for e in programa.estruturas:
            if e.nome in self.estruturas:
                raise ErroSemantico(f"a estrutura '{e.nome}' já foi definida", e.linha)
            if e.nome in self.funcoes:
                raise ErroSemantico(
                    f"'{e.nome}' já é o nome de uma função/procedimento; escolhe "
                    f"outro nome para a estrutura", e.linha)
            if e.nome in PRIMITIVOS:
                raise ErroSemantico(
                    f"'{e.nome}' é o nome de um tipo primitivo; escolhe outro "
                    f"nome para a estrutura", e.linha)
            if e.nome.lower() in self.bibliotecas_importadas:
                raise ErroSemantico(
                    f"'{e.nome}' já é o nome de uma biblioteca importada; "
                    f"escolhe outro nome para a estrutura", e.linha)
            if e.nome in self.nomes_reservados_codegen:
                raise ErroSemantico(
                    f"'{e.nome}' colide com um nome interno usado pelo código "
                    f"gerado; escolhe outro nome para a estrutura", e.linha)
            if e.nome in self.nomes_internos_bibliotecas:
                raise ErroSemantico(
                    f"'{e.nome}' colide com o nome interno gerado para "
                    f"'{self.nomes_internos_bibliotecas[e.nome]}' (biblioteca "
                    f"importada); escolhe outro nome para a estrutura", e.linha)
            campos = {}
            for c in e.campos:
                if c.nome in campos:
                    raise ErroSemantico(
                        f"a estrutura '{e.nome}' tem o campo '{c.nome}' duplicado", c.linha)
                if c.inicial is not None:
                    raise ErroSemantico(
                        "os campos de uma estrutura não podem ter valor inicial", c.linha)
                if c.dims:
                    # _registar_decl já valida tipo/sinal de cada dimensão
                    # para variáveis normais -- o registo de campos de
                    # 'estrutura' precisa da mesma validação, mas sem
                    # escopo próprio (um campo de estrutura não vê
                    # variáveis nenhumas), só expressões resolúveis sem
                    # nomes fazem sentido aqui.
                    self._validar_dims(c.dims, {}, c.linha, contexto_campo=True)
                dims_n = 0 if c.dims is None else len(c.dims)
                campos[c.nome] = (c.tipo, dims_n, c.dims, c.por_referencia)
                linhas_dos_campos[(e.nome, c.nome)] = c.linha
            self.estruturas[e.nome] = campos

        # valida os tipos dos campos só depois de todas as estruturas estarem
        # registadas, para permitir referências cruzadas entre estruturas
        # (ex: 'estrutura A' pode ter um campo do tipo 'B', definida a seguir)
        for nome_estrutura, campos in self.estruturas.items():
            for nome_campo, (tipo, dims_n, _dims_exprs, por_referencia) in campos.items():
                if tipo not in PRIMITIVOS and tipo not in self.estruturas:
                    linha = linhas_dos_campos[(nome_estrutura, nome_campo)]
                    raise ErroSemantico(
                        f"o campo '{nome_campo}' da estrutura '{nome_estrutura}' tem tipo "
                        f"desconhecido '{tipo}'", linha)
                if por_referencia:
                    linha = linhas_dos_campos[(nome_estrutura, nome_campo)]
                    if tipo in PRIMITIVOS:
                        raise ErroSemantico(
                            f"o campo '{nome_campo}' da estrutura '{nome_estrutura}' é 'ref' "
                            f"mas '{tipo}' é um tipo primitivo; 'ref' só é permitido num campo "
                            f"cujo tipo seja outra 'estrutura'", linha)
                    if dims_n != 0:
                        raise ErroSemantico(
                            f"o campo '{nome_campo}' da estrutura '{nome_estrutura}' não pode "
                            f"ser 'ref' e vetor ao mesmo tempo", linha)

    def _validar_tipo(self, tipo, linha):
        if tipo in PRIMITIVOS:
            return
        if tipo in self.estruturas:
            return
        raise ErroSemantico(
            f"tipo '{tipo}' desconhecido (não é um tipo primitivo nem uma "
            f"estrutura definida com 'estrutura {tipo}')", linha)

    # ---------- ponto de entrada ----------
    def verificar(self):
        escopo_topo = {}
        for d in self.programa.declaracoes:
            self._registar_decl(escopo_topo, d)

        # tabela de globais visível às funções = só as declarações de
        # topo (antes de 'inicio') -- nada declarado dentro de 'inicio'
        # é visível a uma função, mesmo ao nível mais externo do bloco.
        self.globais = dict(escopo_topo)

        for f in self.programa.funcoes:
            self._verificar_funcao(f)

        self._verificar_bloco(self.programa.corpo, escopo_topo, ctx_funcao=None)

    # ---------- funções ----------
    def _verificar_funcao(self, f: A.FuncaoDef):
        escopo = Escopo(self.globais, raiz_funcao=True)
        for p in f.parametros:
            if p.nome in escopo.locais:
                raise ErroSemantico(f"parâmetro '{p.nome}' duplicado", f.linha)
            self._verificar_nome_disponivel(p.nome, f.linha, "o parâmetro")
            self._validar_tipo(p.tipo, f.linha)
            escopo.locais[p.nome] = (p.tipo, p.dims, False)
        if f.tipo_retorno is not None:
            self._validar_tipo(f.tipo_retorno, f.linha)

        self._verificar_bloco(f.corpo, escopo, ctx_funcao=f)

        if not f.eh_procedimento and not self._todos_caminhos_devolvem(f.corpo):
            raise ErroSemantico(
                f"a função '{f.nome}' declara devolver '{f.tipo_retorno}' mas nem "
                f"todos os caminhos terminam com 'retornar' (ex.: falta um 'senao', "
                f"ou um 'escolher' sem 'contrario') -- um caminho que chegue ao fim "
                f"sem retornar nada crasha em runtime", f.linha)

    def _todos_caminhos_devolvem(self, stmts):
        """Verificação CONSERVADORA de que todos os caminhos de execução
        do bloco terminam num 'retornar'. Percorre as instruções em
        ordem; basta UMA garantir sempre 'retornar' para o bloco inteiro
        garantir (tudo o que vier a seguir é código morto, já assinalado
        à parte pelo linter) -- por isso não olha só para a última
        instrução. Um 'se'
        conta só se tiver 'senao' e TODOS os ramos garantirem retornar
        (mesma regra para 'escolher'/'contrario'). Um 'faz...enquanto'
        conta se o corpo garantir (executa sempre pelo menos uma vez,
        antes de a condição sequer ser vista); um 'enquanto' só conta com
        condição literalmente 'verdadeiro'. É deliberadamente
        conservadora: pode recusar um programa correto num caso extremo
        não coberto aqui, mas nunca aceita um que tenha de facto um
        caminho sem 'retornar'.

        Um 'sair'/'continuar' NÃO É uma continuação sequencial normal: é
        um salto que pode abandonar o resto do corpo do ciclo sem nunca
        alcançar um 'retornar' irmão mais à frente na mesma lista. Por
        isso os dois ramos de ciclo abaixo só confiam na leitura
        sequencial do corpo quando não há nenhum 'sair'/'continuar'
        alcançável nele (ver _tem_sair_ou_continuar_alcancavel) -- sem
        isso, é conservadoramente tratado como não-garantido."""
        for s in stmts:
            if isinstance(s, A.Retornar):
                return True
            if isinstance(s, A.Se) and s.senao is not None:
                if (all(self._todos_caminhos_devolvem(corpo) for _cond, corpo in s.ramos)
                        and self._todos_caminhos_devolvem(s.senao)):
                    return True
            elif isinstance(s, A.Escolha) and s.contrario is not None:
                if (all(self._todos_caminhos_devolvem(corpo) for _valores, corpo in s.casos)
                        and self._todos_caminhos_devolvem(s.contrario)):
                    return True
            elif isinstance(s, A.FazEnquanto) \
                    and not self._tem_sair_ou_continuar_alcancavel(s.corpo) \
                    and self._todos_caminhos_devolvem(s.corpo):
                return True
            elif isinstance(s, A.Enquanto) and self._condicao_literalmente_verdadeira(s.condicao) \
                    and not self._tem_sair_ou_continuar_alcancavel(s.corpo) \
                    and self._todos_caminhos_devolvem(s.corpo):
                return True
        return False

    def _tem_sair_ou_continuar_alcancavel(self, stmts):
        """Verdade se 'stmts' contém um 'sair'/'continuar' alcançável,
        descendo em 'se'/'escolher' (todos os ramos) mas SEM entrar em
        'para'/'enquanto'/'fazer...enquanto' aninhados -- um 'sair'/
        'continuar' num ciclo interior só afeta esse ciclo interior, é
        irrelevante para o ciclo exterior que está a ser avaliado por
        _todos_caminhos_devolvem. Não pode reutilizar A.subblocos (essa
        travessia desce também em ciclos aninhados)."""
        for s in stmts:
            if isinstance(s, (A.Sair, A.Continuar)):
                return True
            if isinstance(s, A.Se):
                if any(self._tem_sair_ou_continuar_alcancavel(corpo) for _cond, corpo in s.ramos):
                    return True
                if s.senao is not None and self._tem_sair_ou_continuar_alcancavel(s.senao):
                    return True
            elif isinstance(s, A.Escolha):
                if any(self._tem_sair_ou_continuar_alcancavel(corpo) for _valores, corpo in s.casos):
                    return True
                if s.contrario is not None and self._tem_sair_ou_continuar_alcancavel(s.contrario):
                    return True
        return False

    def _condicao_literalmente_verdadeira(self, expr):
        return isinstance(expr, A.Literal) and expr.tipo == "booleano" and expr.valor is True

    # ---------- declarações ----------
    def _nome_ativo(self, escopo, nome):
        """Verifica se 'nome' já está em uso dentro do mesmo namespace
        Python (a função/procedimento atual, ou o corpo principal),
        incluindo qualquer bloco 'se'/'para'/'enquanto'/... ainda aberto
        à volta do ponto de declaração -- sem subir além dessa fronteira,
        para continuar a permitir que uma função sombreie uma global."""
        nivel = escopo
        while True:
            locais = nivel.locais if isinstance(nivel, Escopo) else nivel
            if nome in locais:
                return True
            if isinstance(nivel, Escopo) and not nivel.raiz_funcao:
                nivel = nivel.pai
                continue
            return False

    def _verificar_nome_disponivel(self, nome, linha, o_que_e):
        """Rejeita 'nome' se colidir com uma função/procedimento, estrutura,
        biblioteca importada, nome interno gerado para uma biblioteca, ou
        tipo primitivo. Partilhado entre _registar_decl (variáveis) e
        _verificar_funcao (parâmetros)."""
        if nome in self.funcoes:
            raise ErroSemantico(
                f"'{nome}' já é o nome de uma função/procedimento; escolhe "
                f"outro nome para {o_que_e}", linha)
        if nome in self.estruturas:
            raise ErroSemantico(
                f"'{nome}' já é o nome de uma estrutura; escolhe outro nome "
                f"para {o_que_e}", linha)
        if nome in self.bibliotecas_importadas:
            raise ErroSemantico(
                f"'{nome}' já é o nome de uma biblioteca importada; escolhe "
                f"outro nome para {o_que_e}", linha)
        if nome in self.aliases_inclusao:
            raise ErroSemantico(
                f"'{nome}' já é o alias de um 'incluir'; escolhe outro nome "
                f"para {o_que_e}", linha)
        if nome in self.nomes_reservados_codegen:
            raise ErroSemantico(
                f"'{nome}' colide com um nome interno usado pelo código "
                f"gerado; escolhe outro nome para {o_que_e}", linha)
        if nome in self.nomes_internos_bibliotecas:
            raise ErroSemantico(
                f"'{nome}' colide com o nome interno gerado para "
                f"'{self.nomes_internos_bibliotecas[nome]}' (biblioteca "
                f"importada); escolhe outro nome para {o_que_e}", linha)
        if nome in self.nomes_internos_aliases:
            raise ErroSemantico(
                f"'{nome}' colide com o nome interno gerado para "
                f"'{self.nomes_internos_aliases[nome]}' (função incluída "
                f"com alias); escolhe outro nome para {o_que_e}", linha)
        if nome in PRIMITIVOS:
            raise ErroSemantico(
                f"'{nome}' é o nome de um tipo primitivo; escolhe outro nome "
                f"para {o_que_e}", linha)

    def _resolver_nome_funcao_local(self, nome):
        """Traduz o nome de uma chamada (bare, ou 'alias.metodo' de um
        'incluir ... como alias') para a chave correspondente em
        self.funcoes -- devolve None para uma chamada de biblioteca
        verdadeira (nunca lê globais ALGO, ver _globais_lidas_
        transitivamente). Uma função incluída com alias É uma função
        ALGO normal do próprio ficheiro incluído, só com nome mangled."""
        if "." not in nome:
            return nome
        alias, metodo = nome.split(".", 1)
        mapa = self.aliases_inclusao.get(alias)
        if mapa and metodo in mapa:
            return mapa[metodo]
        return None

    def _globais_lidas_transitivamente(self, nome_funcao, vistas=None):
        """'_verificar_chamada' só valida os ARGUMENTOS de uma chamada
        contra o escopo no ponto da chamada -- nunca o que o CORPO da
        função chamada lê. '_verificar_funcao' verifica esse corpo, mas
        contra 'self.globais' (o conjunto COMPLETO, final, independente
        da ordem de declaração), por isso uma referência antecipada
        escondida dentro do corpo (ex.: 'funcao pegaB() retornar b'
        chamada antes de 'b' existir) precisa desta verificação separada.

        Devolve o conjunto de nomes que SÃO globais do programa (não
        locais/parâmetros da própria função) lidos pelo corpo de
        'nome_funcao', transitivamente através de chamadas a outras
        funções do próprio ficheiro (não bibliotecas, essas não leem
        globais ALGO). 'vistas' evita recursão infinita em chamadas
        (mútuas ou diretas) -- uma função já vista não é reprocessada,
        simplesmente já não pode contribuir NOVOS nomes que a primeira
        passagem não tenha encontrado."""
        if vistas is None:
            vistas = set()
        if nome_funcao in vistas:
            return set()
        vistas.add(nome_funcao)
        f_def = self.funcoes.get(nome_funcao)
        if f_def is None:  # pragma: no cover -- só chamado depois de confirmar que a função existe
            return set()
        nomes_lidos, chamadas = set(), set()
        _nomes_lidos_em_stmts(f_def.corpo, nomes_lidos, chamadas, self.aliases_inclusao)
        locais = {p.nome for p in f_def.parametros}
        locais_dict = {}
        A.coletar_declaracoes_tipadas(f_def.corpo, locais_dict)
        locais |= set(locais_dict)
        globais = {n for n in nomes_lidos if n not in locais and n in self._nomes_globais_eventuais}
        for chamada in chamadas:
            globais |= self._globais_lidas_transitivamente(chamada, vistas)
        return globais

    def _registar_decl(self, escopo, d: A.Declaracao):
        if self._nome_ativo(escopo, d.nome):
            raise ErroSemantico(f"a variável '{d.nome}' já foi declarada", d.linha)
        self._verificar_nome_disponivel(d.nome, d.linha, "a variável")
        self._validar_tipo(d.tipo, d.linha)
        if d.eh_constante:
            if d.inicial is None:  # pragma: no cover -- o parser já exige '=' em 'constante'
                raise ErroSemantico(
                    f"a constante '{d.nome}' tem de ser inicializada com um valor", d.linha)
            if d.dims is not None:  # pragma: no cover -- 'constante' não tem sintaxe de vetor no parser
                raise ErroSemantico("uma constante não pode ser um vetor", d.linha)
        if d.dims:
            self._validar_dims(d.dims, escopo, d.linha)
        if d.inicial is not None:
            if isinstance(d.inicial, A.VetorLiteral):
                # O parser já não sabe se 'd' é um vetor -- este caso
                # (ex.: "x:inteiro = {1,2,3}") é genuinamente possível e
                # tem de ser apanhado aqui.
                if d.dims is None:
                    raise ErroSemantico(
                        f"'{d.nome}' não é um vetor; não pode ser inicializado com {{...}}",
                        d.linha)
                self._verificar_vetor_literal(d.inicial, d.tipo, d.dims, escopo)
            elif isinstance(d.inicial, A.EstruturaLiteral):
                if d.dims is not None:
                    if d.inicial.campos:
                        raise ErroSemantico(
                            f"'{d.nome}' é um vetor; usa '{{valor, valor, ...}}' para o "
                            f"inicializar, não '{{campo: valor}}'", d.linha)
                    # '{}' vazio é sintaticamente ambíguo entre "struct
                    # vazia" e "vetor vazio" -- o parser não sabe (nem
                    # deve saber) as dimensões do alvo neste ponto. Aqui
                    # já sabemos que o alvo é um vetor, por isso um '{}'
                    # vazio é aceite como um vetor literal sem elementos.
                else:
                    self._verificar_estrutura_literal(d.inicial, d.tipo, escopo)
            elif isinstance(d.inicial, A.Chamada):
                # Ramo unificado para QUALQUER chamada (com ou sem 'ref',
                # incluindo funções de biblioteca) como valor inicial --
                # chama-se _verificar_chamada diretamente em vez de passar
                # por _tipo_expr porque uma chamada com 'ref' não pode ser
                # usada "dentro de uma expressão" (_tipo_expr rejeita-a
                # explicitamente), mas aqui é a própria instrução de
                # declaração, não uma subexpressão.
                tipo_inicial = self._verificar_chamada(d.inicial, escopo)
                if tipo_inicial is None:
                    raise ErroSemantico(
                        f"'{d.inicial.nome}' é um procedimento e não devolve valor", d.linha)
                nome_funcao_local = self._resolver_nome_funcao_local(d.inicial.nome)
                if nome_funcao_local is not None:
                    # Só funções do PRÓPRIO ficheiro, incluindo as
                    # incluídas com alias (não bibliotecas verdadeiras)
                    # podem ler uma global ALGO -- ver
                    # _globais_lidas_transitivamente.
                    for nome_global in sorted(self._globais_lidas_transitivamente(nome_funcao_local)):
                        if nome_global not in escopo:
                            raise ErroSemantico(
                                f"'{d.inicial.nome}' lê a variável global '{nome_global}', que "
                                f"só é declarada mais tarde no programa -- move a declaração de "
                                f"'{nome_global}' para antes desta linha, ou a de '{d.nome}' "
                                f"para depois", d.linha)
                dims_n = 0 if d.dims is None else len(d.dims)
                dims_inicial = self._dims_retorno_de_chamada(d.inicial)
                tipo_inicial, dims_inicial, _ = self._percorrer_acessos(
                    tipo_inicial, dims_inicial, d.inicial.acessos,
                    f"{d.inicial.nome}(...)", d.inicial.linha, escopo)
                if dims_inicial != dims_n:
                    # Mesmo gate "dimensões antes de tipo" usado em
                    # _verificar_chamada/'retornar' -- sem ele um vetor
                    # podia inicializar em silêncio uma variável escalar
                    # (ou vice-versa), partilhando o mesmo 'tipo' ignorando
                    # dims.
                    raise ErroSemantico(
                        f"não é possível inicializar '{d.nome}' "
                        f"({self._descricao_dims(dims_n)}) com "
                        f"{self._descricao_dims(dims_inicial)}", d.linha)
                if dims_n > 0:
                    if tipo_inicial != d.tipo:
                        raise ErroSemantico(
                            f"'{d.nome}' é um vetor de '{d.tipo}' mas está a ser "
                            f"inicializado com um vetor de '{tipo_inicial}' -- vetores "
                            f"não são alargados/estreitados automaticamente, o tipo "
                            f"do elemento tem de ser exatamente igual", d.linha)
                elif not self._compativel(d.tipo, tipo_inicial):
                    raise ErroSemantico(
                        f"não é possível inicializar '{d.nome}' (tipo '{d.tipo}') com um "
                        f"valor do tipo '{tipo_inicial}'", d.linha)
                # Ao contrário do caminho normal de _tipo_expr, este ramo
                # precisa de marcar _tipo_inferido explicitamente --
                # codegen.py:_coagir_decimal depende dele para saber se tem
                # de gerar float(...) no valor de retorno.
                d.inicial._tipo_inferido = tipo_inicial
            else:
                tipo_inicial, _ = self._tipo_expr(d.inicial, escopo)
                if not self._compativel(d.tipo, tipo_inicial):
                    raise ErroSemantico(
                        f"não é possível inicializar '{d.nome}' (tipo '{d.tipo}') com um "
                        f"valor do tipo '{tipo_inicial}'", d.linha)
        dims_n = 0 if d.dims is None else len(d.dims)
        # Guarda o valor resolvido de uma 'constante' inteira escalar
        # (None para tudo o resto) na própria entrada do escopo, para
        # _resolver_constante conseguir "dobrar" uma referência a esta
        # constante quando outra declaração a usar como tamanho de vetor
        # (ex.: 'v:inteiro[N]') ou noutra constante (ex.: 'M = N + 1').
        valor_resolvido = None
        if d.eh_constante and d.tipo == "inteiro" and dims_n == 0:
            valor_resolvido = self._resolver_constante(d.inicial, escopo)
        escopo[d.nome] = (d.tipo, dims_n, d.eh_constante, valor_resolvido)

    def _resolver_constante(self, expr, escopo):
        """'constante N:inteiro = 5' usada como 'v:inteiro[N]' é
        internamente uma referência a variável (A.LValue), não um
        A.Literal, apesar de ser tão previsível em compilação como o
        literal '5' -- mas _valor_literal_negativo/_tamanho_estatico
        (e as suas cópias em tools/linter.py) só reconhecem A.Literal,
        por isso ficam cegas a 'constante' nessas verificações
        específicas de tamanho/limites.

        Devolve o valor inteiro estático de 'expr' se for um literal,
        OU uma referência (direta, ou através de '+'/'-'/'*'/'^', para
        cobrir 'M = N + 1' com 'N' também 'constante') a uma
        'constante' inteira já registada em 'escopo'. Devolve None se
        não for estaticamente resolúvel desta forma (variável normal,
        chamada, etc.)."""
        if isinstance(expr, A.Literal) and expr.tipo == "inteiro":
            return expr.valor
        if isinstance(expr, A.UnOp) and expr.op == "-":
            valor = self._resolver_constante(expr.operando, escopo)
            return None if valor is None else -valor
        if isinstance(expr, A.BinOp) and expr.op in ("+", "-", "*"):
            esq = self._resolver_constante(expr.esq, escopo)
            dire = self._resolver_constante(expr.dire, escopo)
            if esq is None or dire is None:
                return None
            return {"+": esq + dire, "-": esq - dire, "*": esq * dire}[expr.op]
        if isinstance(expr, A.BinOp) and expr.op == "^":
            esq = self._resolver_constante(expr.esq, escopo)
            dire = self._resolver_constante(expr.dire, escopo)
            if esq is None or dire is None or dire < 0:
                # Expoente negativo dobraria para um valor não-inteiro
                # (fracionário) -- fora do que esta função promete devolver.
                return None
            return esq ** dire
        if isinstance(expr, A.LValue) and not expr.acessos and expr.nome in escopo:
            entrada = escopo[expr.nome]
            if len(entrada) > 3:
                return entrada[3]
        return None

    def _validar_dims(self, dims, escopo, linha, contexto_campo=False):
        """Valida cada expressão de dimensão de um vetor: tem de ser
        inteira e não pode ser um literal negativo. Partilhado entre
        declarações normais (com escopo real) e campos de 'estrutura'
        (com escopo vazio -- um campo não vê variáveis).

        'contexto_campo' (só True para o caso de 'estrutura') dá uma
        mensagem dedicada quando o nome referenciado é uma global do
        programa principal -- sem isto, a variável do 'escopo' vazio
        parecia "não declarada" (factualmente errado: está declarada, só
        não é visível aqui, porque as estruturas são registadas ANTES do
        resto do programa, incluindo constantes globais)."""
        for dim_expr in dims:
            if (contexto_campo and isinstance(dim_expr, A.LValue) and not dim_expr.acessos
                    and dim_expr.nome not in escopo and dim_expr.nome in self._nomes_globais_top_level):
                raise ErroSemantico(
                    f"'{dim_expr.nome}' é uma variável/constante do programa principal, "
                    f"mas o tamanho de um vetor-campo de 'estrutura' não pode "
                    f"referenciá-la -- estruturas são registadas antes do resto do "
                    f"programa, por isso nada aí é visível ainda; usa um valor literal",
                    dim_expr.linha)
            tipo, _ = self._tipo_expr(dim_expr, escopo)
            if tipo != "inteiro":
                raise ErroSemantico(
                    "o tamanho de um vetor tem de ser uma expressão inteira", linha)
            valor_literal = self._valor_literal_negativo(dim_expr)
            if valor_literal is None:
                # 'constante N:inteiro = -3; v:inteiro[N]' não é um
                # A.Literal negativo (é uma referência a 'N'), mas é tão
                # previsível em compilação como o literal '-3'.
                valor_resolvido = self._resolver_constante(dim_expr, escopo)
                if valor_resolvido is not None and valor_resolvido < 0:
                    valor_literal = valor_resolvido
            if valor_literal is not None:
                raise ErroSemantico(
                    f"o tamanho de um vetor não pode ser negativo (é {valor_literal})",
                    dim_expr.linha)

    def _valor_literal_negativo(self, expr):
        """Devolve o valor se 'expr' for um literal negativo -- reconhece
        tanto um Literal já negativo como (o caso mais comum, já que o
        lexer nunca produz um número negativo) UnOp('-', Literal(N)).
        Devolve None se não for um literal negativo reconhecível."""
        if isinstance(expr, A.Literal) and isinstance(expr.valor, (int, float)) and expr.valor < 0:  # pragma: no cover -- o lexer nunca produz um Literal já negativo (ver UnOp abaixo)
            return expr.valor
        if isinstance(expr, A.UnOp) and expr.op == "-" and isinstance(expr.operando, A.Literal):
            return -expr.operando.valor
        return None

    def _chave_valor_caso(self, v):
        """Devolve uma chave normalizada (para deteção de 'caso'
        duplicado num 'escolher') se 'v' for um valor estático
        reconhecível, ou None se não for. Reconhece tanto A.Literal como
        um literal numérico negado ('caso -1'), que o parser produz como
        UnOp('-', Literal(1)) já que o lexer nunca produz um Literal já
        negativo (mesma forma que _valor_literal_negativo reconhece) --
        sem isto, 'caso -1' repetido duas vezes não era detetado como
        código morto, ao contrário de 'caso 1' repetido. A chave
        normaliza por FAMÍLIA de tipo, não pelo tipo exato -- 'caso "a"'
        e 'caso \'a\'' (cadeia vs caracter), ou 'caso 1' e 'caso 1.0'
        (inteiro vs decimal), são o MESMO valor em runtime (Python:
        "a" == 'a' e 1 == 1.0)."""
        if (isinstance(v, A.UnOp) and v.op == "-" and isinstance(v.operando, A.Literal)
                and v.operando.tipo in NUMERICOS):
            tipo, valor = v.operando.tipo, -v.operando.valor
        elif isinstance(v, A.Literal):
            tipo, valor = v.tipo, v.valor
        else:
            return None
        if tipo in NUMERICOS:
            return ("numero", valor)
        if tipo in TEXTUAIS:
            return ("texto", valor)
        return (tipo, valor)

    def _verificar_estrutura_literal(self, lit: A.EstruturaLiteral, tipo_esperado, escopo):
        if tipo_esperado not in self.estruturas:
            raise ErroSemantico(
                f"'{{campo: valor, ...}}' só pode inicializar uma estrutura; "
                f"'{tipo_esperado}' não é uma estrutura", lit.linha)
        campos_da_estrutura = self.estruturas[tipo_esperado]
        vistos = set()
        for nome_campo, expr in lit.campos:
            if nome_campo in vistos:
                raise ErroSemantico(
                    f"campo '{nome_campo}' repetido no literal de '{tipo_esperado}'",
                    lit.linha)
            vistos.add(nome_campo)
            if nome_campo not in campos_da_estrutura:
                disponiveis = ", ".join(sorted(campos_da_estrutura))
                raise ErroSemantico(
                    f"a estrutura '{tipo_esperado}' não tem nenhum campo '{nome_campo}'. "
                    f"Campos disponíveis: {disponiveis}", lit.linha)
            tipo_campo, dims_campo, dims_campo_exprs, _por_referencia = campos_da_estrutura[nome_campo]
            if isinstance(expr, A.VetorLiteral):
                if dims_campo == 0:
                    raise ErroSemantico(
                        f"o campo '{nome_campo}' não é um vetor; não pode ser "
                        f"inicializado com '{{...}}'", lit.linha)
                self._verificar_vetor_literal(expr, tipo_campo, dims_campo_exprs, escopo)
                continue
            if dims_campo > 0:
                raise ErroSemantico(
                    f"o campo '{nome_campo}' é um vetor; inicializa-o com "
                    f"'{{valor, valor, ...}}'", lit.linha)
            if isinstance(expr, A.EstruturaLiteral):
                # Um literal '{...}' aninhado dentro doutro literal de
                # estrutura -- o tipo esperado (tipo_campo) já é conhecido
                # pelo contexto, por isso dá para validar recursivamente
                # em vez de cair em _tipo_expr(), que rejeita SEMPRE um
                # '{...}' sem tipo próprio.
                self._verificar_estrutura_literal(expr, tipo_campo, escopo)
                continue
            tipo_valor, _ = self._tipo_expr(expr, escopo)
            if not self._compativel(tipo_campo, tipo_valor):
                raise ErroSemantico(
                    f"o campo '{nome_campo}' de '{tipo_esperado}' espera '{tipo_campo}' "
                    f"mas recebeu '{tipo_valor}'", lit.linha)

    def _tamanho_estatico(self, dim_expr, escopo):
        """Devolve o tamanho declarado de uma dimensão se for um literal
        inteiro estático; None se for uma expressão dinâmica (variável,
        chamada, etc.). Também resolve uma referência a 'constante' (ver
        _resolver_constante) -- 'dim_expr' pode ser None (vetor de
        tamanho não-estático vindo de um parâmetro, ver
        _verificar_vetor_literal)."""
        if isinstance(dim_expr, A.Literal) and dim_expr.tipo == "inteiro":
            return dim_expr.valor
        return self._resolver_constante(dim_expr, escopo)

    def _verificar_vetor_literal(self, lit: A.VetorLiteral, tipo_elemento, dims, escopo):
        # O parser não sabe de antemão quantas dimensões esperar
        # (_parse_literal_chaveta é genérico), por isso estas duas
        # verificações de forma são o único sítio que as apanha. 'dims'
        # (lista de expressões de dimensão, não só a contagem) permite
        # validar o TAMANHO de cada nível quando é um literal estático,
        # não só a profundidade de aninhamento.
        tam_esperado = self._tamanho_estatico(dims[0], escopo)
        if tam_esperado is not None and len(lit.elementos) != tam_esperado:
            raise ErroSemantico(
                f"o vetor tem tamanho declarado {tam_esperado} mas o literal "
                f"'{{...}}' tem {len(lit.elementos)} elemento(s)", lit.linha)
        for elem in lit.elementos:
            if len(dims) > 1:
                if not isinstance(elem, A.VetorLiteral):
                    raise ErroSemantico(
                        f"esperava-se uma lista aninhada {{...}} (o vetor tem "
                        f"{len(dims)} dimensões)", lit.linha)
                self._verificar_vetor_literal(elem, tipo_elemento, dims[1:], escopo)
            else:
                if isinstance(elem, A.VetorLiteral):
                    raise ErroSemantico(
                        "demasiados níveis de aninhamento em {...} para as dimensões "
                        "declaradas", lit.linha)
                if isinstance(elem, A.EstruturaLiteral):
                    # Elemento de vetor que é ele próprio um literal de
                    # estrutura (ex.: vetor de estruturas) -- mesma lógica
                    # do campo aninhado, acima.
                    self._verificar_estrutura_literal(elem, tipo_elemento, escopo)
                    continue
                tipo_elem, _ = self._tipo_expr(elem, escopo)
                if not self._compativel(tipo_elemento, tipo_elem):
                    raise ErroSemantico(
                        f"elemento do vetor é do tipo '{tipo_elem}', esperava-se "
                        f"'{tipo_elemento}'", lit.linha)

    # ---------- blocos / instruções ----------
    def _verificar_bloco(self, stmts, escopo, ctx_funcao, dentro_de_ciclo=False):
        for s in stmts:
            self._verificar_stmt(s, escopo, ctx_funcao, dentro_de_ciclo)

    def _tem_ref(self, chamada: A.Chamada):
        # Uma chamada de biblioteca verdadeira nunca tem 'ref' -- mas uma
        # função incluída com alias ('incluir "x.algo" como L') é uma
        # função ALGO normal e PODE ter, por isso resolve o alias antes
        # de decidir (ver _resolver_nome_funcao_local).
        nome_local = self._resolver_nome_funcao_local(chamada.nome)
        if nome_local is None:
            return False
        f_def = self.funcoes.get(nome_local)
        return f_def is not None and any(p.por_referencia for p in f_def.parametros)

    def _dims_retorno_de_chamada(self, chamada: A.Chamada):
        """Nº de dimensões do vetor devolvido por 'chamada' (0 para valor
        escalar ou procedimento). Uma função de biblioteca também pode
        devolver vetor (ex.: cadeia.dividir) -- indicado pelo 4º elemento
        opcional do tuplo em FUNCOES (ver bibliotecas/__init__.py);
        ausente/tuplo de 3 elementos significa escalar, como sempre."""
        if "." in chamada.nome:
            biblioteca, metodo = chamada.nome.split(".", 1)
            info = self.bibliotecas_importadas.get(biblioteca)
            entrada = info["funcoes"].get(metodo) if info else None
            if entrada is None:
                return 0
            return entrada[3] if len(entrada) > 3 else 0
        f_def = self.funcoes.get(chamada.nome)
        if f_def is None or f_def.eh_procedimento:
            return 0
        return f_def.dims_retorno

    @staticmethod
    def _descricao_dims(dims):
        return "um valor escalar" if dims == 0 else f"um vetor de {dims} dimensão(ões)"

    def _verificar_stmt(self, s, escopo, ctx_funcao, dentro_de_ciclo=False):
        if isinstance(s, A.Declaracao):
            self._registar_decl(escopo, s)

        elif isinstance(s, A.Atribuicao):
            self._verificar_nao_constante(s.alvo, escopo, "atribuir a")
            tipo_alvo, dims_alvo = self._tipo_lvalue(s.alvo, escopo)
            if dims_alvo > 0:
                raise ErroSemantico(
                    f"'{s.alvo.nome}' é um vetor; não pode ser atribuído "
                    f"diretamente (falta indexá-lo, ex: {s.alvo.nome}[i] = ...)",
                    s.linha)
            if isinstance(s.expr, A.Chamada) and self._tem_ref(s.expr):
                tipo_retorno = self._verificar_chamada(s.expr, escopo)
                if tipo_retorno is None:
                    raise ErroSemantico(
                        f"'{s.expr.nome}' é um procedimento e não devolve valor",
                        s.linha)
                # dims_alvo já é garantidamente 0 aqui (o vetor acima
                # rejeita reatribuição direta a um vetor inteiro) -- falta
                # só garantir que o LADO DIREITO também não é um vetor
                # (partilharia o mesmo 'tipo' que um escalar, ignorando
                # dims, se não fosse este gate).
                dims_retorno = self._dims_retorno_de_chamada(s.expr)
                tipo_retorno, dims_retorno, caminho = self._percorrer_acessos(
                    tipo_retorno, dims_retorno, s.expr.acessos, f"{s.expr.nome}(...)",
                    s.linha, escopo)
                if dims_retorno > 0:
                    raise ErroSemantico(
                        f"'{caminho}' devolve {self._descricao_dims(dims_retorno)} "
                        f"mas '{s.alvo.nome}' é {self._descricao_dims(dims_alvo)}",
                        s.linha)
                if not self._compativel(tipo_alvo, tipo_retorno):
                    raise ErroSemantico(
                        f"não é possível atribuir um valor do tipo '{tipo_retorno}' à "
                        f"variável '{s.alvo.nome}' (tipo '{tipo_alvo}')", s.linha)
                # Mesma lógica que a declaração, acima.
                s.expr._tipo_inferido = tipo_retorno
            elif isinstance(s.expr, A.EstruturaLiteral):
                # Mesma ideia que a declaração/argumento de chamada: um
                # literal de estrutura não tem tipo próprio, mas o tipo
                # esperado já é conhecido pelo contexto (o tipo já
                # declarado do alvo) -- sem este ramo, 'p = {x: 9}' falhava
                # com "não há informação suficiente" mesmo sabendo-se
                # exatamente que forma esperar.
                self._verificar_estrutura_literal(s.expr, tipo_alvo, escopo)
            else:
                tipo_expr, _ = self._tipo_expr(s.expr, escopo)
                if not self._compativel(tipo_alvo, tipo_expr):
                    raise ErroSemantico(
                        f"não é possível atribuir um valor do tipo '{tipo_expr}' à "
                        f"variável '{s.alvo.nome}' (tipo '{tipo_alvo}')", s.linha)

        elif isinstance(s, A.Ler):
            for alvo in s.alvos:
                self._verificar_nao_constante(alvo, escopo, "ler para")
                tipo_alvo, dims_alvo = self._tipo_lvalue(alvo, escopo)
                if dims_alvo > 0:
                    # Mesma verificação que a atribuição, acima.
                    raise ErroSemantico(
                        f"'{alvo.nome}' é um vetor; não pode ser o alvo direto "
                        f"de 'ler' (falta indexá-lo, ex: ler({alvo.nome}[i]))",
                        alvo.linha)
                if tipo_alvo not in PRIMITIVOS:
                    # 'ler' só sabe preencher um valor primitivo -- sem
                    # isto, 'ler(a)' com 'a' de tipo 'estrutura' compilava
                    # para o leitor de texto, transformando 'a'
                    # silenciosamente numa string.
                    raise ErroSemantico(
                        f"'{alvo.nome}' é do tipo '{tipo_alvo}'; 'ler' só pode "
                        f"preencher um valor de tipo primitivo (inteiro, decimal, "
                        f"booleano, cadeia ou caracter) -- lê os campos "
                        f"individualmente", alvo.linha)

        elif isinstance(s, A.Escrever):
            for e in s.exprs:
                tipo, _ = self._tipo_expr(e, escopo)
                if tipo in self.estruturas:
                    # Vetores já eram implicitamente rejeitados (via
                    # dims>0 de _tipo_expr), mas estruturas precisam da
                    # mesma verificação -- sem isto, 'escrever(p)' imprimia
                    # algo como "<__main__.Ponto object at 0x...>".
                    raise ErroSemantico(
                        f"não é possível escrever um valor do tipo '{tipo}' "
                        f"diretamente -- escreve os campos individualmente, "
                        f"ex: '{A.texto_expr(e)}.campo'", s.linha)

        elif isinstance(s, A.Se):
            for cond, corpo in s.ramos:
                tipo, _ = self._tipo_expr(cond, escopo)
                if tipo != "booleano":
                    raise ErroSemantico(
                        f"a condição de 'se' tem de ser booleana (é '{tipo}')",
                        getattr(cond, "linha", s.linha))
                self._verificar_bloco(corpo, Escopo(escopo), ctx_funcao, dentro_de_ciclo)
            if s.senao is not None:
                self._verificar_bloco(s.senao, Escopo(escopo), ctx_funcao, dentro_de_ciclo)

        elif isinstance(s, A.Para):
            escopo_corpo = Escopo(escopo)
            if s.var not in escopo:
                raise ErroSemantico(
                    f"a variável de controlo '{s.var}' do ciclo 'para' não foi "
                    f"declarada -- declara-a antes do ciclo, ex.: '{s.var}:inteiro'",
                    s.linha)
            if escopo[s.var][:2] != ("inteiro", 0):
                raise ErroSemantico(
                    f"a variável de controlo '{s.var}' do ciclo 'para' tem de ser "
                    f"inteiro", s.linha)
            if escopo[s.var][2]:
                raise ErroSemantico(
                    f"'{s.var}' é uma constante; não pode ser usada como variável "
                    f"de controlo de um ciclo 'para'", s.linha)
            for expr, rotulo in ((s.ini, "inicial"), (s.fim, "final")):
                tipo, _ = self._tipo_expr(expr, escopo_corpo)
                if tipo != "inteiro":
                    raise ErroSemantico(
                        f"o valor {rotulo} do ciclo 'para' tem de ser inteiro (é "
                        f"'{tipo}')", s.linha)
            if s.passo is not None:
                tipo, _ = self._tipo_expr(s.passo, escopo_corpo)
                if tipo != "inteiro":
                    raise ErroSemantico("o 'passo' do ciclo 'para' tem de ser inteiro", s.linha)
                if isinstance(s.passo, A.Literal) and s.passo.valor == 0:
                    raise ErroSemantico(
                        "o 'passo' de um ciclo 'para' não pode ser 0 (o ciclo nunca "
                        "avançaria)", s.passo.linha)
            self._verificar_bloco(s.corpo, escopo_corpo, ctx_funcao, dentro_de_ciclo=True)

        elif isinstance(s, A.Enquanto):
            tipo, _ = self._tipo_expr(s.condicao, escopo)
            if tipo != "booleano":
                raise ErroSemantico(
                    f"a condição de 'enquanto' tem de ser booleana (é '{tipo}')", s.linha)
            self._verificar_bloco(s.corpo, Escopo(escopo), ctx_funcao, dentro_de_ciclo=True)

        elif isinstance(s, A.FazEnquanto):
            escopo_corpo = Escopo(escopo)
            self._verificar_bloco(s.corpo, escopo_corpo, ctx_funcao, dentro_de_ciclo=True)
            tipo, _ = self._tipo_expr(s.condicao, escopo_corpo)
            if tipo != "booleano":
                raise ErroSemantico(
                    f"a condição de 'fazer...enquanto' tem de ser booleana (é "
                    f"'{tipo}')", s.linha)

        elif isinstance(s, A.Escolha):
            tipo_base, _ = self._tipo_expr(s.expr, escopo)
            valores_vistos = set()
            for valores, corpo in s.casos:
                for v in valores:
                    tipo_v, _ = self._tipo_expr(v, escopo)
                    if not self._tipos_comparaveis(tipo_base, tipo_v):
                        raise ErroSemantico(
                            f"o valor de 'caso' é do tipo '{tipo_v}', incompatível com "
                            f"'{tipo_base}' de 'escolher'", getattr(v, "linha", s.linha))
                    chave = self._chave_valor_caso(v)
                    if chave is not None:
                        # Um valor de 'caso' repetido faz o segundo ramo
                        # nunca ser alcançado. A chave normaliza por
                        # FAMÍLIA de tipo, não pelo tipo exato -- 'caso
                        # "a"' e 'caso \'a\'' (cadeia vs caracter), ou
                        # 'caso 1' e 'caso 1.0' (inteiro vs decimal), são
                        # o MESMO valor em runtime (Python: "a" == 'a' e
                        # 1 == 1.0) -- ver _chave_valor_caso.
                        if chave in valores_vistos:
                            raise ErroSemantico(
                                f"o valor '{A.texto_expr(v)}' já apareceu antes neste "
                                f"'escolher' -- este ramo nunca seria alcançado",
                                getattr(v, "linha", s.linha))
                        valores_vistos.add(chave)
                self._verificar_bloco(corpo, Escopo(escopo), ctx_funcao, dentro_de_ciclo)
            if s.contrario is not None:
                self._verificar_bloco(s.contrario, Escopo(escopo), ctx_funcao, dentro_de_ciclo)

        elif isinstance(s, A.Retornar):
            if ctx_funcao is None:
                raise ErroSemantico(
                    "'retornar' só pode ser usado dentro de uma função ou de um "
                    "procedimento", s.linha)
            if ctx_funcao.eh_procedimento:
                if s.expr is not None:
                    raise ErroSemantico(
                        f"o procedimento '{ctx_funcao.nome}' não devolve valor "
                        f"nenhum -- 'retornar' aqui serve só para sair mais cedo, "
                        f"sem expressão a seguir", s.linha)
                return
            if s.expr is None:
                raise ErroSemantico(
                    f"a função '{ctx_funcao.nome}' tem de retornar um valor do "
                    f"tipo '{ctx_funcao.tipo_retorno}' -- 'retornar' sem "
                    f"expressão só é válido dentro de um procedimento", s.linha)
            if isinstance(s.expr, A.VetorLiteral):
                self._verificar_vetor_literal(
                    s.expr, ctx_funcao.tipo_retorno, [None] * ctx_funcao.dims_retorno, escopo)
                tipo, dims = ctx_funcao.tipo_retorno, ctx_funcao.dims_retorno
            elif isinstance(s.expr, A.EstruturaLiteral):
                # Literal de estrutura devolvido diretamente -- o tipo já é
                # conhecido pelo contexto (o tipo de retorno declarado da
                # função), mesma ideia do ramo de A.VetorLiteral acima.
                self._verificar_estrutura_literal(s.expr, ctx_funcao.tipo_retorno, escopo)
                tipo, dims = ctx_funcao.tipo_retorno, 0
            else:
                tipo, dims = self._tipo_expr(s.expr, escopo, permitir_vetor=True)
            if dims != ctx_funcao.dims_retorno:
                # Mesmo gate "dimensões antes de tipo" de _verificar_chamada --
                # sem ele um vetor podia ser devolvido em silêncio onde se
                # espera um escalar, ou vice-versa.
                raise ErroSemantico(
                    f"a função '{ctx_funcao.nome}' devolve "
                    f"{self._descricao_dims(ctx_funcao.dims_retorno)} mas está a "
                    f"retornar {self._descricao_dims(dims)}", s.linha)
            if ctx_funcao.dims_retorno > 0:
                if tipo != ctx_funcao.tipo_retorno:
                    raise ErroSemantico(
                        f"a função '{ctx_funcao.nome}' devolve um vetor de "
                        f"'{ctx_funcao.tipo_retorno}' mas está a retornar um vetor de "
                        f"'{tipo}' -- vetores não são alargados/estreitados "
                        f"automaticamente, o tipo do elemento tem de ser exatamente "
                        f"igual", s.linha)
            elif not self._compativel(ctx_funcao.tipo_retorno, tipo):
                raise ErroSemantico(
                    f"a função '{ctx_funcao.nome}' devolve '{ctx_funcao.tipo_retorno}' "
                    f"mas está a retornar um valor do tipo '{tipo}'", s.linha)

        elif isinstance(s, A.ChamadaStmt):
            self._verificar_chamada(s.chamada, escopo)

        elif isinstance(s, A.Afirmar):
            tipo, _ = self._tipo_expr(s.condicao, escopo)
            if tipo != "booleano":
                raise ErroSemantico(
                    f"a condição de 'afirmar' tem de ser booleana (é '{tipo}')", s.linha)
            if s.mensagem is not None:
                tipo_msg, _ = self._tipo_expr(s.mensagem, escopo)
                if tipo_msg not in TEXTUAIS:
                    raise ErroSemantico(
                        f"a mensagem de 'afirmar' tem de ser texto (é '{tipo_msg}')", s.linha)

        elif isinstance(s, A.Sair):
            if not dentro_de_ciclo:
                raise ErroSemantico(
                    "'sair' só pode ser usado dentro de um ciclo "
                    "(enquanto/para/fazer...enquanto)", s.linha)

        elif isinstance(s, A.Continuar):
            if not dentro_de_ciclo:
                raise ErroSemantico(
                    "'continuar' só pode ser usado dentro de um ciclo "
                    "(enquanto/para/fazer...enquanto)", s.linha)

        else:  # pragma: no cover -- todos os tipos de instrução da AST são tratados acima
            raise ErroSemantico(f"instrução não reconhecida: {type(s).__name__}", getattr(s, "linha", 0))

    # ---------- expressões ----------
    def _verificar_nao_constante(self, lv: A.LValue, escopo, acao):
        if lv.nome in escopo and len(escopo[lv.nome]) > 2 and escopo[lv.nome][2]:
            raise ErroSemantico(
                f"não é possível {acao} '{lv.nome}': é uma constante", lv.linha)

    def _percorrer_acessos(self, tipo, dims, acessos, caminho, linha, escopo):
        """Aplica uma lista de acessos ('indice'/'campo') a partir de um
        (tipo, dims) inicial -- partilhado entre _tipo_lvalue (a partir de
        uma variável do escopo) e o ramo A.Chamada de _tipo_expr (a partir
        do TIPO/DIMS DEVOLVIDOS por uma chamada, ex.: 'cadeia.dividir(...)
        [0]'), já que indexar/aceder a um campo é validado da mesma forma
        nos dois casos. 'caminho' é o texto já acumulado (variável ou
        'nome(...)'), estendido a cada passo para as mensagens de erro
        referirem o campo/índice exato. Devolve (tipo, dims, caminho)
        finais."""
        for tag, valor in acessos:
            if tag == "indice":
                if dims <= 0:
                    if tipo in ("cadeia", "caracter"):
                        # Caso comum o suficiente (tentar 's[0]' para obter
                        # um caracter, como noutras linguagens) para merecer
                        # uma mensagem dedicada em vez da genérica de "não é
                        # um vetor" -- essa mensagem não diz o que fazer a
                        # seguir.
                        raise ErroSemantico(
                            f"'{caminho}' é do tipo '{tipo}'; não pode ser indexado "
                            f"com '[...]' -- usa 'cadeia.caracter({caminho}, indice)'",
                            linha)
                    raise ErroSemantico(
                        f"'{caminho}' não é um vetor; não pode ser indexado", linha)
                tipo_idx, _ = self._tipo_expr(valor, escopo)
                if tipo_idx != "inteiro":
                    raise ErroSemantico(
                        f"o índice de '{caminho}' tem de ser inteiro (é '{tipo_idx}')",
                        linha)
                dims -= 1
                caminho = f"{caminho}[{A.texto_expr(valor)}]"
            else:  # "campo"
                if dims > 0:
                    raise ErroSemantico(
                        f"'{caminho}' é um vetor; falta indexá-lo antes de aceder a "
                        f"'.{valor}'", linha)
                if tipo not in self.estruturas:
                    raise ErroSemantico(
                        f"'{tipo}' não é uma estrutura; não tem campo '{valor}'", linha)
                campos = self.estruturas[tipo]
                if valor not in campos:
                    disponiveis = ", ".join(sorted(campos))
                    raise ErroSemantico(
                        f"a estrutura '{tipo}' não tem nenhum campo '{valor}'. "
                        f"Campos disponíveis: {disponiveis}", linha)
                tipo, dims, _, _ = campos[valor]
                caminho = f"{caminho}.{valor}"
        return tipo, dims, caminho

    def _tipo_lvalue(self, lv: A.LValue, escopo):
        if lv.nome not in escopo:
            raise ErroSemantico(f"a variável '{lv.nome}' não foi declarada", lv.linha)
        tipo, dims = escopo[lv.nome][0], escopo[lv.nome][1]
        tipo, dims, _ = self._percorrer_acessos(
            tipo, dims, lv.acessos, lv.nome, lv.linha, escopo)
        return tipo, dims

    def _tipo_expr(self, expr, escopo, permitir_vetor=False):
        """Cada 'return' de sucesso também guarda o tipo em
        expr._tipo_inferido -- codegen.py reaproveita-o para decidir onde
        inserir coerções 'inteiro' -> 'decimal' (ex.: 'x: decimal = 5' ou
        devolver um inteiro de uma função 'decimal'), sem duplicar aqui
        toda a lógica de inferência de tipos.

        'permitir_vetor' (por omissão False) controla se um vetor "nu" (não
        indexado) é aceite como valor -- só os dois sítios legítimos disso
        (argumento de chamada, expressão de 'retornar') passam True; todos
        os outros contextos (aritmética, condições, escrever(), etc.)
        continuam a rejeitar um vetor nu com o erro de sempre."""
        if isinstance(expr, A.Literal):
            expr._tipo_inferido = expr.tipo
            return expr.tipo, 0
        if isinstance(expr, A.LValue):
            tipo, dims = self._tipo_lvalue(expr, escopo)
            if dims > 0 and not permitir_vetor:
                raise ErroSemantico(
                    f"'{expr.nome}' é um vetor; falta indexá-lo (ex: {expr.nome}[i])",
                    expr.linha)
            expr._tipo_inferido = tipo
            return tipo, dims
        if isinstance(expr, A.BinOp):
            tipo, dims = self._tipo_binop(expr, escopo)
            expr._tipo_inferido = tipo
            return tipo, dims
        if isinstance(expr, A.UnOp):
            tipo, _ = self._tipo_expr(expr.operando, escopo)
            if expr.op == "nao":
                if tipo != "booleano":
                    raise ErroSemantico(
                        f"'nao' só se aplica a valores booleanos (é '{tipo}')", expr.linha)
                expr._tipo_inferido = "booleano"
                return "booleano", 0
            if expr.op == "-":
                if tipo not in NUMERICOS:
                    raise ErroSemantico(
                        f"'-' unário só se aplica a números (é '{tipo}')", expr.linha)
                expr._tipo_inferido = tipo
                return tipo, 0
        if isinstance(expr, A.Chamada):
            if self._tem_ref(expr):
                raise ErroSemantico(
                    f"'{expr.nome}' tem parâmetros por referência e não pode ser "
                    f"usada dentro de uma expressão; usa-a como instrução, ex: "
                    f"'x = {expr.nome}(...)'", expr.linha)
            tipo_retorno = self._verificar_chamada(expr, escopo)
            if tipo_retorno is None:
                raise ErroSemantico(
                    f"'{expr.nome}' é um procedimento e não devolve valor; não pode "
                    f"ser usado dentro de uma expressão", expr.linha)
            dims_retorno = self._dims_retorno_de_chamada(expr)
            tipo_retorno, dims_retorno, caminho = self._percorrer_acessos(
                tipo_retorno, dims_retorno, expr.acessos, f"{expr.nome}(...)",
                expr.linha, escopo)
            if dims_retorno > 0 and not permitir_vetor:
                raise ErroSemantico(
                    f"'{caminho}' devolve um vetor; falta indexá-lo (ex: "
                    f"{caminho}[i])", expr.linha)
            expr._tipo_inferido = tipo_retorno
            return tipo_retorno, dims_retorno
        if isinstance(expr, (A.VetorLiteral, A.EstruturaLiteral)):
            # Um literal '{...}' não tem um tipo próprio -- só faz sentido
            # onde o tipo/forma esperado já é conhecido pelo contexto
            # (tratados antes de chegar aqui). Nas outras posições (ex.:
            # operando de '+', dentro de escrever(...)), não há
            # informação suficiente.
            raise ErroSemantico(
                "um literal '{...}' só pode ser usado para inicializar uma variável "
                "ou como argumento de uma função/procedimento com um parâmetro do "
                "tipo certo -- aqui não há informação suficiente para saber que "
                "forma se espera", expr.linha)
        raise ErroSemantico(  # pragma: no cover -- todos os tipos de expressão da AST são tratados acima
            f"expressão não reconhecida: {type(expr).__name__}", getattr(expr, "linha", 0))

    def _expoente_estaticamente_nao_negativo(self, expr, escopo) -> bool:
        """Um literal numérico não-negativo é seguro; qualquer outra
        expressão que _resolver_constante consiga "dobrar" em compilação
        (uma referência a 'constante' inteira, ou uma subexpressão só de
        literais/constantes com '+'/'-'/'*'/'^') também é segura se o
        valor resolvido não for negativo. Uma expressão com sinal
        genuinamente desconhecido em compilação (variável normal,
        chamada, etc.) não é considerada não-negativa."""
        valor = self._resolver_constante(expr, escopo)
        return valor is not None and valor >= 0

    def _tipo_binop(self, expr: A.BinOp, escopo):
        t_e, _ = self._tipo_expr(expr.esq, escopo)
        t_d, _ = self._tipo_expr(expr.dire, escopo)
        op = expr.op

        if op == "+":
            if t_e in NUMERICOS and t_d in NUMERICOS:
                return ("decimal" if "decimal" in (t_e, t_d) else "inteiro"), 0
            if t_e in TEXTUAIS and t_d in TEXTUAIS:
                return "cadeia", 0
            raise ErroSemantico(
                f"'+' só pode ser usado entre dois números (soma) ou entre dois "
                f"textos (concatenação) — tens '{t_e}' e '{t_d}'", expr.linha)

        if op in ("-", "*", "^"):
            if t_e not in NUMERICOS or t_d not in NUMERICOS:
                raise ErroSemantico(
                    f"o operador '{op}' só pode ser usado entre números (tens "
                    f"'{t_e}' e '{t_d}')", expr.linha)
            if "decimal" in (t_e, t_d):
                return "decimal", 0
            if op == "^" and not self._expoente_estaticamente_nao_negativo(expr.dire, escopo):
                # '**' do Python devolve float quando a base é int e o
                # expoente é negativo -- se não conseguimos provar em
                # compilação que o expoente nunca é negativo, o resultado
                # tem de ser tipado 'decimal', não 'inteiro'.
                return "decimal", 0
            return "inteiro", 0

        if op == "/":
            if t_e not in NUMERICOS or t_d not in NUMERICOS:
                raise ErroSemantico(
                    f"o operador '/' só pode ser usado entre números (tens "
                    f"'{t_e}' e '{t_d}')", expr.linha)
            return "decimal", 0

        if op in ("div", "mod"):
            if t_e != "inteiro" or t_d != "inteiro":
                raise ErroSemantico(
                    f"o operador '{op}' exige dois valores inteiros (tens "
                    f"'{t_e}' e '{t_d}')", expr.linha)
            return "inteiro", 0

        if op in ("==", "<>"):
            if not self._tipos_comparaveis(t_e, t_d):
                raise ErroSemantico(
                    f"não é possível comparar '{t_e}' com '{t_d}'", expr.linha)
            return "booleano", 0

        if op in ("<", ">", "<=", ">="):
            ambos_num = t_e in NUMERICOS and t_d in NUMERICOS
            ambos_texto = t_e in TEXTUAIS and t_d in TEXTUAIS
            if not (ambos_num or ambos_texto):
                raise ErroSemantico(
                    f"o operador '{op}' só pode ser usado entre números ou entre "
                    f"texto (tens '{t_e}' e '{t_d}')", expr.linha)
            return "booleano", 0

        if op in ("e", "ou"):
            if t_e != "booleano" or t_d != "booleano":
                raise ErroSemantico(
                    f"o operador '{op}' só pode ser usado entre valores booleanos "
                    f"(tens '{t_e}' e '{t_d}')", expr.linha)
            return "booleano", 0

        raise ErroSemantico(f"operador desconhecido '{op}'", expr.linha)  # pragma: no cover -- o parser só produz operadores conhecidos

    def _tipos_comparaveis(self, a, b):
        if a in NUMERICOS and b in NUMERICOS:
            return True
        if a in TEXTUAIS and b in TEXTUAIS:
            return True
        # 'nulo' compara-se com qualquer tipo de estrutura (ex.: 'enquanto
        # no <> nulo fazer ...', o idioma de PERCORRER uma lista ligada já
        # construída). Não confundir com "apontador mutável": 'estrutura'
        # copia sempre por valor, mesmo ao atribuir a um campo (ver
        # docs/manual/07-Estruturas.md, secção 7.5) -- este 'nulo' só
        # sustenta o percurso, não permite duas variáveis partilharem o
        # mesmo nó nem construir uma lista ligando/mutando nós já criados.
        if (a == "nulo" and b in self.estruturas) or (b == "nulo" and a in self.estruturas):
            return True
        return a == b

    def _compativel(self, tipo_alvo, tipo_valor):
        if tipo_alvo == tipo_valor:
            return True
        if tipo_alvo == "decimal" and tipo_valor == "inteiro":
            return True
        if tipo_alvo == "cadeia" and tipo_valor == "caracter":
            return True
        # 'nulo' é aceite em qualquer sítio que espere uma estrutura (campo,
        # declaração, parâmetro, retorno) -- é o valor que representa "esta
        # referência ainda não aponta para nenhuma instância".
        if tipo_valor == "nulo" and tipo_alvo in self.estruturas:
            return True
        return False

    # ---------- chamadas ----------
    def _acessos_ref_estaticos(self, arg: A.LValue):
        """Devolve (nome, acessos) para detetar aliasing de 'ref'.

        Devolve sempre os acessos completos; a decisão de "colidem ou
        não" fica em _caminhos_ref_colidem, que só desiste (não sabe)
        quando a AMBIGUIDADE está mesmo na comparação -- dois acessos por
        índice na MESMA profundidade (ex.: 'v[i]' vs 'v[j]') continuam
        por resolver, uma limitação conhecida (ver
        test_indices_diferentes_do_mesmo_vetor_por_referencia_continua_a_compilar)."""
        return (arg.nome, tuple(arg.acessos))

    def _caminhos_ref_colidem(self, acessos_a, acessos_b):
        """Verdade se dois caminhos de acesso (mesmo nome base) têm de
        apontar sempre para a mesma posição de memória -- um é prefixo
        do outro (incluindo iguais), com todos os acessos em comum
        sendo campos idênticos. Um caminho mais curto que termina antes
        do outro diverge sempre conta como colisão (a base inteira já
        cobre tudo o que vier a seguir, seja campo ou índice) -- só
        devolve False ("não sei") assim que a comparação, DENTRO do
        comprimento comum, cair sobre um acesso por índice."""
        for (tag_a, val_a), (tag_b, val_b) in zip(acessos_a, acessos_b):
            if tag_a == "indice" or tag_b == "indice":
                return False
            if val_a != val_b:
                return False
        return True

    def _verificar_chamada(self, chamada: A.Chamada, escopo):
        if "." in chamada.nome:
            biblioteca, metodo = chamada.nome.split(".", 1)
            if biblioteca in self.aliases_inclusao:
                mapa = self.aliases_inclusao[biblioteca]
                if metodo not in mapa:
                    disponiveis = ", ".join(sorted(mapa))
                    raise ErroSemantico(
                        f"'{biblioteca}' (inclusão) não tem nenhuma função '{metodo}'. "
                        f"Disponíveis: {disponiveis}", chamada.linha)
                f_def = self.funcoes[mapa[metodo]]
                return self._verificar_chamada_funcao_definida(f_def, chamada, escopo)
            if biblioteca not in self.bibliotecas_importadas:
                # 'p.campo(args)' (campo de estrutura chamado como se fosse
                # método) é sintaticamente indistinguível de uma chamada de
                # biblioteca -- o parser não tem informação de tipos para
                # saber a diferença. Antes de assumir "biblioteca não
                # importada" (mensagem enganadora quando 'biblioteca' é na
                # verdade uma variável declarada), verifica se é mesmo esse
                # caso e dá uma mensagem que aponta para a causa real.
                if biblioteca in escopo:
                    tipo_var = escopo[biblioteca][0]
                    if tipo_var in self.estruturas and metodo in self.estruturas[tipo_var]:
                        raise ErroSemantico(
                            f"'{metodo}' é um campo da estrutura '{tipo_var}', não uma "
                            f"função -- campos não podem ser chamados como "
                            f"'{biblioteca}.{metodo}(...)', só lidos ou atribuídos "
                            f"(ex.: '{biblioteca}.{metodo}')", chamada.linha)
                raise ErroSemantico(
                    f"a biblioteca '{biblioteca}' não foi importada — usa "
                    f"'importar {biblioteca.capitalize()}' no topo do ficheiro",
                    chamada.linha)
            info = self.bibliotecas_importadas[biblioteca]
            if metodo not in info["funcoes"]:
                disponiveis = ", ".join(sorted(info["funcoes"]))
                raise ErroSemantico(
                    f"'{biblioteca}' não tem nenhuma função '{metodo}'. Disponíveis: "
                    f"{disponiveis}", chamada.linha)
            categorias, tipo_retorno, _codigo = info["funcoes"][metodo][:3]
            if len(chamada.args) != len(categorias):
                raise ErroSemantico(
                    f"'{chamada.nome}' espera {len(categorias)} argumento(s), "
                    f"recebeu {len(chamada.args)}", chamada.linha)
            tipos_args = []
            for arg, categoria in zip(chamada.args, categorias):
                tipo, _ = self._tipo_expr(arg, escopo)
                tipos_args.append(tipo)
                if categoria == "numeric" and tipo not in NUMERICOS:
                    raise ErroSemantico(
                        f"'{chamada.nome}' espera um argumento numérico (é '{tipo}')",
                        chamada.linha)
                if categoria == "cadeia" and tipo not in TEXTUAIS:
                    raise ErroSemantico(
                        f"'{chamada.nome}' espera texto (é '{tipo}')", chamada.linha)
                if categoria == "inteiro" and tipo != "inteiro":
                    raise ErroSemantico(
                        f"'{chamada.nome}' espera um inteiro (é '{tipo}')", chamada.linha)
                if categoria == "caracter" and tipo != "caracter":
                    raise ErroSemantico(
                        f"'{chamada.nome}' espera um caracter (é '{tipo}')", chamada.linha)
                if categoria == "primitivo" and tipo not in PRIMITIVOS:
                    raise ErroSemantico(
                        f"'{chamada.nome}' espera um valor de tipo primitivo — inteiro, "
                        f"decimal, booleano, cadeia ou caracter (é '{tipo}')", chamada.linha)
            if tipo_retorno == "numeric":
                # Tipo de retorno "espelha" o do primeiro argumento
                # numérico (ex.: matematica.absoluto(inteiro) devolve
                # inteiro, não sempre decimal).
                tipo_retorno = tipos_args[0]
            return tipo_retorno

        f_def = self.funcoes.get(chamada.nome)
        if f_def is None:
            raise ErroSemantico(
                f"função ou procedimento '{chamada.nome}' não foi definido", chamada.linha)
        return self._verificar_chamada_funcao_definida(f_def, chamada, escopo)

    def _verificar_chamada_funcao_definida(self, f_def, chamada: A.Chamada, escopo):
        """Verifica os argumentos de uma chamada contra a definição 'f_def'
        já resolvida -- partilhado por uma chamada direta ('funcao(...)')
        e por uma chamada a uma função incluída com alias
        ('alias.funcao(...)'), que só diferem em COMO 'f_def' é
        encontrado (ver '_verificar_chamada')."""
        if len(chamada.args) != len(f_def.parametros):
            raise ErroSemantico(
                f"'{chamada.nome}' espera {len(f_def.parametros)} argumento(s), "
                f"recebeu {len(chamada.args)}", chamada.linha)
        refs_estaticos_usados = []
        for arg, p in zip(chamada.args, f_def.parametros):
            if p.por_referencia:
                if not isinstance(arg, A.LValue):
                    raise ErroSemantico(
                        f"o argumento para o parâmetro por referência '{p.nome}' tem "
                        f"de ser uma variável, um elemento de vetor ou um campo, não "
                        f"uma expressão calculada", chamada.linha)
                if arg.nome not in escopo:
                    raise ErroSemantico(
                        f"a variável '{arg.nome}' não foi declarada", chamada.linha)
                if len(escopo[arg.nome]) > 2 and escopo[arg.nome][2]:
                    raise ErroSemantico(
                        f"'{arg.nome}' é uma constante; não pode ser passada por "
                        f"referência ao parâmetro '{p.nome}'", chamada.linha)
                # Apanha tanto o mesmo caminho exato (a mesma variável
                # simples, ou o mesmo campo de estrutura) como um caminho
                # que é PREFIXO de outro (ex.: 'ref p' + 'ref p.x' -- a
                # estrutura inteira e um campo dela são sempre a mesma
                # posição de memória). 'v[i]' e 'v[j]' continuam por
                # resolver -- ver _caminhos_ref_colidem.
                nome_atual, acessos_atual = self._acessos_ref_estaticos(arg)
                for nome_anterior, acessos_anterior in refs_estaticos_usados:
                    if nome_anterior == nome_atual \
                            and self._caminhos_ref_colidem(acessos_anterior, acessos_atual):
                        raise ErroSemantico(
                            f"'{A.texto_expr(arg)}' é passado por referência mais do "
                            f"que uma vez na mesma chamada a '{chamada.nome}'",
                            chamada.linha)
                refs_estaticos_usados.append((nome_atual, acessos_atual))
            if isinstance(arg, A.EstruturaLiteral):
                # Um literal de estrutura não tem tipo próprio -- valida-se
                # diretamente contra o tipo do parâmetro (mesma lógica já
                # usada para o valor inicial de uma declaração). Um
                # parâmetro 'por_referencia' já teria sido rejeitado acima
                # (só aceita A.LValue), por isso chegar aqui implica sempre
                # um parâmetro por valor.
                self._verificar_estrutura_literal(arg, p.tipo, escopo)
                tipo, dims = p.tipo, 0
            elif isinstance(arg, A.VetorLiteral):
                # Mesma ideia para um literal de vetor ('{...}') passado
                # diretamente como argumento -- valida-se a FORMA contra as
                # dimensões do parâmetro (sem tamanho estático a verificar,
                # já que um parâmetro vetor aceita qualquer tamanho).
                self._verificar_vetor_literal(arg, p.tipo, [None] * p.dims, escopo)
                tipo, dims = p.tipo, p.dims
            else:
                tipo, dims = self._tipo_expr(arg, escopo, permitir_vetor=True)
            if dims != p.dims:
                # Tem de ser verificado ANTES de qualquer compatibilidade de
                # tipo: um vetor e um escalar podem partilhar o mesmo 'tipo'
                # (ex.: ambos "inteiro") ignorando dims -- sem este gate um
                # vetor inteiro seria aceite em silêncio onde se espera um
                # valor escalar, ou vice-versa.
                raise ErroSemantico(
                    f"o parâmetro '{p.nome}' de '{chamada.nome}' espera "
                    f"{self._descricao_dims(p.dims)} mas '{A.texto_expr(arg)}' é "
                    f"{self._descricao_dims(dims)}", chamada.linha)
            if p.dims > 0:
                # Parâmetro vetor: tipo do elemento exato, tanto por valor
                # como por referência -- uma só regra para vetores (ver
                # justificação do caso 'ref' logo abaixo; por valor segue a
                # mesma regra por simplicidade, para não haver coerção
                # elemento-a-elemento de um vetor inteiro).
                if tipo != p.tipo:
                    raise ErroSemantico(
                        f"o parâmetro '{p.nome}' de '{chamada.nome}' é um vetor de "
                        f"'{p.tipo}' mas '{A.texto_expr(arg)}' é um vetor de '{tipo}' "
                        f"-- vetores não são alargados/estreitados automaticamente, "
                        f"o tipo do elemento tem de ser exatamente igual",
                        chamada.linha)
            elif p.por_referencia:
                # Um parâmetro 'ref' devolve o seu valor final à variável
                # do CHAMADOR (ver codegen.py:_gerar_lista_args/out_vars)
                # -- ao contrário de um parâmetro por valor, aceitar aqui a
                # mesma compatibilidade "larga" (decimal aceita inteiro,
                # cadeia aceita caracter) deixaria a variável do chamador
                # com um valor de tipo MAIS LARGO do que o seu tipo
                # declarado. 'ref' exige o tipo exatamente igual.
                if tipo != p.tipo:
                    raise ErroSemantico(
                        f"o parâmetro '{p.nome}' de '{chamada.nome}' é por referência "
                        f"e espera exatamente '{p.tipo}', mas '{A.texto_expr(arg)}' é "
                        f"do tipo '{tipo}' -- por referência os tipos têm de ser "
                        f"exatamente iguais (não só compatíveis), porque o valor final "
                        f"é escrito de volta na variável do chamador", chamada.linha)
            elif not self._compativel(p.tipo, tipo):
                raise ErroSemantico(
                    f"o parâmetro '{p.nome}' de '{chamada.nome}' espera "
                    f"'{p.tipo}' mas recebeu '{tipo}'", chamada.linha)
        return None if f_def.eh_procedimento else f_def.tipo_retorno


def verificar(programa: A.Programa):
    verificar_nomes_python(programa)
    VerificadorTipos(programa).verificar()
