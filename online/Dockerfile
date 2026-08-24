# ON-29: digest fixado (não só a tag "3.12-slim", que pode apontar para
# uma imagem diferente amanhã sem aviso nenhum) -- reprodutibilidade e
# resistência a um base image comprometido/alterado silenciosamente no
# registo. Atualizar o digest é uma decisão deliberada (nova imagem =
# novo `docker pull`+`docker inspect`), não um acidente de cache.
FROM python:3.12-slim@sha256:229a2c5bfa27522db7815ea81f9bed70af17ccb9de9fc7ad142b1877b5830d36

# graphviz -- é isto que resolve o fluxograma, e é exatamente o tipo
# de dependência de sistema que uma imagem Docker existe para tratar
# de forma reproduzível, em vez de assumir que já está na máquina.
RUN apt-get update \
    && apt-get install -y --no-install-recommends graphviz \
    && rm -rf /var/lib/apt/lists/*

# ON-27: nunca correr o servidor como root -- utilizador dedicado, sem
# privilégios, criado antes de copiar o código para já ficar dono dos
# ficheiros (evita um chown -R separado mais tarde).
RUN groupadd --gid 1000 algo \
    && useradd --uid 1000 --gid algo --create-home --shell /usr/sbin/nologin algo

WORKDIR /app

# algo_lang/ e alguem/ primeiro (mudam menos vezes que online/ durante
# o desenvolvimento -- melhor aproveitamento da cache de camadas)
COPY --chown=algo:algo algo_lang /app/algo_lang
COPY --chown=algo:algo alguem /app/alguem
COPY --chown=algo:algo online /app/online
# irmã de online/, não dentro -- é lida diretamente do disco pela rota
# /api/exemplos (ver online/main.py:PASTA_EXEMPLOS); sem esta linha a
# pasta fica ausente na imagem e a aba "Exemplos" da ajuda fica vazia.
COPY --chown=algo:algo exemplos /app/exemplos

RUN pip install --no-cache-dir -r /app/online/requerimentos.txt

WORKDIR /app/online

# a base de dados SQLite fica em online/dados/ -- é essa subpasta que
# deve ser montada como volume, para os dados sobreviverem a um
# reinício do contentor (ex: docker run -v algo_dados:/app/online/dados ...)
RUN mkdir -p /app/online/dados && chown algo:algo /app/online/dados
VOLUME ["/app/online/dados"]

USER algo

EXPOSE 8000

# ON-28: sem curl na imagem slim (não vale a pena instalar só para
# isto) -- usa o próprio Python, já garantido presente, para pedir "/"
# (rota pública, não exige sessão -- ver main.py:pagina_inicial) e
# confirmar HTTP 200.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request as u,sys; sys.exit(0 if u.urlopen('http://localhost:8000/', timeout=2).status == 200 else 1)"

# ON-22: --ws-max-size explícito (2 MB) em vez de confiar no default
# implícito do uvicorn -- limita o tamanho de uma única mensagem
# WebSocket (ex: /ws/executar, /ws/alguem), consistente com
# LIMITE_TAMANHO_CORPO_BYTES já aplicado às rotas HTTP em main.py.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--ws-max-size", "2000000"]
