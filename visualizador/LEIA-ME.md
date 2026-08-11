# Visualizador Web do Trace

Abre `algo-trace-viewer.html` com duplo-clique (abre no teu navegador
normal) e carrega lá dentro um ficheiro `..._trace.json`, gerado com:

```bash
algo executa meuprograma.algo --json
```

Não precisa de instalação nenhuma nem de ligação à internet -- é um
único ficheiro HTML autónomo (React, Babel e Tailwind já vêm embutidos
no próprio ficheiro, não de um CDN, para funcionar mesmo sem rede logo
na primeira vez que abre).

`algo-trace-viewer.jsx` é a mesma aplicação, em formato para quem
quiser importar para um projeto React próprio.
