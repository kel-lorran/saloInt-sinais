#!/usr/bin/env python3
"""Sensor de skills: registra todo repositório novo de skills de agente e acompanha as estrelas.

Uso: python coletores/skills.py [--dias N]
  --dias N  registra os repositórios criados nos N dias anteriores (padrão 1; use mais na primeira vez)

Precisa de GITHUB_TOKEN no ambiente (no GitHub Actions vem automático). Grava:
- dados/skills/repos.csv: um registro por repositório, na primeira vez em que aparece. Todos entram,
  inclusive os que nunca vão crescer: sem eles, a taxa de acerto fica inflada (viés de sobrevivência).
- dados/skills/estrelas/AAAA-MM.csv: as estrelas dos repositórios criados nos últimos 30 dias, gravadas
  só quando o número muda desde a última leitura (a maioria fica parada; assim os dados não incham).

Só biblioteca padrão. Não guarda nada sobre os autores além do nome público do repositório.
"""
import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DADOS = Path(os.environ.get("SKILLS_DADOS", RAIZ / "dados" / "skills"))  # outra pasta só para testes
TOPICOS = ["agent-skills", "claude-skills", "claude-code-skills"]
JANELA_DIAS = 30  # cerca de 800 repositórios novos por dia: 30 dias bastam para medir se dobrou
COLUNAS_REPOS = ["registrado_em", "repo", "node_id", "criado_em", "estrelas_iniciais", "linguagem",
                 "topicos", "descricao", "tema", "brasil"]
COLUNAS_ESTRELAS = ["lido_em", "repo", "estrelas", "ultimo_push", "arquivado"]

# Classificação simples por palavras do nome, da descrição e dos tópicos.
TEMAS = {
    "documentos": r"\b(pdf|docx?|pptx?|xlsx?|excel|word|powerpoint|slides?|planilha)\b",
    "frontend e design": r"\b(ui|ux|design|css|tailwind|react|vue|frontend|figma|component)\b",
    "testes e qualidade": r"\b(tests?|tdd|qa|e2e|playwright|cypress|review|lint)\b",
    "dados": r"\b(sql|data|analytics|dashboard|etl|pandas|database)\b",
    "devops e nuvem": r"\b(docker|kubernetes|k8s|deploy|ci|cd|aws|gcp|azure|terraform|devops)\b",
    "segurança": r"\b(security|seguran[cç]a|pentest|vulnerab\w*|secrets?)\b",
    "marketing e seo": r"\b(seo|marketing|ads|copy|social|growth)\b",
    "jurídico": r"\b(legal|law|jur[ií]dic\w*|contracts?|contratos?|compliance|lgpd|gdpr)\b",
    "finanças e fiscal": r"\b(financ\w*|invoice|tax|fiscal|nota fiscal|nfe|accounting|contab\w*)\b",
    "pesquisa e web": r"\b(research|search|scrap\w*|crawl\w*|browser|web)\b",
    "memória e contexto": r"\b(memory|context|mem[oó]ria|contexto|knowledge)\b",
    "planejamento e spec": r"\b(spec|prd|plan\w*|requirements?|sdd)\b",
}
BRASIL = re.compile(r"\b(brasil|brazil|pt-?br|portugu[eê]s|nota fiscal|nf-?e|pix|clt|receita federal|cnpj|cpf|"
                    r"esocial|sped|abnt|lgpd|sefaz|boleto|simples nacional)\b", re.I)


def pedir(url, corpo=None):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN não definido")
    cab = {"Authorization": f"Bearer {token}", "User-Agent": "saloInt-sinais", "Accept": "application/vnd.github+json"}
    dados = json.dumps(corpo).encode() if corpo is not None else None
    for tentativa in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=dados, headers=cab), timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (403, 429, 502, 503) and tentativa < 3:  # limite de busca ou instabilidade
                time.sleep(30 * (tentativa + 1))
                continue
            raise


def classificar(texto):
    temas = [t for t, rx in TEMAS.items() if re.search(rx, texto, re.I)]
    return "; ".join(temas) or "outros"


def novos_repos(dias, agora):
    achados = {}
    for d in range(1, dias + 1):
        dia = (agora - dt.timedelta(days=d)).date().isoformat()
        for topico in TOPICOS:
            for pagina in range(1, 11):  # a busca do GitHub devolve no máximo 1000 resultados
                q = urllib.parse.quote(f"topic:{topico} created:{dia}")
                r = pedir(f"https://api.github.com/search/repositories?q={q}&per_page=100&page={pagina}")
                for it in r["items"]:
                    achados[it["full_name"]] = it
                if len(r["items"]) < 100:
                    break
                time.sleep(2)
            time.sleep(2)  # 30 buscas por minuto com token
    return achados


def ler_csv(caminho):
    if not caminho.exists():
        return []
    with open(caminho, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def acrescentar(caminho, colunas, linhas):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    novo = not caminho.exists()
    with open(caminho, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=colunas)
        if novo:
            w.writeheader()
        w.writerows(linhas)


def estrelas(node_ids):
    """Estrelas de até 100 repositórios por consulta, pela API GraphQL."""
    consulta = ("query($ids:[ID!]!){nodes(ids:$ids){... on Repository"
                "{nameWithOwner stargazerCount pushedAt isArchived}}}")
    for i in range(0, len(node_ids), 100):
        r = pedir("https://api.github.com/graphql", {"query": consulta, "variables": {"ids": node_ids[i:i + 100]}})
        for n in (r.get("data") or {}).get("nodes") or []:
            if n:  # repositório apagado volta como nulo
                yield n


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=1)
    args = ap.parse_args()
    agora = dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0)
    hoje = agora.isoformat(timespec="minutes")

    registrados = ler_csv(DADOS / "repos.csv")
    conhecidos = {r["repo"] for r in registrados}
    novos = []
    for nome, it in novos_repos(args.dias, agora).items():
        if nome in conhecidos:
            continue
        texto = " ".join([nome, it.get("description") or "", " ".join(it.get("topics") or [])])
        novos.append({"registrado_em": hoje, "repo": nome, "node_id": it["node_id"],
                      "criado_em": it["created_at"], "estrelas_iniciais": it["stargazers_count"],
                      "linguagem": it.get("language") or "", "topicos": " ".join(it.get("topics") or []),
                      "descricao": (it.get("description") or "").replace("\n", " ")[:300],
                      "tema": classificar(texto), "brasil": "sim" if BRASIL.search(texto) else "não"})
    acrescentar(DADOS / "repos.csv", COLUNAS_REPOS, novos)
    registrados += novos

    limite = agora - dt.timedelta(days=JANELA_DIAS)
    acompanhar = [r["node_id"] for r in registrados
                  if dt.datetime.fromisoformat(r["criado_em"].replace("Z", "+00:00")) >= limite]
    # Última contagem conhecida de cada repositório (este mês e o anterior bastam: a janela é de 30 dias).
    mes_passado = (agora.replace(day=1) - dt.timedelta(days=1))
    ultima = {}
    for arq in [DADOS / "estrelas" / f"{mes_passado:%Y-%m}.csv", DADOS / "estrelas" / f"{agora:%Y-%m}.csv"]:
        for r in ler_csv(arq):
            ultima[r["repo"]] = r["estrelas"]
    leituras = [{"lido_em": hoje, "repo": n["nameWithOwner"], "estrelas": n["stargazerCount"],
                 "ultimo_push": n["pushedAt"], "arquivado": "sim" if n["isArchived"] else "não"}
                for n in estrelas(acompanhar)
                if ultima.get(n["nameWithOwner"]) != str(n["stargazerCount"])]
    acrescentar(DADOS / "estrelas" / f"{agora:%Y-%m}.csv", COLUNAS_ESTRELAS, leituras)
    brasil = sum(1 for r in novos if r["brasil"] == "sim")
    print(f"{len(novos)} repositórios novos ({brasil} com recorte Brasil); {len(acompanhar)} acompanhados, "
          f"{len(leituras)} com estrelas novas gravadas")


if __name__ == "__main__":
    main()
