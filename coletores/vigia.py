#!/usr/bin/env python3
"""Vigia: confere se cada coletor gravou dado recente. Sai com erro se algum estiver parado.

Existe porque a coleta de tendências passou 4 dias com execuções verdes e nenhum dado (22 a 26/out/2026).
Mede o dado gravado, não o status da execução.
"""
import csv
import datetime as dt
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
LIMITES = {  # coletor: (arquivos, coluna com a data, horas sem dado novo até alarmar)
    "tendências": ("dados/trends/*.csv", "lido_em", 6),
    "skills": ("dados/skills/repos.csv", "registrado_em", 36),
}


def ultima(padrao, coluna):
    arquivos = sorted(RAIZ.glob(padrao))
    if not arquivos:
        return None
    with open(arquivos[-1], encoding="utf-8", newline="") as f:
        datas = [l[coluna] for l in csv.DictReader(f) if l.get(coluna)]
    return max((dt.datetime.fromisoformat(d.replace("Z", "+00:00")) for d in datas), default=None)


def main():
    agora = dt.datetime.now(dt.timezone.utc)
    parados = []
    for nome, (padrao, coluna, horas) in LIMITES.items():
        quando = ultima(padrao, coluna)
        atraso = (agora - quando).total_seconds() / 3600 if quando else float("inf")
        print(f"{nome}: último dado {quando:%d/%m %H:%M} UTC, há {atraso:.1f} h (limite {horas} h)" if quando
              else f"{nome}: nenhum dado")
        if atraso > horas:
            parados.append(nome)
    if parados:
        sys.exit(f"coletor parado: {', '.join(parados)}")


if __name__ == "__main__":
    main()
