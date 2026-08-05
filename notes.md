python -c "from cifragem import gerar_chave_nova; print(gerar_chave_nova())"
python -c "import secrets; print(secrets.token_hex(32))"

docker compose up -d --build