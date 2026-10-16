#!/usr/bin/env python3
"""Lê o feed público de buscas em alta do Google Trends Brasil e acrescenta a leitura ao CSV do mês.

Uso: python coletores/trends.py
Grava em dados/trends/AAAA-MM.csv, uma linha por termo por leitura. Nada é filtrado
na coleta: tudo fica registrado, inclusive o que depois some (os sinais que "morreram"
são necessários para medir o acerto sem viés de sobrevivência).

Sai com código 1 se o feed falhar ou vier vazio, para o GitHub Actions marcar a execução
como falha e o bloqueio aparecer logo.
Só biblioteca padrão.
"""
import csv
import datetime as dt
import email.utils
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

URL = "https://trends.google.com/trending/rss?geo=BR"
HT = "{https://trends.google.com/trending/rss}"
RAIZ = Path(__file__).resolve().parent.parent
COLUNAS = ["lido_em", "termo", "faixa", "volume_min", "entrou_em",
           "noticias", "noticia_titulo", "noticia_fonte", "noticia_url"]


def baixar():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (saloInt-sinais)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def volume_min(faixa):
    """'20000+' -> 20000. Serve para comparar faixas entre leituras."""
    digitos = "".join(c for c in faixa if c.isdigit())
    return int(digitos) if digitos else 0


def ler(xml, agora):
    linhas = []
    for item in ET.fromstring(xml).iter("item"):
        faixa = (item.findtext(HT + "approx_traffic") or "").strip()
        data = item.findtext("pubDate")
        entrou = email.utils.parsedate_to_datetime(data).astimezone(dt.timezone.utc) if data else None
        noticias = item.findall(HT + "news_item")
        primeira = noticias[0] if noticias else None
        linhas.append({
            "lido_em": agora.isoformat(timespec="minutes"),
            "termo": (item.findtext("title") or "").strip(),
            "faixa": faixa,
            "volume_min": volume_min(faixa),
            "entrou_em": entrou.isoformat(timespec="minutes") if entrou else "",
            "noticias": len(noticias),
            "noticia_titulo": (primeira.findtext(HT + "news_item_title") or "").strip() if primeira is not None else "",
            "noticia_fonte": (primeira.findtext(HT + "news_item_source") or "").strip() if primeira is not None else "",
            "noticia_url": (primeira.findtext(HT + "news_item_url") or "").strip() if primeira is not None else "",
        })
    return linhas


def assinatura(linhas):
    """O que define uma leitura: termos, faixas e horários de entrada."""
    return sorted((l["termo"], str(l["faixa"]), l["entrou_em"]) for l in linhas)


def ultima_leitura(destino):
    with open(destino, encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f))
    if not linhas:
        return []
    ultima = linhas[-1]["lido_em"]
    return [l for l in linhas if l["lido_em"] == ultima]


def main():
    agora = dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0)
    try:
        linhas = ler(baixar(), agora)
    except Exception as e:  # rede, bloqueio ou mudança de formato: falhar alto
        sys.exit(f"falha ao ler o feed: {e}")
    if not linhas:
        sys.exit("o feed veio sem itens")
    destino = RAIZ / "dados" / "trends" / f"{agora:%Y-%m}.csv"
    destino.parent.mkdir(parents=True, exist_ok=True)
    novo = not destino.exists()
    if not novo and assinatura(linhas) == assinatura(ultima_leitura(destino)):
        print("feed igual à última leitura; nada gravado")
        return
    with open(destino, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS)
        if novo:
            w.writeheader()
        w.writerows(linhas)
    print(f"{len(linhas)} termos gravados em {destino.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
