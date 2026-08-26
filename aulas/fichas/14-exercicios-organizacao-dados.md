# Ficha de Trabalho — Aula 14: Exercícios III (Organização de Dados — Mini-Projeto Final)

## Antes de começares

Não há matéria nova nesta ficha — usa livremente tudo o que aprendeste no curso todo (Aulas 1 a 11). Os exercícios 1 a 7 são independentes; o Exercício 8 é o **mini-projeto final** e é maior que os outros — deixa-o para o fim. Testa sempre o teu programa a correr, não só a lê-lo.

### Exercício 1 — Lista telefónica com busca

Define uma `estrutura Contacto` (`nome`, `telefone`). Pede vários contactos para um vetor. Escreve uma `funcao procurarContacto(contactos:Contacto[], tamanho:inteiro, alvo:cadeia):inteiro` que devolve o índice do contacto com esse nome, ou `-1` se não existir. Pede um nome ao utilizador e mostra o resultado.

### Exercício 2 — Agenda de eventos ordenada

Define uma `estrutura Evento` (`descricao`, `dia`). Pede vários eventos para um vetor e ordena-os por dia (comparar vizinhos e trocar, repetidamente). Escreve a agenda final, já ordenada.

### Exercício 3 — Inventário com stock baixo

Define uma `estrutura Produto` (`nome`, `stock`). Usa uma `constante` para o stock mínimo. Escreve uma `funcao contarStockBaixo` que conta quantos produtos estão abaixo do mínimo. Lista os produtos com stock baixo e o total.

### Exercício 4 — Estatísticas de turma

Define uma `estrutura Aluno` (`nome`, `media`). Pede os dados de vários alunos para um vetor e encontra o de melhor e o de pior média.

### Exercício 5 — Catálogo com empréstimos

Define uma `estrutura Livro` (`titulo`, `emprestado`). Escreve `procedimento emprestar(ref livro:Livro)` e `procedimento devolver(ref livro:Livro)`, cada um com um `afirmar` a garantir que a operação faz sentido (não emprestar o que já está emprestado, não devolver o que não estava). Testa com um catálogo de vários livros.

### Exercício 6 — Conflitos de horário

Define uma `estrutura Reserva` (`nome`, `horaInicio`, `horaFim`). Escreve uma `funcao haConflito(a:Reserva, b:Reserva):booleano` que verifica se dois horários se sobrepõem. Compara todas as reservas entre si (par a par) e reporta os conflitos encontrados.

### Exercício 7 — Vendas por mês

Define uma `estrutura Venda` (`produto`, `valor`, `mes`). Pede várias vendas para um vetor. Escreve uma `funcao totalPorMes` que soma o valor das vendas de um determinado mês, e usa-a para responder a uma consulta do utilizador.

---

## Exercício 8 — Mini-Projeto Final: Sistema de Gestão de Biblioteca

Constrói um programa com um **menu interativo** (repete até o utilizador escolher sair) que gere uma biblioteca:

1. **Adicionar livro** — pede título e autor, e guarda-o (usa um vetor com capacidade máxima e uma variável a contar quantos livros existem realmente, tal como visto na aula).
2. **Listar livros** — mostra todos os livros e o seu estado (disponível/emprestado), e quantos estão disponíveis no total.
3. **Emprestar livro** — pede um título, procura-o (sem distinguir maiúsculas/minúsculas — usa `importar Cadeia`), e marca-o como emprestado (ou avisa se não encontrar).
4. **Devolver livro** — o mesmo, mas para marcar como disponível.
5. **Sair** — termina o programa.

Usa `afirmar` para impedir adicionar livros além da capacidade máxima. Testa o programa a fazer várias operações seguidas, incluindo tentar emprestar um livro que não existe.
