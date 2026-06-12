#!/usr/bin/env python3
"""Revisão semanal da Mesa Brooks — lê journal.csv e calcula estatísticas.

Uso: python scripts/weekly_review.py [--semanas N]

Saída:
  - Imprime relatório de expectância no terminal
  - Salva data/suspended_setups.txt se algum setup tiver expectância negativa
    com 20+ ocorrências (protocolo CLAUDE.md)

Deve ser rodado toda domingo ou chamado manualmente.
"""

import csv
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JOURNAL = ROOT / "data" / "journal.csv"
SUSPENDED = ROOT / "data" / "suspended_setups.txt"
RELATORIO_DIR = ROOT / "reports"


def ler_journal() -> list[dict]:
    if not JOURNAL.exists():
        return []
    with JOURNAL.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def calcular_stats(trades: list[dict]) -> dict:
    """Retorna estatísticas gerais e por setup."""
    geral = {"total": 0, "wins": 0, "losses": 0, "r_total": 0.0}
    por_setup: dict[str, dict] = defaultdict(lambda: {
        "total": 0, "wins": 0, "losses": 0, "r_total": 0.0
    })

    for t in trades:
        try:
            r = float(t.get("r_realizado") or 0)
        except ValueError:
            continue
        setup = t.get("setup", "Desconhecido")
        ganhou = r > 0

        geral["total"] += 1
        geral["r_total"] += r
        if ganhou:
            geral["wins"] += 1
        else:
            geral["losses"] += 1

        por_setup[setup]["total"] += 1
        por_setup[setup]["r_total"] += r
        if ganhou:
            por_setup[setup]["wins"] += 1
        else:
            por_setup[setup]["losses"] += 1

    return {"geral": geral, "por_setup": dict(por_setup)}


def formatar_relatorio(stats: dict, trades: list[dict]) -> str:
    g = stats["geral"]
    agora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    linhas = [
        f"# Revisão Semanal Mesa Brooks — {agora}",
        "",
        "## Estatísticas Gerais",
        "",
        f"| Métrica | Valor |",
        f"|---|---|",
        f"| Total de trades | {g['total']} |",
        f"| Vencedores | {g['wins']} ({g['wins']/g['total']*100:.0f}% win rate)" if g["total"] else "| Vencedores | 0 |",
        f"| Perdedores | {g['losses']} |",
        f"| R total acumulado | {g['r_total']:+.2f}R |",
        f"| Expectância média | {g['r_total']/g['total']:+.3f}R/trade |" if g["total"] else "| Expectância média | — |",
        "",
        "## Desempenho por Setup",
        "",
        "| Setup | Trades | Win% | R Total | Expectância | Status |",
        "|---|---|---|---|---|---|",
    ]

    setups_suspensos = []
    for nome, s in sorted(stats["por_setup"].items()):
        total = s["total"]
        winpct = s["wins"] / total * 100 if total else 0
        exp = s["r_total"] / total if total else 0
        suspenso = total >= 20 and exp < 0
        status = "⛔ SUSPENSO" if suspenso else ("✓" if exp >= 0 else "⚠️ Atenção")
        linhas.append(
            f"| {nome} | {total} | {winpct:.0f}% | {s['r_total']:+.2f}R | "
            f"{exp:+.3f}R | {status} |"
        )
        if suspenso:
            setups_suspensos.append(nome)

    if setups_suspensos:
        linhas += [
            "",
            "## ⛔ Setups Suspensos",
            "",
            "Os seguintes setups acumularam expectância negativa com 20+ ocorrências",
            "e foram suspensos conforme protocolo CLAUDE.md:",
            "",
        ]
        for s in setups_suspensos:
            linhas.append(f"- **{s}**")

    linhas += [
        "",
        "## Últimos 10 Trades",
        "",
        "| Data | Ativo | Setup | Dir. | Entrada | Stop | Alvo | R Plan. | R Real | Seguiu |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for t in trades[-10:]:
        linhas.append(
            f"| {t.get('data','')} | {t.get('ativo','')} | {t.get('setup','')} | "
            f"{t.get('direcao','')} | {t.get('entrada','')} | {t.get('stop','')} | "
            f"{t.get('alvo','')} | {t.get('r_planejado','')} | {t.get('r_realizado','')} | "
            f"{t.get('seguiu_plano','')} |"
        )

    return "\n".join(linhas), setups_suspensos


def main():
    trades = ler_journal()

    if not trades:
        print("Journal vazio — nenhum trade registrado ainda.")
        return

    stats = calcular_stats(trades)
    relatorio_md, suspensos = formatar_relatorio(stats, trades)
    print(relatorio_md)

    # Salva relatório em reports/
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    saida = RELATORIO_DIR / f"weekly-review-{hoje}.md"
    saida.write_text(relatorio_md, encoding="utf-8")
    print(f"\n→ Relatório salvo: {saida.name}")

    # Atualiza lista de setups suspensos
    if suspensos:
        SUSPENDED.write_text(
            "\n".join(suspensos) + "\n", encoding="utf-8"
        )
        print(f"→ Setups suspensos gravados: {', '.join(suspensos)}")
    elif SUSPENDED.exists():
        # Limpa suspensões se não há mais setup suspenso
        SUSPENDED.unlink()
        print("→ Nenhum setup suspenso — arquivo de suspensões removido.")


if __name__ == "__main__":
    main()
