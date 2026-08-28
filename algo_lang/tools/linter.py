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
        self._verificar_inclusoes_duplicadas()
        self._verificar_importares_duplicados()
        self._verificar_casos_duplicados_em_escolha()
        self._verificar_escolha_sem_casos()
        self._verificar_resultado_de_funcao_descartado()
        self._verificar_recursao_sem_condicao()

        nomes_globais = {d.nome for d in self.programa.declaracoes}
        nomes_globais |= self._nomes_declarados(self.programa.corpo)

        nomes_constantes = {d.nome for d in self.programa.declaracoes if d.eh_constante}
        nomes_constantes |= self._nomes_constantes_declaradas(self.programa.corpo)
        nomes_globais_mutaveis = nomes_globais - nomes_constantes

        # nome de 'constante' -> valor inteiro resolvido, calculado uma
        # única vez e partilhado pelos dois mapas abaixo.
        valores_constantes = self._valores_constantes()

        vetores_globais = self._vetores_com_tamanho_literal(
            self.programa.declaracoes, valores_constantes)
        # nome_campo -> tamanho, para campos-vetor de QUALQUER 'estrutura'
        # (ex.: 't.notas[10]') terem a mesma verificação de índice fora
        # dos limites que um vetor declarado diretamente já tem.
        campos_vetor = self._campos_vetor_por_nome(valores_constantes)

        self._verificar_variaveis_nao_usadas(
            self.programa.corpo, contexto="no programa principal",
            tambem_procurar_em=[f.corpo for f in self.programa.funcoes])
        self._verificar_globais_nao_usadas()
        self._verificar_divisoes_e_comparacoes(self.programa.corpo)
        self._verificar_codigo_depois_de_retornar(self.programa.corpo)
        self._verificar_ciclo_verdadeiro_sem_saida(self.programa.corpo)
        self._verificar_indices_fora_dos_limites(
            self.programa.corpo, vetores_globais, campos_vetor, valores_constantes)

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
            self._verificar_codigo_depois_de_retornar(f.corpo)
            self._verificar_ciclo_verdadeiro_sem_saida(f.corpo)
            self._verificar_indices_fora_dos_limites(
                f.corpo, vetores_globais, campos_vetor, valores_constantes)

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
            # 's.dims' (tamanho de um vetor, ex.: 'v:inteiro[N]') também LÊ
            # cada nome que usar.
            exprs = list(s.dims) if s.dims else []
            if s.inicial is not None:
                exprs.append(s.inicial)
            return exprs
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
        if isinstance(s, A.Retornar):
            return [s.expr] if s.expr is not None else []
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
                    # Uma rotina que só se chama a si própria não deve
                    # contar como "usada" por essa autochamada -- só
                    # chamadas vindas de FORA contam.
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
        estrutura de controlo já pode estar a usá-la como caso base -- só
        apanha o caso mais claro, um corpo inteiramente em linha reta que
        ainda assim se chama a si próprio."""
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
            else:
                # 'alias.metodo(...)' -- se 'alias' vem de 'incluir ...
                # como alias' (agora sempre obrigatório), o nome real da
                # função é o MANGLED ('alias_metodo', ver inclusoes.py),
                # não o texto literal escrito na chamada; sem isto, toda
                # função incluída parecia "nunca chamada" mesmo quando
                # era, porque só se comparava contra o texto cru. Uma
                # biblioteca embutida (ex.: 'matematica.raiz') nunca
                # aparece em 'aliases_inclusao', por isso continua a ser
                # ignorada como antes (não é uma rotina do próprio
                # programa a rastrear aqui).
                alias, _, metodo = expr.nome.partition(".")
                mapa_metodos = self.programa.aliases_inclusao.get(alias)
                if mapa_metodos is not None and metodo in mapa_metodos:
                    destino_chamadas.add(mapa_metodos[metodo])
            for a in expr.args:
                self._extrair_lvalues_e_chamadas(a, destino_vars, destino_chamadas)
        elif isinstance(expr, A.VetorLiteral):
            for e in expr.elementos:
                self._extrair_lvalues_e_chamadas(e, destino_vars, destino_chamadas)
        elif isinstance(expr, A.EstruturaLiteral):
            for _nome, valor in expr.campos:
                self._extrair_lvalues_e_chamadas(valor, destino_vars, destino_chamadas)

    def _verificar_variaveis_nao_usadas(self, corpo, contexto, tambem_procurar_em=None):
        """'tambem_procurar_em' (lista extra de corpos onde procurar USO,
        não declarações) -- uma variável declarada dentro de 'inicio' é
        tão global quanto uma declarada antes, por isso pode ser usada só
        dentro de uma função."""
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
        """_verificar_variaveis_nao_usadas só olha para o bloco 'inicio' e
        para cada função isoladamente -- nunca para as declarações
        globais de topo, que podem ser usadas em QUALQUER função. Por
        isso o uso tem de ser recolhido combinando todos os corpos."""
        usadas = set()
        for corpo in [self.programa.corpo] + [f.corpo for f in self.programa.funcoes]:
            eh_corpo_principal = corpo is self.programa.corpo
            for s in self._todas_as_stmts(corpo):
                for e in self._expressoes_lidas(s):
                    self._extrair_lvalues(e, usadas)
                if isinstance(s, A.Para) and eh_corpo_principal:
                    # 'para var' DENTRO de uma função é sempre uma
                    # variável local independente (gerador_base.py
                    # exclui-a do 'global' dessa função) -- só no CORPO
                    # PRINCIPAL ('inicio') é que 'para var' mesmo muta a
                    # global, por isso só aí conta como "uso".
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

    def _verificar_escolha_sem_casos(self):
        """'escolher' sem nenhum 'caso' (só 'contrario', ou nem isso) não
        faz o que o nome sugere. Vale a pena avisar mesmo sem ser um erro
        de compilação, porque quase sempre é um 'caso' esquecido por
        engano."""
        for stmts in [self.programa.corpo] + [f.corpo for f in self.programa.funcoes]:
            for s in self._todas_as_stmts(stmts):
                if isinstance(s, A.Escolha) and not s.casos:
                    self.avisos.append(Aviso(
                        "'escolher' sem nenhum 'caso' -- só o 'contrario' (se existir) "
                        "é executado, sempre, sem nenhuma escolha a fazer", s.linha))

    def _verificar_codigo_depois_de_retornar(self, stmts):
        """Instruções a seguir a um 'retornar', no mesmo bloco, são código
        morto -- normalmente sobras de uma refatoração incompleta."""
        for i, s in enumerate(stmts):
            if isinstance(s, A.Retornar) and i < len(stmts) - 1:
                self.avisos.append(Aviso(
                    "instruções a seguir a este 'retornar' nunca são executadas",
                    stmts[i + 1].linha))
            for bloco in A.subblocos(s):
                self._verificar_codigo_depois_de_retornar(bloco)

    def _verificar_atribuicao_a_parametro_por_valor(self, f: A.FuncaoDef):
        """Atribuir diretamente a um parâmetro que não é 'por referência'
        (ou a um campo/elemento seu, já que struct/vetor são copiados por
        valor) só muda a cópia local -- confusão clássica entre passagem
        por valor e por referência."""
        nomes_por_valor = {p.nome for p in f.parametros if not p.por_referencia}
        for s in self._todas_as_stmts(f.corpo):
            if isinstance(s, A.Atribuicao) and s.alvo.nome in nomes_por_valor:
                sufixo = " (aqui, um campo/elemento seu)" if s.alvo.acessos else ""
                self.avisos.append(Aviso(
                    f"o parâmetro '{s.alvo.nome}' de '{f.nome}' não é 'por referência' -- "
                    f"atribuir-lhe{sufixo} um novo valor não é visto por quem chamou a função",
                    s.linha))
            elif isinstance(s, A.Ler):
                # 'ler(x)' sobre um parâmetro por valor também só escreve
                # na cópia local -- mesmo aviso que A.Atribuicao, mais
                # específico do que o genérico "nunca é usado".
                for alvo in s.alvos:
                    if alvo.nome in nomes_por_valor:
                        sufixo = " (aqui, um campo/elemento seu)" if alvo.acessos else ""
                        self.avisos.append(Aviso(
                            f"o parâmetro '{alvo.nome}' de '{f.nome}' não é 'por referência' "
                            f"-- 'ler' para ele{sufixo} aqui não é visto por quem chamou a função",
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
        """Um 'enquanto verdadeiro'/'faz...enquanto verdadeiro' só pode
        terminar através de um 'retornar' ou 'sair' algures no corpo. O
        mesmo problema aparece, de forma menos óbvia, quando a condição
        é uma única variável 'booleano' usada como bandeira de controlo
        (ex.: 'ativo') que nunca é alterada dentro do próprio corpo do
        ciclo -- é um padrão idiomático comum no ALGO para sair de um
        ciclo dentro do 'inicio', onde 'retornar' não é permitido (ver
        _verificar_recursao_sem_condicao para o equivalente em funções),
        e por isso também um erro comum: esquecer de mudar a bandeira
        (ou de acrescentar um 'sair')."""
        funcoes_por_nome = {f.nome: f for f in self.programa.funcoes}
        for s in self._todas_as_stmts(corpo):
            if not isinstance(s, (A.Enquanto, A.FazEnquanto)):
                continue
            tem_retornar = any(isinstance(sub, A.Retornar) for sub in self._todas_as_stmts(s.corpo))
            if tem_retornar or self._tem_sair_alcancavel(s.corpo):
                continue
            if self._eh_literal_verdadeiro(s.condicao):
                self.avisos.append(Aviso(
                    "ciclo com condição sempre verdadeira e sem nenhum 'retornar'/'sair' "
                    "no corpo -- isto nunca termina", s.linha))
            elif isinstance(s.condicao, A.LValue) and not s.condicao.acessos \
                    and getattr(s.condicao, "_tipo_inferido", None) == "booleano" \
                    and not self._variavel_e_alterada_no_corpo(
                        s.condicao.nome, s.corpo, funcoes_por_nome):
                self.avisos.append(Aviso(
                    f"o ciclo depende da variável '{s.condicao.nome}' para terminar, "
                    f"mas ela nunca é alterada dentro do corpo -- isto nunca termina",
                    s.linha))

    def _eh_literal_verdadeiro(self, expr):
        return isinstance(expr, A.Literal) and expr.tipo == "booleano" and expr.valor is True

    def _tem_sair_alcancavel(self, stmts):
        """Verdade se 'stmts' contém um 'sair' alcançável, descendo em
        'se'/'escolher' mas SEM entrar em 'para'/'enquanto'/
        'fazer...enquanto' aninhados -- um 'sair' num ciclo interior só
        sai desse ciclo, é irrelevante para o ciclo EXTERIOR que
        _verificar_ciclo_verdadeiro_sem_saida está a avaliar. Não pode
        reutilizar _todas_as_stmts/A.subblocos (essa travessia desce
        também em ciclos aninhados)."""
        for s in stmts:
            if isinstance(s, A.Sair):
                return True
            if isinstance(s, A.Se):
                if any(self._tem_sair_alcancavel(corpo) for _cond, corpo in s.ramos):
                    return True
                if s.senao is not None and self._tem_sair_alcancavel(s.senao):
                    return True
            elif isinstance(s, A.Escolha):
                if any(self._tem_sair_alcancavel(corpo) for _valores, corpo in s.casos):
                    return True
                if s.contrario is not None and self._tem_sair_alcancavel(s.contrario):
                    return True
        return False

    def _variavel_e_alterada_no_corpo(self, nome, corpo, funcoes_por_nome=None):
        """Verdade se 'nome' pode deixar de ter o valor que tinha à
        entrada do ciclo: atribuição direta, 'ler' direto, passada nua
        como argumento a qualquer chamada (assume-se 'ref' possível), ou
        uma chamada cujo PRÓPRIO corpo atribui diretamente a 'nome'. Este
        último caso só olha 1 nível (não segue chamadas transitivas) --
        mesma filosofia conservadora: prefere um falso negativo a um
        falso positivo."""
        for s in self._todas_as_stmts(corpo):
            if isinstance(s, A.Atribuicao) and not s.alvo.acessos and s.alvo.nome == nome:
                return True
            if isinstance(s, A.Ler) and any(
                    not alvo.acessos and alvo.nome == nome for alvo in s.alvos):
                return True
            for e in self._expressoes_lidas(s):
                if self._chamada_com_argumento_nu(e, nome):
                    return True
                if funcoes_por_nome and self._chamada_altera_global_diretamente(
                        e, nome, funcoes_por_nome):
                    return True
            if isinstance(s, A.ChamadaStmt):
                if self._chamada_com_argumento_nu(s.chamada, nome):
                    return True
                if funcoes_por_nome and self._chamada_altera_global_diretamente(
                        s.chamada, nome, funcoes_por_nome):
                    return True
        return False

    def _chamada_altera_global_diretamente(self, expr, nome, funcoes_por_nome):
        """Verdade se chamar 'expr' altera 'nome' diretamente dentro do
        próprio corpo da função/procedimento chamado (ex.: um
        procedimento que faz 'ativo = falso') -- caso que
        _variavel_e_alterada_no_corpo, sozinha, não reconhece."""
        if not isinstance(expr, A.Chamada):
            return False
        f_def = funcoes_por_nome.get(expr.nome)
        if f_def is None:
            return False
        return any(
            isinstance(s, A.Atribuicao) and not s.alvo.acessos and s.alvo.nome == nome
            for s in self._todas_as_stmts(f_def.corpo))

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

    def _valores_constantes(self):
        """nome de 'constante' -> valor inteiro resolvido, achatado para
        todo o programa. Aproximação por NOME: um nome redeclarado com
        valores potencialmente diferentes fica ambíguo e é excluído.
        Resolve literais e expressões '+'/'-'/'*' entre constantes já
        resolvidas, com proteção contra referência circular."""
        declaracoes = list(self.programa.declaracoes)
        declaracoes += [s for s in self._todas_as_stmts(self.programa.corpo)
                        if isinstance(s, A.Declaracao)]
        for f in self.programa.funcoes:
            declaracoes += [s for s in self._todas_as_stmts(f.corpo)
                             if isinstance(s, A.Declaracao)]

        por_nome = {}
        ambiguos = set()
        for d in declaracoes:
            if not d.eh_constante:
                continue
            if d.nome in por_nome:
                ambiguos.add(d.nome)
            else:
                por_nome[d.nome] = d
        for nome in ambiguos:
            del por_nome[nome]

        cache = {}

        def resolver_expr(expr, vistos):
            if isinstance(expr, A.Literal) and expr.tipo == "inteiro":
                return expr.valor
            if isinstance(expr, A.UnOp) and expr.op == "-":
                valor = resolver_expr(expr.operando, vistos)
                return None if valor is None else -valor
            if isinstance(expr, A.BinOp) and expr.op in ("+", "-", "*"):
                esq = resolver_expr(expr.esq, vistos)
                dire = resolver_expr(expr.dire, vistos)
                if esq is None or dire is None:
                    return None
                return {"+": esq + dire, "-": esq - dire, "*": esq * dire}[expr.op]
            if isinstance(expr, A.LValue) and not expr.acessos:
                return resolver_nome(expr.nome, vistos)
            return None

        def resolver_nome(nome, vistos):
            if nome in cache:
                return cache[nome]
            if nome in vistos or nome not in por_nome:
                return None
            vistos.add(nome)
            valor = resolver_expr(por_nome[nome].inicial, vistos)
            cache[nome] = valor
            return valor

        valores = {}
        for nome in por_nome:
            valor = resolver_nome(nome, set())
            if valor is not None:
                valores[nome] = valor
        return valores

    def _tamanho_resolvido(self, dim_expr, valores_constantes):
        """Tamanho estático de UMA dimensão, literal ou 'constante' (ver
        _valores_constantes)."""
        if isinstance(dim_expr, A.Literal) and dim_expr.tipo == "inteiro":
            return dim_expr.valor
        if isinstance(dim_expr, A.LValue) and not dim_expr.acessos:
            return valores_constantes.get(dim_expr.nome)
        return None

    def _vetores_com_tamanho_literal(self, declaracoes, valores_constantes):
        """nome -> lista de tamanhos, um por dimensão (ex.:
        'v:inteiro[8][8]' -> [8, 8]; None numa posição para uma dimensão
        dinâmica, não estaticamente resolúvel). Regista a lista completa
        para cada dimensão ser verificada independentemente em
        _verificar_indices_expr."""
        tamanhos = {}
        for d in declaracoes:
            if d.dims:
                tamanhos[d.nome] = [self._tamanho_resolvido(dim, valores_constantes)
                                     for dim in d.dims]
        return tamanhos

    def _campos_vetor_por_nome(self, valores_constantes):
        """nome_campo -> lista de tamanhos (um por dimensão), para campos
        de QUALQUER 'estrutura' -- aproximação por NOME de campo (não
        pelo tipo da variável). Se o mesmo nome de campo aparecer em mais
        do que uma 'estrutura' com listas de tamanhos DIFERENTES, fica
        ambíguo e é excluído."""
        tamanhos = {}
        ambiguos = set()
        for e in self.programa.estruturas:
            for c in e.campos:
                if c.dims:
                    lista = [self._tamanho_resolvido(dim, valores_constantes) for dim in c.dims]
                    if c.nome in tamanhos and tamanhos[c.nome] != lista:
                        ambiguos.add(c.nome)
                    else:
                        tamanhos[c.nome] = lista
        for nome in ambiguos:
            del tamanhos[nome]
        return tamanhos

    def _verificar_indices_fora_dos_limites(self, corpo, vetores_globais, campos_vetor,
                                             valores_constantes):
        vetores = dict(vetores_globais)
        locais = [s for s in self._todas_as_stmts(corpo) if isinstance(s, A.Declaracao)]
        vetores.update(self._vetores_com_tamanho_literal(locais, valores_constantes))
        for s in self._todas_as_stmts(corpo):
            for e in self._expressoes_lidas(s):
                # _expressoes_lidas já inclui 's.alvo' quando indexado/tem
                # campo -- mas aqui o alvo de uma Atribuicao é verificado
                # explicitamente a seguir; sem este 'continue', dava o
                # mesmo aviso duas vezes.
                if isinstance(s, A.Atribuicao) and e is s.alvo:
                    continue
                self._verificar_indices_expr(e, vetores, campos_vetor)
            if isinstance(s, A.Atribuicao):
                self._verificar_indices_expr(s.alvo, vetores, campos_vetor)

    def _verificar_indices_expr(self, expr, vetores, campos_vetor):
        if expr is None:  # pragma: no cover -- mesmo raciocínio de _extrair_lvalues_e_chamadas
            return
        if isinstance(expr, A.LValue):
            # 'dims_tamanhos' é uma LISTA (um tamanho por dimensão) --
            # 'nivel' avança a cada acesso 'indice' consecutivo, para cada
            # dimensão ser comparada contra o SEU próprio tamanho, não
            # sempre o da 1ª.
            dims_tamanhos = vetores.get(expr.nome)
            nivel = 0
            caminho = expr.nome
            for tag, valor in expr.acessos:
                if tag == "campo":
                    # Muda para os tamanhos (se algum) do CAMPO agora
                    # acedido, não o do vetor de TOPO.
                    dims_tamanhos = campos_vetor.get(valor)
                    nivel = 0
                    caminho = f"{caminho}.{valor}"
                    continue
                tamanho = (dims_tamanhos[nivel]
                           if dims_tamanhos is not None and nivel < len(dims_tamanhos)
                           else None)
                indice = self._valor_literal_inteiro(valor)
                if tamanho is not None and indice is not None and not (0 <= indice < tamanho):
                    self.avisos.append(Aviso(
                        f"índice {indice} está fora dos limites de '{caminho}' (tamanho "
                        f"{tamanho}, índices válidos: 0 a {tamanho - 1})", expr.linha))
                self._verificar_indices_expr(valor, vetores, campos_vetor)
                caminho = f"{caminho}[{A.texto_expr(valor)}]"
                nivel += 1
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

def analisar(programa: A.Programa, codigo_fonte: str = None):
    return Linter(programa, codigo_fonte).analisar()
