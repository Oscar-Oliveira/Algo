FROM python:3.12-slim

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

RUN pip install --no-cache-dir -r /app/online/requerimentos.txt

WORKDIR /app/online

# a base de dados SQLite fica em online/dados/ -- é essa subpasta que
# deve ser montada como volume, para os dados sobreviverem a um
# reinício do contentor (ex: docker run -v algo_dados:/app/online/dados ...)
RUN mkdir -p /app/online/dados && chown algo:algo /app/online/dados
VOLUME ["/app/online/dados"]

USER algo

EXPOSE 8000

# ON-22: --ws-max-size explícito (2 MB) em vez de confiar no default
# implícito do uvicorn -- limita o tamanho de uma única mensagem
# WebSocket (ex: /ws/executar, /ws/alguem), consistente com
# LIMITE_TAMANHO_CORPO_BYTES já aplicado às rotas HTTP em main.py.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--ws-max-size", "2000000"]
