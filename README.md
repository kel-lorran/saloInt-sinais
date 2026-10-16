# saloInt-sinais

Dados coletados automaticamente para o sensor de tendências da base saloInt. Repositório separado para que os commits automáticos (até alguns milhares por mês) não se misturem ao histórico de decisões da base.

## O que roda
- `coletores/trends.py`: lê o feed público de buscas em alta do Google Trends Brasil e acrescenta a leitura em `dados/trends/AAAA-MM.csv`.
- `.github/workflows/trends.yml`: roda o coletor a cada 10 minutos, pelo botão "Run workflow" ou quando o coletor muda. Quando o feed não mudou desde a última leitura, nada é gravado.

O repositório é público para ter minutos ilimitados no GitHub Actions; os dados são do feed público do Google Trends e não há nenhuma chave aqui.

## Regras
- Tudo o que o feed traz é gravado, inclusive termos que somem depois. Sem os sinais que "morreram", a medida de acerto do sensor fica inflada (viés de sobrevivência).
- O feed traz nomes de pessoas comuns; eles ficam nos dados brutos, que já são públicos, e são descartados na análise.
- Só fontes públicas e gratuitas. Nenhuma rede social é raspada.

## Colunas de `dados/trends/*.csv`
| Coluna | O que é |
|---|---|
| `lido_em` | quando a leitura foi feita (UTC) |
| `termo` | a busca em alta |
| `faixa` | volume aproximado, como o Google mostra ("1000+") |
| `volume_min` | o número da faixa, para comparar leituras |
| `entrou_em` | quando o termo entrou na lista (UTC) |
| `noticias` | quantas notícias o feed associa ao termo |
| `noticia_titulo`, `noticia_fonte`, `noticia_url` | a primeira notícia associada |

O desenho do sensor, as variáveis e a forma de medir acerto estão em `saloInt/sensores/sensor-tendencias.md`.
