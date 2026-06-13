#!/usr/bin/env python3
"""Valida os preços de um relatório Mesa B3 contra os dados reais (OHLC D1).

Uso: python scripts/validate_report.py <relatorio.md>

Checagens por cartão de OPORTUNIDADE:
1. PREÇO ATUAL — bate com o último fechamento D1 do CSV (tolerância 0.3%)
2. FRESCURA — última barra D1 ≤ 4 dias corridos (cobre fim de semana + feriado)
3. ZONA DE COMPRA — faixa válida (min ≤ max) e não acima do preço atual em
   mais de 1% (zona de compra acima do preço = perseguição, não acumulação)
4. INVALIDAÇÃO — abaixo do piso da zona de compra

Saída: PASS/FAIL por cartão. Exit code 1 se qualquer checagem falhar.
"""

import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

OHLC_DIR = Path(__file__).resolve().parent.parent / "data" / "ohlc"
TOL_PRECO = 0.003
MAX_IDADE = timedelta(days=4)
MAX_ZONA_ACIMA = 0.01


def arquivo_csv(ticker: str) -> Path:
    limpo = ticker.replace(".SA", "").replace("^", "")
    return OHLC_DIR / f"{limpo}_1d.csv"


def ultima_barra(ticker: str):
    f = arquivo_csv(ticker)
    if not f.exists():
        return None
    ultima = f.read_text().strip().splitlines()[-1].split(",")
    ts = datetime.fromisoformat(ultima[0])
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts, float(ultima[4])


def numeros(valor: str) -> list[float]:
    return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", valor.replace(",", "."))]


def parse_oportunidades(md: str) -> list[dict]:
    cartoes = []
    for b in re.split(r"^## ", md, flags=re.M):
        if not b.startswith("OPORTUNIDADE"):
            continue
        m = re.match(r"OPORTUNIDADE\s*—\s*(\S+)", b)
        c = {"ativo": m.group(1) if m else "?"}
        for campo in ("Preço atual", "Zona de compra", "Invalidação"):
            mm = re.search(rf"\*\*{campo}:\*\*\s*(.+)", b)
            c[campo] = mm.group(1).strip() if mm else None
        cartoes.append(c)
    return cartoes


def valida(c: dict, agora: datetime) -> list[str]:
    erros = []
    ativo = c["ativo"]

    atual_n = numeros(c.get("Preço atual") or "")
    zona_n = numeros(c.get("Zona de compra") or "")
    inval_n = numeros(c.get("Invalidação") or "")

    if not atual_n:
        erros.append("campo Preço atual ausente/ilegível")
    if not zona_n:
        erros.append("campo Zona de compra ausente/ilegível")
    if not inval_n:
        erros.append("campo Invalidação ausente/ilegível")
    if erros:
        return erros

    atual = atual_n[0]
    zona_min, zona_max = min(zona_n), max(zona_n)
    invalidacao = inval_n[0]

    barra = ultima_barra(ativo)
    if barra is None:
        erros.append(f"CSV não encontrado: {arquivo_csv(ativo).name}")
    else:
        ts, close = barra
        if agora - ts > MAX_IDADE:
            erros.append(f"dado velho: última barra {ts:%Y-%m-%d} "
                         f"({(agora - ts).days}d atrás, máx {MAX_IDADE.days}d)")
        desvio = abs(atual - close) / close
        if desvio > TOL_PRECO:
            erros.append(f"preço atual {atual} difere do fechamento real "
                         f"{close:.4g} em {desvio*100:.2f}% (tol {TOL_PRECO*100}%)")

    if zona_min > atual * (1 + MAX_ZONA_ACIMA):
        erros.append(f"zona de compra ({zona_min}–{zona_max}) acima do preço atual "
                     f"({atual}) — perseguição, não acumulação")
    if invalidacao >= zona_min:
        erros.append(f"invalidação ({invalidacao}) deve ficar abaixo do piso "
                     f"da zona de compra ({zona_min})")

    return erros


def main():
    if len(sys.argv) != 2:
        sys.exit("Uso: validate_report.py <relatorio.md>")
    md = Path(sys.argv[1]).read_text(encoding="utf-8")
    agora = datetime.now(timezone.utc)
    cartoes = parse_oportunidades(md)

    if not cartoes:
        print("Nenhum cartão de OPORTUNIDADE — nada a validar. PASS")
        return

    falhou = False
    for c in cartoes:
        erros = valida(c, agora)
        falhou |= bool(erros)
        print(f"[{'FAIL' if erros else 'PASS'}] OPORTUNIDADE {c['ativo']}")
        for e in erros:
            print(f"       ✗ {e}")

    if falhou:
        sys.exit(1)
    print("Todas as oportunidades validadas contra os dados reais.")


if __name__ == "__main__":
    main()
