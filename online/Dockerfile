FROM python:3.12-slim

# graphviz -- é isto que resolve o fluxograma, e é exatamente o tipo
# de dependência de sistema que uma imagem Docker existe para tratar
# de forma reproduzível, em vez de assumir que já está na máquina.
RUN apt-get update \
    && apt-get install -y --no-install-recommends graphviz \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# algo_lang/ e alguem/ primeiro (mudam menos vezes que online/ durante
# o desenvolvimento -- melhor aproveitamento da cache de camadas)
COPY algo_lang /app/algo_lang
COPY alguem /app/alguem
COPY online /app/online

RUN pip install --no-cache-dir -r /app/online/requerimentos.txt

WORKDIR /app/online

# a base de dados SQLite fica em online/dados/ -- é essa subpasta que
# deve ser montada como volume, para os dados sobreviverem a um
# reinício do contentor (ex: docker run -v algo_dados:/app/online/dados ...)
VOLUME ["/app/online/dados"]

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
