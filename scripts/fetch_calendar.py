#!/usr/bin/env python3
"""Baixa o calendário econômico da semana (ForexFactory) e salva o destilado.

Uso: python scripts/fetch_calendar.py

Saída: data/calendar.json — apenas eventos de impacto Alto (High) e Médio
(Medium) das moedas relevantes (USD em primeiro lugar), com timestamps em UTC
e em horário de Brasília (BRT, UTC-3).

A Mesa Brooks consulta esse arquivo antes de emitir sinais: evento de alto
impacto no dia → alerta no relatório (não bloqueia o sinal, mas avisa que a
probabilidade estimada pode ser afetada pela volatilidade do evento).
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
DESTINO = Path(__file__).resolve().parent.parent / "data" / "calendar.json"

# moedas que afetam os ativos da mesa (índices, metais, petróleo, cripto)
MOEDAS = {"USD", "EUR", "GBP", "CNY"}
IMPACTOS = {"High", "Medium"}
BRT = timezone(timedelta(hours=-3))


def main():
    req = Request(URL, headers={"User-Agent": "mesa-brooks/1.0"})
    with urlopen(req, timeout=30) as r:
        eventos = json.loads(r.read().decode("utf-8"))

    selecionados = []
    for ev in eventos:
        if ev.get("impact") not in IMPACTOS:
            continue
        if ev.get("country") not in MOEDAS:
            continue
        try:
            ts = datetime.fromisoformat(ev["date"])
        except (KeyError, ValueError):
            continue
        ts_utc = ts.astimezone(timezone.utc)
        selecionados.append({
            "evento": ev.get("title", "?"),
            "moeda": ev.get("country"),
            "impacto": "ALTO" if ev["impact"] == "High" else "MÉDIO",
            "utc": ts_utc.strftime("%Y-%m-%d %H:%M"),
            "brt": ts.astimezone(BRT).strftime("%Y-%m-%d %H:%M"),
            "previsao": ev.get("forecast") or "",
            "anterior": ev.get("previous") or "",
        })

    selecionados.sort(key=lambda e: e["utc"])
    DESTINO.write_text(json.dumps({
        "atualizado_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "fonte": "ForexFactory (faireconomy.media)",
        "eventos": selecionados,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    altos = sum(1 for e in selecionados if e["impacto"] == "ALTO")
    print(f"OK: {len(selecionados)} eventos ({altos} de alto impacto) → {DESTINO.name}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # falha não pode quebrar o fetch principal — registra e segue
        print(f"AVISO: falha ao baixar calendário econômico: {e}", file=sys.stderr)
        sys.exit(0)
