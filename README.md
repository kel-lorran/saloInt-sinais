# saloInt-sinais

Dados coletados automaticamente para o sensor de tendências da base saloInt. Repositório separado para que os commits automáticos (até alguns milhares por mês) não se misturem ao histórico de decisões da base.

## O que roda
- `coletores/trends.py`: lê o feed público de buscas em alta do Google Trends Brasil e acrescenta a leitura em `dados/trends/AAAA-MM.csv`.
- `.github/workflows/trends.yml`: cada execução fica ligada cerca de 110 minutos e lê o feed a cada 5 minutos; o GitHub inicia uma a cada 2 horas (o agendamento dele atrasa muito, por isso a execução longa). Quando o feed não mudou desde a última leitura, nada é gravado.

- `coletores/skills.py` e `.github/workflows/skills.yml`: uma vez por dia, registram todo repositório novo de skills de agente (tópicos `agent-skills`, `claude-skills` e `claude-code-skills`) em `dados/skills/repos.csv`, com tema e recorte Brasil, e gravam as estrelas dos criados nos últimos 30 dias em `dados/skills/estrelas/`, só quando mudam. O primeiro teste achou cerca de 800 repositórios novos num único dia.

O repositório é público para ter minutos ilimitados no GitHub Actions; os dados são do feed público do Google Trends e não há nenhuma chave aqui.

## Regras
- Tudo o que o feed traz é gravado, inclusive termos que somem depois. Sem os sinais que "morreram", a medida de acerto do sensor fica inflada (viés de sobrevivência).
- **Nomes de pessoas não são publicados.** Antes de gravar, o coletor consulta a API de nomes do IBGE: um termo de duas ou mais palavras, sem números e que não é jogo, cuja primeira palavra é um prenome registrado no Censo, vira `[pessoa]`, e a notícia associada (que traz o nome) é apagada. A faixa e os horários ficam, para a contagem de sinais. As respostas ficam em `dados/trends/nomes-conhecidos.json`, e só palavras novas vão ao IBGE. Se o IBGE não responder (desde 22/out/2026 ele não responde aos servidores do GitHub), toda palavra nova conta como nome: a leitura é gravada, anonimizada a mais.
- Nomes de uma palavra só (apelidos, artistas) passam pelo filtro.
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

## Vigia
`coletores/vigia.py` roda a cada 6 horas (`.github/workflows/vigia.yml`) e confere o **dado gravado**, não o status das execuções: tendências sem leitura nova há mais de 6 horas, ou skills há mais de 36, deixam o vigia vermelho e o GitHub manda e-mail. A coleta de tendências também fica vermelha quando mais da metade das leituras de uma execução falha.
