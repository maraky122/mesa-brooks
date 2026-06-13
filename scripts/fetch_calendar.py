#!/usr/bin/env python3
"""Baixa o calendário econômico da semana (ForexFactory) e salva o destilado.

Uso: python scripts/fetch_calendar.py

Saída: data/calendar.json — eventos de impacto ALTO e MÉDIO das moedas
relevantes (USD, EUR, GBP, CNY), com timestamps em UTC e BRT.

Em caso de falha de rede, grava um stub com status="indisponível" para que o
agente possa declarar a ausência no cabeçalho sem omitir a seção.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

DESTINO = Path(__file__).resolve().parent.parent / "data" / "calendar.json"

URLS = [
    "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
    "https://nfs.faireconomy.media/ff_calendar_nextweek.json",
]

MOEDAS = {"USD", "EUR", "GBP", "CNY"}
IMPACTOS = {"High", "Medium"}
BRT = timezone(timedelta(hours=-3))
UTC = timezone.utc


def fetch_url(url: str) -> list:
    req = Request(url, headers={"User-Agent": "mesa-brooks/1.0"})
    with urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def parse_eventos(raw: list) -> list:
    selecionados = []
    for ev in raw:
        if ev.get("impact") not in IMPACTOS:
            continue
        if ev.get("country") not in MOEDAS:
            continue
        try:
            ts = datetime.fromisoformat(ev["date"])
        except (KeyError, ValueError):
            continue
        ts_utc = ts.astimezone(UTC)
        selecionados.append({
            "evento": ev.get("title", "?"),
            "moeda": ev.get("country"),
            "impacto": "ALTO" if ev["impact"] == "High" else "MÉDIO",
            "utc": ts_utc.strftime("%Y-%m-%d %H:%M"),
            "brt": ts.astimezone(BRT).strftime("%Y-%m-%d %H:%M"),
            "previsao": ev.get("forecast") or "",
            "anterior": ev.get("previous") or "",
        })
    return selecionados


def main():
    agora_utc = datetime.now(UTC).strftime("%Y-%m-%d %H:%M")
    todos = []

    for url in URLS:
        try:
            raw = fetch_url(url)
            todos.extend(parse_eventos(raw))
            print(f"OK: {url.split('/')[-1]}")
        except (URLError, HTTPError, json.JSONDecodeError, OSError) as e:
            print(f"AVISO: {url.split('/')[-1]} → {e}", file=sys.stderr)

    if not todos:
        # Grava stub para que o agente saiba que o calendário está indisponível
        DESTINO.write_text(json.dumps({
            "status": "indisponível",
            "atualizado_utc": agora_utc,
            "fonte": "ForexFactory (faireconomy.media)",
            "erro": "API inacessível — sem dados de calendário para esta semana",
            "eventos": [],
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        print("AVISO: calendário indisponível — stub gravado.", file=sys.stderr)
        return

    # Remove duplicatas (mesma url + evento pode aparecer em ambas as semanas)
    vistos = set()
    unicos = []
    for e in todos:
        chave = (e["utc"], e["evento"], e["moeda"])
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(e)

    unicos.sort(key=lambda e: e["utc"])
    altos = sum(1 for e in unicos if e["impacto"] == "ALTO")

    DESTINO.write_text(json.dumps({
        "status": "ok",
        "atualizado_utc": agora_utc,
        "fonte": "ForexFactory (faireconomy.media)",
        "eventos": unicos,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"OK: {len(unicos)} eventos ({altos} de alto impacto) → {DESTINO.name}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERRO inesperado no fetch_calendar: {e}", file=sys.stderr)
        # Grava stub mínimo para não deixar arquivo ausente
        DESTINO.write_text(json.dumps({
            "status": "indisponível",
            "atualizado_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "fonte": "ForexFactory (faireconomy.media)",
            "erro": str(e),
            "eventos": [],
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        sys.exit(0)
