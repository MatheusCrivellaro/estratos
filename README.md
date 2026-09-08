# Estratos

Feed de artigos e descobertas acadêmicas sobre a Bíblia e o cristianismo: arqueologia, manuscritos, história, teologia e ciência.

É um site estático. Um script em Python coleta as fontes e grava um JSON; a página lê esse JSON no navegador. Não há servidor nem banco de dados.

## Estrutura

| Arquivo | Função |
| --- | --- |
| `fetch.py` | Coleta feeds RSS/Atom e a API da CrossRef, filtra por relevância e grava `data/articles.json` |
| `index.html`, `style.css`, `app.js` | O site: filtros por tema, busca, apenas revisados por pares, agrupamento por dia |
| `.github/workflows/update.yml` | Roda o script a cada 6 horas e publica no GitHub Pages |

## Rodar localmente

```
pip install -r requirements.txt
python fetch.py
python -m http.server 8000
```

Abra http://localhost:8000.

## Publicar

1. Crie um repositório no GitHub e envie estes arquivos para a branch `main`.
2. Em *Settings → Pages*, escolha *Source: GitHub Actions*.
3. O workflow roda no primeiro push e depois a cada 6 horas.

## Adicionar fontes

Edite a lista `FEEDS` em `fetch.py`. Cada entrada tem nome, URL do feed e tema (`arqueologia`, `manuscritos`, `historia`, `teologia`, `ciencia`). Use `"peer": True` para periódicos revisados por pares e `"filter": True` para feeds gerais que só devem entrar quando o texto cita algo bíblico.

Para periódicos acadêmicos, prefira acrescentar uma consulta em `CROSSREF_QUERIES`: a CrossRef cobre quase todas as editoras e não bloqueia leitores automáticos, ao contrário de Sage, Brill, Taylor & Francis e Chicago.
