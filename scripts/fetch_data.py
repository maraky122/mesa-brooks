#!/usr/bin/env python3
"""
Baixa dados OHLC de todos os ativos do config.yaml.
Fontes: Binance (cripto) e Yahoo Finance (ações/commodities).
Fallback: Stooq para dados diários caso Yahoo falhe.
"""

import os
import sys
import yaml
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data" / "ohlc"
CONFIG_FILE = ROOT / "config.yaml"

BINANCE_BASE = "https://api.binance.com"
STOOQ_BASE = "https://stooq.com/q/d/l/"


def load_config():
    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f)


# ---------- Binance ----------

BINANCE_INTERVAL_MAP = {"1d": "1d", "4h": "4h", "1h": "1h"}

def fetch_binance(ticker: str, tf: str, limit: int = 200) -> pd.DataFrame:
    interval = BINANCE_INTERVAL_MAP.get(tf)
    if not interval:
        return None
    url = f"{BINANCE_BASE}/api/v3/klines"
    params = {"symbol": ticker, "interval": interval, "limit": limit}
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        raw = r.json()
    except Exception as e:
        print(f"  [ERRO Binance] {ticker} {tf}: {e}")
        return None

    cols = ["timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_vol", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore"]
    df = pd.DataFrame(raw, columns=cols)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df[["timestamp", "open", "high", "low", "close", "volume"]].copy()
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = df[c].astype(float)
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


# ---------- Yahoo Finance ----------

def fetch_yahoo(ticker: str, tf: str, limit: int = 200) -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError:
        print("  [AVISO] yfinance não instalado. Rode: pip install yfinance")
        return None

    yf_period_map = {
        "1d": ("1y", "1d"),
        "4h": ("60d", "1h"),   # agregamos para 4h depois
        "1h": ("60d", "1h"),
    }
    if tf not in yf_period_map:
        return None

    period, interval = yf_period_map[tf]
    try:
        raw = yf.download(ticker, period=period, interval=interval,
                          auto_adjust=True, progress=False)
    except Exception as e:
        print(f"  [ERRO Yahoo] {ticker} {tf}: {e}")
        return None

    if raw is None or raw.empty:
        return None

    # yfinance pode retornar MultiIndex de colunas (ticker como nível superior)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)

    df = raw.reset_index()
    # normaliza nome da coluna de timestamp
    dt_col = "Datetime" if "Datetime" in df.columns else "Date"
    df = df.rename(columns={dt_col: "timestamp", "Open": "open",
                             "High": "high", "Low": "low",
                             "Close": "close", "Volume": "volume"})
    df = df[["timestamp", "open", "high", "low", "close", "volume"]].copy()

    # garante timezone-aware
    if df["timestamp"].dt.tz is None:
        df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")
    else:
        df["timestamp"] = df["timestamp"].dt.tz_convert("UTC")

    # agrega 1h -> 4h se necessário
    if tf == "4h":
        df = df.set_index("timestamp")
        df = df.resample("4h", closed="left", label="left").agg(
            {"open": "first", "high": "max", "low": "min",
             "close": "last", "volume": "sum"}
        ).dropna().reset_index()

    df = df.tail(limit).reset_index(drop=True)
    return df


# ---------- Fallback Stooq (apenas D1) ----------

def fetch_stooq(ticker: str) -> pd.DataFrame:
    # Stooq usa tickers próprios; faz melhor esforço
    stooq_ticker = ticker.lower().replace("=f", ".f").replace("=", "")
    url = STOOQ_BASE
    params = {"s": stooq_ticker, "i": "d"}
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        from io import StringIO
        df = pd.read_csv(StringIO(r.text))
        if df.empty or "Date" not in df.columns:
            return None
        df = df.rename(columns={"Date": "timestamp", "Open": "open",
                                 "High": "high", "Low": "low",
                                 "Close": "close", "Volume": "volume"})
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df[["timestamp", "open", "high", "low", "close", "volume"]].copy()
        df = df.sort_values("timestamp").tail(200).reset_index(drop=True)
        return df
    except Exception as e:
        print(f"  [ERRO Stooq] {ticker}: {e}")
        return None


# ---------- Orquestração ----------

def save(df: pd.DataFrame, ticker: str, tf: str):
    safe = ticker.replace("=", "").replace("/", "")
    path = DATA_DIR / f"{safe}_{tf}.csv"
    df.to_csv(path, index=False)
    print(f"  [OK] {ticker} {tf} → {path.name} ({len(df)} barras)")


def check_staleness(df: pd.DataFrame, tf: str, ticker: str) -> bool:
    """Retorna True se os dados estiverem velhos demais."""
    if df is None or df.empty:
        return True
    last = df["timestamp"].max()
    now = pd.Timestamp.utcnow()
    delta = now - last
    is_cripto = any(c in ticker for c in ["BTC", "ETH", "USDT"])
    # D1 fecha à meia-noite; tolerar até 48h é normal
    if tf == "1d":
        if delta > timedelta(hours=48):
            print(f"  [AVISO] {ticker} {tf}: dados velhos ({delta}). Não analisar.")
            return True
        return False
    if is_cripto and delta > timedelta(hours=2):
        print(f"  [AVISO] {ticker} {tf}: dados velhos ({delta}). Não analisar.")
        return True
    # Para ações/futuros: toleramos 1 dia (fechamento do pregão anterior)
    if not is_cripto and tf == "1h" and delta > timedelta(hours=26):
        print(f"  [AVISO] {ticker} {tf}: dados velhos ({delta}). Não analisar.")
        return True
    return False


def run():
    config = load_config()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    falhas = []
    avisos = []

    all_tickers = []
    # contexto de mercado primeiro
    ctx = config.get("contexto_mercado", {})
    if ctx:
        all_tickers.append((ctx["ticker"], ctx["fonte"], "contexto"))

    for grupo in ["cripto", "acoes_etfs", "commodities"]:
        for a in config.get("ativos", {}).get(grupo, []):
            all_tickers.append((a["ticker"], a["fonte"], grupo))

    tfs = config.get("timeframes", ["1d", "4h", "1h"])
    limit = config.get("barras_historico", 200)

    for ticker, fonte, grupo in all_tickers:
        print(f"\n→ {ticker} ({fonte})")
        for tf in tfs:
            df = None
            if fonte == "binance":
                df = fetch_binance(ticker, tf, limit)
            elif fonte == "yahoo":
                df = fetch_yahoo(ticker, tf, limit)
                if (df is None or df.empty) and tf == "1d":
                    print(f"  [FALLBACK] Tentando Stooq para {ticker} D1...")
                    df = fetch_stooq(ticker)
                    if df is not None and not df.empty:
                        avisos.append(f"{ticker} D1: dados via Stooq (Yahoo falhou)")

            if df is None or df.empty:
                falhas.append(f"{ticker} {tf}")
                print(f"  [FALHA] {ticker} {tf}: sem dados")
                continue

            stale = check_staleness(df, tf, ticker)
            if stale:
                avisos.append(f"{ticker} {tf}: dados podem estar desatualizados")

            save(df, ticker, tf)

    print("\n--- Resumo ---")
    if falhas:
        print(f"Falhas ({len(falhas)}): {', '.join(falhas)}")
    else:
        print("Todos os ativos baixados com sucesso.")
    if avisos:
        print(f"Avisos: {'; '.join(avisos)}")

    # Salva resumo para o agente ler
    summary_path = ROOT / "data" / "fetch_summary.txt"
    with open(summary_path, "w") as f:
        f.write(f"Executado: {datetime.utcnow().isoformat()}Z\n")
        f.write(f"Falhas: {', '.join(falhas) if falhas else 'nenhuma'}\n")
        f.write(f"Avisos: {'; '.join(avisos) if avisos else 'nenhum'}\n")

    return len(falhas) == 0


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
