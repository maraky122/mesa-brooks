#!/usr/bin/env python3
"""Valida os preços de um relatório Mesa Brooks contra os dados reais (OHLC).

Uso: python scripts/validate_report.py <relatorio.md>

Checagens por cartão de SINAL (rigor de mesa profissional):
1. PREÇO ATUAL — deve bater com o último fechamento H1 do CSV (tolerância 0.2%)
2. FRESCURA — última barra H1: cripto ≤ 2h; demais ≤ 26h da hora do relatório
3. COERÊNCIA DIRECIONAL —
   COMPRA: stop < entrada < alvo  |  VENDA: alvo < entrada < stop
4. TRADER'S EQUATION MÍNIMA — |alvo-entrada| ≥ |entrada-stop| (R alvo ≥ R stop)
5. ENTRADA EXECUTÁVEL — entrada a no máximo 1R do preço atual e ainda não
   ultrapassada em mais de 0.25R (sinal "perdido" é sinal inválido)

Saída: PASS/FAIL por sinal. Exit code 1 se qualquer checagem falhar.
"""

import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

OHLC_DIR = Path(__file__).resolve().parent.parent / "data" / "ohlc"
CRIPTO = {"BTCUSDT", "ETHUSDT"}
TOL_PRECO_ATUAL = 0.002   # 0.2%
MAX_DIST_ENTRADA_R = 1.0  # entrada a no máx. 1R do preço atual
MAX_ULTRAPASSE_R = 0.25   # entrada já rompida além disso = perdida


def arquivo_csv(ticker: str) -> Path:
    return OHLC_DIR / f"{ticker.replace('=', '')}_1h.csv"


def ultima_barra(ticker: str):
    """Retorna (timestamp_utc, close) da última barra H1 do CSV."""
    f = arquivo_csv(ticker)
    if not f.exists():
        return None
    ultima = f.read_text().strip().splitlines()[-1].split(",")
    ts = datetime.fromisoformat(ultima[0])
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts, float(ultima[4])


def extrai_numero(valor: str):
    m = re.search(r"[-+]?\d[\d.,]*", valor.replace(",", ""))
    return float(m.group(0)) if m else None


def parse_sinais(md: str):
    """Extrai cartões de SINAL: ativo, direção e preços."""
    sinais = []
    blocos = re.split(r"^## ", md, flags=re.M)
    for b in blocos:
        if not b.startswith("SINAL"):
            continue
        # Prefere ticker entre parênteses: "SINAL — Ouro Futuro (GC=F) H1" → "GCF"
        m_ticker = re.search(r"\(([^)]+)\)", b.split("\n")[0])
        if m_ticker:
            ativo = m_ticker.group(1).replace("=", "")
        else:
            m = re.match(r"SINAL\s*—\s*(\S+)", b)
            ativo = m.group(1) if m else "?"
        sinal = {"ativo": ativo}
        for campo in ("Direção", "Preço atual", "Entrada", "Stop", "Alvo"):
            mm = re.search(rf"\*\*{campo}:\*\*\s*(.+)", b)
            sinal[campo] = mm.group(1).strip() if mm else None
        sinais.append(sinal)
    return sinais


def valida_sinal(s: dict, agora: datetime) -> list[str]:
    erros = []
    ativo = s["ativo"]
    direcao = (s.get("Direção") or "").upper()
    atual = extrai_numero(s.get("Preço atual") or "")
    entrada = extrai_numero(s.get("Entrada") or "")
    stop = extrai_numero(s.get("Stop") or "")
    alvo = extrai_numero(s.get("Alvo") or "")

    for nome, v in (("Preço atual", atual), ("Entrada", entrada),
                    ("Stop", stop), ("Alvo", alvo)):
        if v is None:
            erros.append(f"campo obrigatório ausente ou ilegível: {nome}")
    if erros:
        return erros

    # 1+2. preço atual vs CSV + frescura
    barra = ultima_barra(ativo)
    if barra is None:
        erros.append(f"CSV não encontrado: {arquivo_csv(ativo).name}")
    else:
        ts, close = barra
        limite = timedelta(hours=2) if ativo in CRIPTO else timedelta(hours=26)
        idade = agora - ts
        if idade > limite:
            erros.append(f"dado velho: última barra {ts:%Y-%m-%d %H:%M} UTC "
                         f"({idade.total_seconds()/3600:.1f}h atrás, limite {limite})")
        desvio = abs(atual - close) / close
        if desvio > TOL_PRECO_ATUAL:
            erros.append(f"preço atual {atual} difere do último fechamento real "
                         f"{close:.4g} em {desvio*100:.2f}% (tolerância {TOL_PRECO_ATUAL*100}%)")

    # 3. coerência direcional
    if "COMPRA" in direcao:
        if not (stop < entrada < alvo):
            erros.append(f"COMPRA exige stop < entrada < alvo "
                         f"(stop={stop}, entrada={entrada}, alvo={alvo})")
    elif "VENDA" in direcao:
        if not (alvo < entrada < stop):
            erros.append(f"VENDA exige alvo < entrada < stop "
                         f"(stop={stop}, entrada={entrada}, alvo={alvo})")
    else:
        erros.append(f"direção inválida: '{direcao}'")
        return erros

    # 4. retorno mínimo 1:1
    risco = abs(entrada - stop)
    retorno = abs(alvo - entrada)
    if risco <= 0:
        erros.append("risco zero: entrada igual ao stop")
    elif retorno < risco:
        erros.append(f"retorno ({retorno:.4g}) menor que o risco ({risco:.4g}) — "
                     f"viola a Trader's Equation")

    # 5. entrada executável em relação ao preço atual
    if risco > 0:
        dist = abs(entrada - atual) / risco
        compra = "COMPRA" in direcao
        ja_passou = (atual > entrada) if compra else (atual < entrada)
        if ja_passou and dist > MAX_ULTRAPASSE_R:
            erros.append(f"entrada perdida: preço atual já ultrapassou a entrada "
                         f"em {dist:.2f}R (máx {MAX_ULTRAPASSE_R}R)")
        elif not ja_passou and dist > MAX_DIST_ENTRADA_R:
            erros.append(f"entrada distante: {dist:.2f}R do preço atual "
                         f"(máx {MAX_DIST_ENTRADA_R}R) — sinal especulativo demais")

    return erros


def main():
    if len(sys.argv) != 2:
        sys.exit("Uso: validate_report.py <relatorio.md>")
    md = Path(sys.argv[1]).read_text(encoding="utf-8")
    agora = datetime.now(timezone.utc)
    sinais = parse_sinais(md)

    if not sinais:
        print("Nenhum cartão de SINAL no relatório — nada a validar. PASS")
        return

    falhou = False
    for s in sinais:
        erros = valida_sinal(s, agora)
        status = "FAIL" if erros else "PASS"
        falhou |= bool(erros)
        print(f"[{status}] SINAL {s['ativo']} {s.get('Direção','')}")
        for e in erros:
            print(f"       ✗ {e}")

    if falhou:
        sys.exit(1)
    print("Todos os sinais validados contra os dados reais.")


if __name__ == "__main__":
    main()
