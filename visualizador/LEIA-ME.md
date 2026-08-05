# Visualizador Web do Trace

Abre `algo-trace-viewer.html` com duplo-clique (abre no teu navegador
normal) e carrega lá dentro um ficheiro `..._trace.json`, gerado com:

```bash
algo executa meuprograma.algo --json
```

Não precisa de instalação nenhuma nem de ligação à internet depois de
carregado -- é um único ficheiro HTML autónomo (usa React e Tailwind a
partir de um CDN só na primeira vez que abre, com a página).

`algo-trace-viewer.jsx` é a mesma aplicação, em formato para quem
quiser importar para um projeto React próprio.
