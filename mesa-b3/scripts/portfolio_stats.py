#!/usr/bin/env python3
"""Estatísticas da carteira Mesa B3 — alocação atual vs alvo e aporte do mês.

Uso: python scripts/portfolio_stats.py
"""

import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PORTFOLIO = ROOT / "data" / "portfolio.csv"
CONFIG = ROOT / "config.yaml"


def main():
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    aporte_mensal = cfg["plano"]["aporte_mensal_brl"]
    alvo = cfg["plano"]["alocacao_alvo"]

    compras = []
    if PORTFOLIO.exists():
        with PORTFOLIO.open(encoding="utf-8") as f:
            compras = list(csv.DictReader(f))

    if not compras:
        print("Carteira vazia — nenhuma compra registrada.")
        print(f"Aporte disponível este mês: R$ {aporte_mensal:.2f}")
        return

    total = 0.0
    por_classe = defaultdict(float)
    por_ativo = defaultdict(float)
    mes_atual = datetime.now(timezone.utc).strftime("%Y-%m")
    gasto_mes = 0.0

    for c in compras:
        try:
            valor = float(c["valor_brl"])
        except (KeyError, ValueError):
            continue
        total += valor
        por_classe[c.get("classe", "?")] += valor
        por_ativo[c.get("ativo", "?")] += valor
        if c.get("data", "").startswith(mes_atual):
            gasto_mes += valor

    print(f"# Carteira Mesa B3 — {datetime.now(timezone.utc):%Y-%m-%d}")
    print(f"\nTotal investido: R$ {total:,.2f}")
    print(f"Aporte do mês: R$ {gasto_mes:.2f} usados de R$ {aporte_mensal:.2f} "
          f"(restam R$ {max(aporte_mensal - gasto_mes, 0):.2f})")

    print("\n## Alocação por classe (atual vs alvo)\n")
    print("| Classe | Atual | Alvo | Desvio |")
    print("|---|---|---|---|")
    for classe, pct_alvo in alvo.items():
        pct_atual = por_classe.get(classe, 0) / total * 100 if total else 0
        desvio = pct_atual - pct_alvo
        seta = "▲" if desvio > 2 else ("▼" if desvio < -2 else "·")
        print(f"| {classe} | {pct_atual:.1f}% | {pct_alvo}% | {seta} {desvio:+.1f}pp |")

    print("\n## Posições\n")
    print("| Ativo | Total investido | % carteira |")
    print("|---|---|---|")
    for ativo, valor in sorted(por_ativo.items(), key=lambda x: -x[1]):
        print(f"| {ativo} | R$ {valor:,.2f} | {valor/total*100:.1f}% |")


if __name__ == "__main__":
    main()
