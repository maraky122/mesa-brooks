#!/usr/bin/env python3
"""
Gera gráficos candlestick (PNG) com EMA 20 para cada ativo/timeframe.
Saída: reports/img/{ticker}_{tf}.png
"""

import sys
import yaml
import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data" / "ohlc"
IMG_DIR = ROOT / "reports" / "img"
CONFIG_FILE = ROOT / "config.yaml"

BARS_TO_PLOT = 120


def load_config():
    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f)


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def plot_chart(ticker: str, tf: str):
    safe = ticker.replace("=", "").replace("/", "")
    csv_path = DATA_DIR / f"{safe}_{tf}.csv"
    if not csv_path.exists():
        print(f"  [SKIP] {ticker} {tf}: arquivo não encontrado")
        return False

    try:
        import mplfinance as mpf
        import matplotlib
        matplotlib.use("Agg")
    except ImportError:
        print("  [AVISO] mplfinance não instalado. Rode: pip install mplfinance")
        return False

    df = pd.read_csv(csv_path, parse_dates=["timestamp"])
    df = df.set_index("timestamp")
    df.index = pd.DatetimeIndex(df.index)
    df = df[["open", "high", "low", "close", "volume"]].tail(BARS_TO_PLOT)

    if len(df) < 20:
        print(f"  [SKIP] {ticker} {tf}: barras insuficientes ({len(df)})")
        return False

    df["ema20"] = ema(df["close"], 20)

    add_plots = [
        mpf.make_addplot(df["ema20"], color="#FF6B35", width=1.5, label="EMA 20")
    ]

    out_path = IMG_DIR / f"{safe}_{tf}.png"
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    style = mpf.make_mpf_style(
        base_mpf_style="charles",
        marketcolors=mpf.make_marketcolors(
            up="#26a69a", down="#ef5350",
            wick={"up": "#26a69a", "down": "#ef5350"},
            volume={"up": "#26a69a", "down": "#ef5350"},
        ),
        gridstyle=":",
        gridcolor="#333333",
        facecolor="#1a1a2e",
        figcolor="#1a1a2e",
        rc={"axes.labelcolor": "#cccccc", "xtick.color": "#cccccc",
            "ytick.color": "#cccccc"}
    )

    fig, axes = mpf.plot(
        df,
        type="candle",
        style=style,
        addplot=add_plots,
        volume=True,
        title=f"\n{ticker} — {tf.upper()}",
        ylabel="Preço",
        ylabel_lower="Volume",
        figsize=(14, 8),
        tight_layout=True,
        returnfig=True,
    )

    fig.savefig(out_path, dpi=120, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    fig.clf()
    import matplotlib.pyplot as plt
    plt.close("all")

    print(f"  [OK] {out_path.name}")
    return True


def run():
    config = load_config()
    tfs = config.get("timeframes", ["1d", "4h", "1h"])

    all_tickers = []
    ctx = config.get("contexto_mercado", {})
    if ctx:
        all_tickers.append(ctx["ticker"])
    for grupo in ["cripto", "acoes_etfs", "commodities"]:
        for a in config.get("ativos", {}).get(grupo, []):
            all_tickers.append(a["ticker"])

    ok_count = 0
    for ticker in all_tickers:
        print(f"\n→ {ticker}")
        for tf in tfs:
            if plot_chart(ticker, tf):
                ok_count += 1

    print(f"\n{ok_count} gráfico(s) gerado(s) em {IMG_DIR}")


if __name__ == "__main__":
    run()
