# -*- coding: utf-8 -*-
"""Linter para a linguagem ALGO.

Ao contrário de semantics.py (que verifica se o programa é válido e
impede a compilação em caso de erro), o linter procura problemas que não
impedem a compilação mas que são provavelmente enganos do programador:
variáveis/parâmetros nunca usados, funções nunca chamadas, divisões por
zero óbvias, comparações sempre verdadeiras, e variáveis locais que
sombreiam uma variável global.
"""
import os

from ..compilador import ast_nodes as A


class Aviso:
    def __init__(self, mensagem, linha):
        self.mensagem = mensagem
        self.linha = linha

    def __str__(self):
        return f"linha {self.linha}: {self.mensagem}"


class Linter:
    def __init__(self, programa: A.Programa, codigo_fonte: str = None):
        self.programa = programa
        self.codigo_fonte = codigo_fonte
        self.avisos = []

    def analisar(self):
        self.avisos = []
        self._verificar_rotinas_nunca_chamadas()
        self._verificar_indentacao_consistente()
        self._verificar_inclusoes_duplicadas()
        self._verificar_importares_duplicados()
        self._verificar_casos_duplicados_em_escolha()
        self._verificar_resultado_de_funcao_descartado()
        self._verificar_campos_em_falta_em_literal_de_estrutura()

        nomes_globais = {d.nome for d in self.programa.declaracoes}
        nomes_globais |= self._nomes_declarados(self.programa.corpo)

        nomes_constantes = {d.nome for d in self.programa.declaracoes if d.eh_constante}
        nomes_constantes |= self._nomes_constantes_declaradas(self.programa.corpo)
        nomes_globais_mutaveis = nomes_globais - nomes_constantes

        arrays_globais = self._arrays_com_tamanho_literal(self.programa.declaracoes)

        self._verificar_variaveis_nao_usadas(self.programa.corpo, contexto="no programa principal")
        self._verificar_divisoes_e_comparacoes(self.programa.corpo)
        self._verificar_codigo_depois_de_devolver(self.programa.corpo)
        self._verificar_ciclo_verdadeiro_sem_saida(self.programa.corpo)
        self._verificar_indices_fora_dos_limites(self.programa.corpo, arrays_globais)

        for f in self.programa.funcoes:
            self._verificar_parametros_nao_usados(f)
            tipo = "procedimento" if f.eh_procedimento else "função"
            artigo = "no" if f.eh_procedimento else "na"
            self._verificar_variaveis_nao_usadas(
                f.corpo, contexto=f"{artigo} {tipo} '{f.nome}'")
            self._verificar_sombra_de_global(f, nomes_globais)
            self._verificar_uso_de_globais(f, nomes_globais_mutaveis)
            self._verificar_divisoes_e_comparacoes(f.corpo)
            self._verificar_atribuicao_a_parametro_por_valor(f)
            self._verificar_codigo_depois_de_devolver(f.corpo)
            self._verificar_ciclo_verdadeiro_sem_saida(f.corpo)
            self._verificar_indices_fora_dos_limites(f.corpo, arrays_globais)

        self.avisos.sort(key=lambda a: a.linha)
        return self.avisos

    # ---------- utilidades de percurso ----------
    def _nomes_declarados(self, stmts):
        nomes = set()
        for s in stmts:
            if isinstance(s, A.Declaracao):
                nomes.add(s.nome)
            for bloco in A.subblocos(s):
                nomes |= self._nomes_declarados(bloco)
        return nomes

    def _nomes_constantes_declaradas(self, stmts):
        nomes = set()
        for s in stmts:
            if isinstance(s, A.Declaracao) and s.eh_constante:
                nomes.add(s.nome)
            for bloco in A.subblocos(s):
                nomes |= self._nomes_constantes_declaradas(bloco)
        return nomes

    def _todas_as_stmts(self, stmts):
        """Devolve a lista achatada de todas as instruções, incluindo as
        que estão dentro de blocos aninhados (se/para/enquanto/escolher)."""
        todas = []
        for s in stmts:
            todas.append(s)
            for bloco in A.subblocos(s):
                todas.extend(self._todas_as_stmts(bloco))
        return todas

    def _extrair_lvalues(self, expr, destino):
        """Atalho: extrai só os nomes de variáveis (ignora chamadas)."""
        self._extrair_lvalues_e_chamadas(expr, destino, set())

    def _expressoes_lidas(self, s):
        """Expressões que a instrução 's' LÊ (não conta o nome de uma
        variável simples só porque está a ser atribuída)."""
        if isinstance(s, A.Declaracao):
            return [s.inicial] if s.inicial is not None else []
        if isinstance(s, A.Atribuicao):
            exprs = [s.expr]
            if s.alvo.acessos:
                # 'v[i] = ...' ou 'p.campo = ...' -- a base (v, p) tem de já
                # existir para isto fazer sentido, por isso conta como uso;
                # só 'x = ...' sem acessos é que NÃO conta (essa é a atribuição
                # simples que estamos mesmo a tentar detetar como não-lida)
                exprs.append(s.alvo)
            return exprs
        if isinstance(s, A.Ler):
            exprs = []
            for alvo in s.alvos:
                if alvo.acessos:
                    exprs.append(alvo)
            return exprs
        if isinstance(s, A.Escrever):
            return list(s.exprs)
        if isinstance(s, A.Se):
            return [cond for cond, _corpo in s.ramos]
        if isinstance(s, A.Para):
            exprs = [s.ini, s.fim]
            if s.passo is not None:
                exprs.append(s.passo)
            return exprs
        if isinstance(s, (A.Enquanto, A.FazEnquanto)):
            return [s.condicao]
        if isinstance(s, A.Escolha):
            exprs = [s.expr]
            for valores, _corpo in s.casos:
                exprs.extend(valores)
            return exprs
        if isinstance(s, A.Devolver):
            return [s.expr]
        if isinstance(s, A.ChamadaStmt):
            return [s.chamada]
        if isinstance(s, A.Afirmar):
            exprs = [s.condicao]
            if s.mensagem is not None:
                exprs.append(s.mensagem)
            return exprs
        return []  # pragma: no cover -- os 12 tipos de instrução da AST estão todos tratados acima

    # ---------- verificações ----------
    def _verificar_rotinas_nunca_chamadas(self):
        chamadas = set()
        for stmts in [self.programa.corpo] + [f.corpo for f in self.programa.funcoes]:
            for s in self._todas_as_stmts(stmts):
                nomes = set()
                for e in self._expressoes_lidas(s):
                    self._extrair_lvalues_e_chamadas(e, nomes, chamadas)
                if isinstance(s, A.ChamadaStmt):
                    self._extrair_lvalues_e_chamadas(s.chamada, set(), chamadas)
        for f in self.programa.funcoes:
            if f.nome not in chamadas:
                if f.eh_procedimento:
                    self.avisos.append(Aviso(
                        f"o procedimento '{f.nome}' nunca é chamado em lado nenhum do "
                        f"programa", f.linha))
                else:
                    self.avisos.append(Aviso(
                        f"a função '{f.nome}' nunca é chamada em lado nenhum do programa",
                        f.linha))

    def _extrair_lvalues_e_chamadas(self, expr, destino_vars, destino_chamadas):
        if expr is None:  # pragma: no cover -- nenhum chamador passa None (_expressoes_lidas nunca inclui None nas suas listas)
            return
        if isinstance(expr, A.LValue):
            destino_vars.add(expr.nome)
            for tag, valor in expr.acessos:
                if tag == "indice":
                    self._extrair_lvalues_e_chamadas(valor, destino_vars, destino_chamadas)
        elif isinstance(expr, A.BinOp):
            self._extrair_lvalues_e_chamadas(expr.esq, destino_vars, destino_chamadas)
            self._extrair_lvalues_e_chamadas(expr.dire, destino_vars, destino_chamadas)
        elif isinstance(expr, A.UnOp):
            self._extrair_lvalues_e_chamadas(expr.operando, destino_vars, destino_chamadas)
        elif isinstance(expr, A.Chamada):
            if "." not in expr.nome:
                destino_chamadas.add(expr.nome)
            for a in expr.args:
                self._extrair_lvalues_e_chamadas(a, destino_vars, destino_chamadas)
        elif isinstance(expr, A.ArrayLiteral):
            for e in expr.elementos:
                self._extrair_lvalues_e_chamadas(e, destino_vars, destino_chamadas)
        elif isinstance(expr, A.EstruturaLiteral):
            for _nome, valor in expr.campos:
                self._extrair_lvalues_e_chamadas(valor, destino_vars, destino_chamadas)

    def _verificar_variaveis_nao_usadas(self, corpo, contexto):
        declaradas = {}   # nome -> linha (só declarações explícitas, não variáveis de ciclo 'para')
        for s in self._todas_as_stmts(corpo):
            if isinstance(s, A.Declaracao):
                declaradas[s.nome] = s.linha

        usadas = set()
        for s in self._todas_as_stmts(corpo):
            for e in self._expressoes_lidas(s):
                self._extrair_lvalues(e, usadas)

        for nome, linha in declaradas.items():
            if nome not in usadas:
                self.avisos.append(Aviso(
                    f"a variável '{nome}' é declarada mas nunca é usada {contexto}",
                    linha))

    def _verificar_parametros_nao_usados(self, f: A.FuncaoDef):
        usadas = set()
        for s in self._todas_as_stmts(f.corpo):
            for e in self._expressoes_lidas(s):
                self._extrair_lvalues(e, usadas)
        for p in f.parametros:
            if p.nome not in usadas:
                self.avisos.append(Aviso(
                    f"o parâmetro '{p.nome}' de '{f.nome}' nunca é usado", f.linha))

    def _verificar_sombra_de_global(self, f: A.FuncaoDef, nomes_globais):
        for p in f.parametros:
            if p.nome in nomes_globais:
                self.avisos.append(Aviso(
                    f"o parâmetro '{p.nome}' de '{f.nome}' tem o mesmo nome de uma "
                    f"variável global -- dentro da função refere-se sempre ao parâmetro, "
                    f"nunca à global", f.linha))
        for s in self._todas_as_stmts(f.corpo):
            if isinstance(s, A.Declaracao) and s.nome in nomes_globais:
                self.avisos.append(Aviso(
                    f"a variável local '{s.nome}' tem o mesmo nome de uma variável "
                    f"global -- pode ser confuso", s.linha))

    def _verificar_uso_de_globais(self, f: A.FuncaoDef, nomes_globais_mutaveis):
        """Avisa quando uma função/procedimento acede diretamente a uma
        variável global MUTÁVEL, em vez de a receber como parâmetro --
        isto funciona (o âmbito da linguagem permite-o), mas torna a
        função mais difícil de perceber e reutilizar isoladamente.
        Constantes globais ficam de fora: são valores fixos, não estado
        escondido, por isso aceder-lhes diretamente não tem o mesmo
        problema (é o mesmo que usar math.PI numa linguagem real)."""
        nomes_locais = {p.nome for p in f.parametros}
        for s in self._todas_as_stmts(f.corpo):
            if isinstance(s, A.Declaracao):
                nomes_locais.add(s.nome)
            elif isinstance(s, A.Para):
                nomes_locais.add(s.var)

        usados = set()
        for s in self._todas_as_stmts(f.corpo):
            for e in self._expressoes_lidas(s):
                self._extrair_lvalues(e, usados)
            if isinstance(s, A.Atribuicao):
                usados.add(s.alvo.nome)
            elif isinstance(s, A.Ler):
                usados.update(alvo.nome for alvo in s.alvos)

        globais_usadas = sorted(nome for nome in usados
                                 if nome in nomes_globais_mutaveis and nome not in nomes_locais)
        if globais_usadas:
            lista = ", ".join(f"'{n}'" for n in globais_usadas)
            artigo = "o procedimento" if f.eh_procedimento else "a função"
            if len(globais_usadas) > 1:
                sujeito, verbo = "às variáveis globais", "passá-las"
            else:
                sujeito, verbo = "à variável global", "passá-la"
            self.avisos.append(Aviso(
                f"{artigo} '{f.nome}' acede diretamente {sujeito} {lista} -- considera "
                f"{verbo} como parâmetro em vez disso, para a função ficar mais "
                f"previsível e mais fácil de reutilizar", f.linha))

    def _verificar_divisoes_e_comparacoes(self, corpo):
        for s in self._todas_as_stmts(corpo):
            for e in self._expressoes_lidas(s):
                self._verificar_expr_recursiva(e)

    def _verificar_expr_recursiva(self, expr):
        if expr is None:  # pragma: no cover -- nenhum chamador passa None (mesmo raciocínio de _extrair_lvalues_e_chamadas)
            return
        if isinstance(expr, A.BinOp):
            if expr.op in ("/", "div", "mod") and self._eh_literal_zero(expr.dire):
                self.avisos.append(Aviso(
                    f"divisão por zero: o lado direito de '{expr.op}' é sempre 0",
                    expr.linha))
            if expr.op in ("==", "<>") and self._mesma_variavel(expr.esq, expr.dire):
                resultado = "verdadeira" if expr.op == "==" else "falsa"
                self.avisos.append(Aviso(
                    f"comparação sempre {resultado}: os dois lados de '{expr.op}' são "
                    f"a mesma variável", expr.linha))
            self._verificar_expr_recursiva(expr.esq)
            self._verificar_expr_recursiva(expr.dire)
        elif isinstance(expr, A.UnOp):
            self._verificar_expr_recursiva(expr.operando)
        elif isinstance(expr, A.Chamada):
            for a in expr.args:
                self._verificar_expr_recursiva(a)
        elif isinstance(expr, A.ArrayLiteral):
            for e in expr.elementos:
                self._verificar_expr_recursiva(e)
        elif isinstance(expr, A.EstruturaLiteral):
            for _nome, valor in expr.campos:
                self._verificar_expr_recursiva(valor)

    def _eh_literal_zero(self, expr):
        return isinstance(expr, A.Literal) and expr.tipo in ("inteiro", "decimal") and expr.valor == 0

    def _mesma_variavel(self, a, b):
        if not (isinstance(a, A.LValue) and isinstance(b, A.LValue)):
            return False
        if a.nome != b.nome or len(a.acessos) != len(b.acessos):
            return False
        for (tag_a, val_a), (tag_b, val_b) in zip(a.acessos, b.acessos):
            if tag_a != tag_b:  # pragma: no cover -- o sistema de tipos do ALGO garante que a mesma variável tem sempre a mesma forma de acesso
                return False
            if tag_a == "campo" and val_a != val_b:
                return False
            if tag_a == "indice" and not self._mesma_expressao_simples(val_a, val_b):
                return False
        return True

    def _mesma_expressao_simples(self, a, b):
        if isinstance(a, A.Literal) and isinstance(b, A.Literal):
            return a.tipo == b.tipo and a.valor == b.valor
        if isinstance(a, A.LValue) and isinstance(b, A.LValue):
            return self._mesma_variavel(a, b)
        return False

    def _verificar_indentacao_consistente(self):
        """O lexer já garante que CADA LINHA usa só tabs ou só grupos de 4
        espaços (nunca uma mistura na mesma linha) -- isso é um erro de
        compilação, não um aviso. O que o lexer não vê é a consistência
        ao longo do FICHEIRO INTEIRO: uma linha indentada com tabs e
        outra com espaços são cada uma válida isoladamente, mas misturar
        os dois estilos no mesmo ficheiro é um cheiro de estilo -- avisa
        aqui."""
        if not self.codigo_fonte:
            return
        usa_tabs = False
        usa_espacos = False
        primeira_linha_tab = None
        primeira_linha_espaco = None
        for num, linha in enumerate(self.codigo_fonte.split("\n"), start=1):
            sem_indent = linha.lstrip(" \t")
            bruto = linha[: len(linha) - len(sem_indent)]
            if not bruto or not sem_indent.strip():
                continue
            if "\t" in bruto and not usa_tabs:
                usa_tabs = True
                primeira_linha_tab = num
            elif " " in bruto and not usa_espacos:
                usa_espacos = True
                primeira_linha_espaco = num
        if usa_tabs and usa_espacos:
            self.avisos.append(Aviso(
                f"o ficheiro mistura indentação por tabs (ex: linha {primeira_linha_tab}) "
                f"e por espaços (ex: linha {primeira_linha_espaco}) -- escolhe só um dos "
                f"dois estilos e usa-o em todo o ficheiro", primeira_linha_espaco))

    def _verificar_inclusoes_duplicadas(self):
        """_resolver_inclusoes (cli.py e online/executor.py) ignora
        silenciosamente uma 'incluir' repetida -- não é erro de compilação,
        mas é quase sempre um lapso do programador, por isso avisa aqui."""
        primeira_ocorrencia = {}
        for inc in self.programa.inclusoes:
            caminho = os.path.normpath(inc.caminho)
            if caminho in primeira_ocorrencia:
                self.avisos.append(Aviso(
                    f"o ficheiro '{inc.caminho}' já tinha sido incluído na linha "
                    f"{primeira_ocorrencia[caminho]} -- esta inclusão repetida é ignorada",
                    inc.linha))
            else:
                primeira_ocorrencia[caminho] = inc.linha

    def _verificar_importares_duplicados(self):
        """Mesma situação que _verificar_inclusoes_duplicadas, mas para
        'importar' -- semantics.py também ignora silenciosamente uma
        biblioteca já importada (comparando nomes sem distinguir
        maiúsculas/minúsculas, tal como faz para resolver a chamada)."""
        primeira_ocorrencia = {}
        for imp in self.programa.importares:
            chave = imp.nome.lower()
            if chave in primeira_ocorrencia:
                self.avisos.append(Aviso(
                    f"a biblioteca '{imp.nome}' já tinha sido importada na linha "
                    f"{primeira_ocorrencia[chave]} -- esta importação repetida é ignorada",
                    imp.linha))
            else:
                primeira_ocorrencia[chave] = imp.linha

    def _verificar_casos_duplicados_em_escolha(self):
        for stmts in [self.programa.corpo] + [f.corpo for f in self.programa.funcoes]:
            for s in self._todas_as_stmts(stmts):
                if not isinstance(s, A.Escolha):
                    continue
                vistos = []   # lista de (expr, linha) já vistos neste 'escolher'
                for valores, _corpo in s.casos:
                    for v in valores:
                        repetido = next(
                            (linha for v_vista, linha in vistos
                             if self._mesma_expressao_simples(v_vista, v)), None)
                        if repetido is not None:
                            self.avisos.append(Aviso(
                                f"este valor de 'caso' já apareceu na linha {repetido} "
                                f"deste 'escolher' -- este ramo nunca é alcançado", v.linha))
                        else:
                            vistos.append((v, v.linha))

    def _verificar_codigo_depois_de_devolver(self, stmts):
        """Instruções a seguir a um 'devolver', no mesmo bloco, são código
        morto -- normalmente sobras de uma refatoração incompleta."""
        for i, s in enumerate(stmts):
            if isinstance(s, A.Devolver) and i < len(stmts) - 1:
                self.avisos.append(Aviso(
                    "instruções a seguir a este 'devolver' nunca são executadas",
                    stmts[i + 1].linha))
            for bloco in A.subblocos(s):
                self._verificar_codigo_depois_de_devolver(bloco)

    def _verificar_atribuicao_a_parametro_por_valor(self, f: A.FuncaoDef):
        """Atribuir diretamente a um parâmetro que não é 'por referência'
        só muda a cópia local -- confusão clássica entre passagem por
        valor e por referência."""
        nomes_por_valor = {p.nome for p in f.parametros if not p.por_referencia}
        for s in self._todas_as_stmts(f.corpo):
            if isinstance(s, A.Atribuicao) and not s.alvo.acessos and s.alvo.nome in nomes_por_valor:
                self.avisos.append(Aviso(
                    f"o parâmetro '{s.alvo.nome}' de '{f.nome}' não é 'por referência' -- "
                    f"atribuir-lhe aqui um novo valor não é visto por quem chamou a função",
                    s.linha))

    def _verificar_resultado_de_funcao_descartado(self):
        funcoes_por_nome = {f.nome: f for f in self.programa.funcoes}
        for stmts in [self.programa.corpo] + [f.corpo for f in self.programa.funcoes]:
            for s in self._todas_as_stmts(stmts):
                if not isinstance(s, A.ChamadaStmt):
                    continue
                f_def = funcoes_por_nome.get(s.chamada.nome)
                if f_def is not None and not f_def.eh_procedimento:
                    self.avisos.append(Aviso(
                        f"o valor devolvido por '{s.chamada.nome}' é descartado aqui -- "
                        f"se só interessa o efeito, considera torná-la um procedimento; "
                        f"caso contrário falta usar o valor devolvido", s.linha))

    def _verificar_ciclo_verdadeiro_sem_saida(self, corpo):
        """O ALGO não tem instrução para sair de um ciclo a meio -- um
        'enquanto verdadeiro'/'faz...enquanto verdadeiro' só pode terminar
        através de um 'devolver' algures no corpo."""
        for s in self._todas_as_stmts(corpo):
            if isinstance(s, (A.Enquanto, A.FazEnquanto)) and self._eh_literal_verdadeiro(s.condicao):
                if not any(isinstance(sub, A.Devolver) for sub in self._todas_as_stmts(s.corpo)):
                    self.avisos.append(Aviso(
                        "ciclo com condição sempre verdadeira e sem nenhum 'devolver' no "
                        "corpo -- como o ALGO não tem instrução para sair de um ciclo, "
                        "isto nunca termina", s.linha))

    def _eh_literal_verdadeiro(self, expr):
        return isinstance(expr, A.Literal) and expr.tipo == "booleano" and expr.valor is True

    def _arrays_com_tamanho_literal(self, declaracoes):
        """nome -> tamanho, só para arrays de 1 dimensão declarados com um
        tamanho literal (ex: 'v:inteiro[5]') -- os únicos casos em que dá
        para verificar limites estaticamente."""
        tamanhos = {}
        for d in declaracoes:
            if d.dims and len(d.dims) == 1 and isinstance(d.dims[0], A.Literal) \
                    and d.dims[0].tipo == "inteiro":
                tamanhos[d.nome] = d.dims[0].valor
        return tamanhos

    def _verificar_indices_fora_dos_limites(self, corpo, arrays_globais):
        arrays = dict(arrays_globais)
        locais = [s for s in self._todas_as_stmts(corpo) if isinstance(s, A.Declaracao)]
        arrays.update(self._arrays_com_tamanho_literal(locais))
        for s in self._todas_as_stmts(corpo):
            for e in self._expressoes_lidas(s):
                self._verificar_indices_expr(e, arrays)
            if isinstance(s, A.Atribuicao):
                self._verificar_indices_expr(s.alvo, arrays)

    def _verificar_indices_expr(self, expr, arrays):
        if expr is None:  # pragma: no cover -- mesmo raciocínio de _extrair_lvalues_e_chamadas
            return
        if isinstance(expr, A.LValue):
            tamanho = arrays.get(expr.nome)
            for tag, valor in expr.acessos:
                if tag != "indice":
                    continue
                indice = self._valor_literal_inteiro(valor)
                if tamanho is not None and indice is not None and not (0 <= indice < tamanho):
                    self.avisos.append(Aviso(
                        f"índice {indice} está fora dos limites de '{expr.nome}' (tamanho "
                        f"{tamanho}, índices válidos: 0 a {tamanho - 1})", expr.linha))
                self._verificar_indices_expr(valor, arrays)
        elif isinstance(expr, A.BinOp):
            self._verificar_indices_expr(expr.esq, arrays)
            self._verificar_indices_expr(expr.dire, arrays)
        elif isinstance(expr, A.UnOp):
            self._verificar_indices_expr(expr.operando, arrays)
        elif isinstance(expr, A.Chamada):
            for a in expr.args:
                self._verificar_indices_expr(a, arrays)
        elif isinstance(expr, A.ArrayLiteral):
            for e in expr.elementos:
                self._verificar_indices_expr(e, arrays)
        elif isinstance(expr, A.EstruturaLiteral):
            for _nome, valor in expr.campos:
                self._verificar_indices_expr(valor, arrays)

    def _valor_literal_inteiro(self, expr):
        if isinstance(expr, A.Literal) and expr.tipo == "inteiro":
            return expr.valor
        if isinstance(expr, A.UnOp) and expr.op == "-" and isinstance(expr.operando, A.Literal) \
                and expr.operando.tipo == "inteiro":
            return -expr.operando.valor
        return None

    def _verificar_campos_em_falta_em_literal_de_estrutura(self):
        campos_por_estrutura = {e.nome: {c.nome for c in e.campos} for e in self.programa.estruturas}
        declaracoes = list(self.programa.declaracoes)
        for stmts in [self.programa.corpo] + [f.corpo for f in self.programa.funcoes]:
            declaracoes.extend(s for s in self._todas_as_stmts(stmts) if isinstance(s, A.Declaracao))
        for d in declaracoes:
            if not isinstance(d.inicial, A.EstruturaLiteral):
                continue
            campos_da_estrutura = campos_por_estrutura.get(d.tipo)
            if campos_da_estrutura is None:
                continue
            campos_dados = {nome for nome, _expr in d.inicial.campos}
            em_falta = sorted(campos_da_estrutura - campos_dados)
            if em_falta:
                lista = ", ".join(f"'{c}'" for c in em_falta)
                self.avisos.append(Aviso(
                    f"o literal de '{d.tipo}' não define o(s) campo(s) {lista} -- ficam "
                    f"com o valor por omissão", d.linha))


def analisar(programa: A.Programa, codigo_fonte: str = None):
    return Linter(programa, codigo_fonte).analisar()
