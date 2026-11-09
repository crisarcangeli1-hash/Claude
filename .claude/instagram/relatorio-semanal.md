# Relatório semanal de performance: @crisarcangeli

Roda toda segunda-feira às 09h30 (horário de Brasília) por tarefa agendada.
Também pode ser rodado à mão: "gera o relatório semanal do Instagram".

## Regras que não mudam

- **Somente leitura.** Use apenas `get_connectors`, `get_fields` e `get_data`
  do Windsor.ai. Nunca chame `execute_action`, `upload_files` nem qualquer
  ação de escrita: não publicar, não comentar, não responder, não editar.
- **Nunca invente número.** Todo número sai do Windsor.ai ou de conta feita
  sobre ele. Dado ausente: escreva "não disponível" e diga por quê.
- **Sem opinião política em nome da Cris.** Em posts de notícia, descreva
  tema, gancho e métricas; não julgue a posição nem sugira posição política.
- **Produtos (PUMP, Beauty'in, Clínica):** recomendações sem promessa de
  resultado ou alegação de saúde além do material oficial.
- **Idioma:** português do Brasil. Ganchos sugeridos seguem
  `.claude/instagram/voice.md` (CAIXA ALTA, 🚨/🦈/🇧🇷/❤️, 👉🏻, pergunta final).
- Termine sempre com o relatório completo na conversa.

## Período

- Semana analisada: segunda a domingo anteriores, no fuso de Brasília (UTC-3).
- Comparação: a semana imediatamente anterior a ela.
- Os timestamps da API vêm em UTC: post de domingo à noite em Brasília aparece
  com data de segunda em UTC. Por isso puxe um dia a mais e filtre pelo fuso.

## Coleta (Windsor.ai, conector `instagram`, conta 17841400444212867)

1. **Totais da conta** (pequeno, uma chamada), de segunda anterior até domingo:
   `date, reach, views, likes, comments, saves, shares, follower_count_1d,
   reach_followers, reach_non_followers`.
2. **Posts**, de (segunda da semana anterior − 21 dias) até (domingo + 1 dia).
   A resposta é grande: peça **uma semana por chamada** e salve cada resultado.
   Campos: `timestamp, media_id, media_permalink, media_type, media_caption,
   media_reach, media_views, media_saved, media_shares,
   media_reel_avg_watch_time, media_reel_skip_rate`.
   Em chamada separada (`media_id, media_like_count, media_comments_count`),
   porque `media_total_like_count` / `media_total_comments_count` vêm vazios
   nesta conta. Junte por `media_id`.
3. Se uma chamada estourar o tempo, repita com menos campos ou menos dias.

## Cálculo

Junte os posts numa lista JSON (`media.json`) e os totais em `conta.json` e rode:

```
python3 scripts/relatorio_semanal.py --media media.json --conta conta.json \
    --semana AAAA-MM-DD [--temas temas.json]
```

O script imprime totais com variação, mediana de views, top 3, piores 3 (no
geral e entre inéditos), tabela por série e a lista de posts. Revise a coluna
de série lendo as legendas e corrija com `temas.json`
(`{"<shortcode>": "<série>"}`); as séries válidas são:
`Produtos (Beauty'in/PUMP, Clínica Arcangeli)`, `Papo de Tubarões`,
`#FilmesCris`, `Opinião sobre notícias`, `Empreendedorismo`, `Outros`.

Cuidados de leitura que valem toda semana:

- **Alcance da semana** é a soma do alcance diário (a mesma pessoa conta em
  mais de um dia). Diga isso no relatório.
- **Novos seguidores:** dia com 0 ou vazio costuma ser dado que a Meta ainda
  não fechou. Marque como parcial.
- **Repost:** mesmo gancho já publicado antes (o script marca). Um vídeo
  reeditado com gancho levemente diferente escapa da detecção; olhe as
  legendas.
- **Curtidas ou views muito acima do alcance** (ex.: 16 mil curtidas com
  2,5 mil de alcance) não acontecem organicamente; o mais provável é
  impulsionamento. Diga "provável impulsionamento, confirme no Gerenciador de
  Anúncios", nunca afirme.
- Reels não informam seguidores por post (`media_follows` não existe para
  reels): não atribua seguidores a um post específico.

## Formato do relatório

1. **Resumo em 3 linhas:** melhor ou pior que a semana anterior, e por quê.
2. **Números da semana:** posts, alcance, visualizações, curtidas, comentários,
   salvamentos, compartilhamentos, novos seguidores; semana vs anterior e
   variação. Notas sobre dados parciais.
3. **Top 3 e piores 3 posts:** link, gancho (primeira frase), formato e
   métricas; o que fez funcionar ou não, pelo tema, gancho e formato.
4. **Desempenho por série/tema:** #FilmesCris, Papo de Tubarões, opinião sobre
   notícias, produtos (Beauty'in/PUMP, Clínica Arcangeli), empreendedorismo.
   Série sem post na semana: diga "sem posts".
5. **Três recomendações práticas:** fazer mais, parar, e um gancho sugerido no
   estilo dela (rode o gancho pelo `ig-human` com
   `--allow caps-shout,emoji-bullets,hashtag-wall`).
