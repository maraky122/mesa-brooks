#!/usr/bin/env python3
"""Baixa dados OHLC (D1 e W1) dos ativos da B3 via Yahoo Finance.

Uso: python scripts/fetch_data.py

Saída: data/ohlc/{TICKER}_{tf}.csv (ticker sem sufixo .SA, ^ removido)
       data/fetch_summary.txt com status por ativo
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yaml
import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "ohlc"
CONFIG = ROOT / "config.yaml"
SUMMARY = ROOT / "data" / "fetch_summary.txt"

# yfinance: intervalo → (período de download, barras a manter)
TIMEFRAMES = {
    "1d": ("2y", 260),
    "1wk": ("10y", 260),
}


def nome_arquivo(ticker: str, tf: str) -> Path:
    limpo = ticker.replace(".SA", "").replace("^", "").replace("=", "")
    return DATA_DIR / f"{limpo}_{tf}.csv"


def listar_ativos(cfg: dict) -> list[dict]:
    ativos = []
    for grupo in cfg["ativos"].values():
        ativos.extend(grupo)
    ativos.append({"ticker": cfg["contexto_mercado"]["ticker"],
                   "nome": cfg["contexto_mercado"]["nome"]})
    return ativos


def baixar(ticker: str, tf: str, periodo: str, max_barras: int) -> pd.DataFrame:
    df = yf.download(ticker, period=periodo, interval=tf,
                     progress=False, auto_adjust=False)
    if df.empty:
        raise ValueError("retorno vazio")
    # yfinance >= 0.2 retorna MultiIndex nas colunas para 1 ticker
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    df.index.name = "timestamp"
    return df.tail(max_barras)


def main():
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    agora = datetime.now(timezone.utc)

    linhas = [f"Fetch Mesa B3 — {agora:%Y-%m-%d %H:%M} UTC", ""]
    falhas = 0

    for ativo in listar_ativos(cfg):
        ticker = ativo["ticker"]
        for tf, (periodo, max_barras) in TIMEFRAMES.items():
            destino = nome_arquivo(ticker, tf)
            try:
                df = baixar(ticker, tf, periodo, max_barras)
                df.to_csv(destino)
                ultima = df.index[-1]
                idade_dias = (agora - ultima.tz_localize("UTC") if ultima.tzinfo is None
                              else agora - ultima).days
                aviso = " ⚠️ VELHO" if (tf == "1d" and idade_dias > 4) else ""
                linhas.append(f"OK   {ticker:<12} {tf:<4} {len(df)} barras, "
                              f"última {ultima:%Y-%m-%d}{aviso}")
            except Exception as e:
                falhas += 1
                linhas.append(f"FALHA {ticker:<12} {tf:<4} → {e}")

    linhas.append("")
    linhas.append(f"Total de falhas: {falhas}")
    SUMMARY.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print("\n".join(linhas))
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
