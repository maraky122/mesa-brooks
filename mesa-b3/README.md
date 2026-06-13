# Mesa B3 — Acumulação Price Action (Al Brooks)

Sistema autônomo de análise para **acumulação de longo prazo** em ações, FIIs e ETFs brasileiros, usando exclusivamente price action da metodologia Al Brooks (sem notícias, sem fundamentos).

## Filosofia

- **Só compra, nunca venda** — carteira de acumulação perpétua de baixa volatilidade
- **Aporte mensal fixo** (R$ 1.000), fracionado entre as melhores zonas de compra do mês
- **W1 é o mapa, D1 é o gatilho** — pullbacks à EMA 20, fundos de range, descontos climáticos
- **Caixa não é erro** — mês sem zona boa, o aporte espera

## Estrutura

| Caminho | Função |
|---|---|
| `CLAUDE.md` | Protocolo completo da mesa (sessão, setups, gates, formato) |
| `config.yaml` | Ativos (17), alocação alvo por classe, aporte mensal |
| `knowledge/` | Base Brooks destilada (12 arquivos) |
| `scripts/fetch_data.py` | Baixa OHLC D1/W1 da B3 (Yahoo Finance) |
| `scripts/validate_report.py` | Valida preços dos cartões contra dados reais |
| `scripts/render_email.py` | E-mail HTML estilizado |
| `scripts/portfolio_stats.py` | Alocação atual vs alvo + aporte restante |
| `data/portfolio.csv` | Registro de cada compra realizada |
| `.github/workflows/` | Fetch automático (3×/dia útil) + publicação (site/e-mail) |

## Carteira

- **ETFs (30%):** BOVA11, AUVP11, HASH11, IVVB11
- **FIIs (35%):** MXRF11, HGLG11, KNRI11, XPML11, BTLG11
- **Bancos (20%):** ITUB4, BBAS3, BPAC11
- **Perenes (15%):** WEGE3, ABEV3, EGIE3, TAEE11, BBSE3

## Setup (após criar o repositório)

1. Copie todo este diretório para a raiz do novo repo `mesa-b3`
2. Configure os secrets `MAIL_USERNAME` e `MAIL_PASSWORD` (Gmail app password)
3. Ative GitHub Pages: Settings → Pages → Source: GitHub Actions
4. Rode o workflow "Fetch Market Data B3" manualmente uma vez para popular `data/ohlc/`

> Conteúdo educacional — não é recomendação de investimento.
