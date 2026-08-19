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
        # AL-31: a verificação de indentação mista entre linhas foi
        # promovida a erro de compilação (AL-15, lexer.py:tokenizar) --
        # um ficheiro com essa mistura já não chega a compilar, por isso
        # nunca chegaria aqui; o aviso equivalente do linter ficou
        # inalcançável na prática e foi removido.
        self._verificar_inclusoes_duplicadas()
        self._verificar_importares_duplicados()
        self._verificar_casos_duplicados_em_escolha()
        self._verificar_resultado_de_funcao_descartado()
        self._verificar_campos_em_falta_em_literal_de_estrutura()
        self._verificar_recursao_sem_condicao()

        nomes_globais = {d.nome for d in self.programa.declaracoes}
        nomes_globais |= self._nomes_declarados(self.programa.corpo)

        nomes_constantes = {d.nome for d in self.programa.declaracoes if d.eh_constante}
        nomes_constantes |= self._nomes_constantes_declaradas(self.programa.corpo)
        nomes_globais_mutaveis = nomes_globais - nomes_constantes

        vetores_globais = self._vetores_com_tamanho_literal(self.programa.declaracoes)
        # AL-98/B26: nome_campo -> tamanho, para campos-vetor de QUALQUER
        # 'estrutura' -- sem isto, um índice fora dos limites só era
        # verificado para vetores declarados diretamente como variável
        # (ex.: 'v[10]'), nunca para um campo-vetor de estrutura (ex.:
        # 't.notas[10]'), que tem exatamente a mesma restrição estática.
        campos_vetor = self._campos_vetor_por_nome()

        self._verificar_variaveis_nao_usadas(
            self.programa.corpo, contexto="no programa principal",
            tambem_procurar_em=[f.corpo for f in self.programa.funcoes])
        self._verificar_globais_nao_usadas()
        self._verificar_divisoes_e_comparacoes(self.programa.corpo)
        self._verificar_codigo_depois_de_devolver(self.programa.corpo)
        self._verificar_ciclo_verdadeiro_sem_saida(self.programa.corpo)
        self._verificar_indices_fora_dos_limites(self.programa.corpo, vetores_globais, campos_vetor)

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
            self._verificar_indices_fora_dos_limites(f.corpo, vetores_globais, campos_vetor)

        self.avisos.sort(key=lambda a: a.linha)
        return self.avisos

    # ---------- utilidades de percurso ----------
    # ARCH-15: um único percorredor recursivo genérico (_todas_as_stmts,
    # sobre A.subblocos), com _nomes_declarados/_nomes_constantes_declaradas
    # como filtros derivados dele, em vez de três recursões ad hoc
    # separadas que percorriam a mesma árvore de instruções.
    def _todas_as_stmts(self, stmts):
        """Devolve a lista achatada de todas as instruções, incluindo as
        que estão dentro de blocos aninhados (se/para/enquanto/escolher)."""
        todas = []
        for s in stmts:
            todas.append(s)
            for bloco in A.subblocos(s):
                todas.extend(self._todas_as_stmts(bloco))
        return todas

    def _nomes_declarados(self, stmts):
        return {s.nome for s in self._todas_as_stmts(stmts) if isinstance(s, A.Declaracao)}

    def _nomes_constantes_declaradas(self, stmts):
        return {s.nome for s in self._todas_as_stmts(stmts)
                if isinstance(s, A.Declaracao) and s.eh_constante}

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
        corpos_com_dono = (
            [(self.programa.corpo, None)] + [(f.corpo, f.nome) for f in self.programa.funcoes]
        )
        for stmts, dono in corpos_com_dono:
            for s in self._todas_as_stmts(stmts):
                nomes = set()
                chamadas_aqui = set()
                for e in self._expressoes_lidas(s):
                    self._extrair_lvalues_e_chamadas(e, nomes, chamadas_aqui)
                if isinstance(s, A.ChamadaStmt):
                    self._extrair_lvalues_e_chamadas(s.chamada, set(), chamadas_aqui)
                if dono is not None:
                    # AL-29: uma rotina que só se chama a si própria não
                    # deve contar como "usada" por essa autochamada -- só
                    # chamadas vindas de FORA (de outra rotina, ou do
                    # programa principal) contam.
                    chamadas_aqui.discard(dono)
                chamadas |= chamadas_aqui
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

    def _verificar_recursao_sem_condicao(self):
        """Uma função/procedimento que se chama a si própria sem ter
        NENHUMA instrução de controlo de fluxo (se/escolher/para/
        enquanto/faz...enquanto) em lado nenhum do corpo não tem onde
        esconder um caso base -- é sempre o mesmo caminho, sempre
        executado, sempre com a mesma chamada recursiva -- por isso nunca
        termina. Deliberadamente conservador: uma função com QUALQUER
        estrutura de controlo já pode estar a usá-la como caso base (ex.:
        'se n <= 1 entao devolver 1' seguido, sem aninhamento, de
        'devolver n * f(n - 1)') -- não tenta perceber se esse controlo é
        mesmo o caso base; só apanha o caso mais claro de todos, um corpo
        inteiramente em linha reta que ainda assim se chama a si próprio."""
        for f in self.programa.funcoes:
            stmts = self._todas_as_stmts(f.corpo)
            if any(isinstance(s, (A.Se, A.Escolha, A.Para, A.Enquanto, A.FazEnquanto))
                   for s in stmts):
                continue
            for s in f.corpo:
                chamadas = set()
                for e in self._expressoes_lidas(s):
                    self._extrair_lvalues_e_chamadas(e, set(), chamadas)
                if isinstance(s, A.ChamadaStmt):
                    self._extrair_lvalues_e_chamadas(s.chamada, set(), chamadas)
                if f.nome in chamadas:
                    self.avisos.append(Aviso(
                        f"'{f.nome}' chama-se a si própria sem nenhuma instrução de "
                        f"controlo de fluxo no corpo -- não há onde estar um caso "
                        f"base, isto nunca termina", s.linha))
                    break

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
        elif isinstance(expr, A.VetorLiteral):
            for e in expr.elementos:
                self._extrair_lvalues_e_chamadas(e, destino_vars, destino_chamadas)
        elif isinstance(expr, A.EstruturaLiteral):
            for _nome, valor in expr.campos:
                self._extrair_lvalues_e_chamadas(valor, destino_vars, destino_chamadas)

    def _verificar_variaveis_nao_usadas(self, corpo, contexto, tambem_procurar_em=None):
        """AL-66/B26: 'tambem_procurar_em' (lista extra de corpos onde
        procurar USO, não declarações) -- uma variável declarada dentro
        de 'inicio' é tão global quanto uma declarada antes (ver
        codegen.py: A.coletar_declaracoes_tipadas percorre
        'programa.corpo' para a tabela de globais), por isso pode ser
        usada só dentro de uma função. Sem isto (só usado pela chamada
        para 'self.programa.corpo', a partir de analisar()), esta
        verificação só via uso dentro do PRÓPRIO corpo, dando um falso
        positivo "declarada mas nunca usada" ao mesmo tempo que
        _verificar_uso_de_globais provava o contrário (a função "acede
        diretamente" a essa mesma variável) -- a mesma classe de bug que
        AL-28 já tinha corrigido para _verificar_globais_nao_usadas,
        deixada por corrigir aqui."""
        declaradas = {}   # nome -> linha (só declarações explícitas, não variáveis de ciclo 'para')
        for s in self._todas_as_stmts(corpo):
            if isinstance(s, A.Declaracao):
                declaradas[s.nome] = s.linha

        usadas = set()
        for c in [corpo] + list(tambem_procurar_em or []):
            for s in self._todas_as_stmts(c):
                for e in self._expressoes_lidas(s):
                    self._extrair_lvalues(e, usadas)
                if isinstance(s, A.Para):
                    # a variável de controlo tem de estar pré-declarada (ver
                    # semantics.py) -- o próprio ciclo já conta como uso dela,
                    # mesmo que o corpo nunca a leia (idioma comum: repetir N vezes)
                    usadas.add(s.var)

        for nome, linha in declaradas.items():
            if nome not in usadas:
                self.avisos.append(Aviso(
                    f"a variável '{nome}' é declarada mas nunca é usada {contexto}",
                    linha))

    def _verificar_globais_nao_usadas(self):
        """AL-28: _verificar_variaveis_nao_usadas só olha para o bloco
        'inicio' e para cada função isoladamente -- nunca para as
        declarações globais de topo (fora de 'inicio'), que podem ser
        usadas em QUALQUER função ou no próprio 'inicio'. Por isso o
        uso tem de ser recolhido combinando todos os corpos, não um de
        cada vez."""
        usadas = set()
        for corpo in [self.programa.corpo] + [f.corpo for f in self.programa.funcoes]:
            for s in self._todas_as_stmts(corpo):
                for e in self._expressoes_lidas(s):
                    self._extrair_lvalues(e, usadas)
                if isinstance(s, A.Para):
                    usadas.add(s.var)
        for d in self.programa.declaracoes:
            if d.nome not in usadas:
                self.avisos.append(Aviso(
                    f"a variável global '{d.nome}' é declarada mas nunca é usada",
                    d.linha))

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
            elif expr.op in ("==", "<>") \
                    and getattr(expr.esq, "_tipo_inferido", None) == "decimal" \
                    and getattr(expr.dire, "_tipo_inferido", None) == "decimal":
                # 'decimal' é 'float' em Python -- comparar com '==='/'<>'
                # é frágil (imprecisão de vírgula flutuante), mesmo quando
                # os dois lados "deviam" dar o mesmo valor matemático.
                self.avisos.append(Aviso(
                    f"comparar 'decimal' com '{expr.op}' pode falhar por imprecisão "
                    f"de vírgula flutuante -- considera "
                    f"'matematica.absoluto(a - b) < 0.0001' em vez de igualdade exata",
                    expr.linha))
            self._verificar_expr_recursiva(expr.esq)
            self._verificar_expr_recursiva(expr.dire)
        elif isinstance(expr, A.UnOp):
            self._verificar_expr_recursiva(expr.operando)
        elif isinstance(expr, A.Chamada):
            for a in expr.args:
                self._verificar_expr_recursiva(a)
        elif isinstance(expr, A.VetorLiteral):
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
            elif isinstance(s, A.Ler):
                # AL-70/B30: só A.Atribuicao era verificado -- 'ler(x)'
                # sobre um parâmetro por valor 'x' também só escreve na
                # cópia local, mas só disparava o aviso genérico "nunca é
                # usado" (x É lido/escrito, só que a escrita não conta
                # como "uso" para esse aviso), nunca este, mais específico.
                for alvo in s.alvos:
                    if not alvo.acessos and alvo.nome in nomes_por_valor:
                        self.avisos.append(Aviso(
                            f"o parâmetro '{alvo.nome}' de '{f.nome}' não é 'por referência' "
                            f"-- 'ler' para ele aqui não é visto por quem chamou a função",
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
        através de um 'devolver' algures no corpo. O mesmo problema
        aparece, de forma menos óbvia, quando a condição é uma única
        variável 'booleano' usada como bandeira de controlo (ex.:
        'continuar') que nunca é alterada dentro do próprio corpo do
        ciclo -- é o padrão idiomático mais comum no ALGO para sair de um
        ciclo dentro do 'inicio', onde 'devolver' não é permitido (ver
        _verificar_recursao_sem_condicao para o equivalente em funções),
        e por isso também o erro mais comum: esquecer de mudar a
        bandeira."""
        for s in self._todas_as_stmts(corpo):
            if not isinstance(s, (A.Enquanto, A.FazEnquanto)):
                continue
            tem_devolver = any(isinstance(sub, A.Devolver) for sub in self._todas_as_stmts(s.corpo))
            if tem_devolver:
                continue
            if self._eh_literal_verdadeiro(s.condicao):
                self.avisos.append(Aviso(
                    "ciclo com condição sempre verdadeira e sem nenhum 'devolver' no "
                    "corpo -- como o ALGO não tem instrução para sair de um ciclo, "
                    "isto nunca termina", s.linha))
            elif isinstance(s.condicao, A.LValue) and not s.condicao.acessos \
                    and getattr(s.condicao, "_tipo_inferido", None) == "booleano" \
                    and not self._variavel_e_alterada_no_corpo(s.condicao.nome, s.corpo):
                self.avisos.append(Aviso(
                    f"o ciclo depende da variável '{s.condicao.nome}' para terminar, "
                    f"mas ela nunca é alterada dentro do corpo -- isto nunca termina",
                    s.linha))

    def _eh_literal_verdadeiro(self, expr):
        return isinstance(expr, A.Literal) and expr.tipo == "booleano" and expr.valor is True

    def _variavel_e_alterada_no_corpo(self, nome, corpo):
        """Verdade se 'nome' pode deixar de ter o valor que tinha à
        entrada do ciclo: atribuição direta, 'ler' direto, ou passada
        como argumento (nu, sem acessos) a qualquer chamada -- nesse
        último caso não se sabe se o parâmetro correspondente é 'ref',
        por isso assume-se que sim (mais vale não avisar do que avisar
        com um falso positivo)."""
        for s in self._todas_as_stmts(corpo):
            if isinstance(s, A.Atribuicao) and not s.alvo.acessos and s.alvo.nome == nome:
                return True
            if isinstance(s, A.Ler) and any(
                    not alvo.acessos and alvo.nome == nome for alvo in s.alvos):
                return True
            for e in self._expressoes_lidas(s):
                if self._chamada_com_argumento_nu(e, nome):
                    return True
            if isinstance(s, A.ChamadaStmt) and self._chamada_com_argumento_nu(s.chamada, nome):
                return True
        return False

    def _chamada_com_argumento_nu(self, expr, nome):
        if expr is None:  # pragma: no cover -- mesmo raciocínio de _extrair_lvalues_e_chamadas
            return False
        if isinstance(expr, A.Chamada):
            for a in expr.args:
                if isinstance(a, A.LValue) and not a.acessos and a.nome == nome:
                    return True
                if self._chamada_com_argumento_nu(a, nome):
                    return True
            return False
        if isinstance(expr, A.BinOp):
            return self._chamada_com_argumento_nu(expr.esq, nome) \
                or self._chamada_com_argumento_nu(expr.dire, nome)
        if isinstance(expr, A.UnOp):
            return self._chamada_com_argumento_nu(expr.operando, nome)
        if isinstance(expr, A.VetorLiteral):
            return any(self._chamada_com_argumento_nu(e, nome) for e in expr.elementos)
        if isinstance(expr, A.EstruturaLiteral):
            return any(self._chamada_com_argumento_nu(v, nome) for _n, v in expr.campos)
        return False

    def _vetores_com_tamanho_literal(self, declaracoes):
        """nome -> tamanho, só para vetores de 1 dimensão declarados com um
        tamanho literal (ex: 'v:inteiro[5]') -- os únicos casos em que dá
        para verificar limites estaticamente."""
        tamanhos = {}
        for d in declaracoes:
            if d.dims and len(d.dims) == 1 and isinstance(d.dims[0], A.Literal) \
                    and d.dims[0].tipo == "inteiro":
                tamanhos[d.nome] = d.dims[0].valor
        return tamanhos

    def _campos_vetor_por_nome(self):
        """AL-98/B26: nome_campo -> tamanho, para campos de QUALQUER
        'estrutura' que sejam vetores de 1 dimensão com tamanho literal --
        aproximação por NOME de campo (não pelo tipo da variável, que o
        linter não infere de forma completa como semantics.py). Se o
        mesmo nome de campo aparecer em mais do que uma 'estrutura' com
        tamanhos DIFERENTES, fica ambíguo e é excluído -- melhor não
        avisar do que avisar com um tamanho errado."""
        tamanhos = {}
        ambiguos = set()
        for e in self.programa.estruturas:
            for c in e.campos:
                if c.dims and len(c.dims) == 1 and isinstance(c.dims[0], A.Literal) \
                        and c.dims[0].tipo == "inteiro":
                    tamanho = c.dims[0].valor
                    if c.nome in tamanhos and tamanhos[c.nome] != tamanho:
                        ambiguos.add(c.nome)
                    else:
                        tamanhos[c.nome] = tamanho
        for nome in ambiguos:
            del tamanhos[nome]
        return tamanhos

    def _verificar_indices_fora_dos_limites(self, corpo, vetores_globais, campos_vetor):
        vetores = dict(vetores_globais)
        locais = [s for s in self._todas_as_stmts(corpo) if isinstance(s, A.Declaracao)]
        vetores.update(self._vetores_com_tamanho_literal(locais))
        for s in self._todas_as_stmts(corpo):
            for e in self._expressoes_lidas(s):
                self._verificar_indices_expr(e, vetores, campos_vetor)
            if isinstance(s, A.Atribuicao):
                self._verificar_indices_expr(s.alvo, vetores, campos_vetor)

    def _verificar_indices_expr(self, expr, vetores, campos_vetor):
        if expr is None:  # pragma: no cover -- mesmo raciocínio de _extrair_lvalues_e_chamadas
            return
        if isinstance(expr, A.LValue):
            tamanho = vetores.get(expr.nome)
            caminho = expr.nome
            for tag, valor in expr.acessos:
                if tag == "campo":
                    # AL-98/B26: muda para o tamanho (se algum) do CAMPO
                    # agora acedido -- sem isto, só o tamanho do vetor de
                    # TOPO (a variável base) era considerado; um índice
                    # num campo-vetor de estrutura nunca era verificado.
                    tamanho = campos_vetor.get(valor)
                    caminho = f"{caminho}.{valor}"
                    continue
                indice = self._valor_literal_inteiro(valor)
                if tamanho is not None and indice is not None and not (0 <= indice < tamanho):
                    self.avisos.append(Aviso(
                        f"índice {indice} está fora dos limites de '{caminho}' (tamanho "
                        f"{tamanho}, índices válidos: 0 a {tamanho - 1})", expr.linha))
                self._verificar_indices_expr(valor, vetores, campos_vetor)
                caminho = f"{caminho}[{A.texto_expr(valor)}]"
        elif isinstance(expr, A.BinOp):
            self._verificar_indices_expr(expr.esq, vetores, campos_vetor)
            self._verificar_indices_expr(expr.dire, vetores, campos_vetor)
        elif isinstance(expr, A.UnOp):
            self._verificar_indices_expr(expr.operando, vetores, campos_vetor)
        elif isinstance(expr, A.Chamada):
            for a in expr.args:
                self._verificar_indices_expr(a, vetores, campos_vetor)
        elif isinstance(expr, A.VetorLiteral):
            for e in expr.elementos:
                self._verificar_indices_expr(e, vetores, campos_vetor)
        elif isinstance(expr, A.EstruturaLiteral):
            for _nome, valor in expr.campos:
                self._verificar_indices_expr(valor, vetores, campos_vetor)

    def _valor_literal_inteiro(self, expr):
        if isinstance(expr, A.Literal) and expr.tipo == "inteiro":
            return expr.valor
        if isinstance(expr, A.UnOp) and expr.op == "-" and isinstance(expr.operando, A.Literal) \
                and expr.operando.tipo == "inteiro":
            return -expr.operando.valor
        return None

    def _verificar_literal_de_estrutura_campos_em_falta(self, tipo_nome, lit, campos_por_estrutura):
        campos_da_estrutura = campos_por_estrutura.get(tipo_nome)
        if campos_da_estrutura is None:
            return
        campos_dados = {nome for nome, _expr in lit.campos}
        em_falta = sorted(campos_da_estrutura - campos_dados)
        if em_falta:
            lista = ", ".join(f"'{c}'" for c in em_falta)
            self.avisos.append(Aviso(
                f"o literal de '{tipo_nome}' não define o(s) campo(s) {lista} -- ficam "
                f"com o valor por omissão", lit.linha))

    def _verificar_campos_em_falta_em_chamada(self, expr, funcoes_por_nome, campos_por_estrutura):
        """AL-69/B29: semantics.py já documenta que um literal de estrutura
        é válido "como argumento de uma função/procedimento" também --
        esta verificação só olhava para Declaracao.inicial, deixando
        'soma({x: 3})' (com 'y' a ficar silenciosamente a 0) sem aviso
        nenhum. Percorre recursivamente à procura de A.Chamada, para
        também apanhar literais passados a chamadas aninhadas."""
        if isinstance(expr, A.Chamada):
            f_def = funcoes_por_nome.get(expr.nome)
            if f_def is not None:
                for arg, p in zip(expr.args, f_def.parametros):
                    if isinstance(arg, A.EstruturaLiteral):
                        self._verificar_literal_de_estrutura_campos_em_falta(
                            p.tipo, arg, campos_por_estrutura)
            for a in expr.args:
                self._verificar_campos_em_falta_em_chamada(a, funcoes_por_nome, campos_por_estrutura)
        elif isinstance(expr, A.BinOp):
            self._verificar_campos_em_falta_em_chamada(expr.esq, funcoes_por_nome, campos_por_estrutura)
            self._verificar_campos_em_falta_em_chamada(expr.dire, funcoes_por_nome, campos_por_estrutura)
        elif isinstance(expr, A.UnOp):
            self._verificar_campos_em_falta_em_chamada(
                expr.operando, funcoes_por_nome, campos_por_estrutura)
        elif isinstance(expr, A.VetorLiteral):
            for e in expr.elementos:
                self._verificar_campos_em_falta_em_chamada(e, funcoes_por_nome, campos_por_estrutura)
        elif isinstance(expr, A.EstruturaLiteral):
            for _nome, valor in expr.campos:
                self._verificar_campos_em_falta_em_chamada(valor, funcoes_por_nome, campos_por_estrutura)

    def _verificar_campos_em_falta_em_literal_de_estrutura(self):
        campos_por_estrutura = {e.nome: {c.nome for c in e.campos} for e in self.programa.estruturas}
        declaracoes = list(self.programa.declaracoes)
        for stmts in [self.programa.corpo] + [f.corpo for f in self.programa.funcoes]:
            declaracoes.extend(s for s in self._todas_as_stmts(stmts) if isinstance(s, A.Declaracao))
        for d in declaracoes:
            if isinstance(d.inicial, A.EstruturaLiteral):
                self._verificar_literal_de_estrutura_campos_em_falta(
                    d.tipo, d.inicial, campos_por_estrutura)

        funcoes_por_nome = {f.nome: f for f in self.programa.funcoes}
        for stmts in [self.programa.corpo] + [f.corpo for f in self.programa.funcoes]:
            for s in self._todas_as_stmts(stmts):
                for e in self._expressoes_lidas(s):
                    self._verificar_campos_em_falta_em_chamada(e, funcoes_por_nome, campos_por_estrutura)


def analisar(programa: A.Programa, codigo_fonte: str = None):
    return Linter(programa, codigo_fonte).analisar()
