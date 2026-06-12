#!/usr/bin/env python3
"""Renderiza o relatório markdown da Mesa Brooks em HTML amigável para e-mail.

Uso: python scripts/render_email.py <relatorio.md> <saida.html>

- Substitui tickers por nomes amigáveis (GC=F → Ouro, BTCUSDT → Bitcoin...)
- Converte os cartões (SINAL / SEM TRADE) em blocos visuais com cor
- Tabelas legíveis em mobile, tudo com CSS inline (compatível com Gmail)
"""

import re
import sys
from pathlib import Path

# ── Nomes amigáveis ────────────────────────────────────────────────────────
NOMES = {
    "GC=F": "Ouro",
    "SI=F": "Prata",
    "CL=F": "Petróleo WTI",
    "ES=F": "S&P 500 (Futuros)",
    "BTCUSDT": "Bitcoin",
    "ETHUSDT": "Ethereum",
    "SPY": "S&P 500 (ETF SPY)",
    "QQQ": "Nasdaq (ETF QQQ)",
    "NVDA": "NVIDIA",
}

TIMEFRAMES = {"1d": "Diário", "4h": "4 horas", "1h": "1 hora",
              "D1": "Diário", "H4": "4 horas", "H1": "1 hora"}


def nome_amigavel(ticker: str) -> str:
    nome = NOMES.get(ticker.strip())
    return f"{nome}" if nome else ticker


def substitui_tickers(texto: str) -> str:
    """Troca menções de tickers por 'Nome (TICKER)' fora de tabelas/código."""
    for ticker, nome in NOMES.items():
        # evita substituir quando já está no formato Nome (TICKER)
        padrao = re.compile(rf"(?<![\w(]){re.escape(ticker)}(?![\w)])")
        texto = padrao.sub(nome, texto)
    return texto


# ── Estilos inline (e-mail-safe) ───────────────────────────────────────────
S = {
    "body": "margin:0;padding:0;background-color:#f4f5f7;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;",
    "wrap": "max-width:600px;margin:0 auto;padding:16px;",
    "header": "background-color:#1a1f2b;border-radius:12px 12px 0 0;padding:24px 20px;text-align:center;",
    "h1": "margin:0;color:#ffffff;font-size:22px;",
    "h1b": "color:#d4a017;",
    "sub": "margin:6px 0 0;color:#9aa4b2;font-size:13px;",
    "card": "background-color:#ffffff;border-radius:12px;padding:20px;margin-top:12px;border:1px solid #e2e5ea;",
    "card_sinal_compra": "background-color:#ffffff;border-radius:12px;padding:20px;margin-top:12px;border:2px solid #1f883d;",
    "card_sinal_venda": "background-color:#ffffff;border-radius:12px;padding:20px;margin-top:12px;border:2px solid #c93c37;",
    "card_semtrade": "background-color:#fafbfc;border-radius:12px;padding:14px 20px;margin-top:10px;border:1px solid #e2e5ea;",
    "h2": "margin:0 0 10px;font-size:17px;color:#1a1f2b;",
    "h3": "margin:16px 0 6px;font-size:14px;color:#57606a;text-transform:uppercase;letter-spacing:.5px;",
    "p": "margin:8px 0;font-size:15px;line-height:1.6;color:#24292f;",
    "muted": "margin:4px 0;font-size:13px;color:#57606a;line-height:1.5;",
    "badge_compra": "display:inline-block;background-color:#dafbe1;color:#1f883d;font-weight:700;font-size:13px;padding:3px 12px;border-radius:999px;",
    "badge_venda": "display:inline-block;background-color:#ffebe9;color:#c93c37;font-weight:700;font-size:13px;padding:3px 12px;border-radius:999px;",
    "badge_neutro": "display:inline-block;background-color:#eaeef2;color:#57606a;font-weight:600;font-size:12px;padding:3px 12px;border-radius:999px;",
    "table": "width:100%;border-collapse:collapse;margin:10px 0;font-size:13px;",
    "th": "background-color:#f6f8fa;border:1px solid #d8dee4;padding:7px 9px;text-align:left;color:#57606a;font-size:12px;",
    "td": "border:1px solid #d8dee4;padding:7px 9px;color:#24292f;",
    "kv_table": "width:100%;border-collapse:collapse;margin:12px 0;",
    "kv_key": "padding:7px 0;font-size:14px;color:#57606a;width:38%;vertical-align:top;",
    "kv_val": "padding:7px 0;font-size:15px;color:#1a1f2b;font-weight:600;",
    "footer": "padding:18px 8px;text-align:center;color:#9aa4b2;font-size:12px;line-height:1.6;",
    "hr_strip": "height:4px;background-color:#d4a017;border-radius:0 0 4px 4px;font-size:0;line-height:0;",
}


def render_inline(texto: str) -> str:
    texto = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", texto)
    texto = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", texto)
    return texto


def render_tabela(linhas: list[str]) -> str:
    """Converte tabela markdown em <table> com estilos inline."""
    rows = []
    for i, ln in enumerate(linhas):
        celulas = [c.strip() for c in ln.strip().strip("|").split("|")]
        if i == 1 and all(re.fullmatch(r":?-{2,}:?", c) for c in celulas if c):
            continue  # linha separadora
        tag, style = ("th", S["th"]) if i == 0 else ("td", S["td"])
        tds = "".join(f'<{tag} style="{style}">{render_inline(c)}</{tag}>' for c in celulas)
        rows.append(f"<tr>{tds}</tr>")
    return f'<table style="{S["table"]}" cellpadding="0" cellspacing="0">{"".join(rows)}</table>'


def parse_kv(corpo: list[str]) -> tuple[dict, list[str]]:
    """Extrai pares '**Chave:** valor' do início de um cartão de sinal."""
    kv, resto, capturando = {}, [], True
    for ln in corpo:
        m = re.match(r"\*\*(.+?):\*\*\s*(.+)", ln.strip())
        if capturando and m:
            kv[m.group(1)] = m.group(2)
        else:
            if ln.strip():
                capturando = False
            resto.append(ln)
    return kv, resto


KV_LABELS = {
    "Setup": "Estratégia",
    "Direção": "Direção",
    "Entrada": "Preço de entrada",
    "Stop": "Stop (proteção)",
    "Alvo": "Alvo (objetivo)",
    "Trader's Equation": "Equação do Trader",
}


def render_blocos(linhas: list[str]) -> str:
    """Renderiza o corpo de uma seção (parágrafos, listas, tabelas, h3)."""
    html, buf_tab, buf_lista = [], [], []

    def flush():
        if buf_tab:
            html.append(render_tabela(buf_tab[:]))
            buf_tab.clear()
        if buf_lista:
            itens = "".join(f'<li style="{S["p"]}margin:4px 0;">{render_inline(i)}</li>' for i in buf_lista)
            html.append(f'<ul style="margin:8px 0;padding-left:20px;">{itens}</ul>')
            buf_lista.clear()

    for ln in linhas:
        ln_s = ln.strip()
        if ln_s.startswith("|"):
            if buf_lista:
                flush()
            buf_tab.append(ln_s)
            continue
        if buf_tab:
            flush()
        if not ln_s or ln_s == "---":
            flush()
            continue
        if ln_s.startswith("### "):
            flush()
            html.append(f'<h3 style="{S["h3"]}">{render_inline(ln_s[4:])}</h3>')
        elif ln_s.startswith("- "):
            buf_lista.append(ln_s[2:])
        else:
            flush()
            html.append(f'<p style="{S["p"]}">{render_inline(ln_s)}</p>')
    flush()
    return "".join(html)


def render(md: str) -> str:
    md = substitui_tickers(md)
    linhas = md.splitlines()

    titulo, sub_header = "Mesa Brooks", ""
    cards = []

    # ── separa por seções "## " ───────────────────────────────────────────
    secoes, atual = [], None
    for ln in linhas:
        if ln.startswith("# ") and titulo == "Mesa Brooks":
            titulo = ln[2:].strip()
            continue
        if ln.startswith("## "):
            if atual:
                secoes.append(atual)
            atual = {"titulo": ln[3:].strip(), "corpo": []}
        elif atual:
            atual["corpo"].append(ln)
        else:
            sub_header += ln + "\n"
    if atual:
        secoes.append(atual)

    # ── cabeçalho do e-mail ───────────────────────────────────────────────
    m = re.search(r"(\d{4}-\d{2}-\d{2})\s+(\d{2}:?\d{2})", titulo)
    data_fmt = ""
    if m:
        a, me, d = m.group(1).split("-")
        hora = m.group(2).replace(":", "")
        data_fmt = f"{d}/{me}/{a} às {hora[:2]}:{hora[2:]} (UTC)"

    contexto_html = render_blocos(sub_header.splitlines())

    # ── cartões ───────────────────────────────────────────────────────────
    for sec in secoes:
        t = sec["titulo"]
        if t.upper().startswith("SINAL"):
            ativo = render_inline(t.split("—", 1)[1].strip()) if "—" in t else t
            kv, resto = parse_kv(sec["corpo"])
            direcao = kv.get("Direção", "").upper()
            compra = "COMPRA" in direcao
            badge = (f'<span style="{S["badge_compra"]}">▲ COMPRA</span>' if compra
                     else f'<span style="{S["badge_venda"]}">▼ VENDA</span>')
            estilo_card = S["card_sinal_compra"] if compra else S["card_sinal_venda"]
            kv_rows = ""
            for chave, valor in kv.items():
                if chave == "Direção":
                    continue
                label = KV_LABELS.get(chave, chave)
                kv_rows += (f'<tr><td style="{S["kv_key"]}">{label}</td>'
                            f'<td style="{S["kv_val"]}">{render_inline(valor)}</td></tr>')
            cards.append(
                f'<div style="{estilo_card}">'
                f'<h2 style="{S["h2"]}">📌 Sinal de operação — {ativo}</h2>'
                f'{badge}'
                f'<table style="{S["kv_table"]}" cellpadding="0" cellspacing="0">{kv_rows}</table>'
                f'{render_blocos(resto)}'
                f'</div>'
            )
        elif t.upper().startswith("SEM TRADE"):
            ativo = render_inline(t.split("—", 1)[1].strip()) if "—" in t else t
            corpo = render_blocos(sec["corpo"])
            cards.append(
                f'<div style="{S["card_semtrade"]}">'
                f'<p style="margin:0 0 4px;font-size:15px;color:#1a1f2b;"><strong>{ativo}</strong> '
                f'<span style="{S["badge_neutro"]}">Sem operação</span></p>'
                f'<div style="font-size:13px;color:#57606a;">{corpo}</div>'
                f'</div>'
            )
        else:
            cards.append(
                f'<div style="{S["card"]}">'
                f'<h2 style="{S["h2"]}">{render_inline(t)}</h2>'
                f'{render_blocos(sec["corpo"])}'
                f'</div>'
            )

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="{S['body']}">
<div style="{S['wrap']}">
  <div style="{S['header']}">
    <h1 style="{S['h1']}">Mesa <span style="{S['h1b']}">Brooks</span></h1>
    <p style="{S['sub']}">Análise de Price Action · {data_fmt}</p>
  </div>
  <div style="{S['hr_strip']}">&nbsp;</div>
  <div style="{S['card']}">{contexto_html}</div>
  {''.join(cards)}
  <div style="{S['footer']}">
    Relatório gerado automaticamente pela Mesa Brooks (Fase 1 — paper trading).<br>
    Este conteúdo é análise técnica educacional, não recomendação de investimento.<br>
    <a href="https://maraky122.github.io/mesa-brooks" style="color:#d4a017;">Ver todas as análises no site</a>
  </div>
</div>
</body>
</html>"""


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("Uso: render_email.py <relatorio.md> <saida.html>")
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    dst.write_text(render(src.read_text(encoding="utf-8")), encoding="utf-8")
    print(f"OK: {dst} ({dst.stat().st_size} bytes)")
