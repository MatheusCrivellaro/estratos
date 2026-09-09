# Estratos

Feed de artigos e descobertas acadêmicas sobre a Bíblia e o cristianismo, com chamadas traduzidas para o português: arqueologia, manuscritos, história, teologia e ciência.

É um site estático. Um script em Python coleta as fontes e grava um JSON; a página lê esse JSON no navegador. Não há servidor nem banco de dados.

## Estrutura

| Arquivo | Função |
| --- | --- |
| `fetch.py` | Coleta feeds RSS/Atom e a API da CrossRef, filtra por relevância, atribui assuntos, traduz título e resumo e grava `data/articles.json` |
| `index.html`, `style.css`, `app.js` | O site: índice com filtros por período, tema, tipo de fonte, assunto, fonte e revisão por pares; busca; agrupamento por dia |
| `.github/workflows/update.yml` | Roda o script a cada 6 horas e publica no GitHub Pages |

## Rodar localmente

```
pip install -r requirements.txt
python fetch.py
python -m http.server 8000
```

Abra http://localhost:8000.

A primeira coleta traduz todos os artigos e leva alguns minutos. As próximas só traduzem o que é novo, porque as traduções ficam guardadas no JSON. A tradução usa o Google Tradutor sem chave de API; se ela falhar, o site mostra o texto original.

## Publicar

1. Crie um repositório no GitHub e envie estes arquivos para a branch `main`.
2. Em *Settings → Pages*, escolha *Source: GitHub Actions*.
3. O workflow roda no primeiro push e depois a cada 6 horas.

## Assuntos

A lista `TAGS` em `fetch.py` define o índice de assuntos por expressões regulares aplicadas ao título e ao resumo em inglês. Acrescente ou ajuste entradas ali.

## Adicionar fontes

Edite a lista `FEEDS` em `fetch.py`. Cada entrada tem nome, URL do feed e tema (`arqueologia`, `manuscritos`, `historia`, `teologia`, `ciencia`). Informe também o tipo (`revista`, `instituicao`, `blog`, `noticia`). Use `"filter": True` para feeds gerais que só devem entrar quando o texto cita algo bíblico.

Para periódicos acadêmicos, prefira acrescentar uma consulta em `CROSSREF_QUERIES`: a CrossRef cobre quase todas as editoras e não bloqueia leitores automáticos, ao contrário de Sage, Brill, Taylor & Francis e Chicago.
