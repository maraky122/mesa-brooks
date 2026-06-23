#!/usr/bin/env python3
"""
auto_analysis.py — gera o relatório de análise chamando a API do Claude.
Executado pelo GitHub Actions nos horários estratégicos de mercado.
"""

import anthropic
import subprocess
import sys
import re
from datetime import datetime, timezone
from pathlib import Path


def read_csv_tail(path, n=25):
    try:
        lines = Path(path).read_text().strip().split("\n")
        header = lines[0]
        tail = lines[max(1, len(lines) - n) :]
        return header + "\n" + "\n".join(tail)
    except FileNotFoundError:
        return f"[NÃO ENCONTRADO: {path}]"


def build_knowledge_context():
    parts = []
    for f in sorted(Path("knowledge").glob("*.md")):
        parts.append(f"### {f.name}\n{f.read_text()}")
    return "\n\n".join(parts)


def build_data_block():
    tickers = {
        "ESF": ["1d", "4h", "1h"],
        "GCF": ["1d", "4h", "1h"],
        "SIF": ["1d", "4h", "1h"],
        "CLF": ["1d", "4h", "1h"],
        "BTCUSDT": ["1d", "4h", "1h"],
        "ETHUSDT": ["1d", "4h", "1h"],
        "SPY": ["1d", "4h", "1h"],
        "QQQ": ["1d", "4h", "1h"],
        "NVDA": ["1d", "4h", "1h"],
    }
    parts = []
    for ticker, tfs in tickers.items():
        for tf in tfs:
            path = f"data/ohlc/{ticker}_{tf}.csv"
            parts.append(f"#### {ticker} {tf}\n```csv\n{read_csv_tail(path, 60)}\n```")
    return "\n\n".join(parts)


def read_file(path, fallback="Não encontrado"):
    try:
        return Path(path).read_text()
    except FileNotFoundError:
        return fallback


def git_run(*args, check=False):
    return subprocess.run(["git"] + list(args), capture_output=True, text=True, check=check)


def main():
    now = datetime.now(timezone.utc)
    now_str = now.strftime("%Y-%m-%d %H:%M UTC")
    timestamp = now.strftime("%Y-%m-%d-%H%M")
    report_path = Path(f"reports/{timestamp}.md")

    print(f"[auto_analysis] {now_str} — iniciando análise")

    # Pull latest data before analyzing
    git_run("pull", "--rebase", "origin", "main")

    # Build system prompt: CLAUDE.md + base de conhecimento
    claude_md = read_file("CLAUDE.md")
    knowledge = build_knowledge_context()
    system_prompt = f"{claude_md}\n\n---\n\n# Base de Conhecimento\n\n{knowledge}"

    # Build user message: contexto operacional + dados
    fetch_summary = read_file("data/fetch_summary.txt")
    calendar_json = read_file("data/calendar.json", "{}")
    suspended = read_file("data/suspended_setups.txt", "Nenhum setup suspenso")
    journal = read_file("data/journal.csv", "Vazio")
    data_block = build_data_block()

    user_message = f"""Hora atual (UTC): {now_str}

## data/fetch_summary.txt
{fetch_summary}

## data/calendar.json
{calendar_json}

## data/suspended_setups.txt
{suspended}

## data/journal.csv
{journal}

## Dados OHLC — últimas 60 barras por série
{data_block}

---

Execute o protocolo completo de sessão conforme o CLAUDE.md e a base de conhecimento.
Produza o relatório completo no formato exato definido. Não use markdown de explicação — comece direto pelo cabeçalho `# Mesa Brooks`."""

    # Call Claude API
    client = anthropic.Anthropic()
    print("[auto_analysis] chamando API Claude...")

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    report_text = message.content[0].text
    print(f"[auto_analysis] resposta recebida ({len(report_text)} chars)")

    # Save report
    report_path.write_text(report_text)
    print(f"[auto_analysis] relatório salvo: {report_path}")

    # Validate
    val = subprocess.run(
        ["python3", "scripts/validate_report.py", str(report_path)],
        capture_output=True,
        text=True,
    )
    print(val.stdout)
    if "FAIL" in val.stdout:
        print("[auto_analysis] VALIDAÇÃO FALHOU — abortando commit")
        print(val.stderr)
        sys.exit(1)

    # Count signals for commit message
    n_sinais = len(re.findall(r"^## SINAL", report_text, re.M))
    commit_msg = f"relatorio: sessão {timestamp} UTC — {n_sinais} sinal(is) [auto]"

    # Commit and push
    git_run("config", "user.name", "mesa-brooks-bot")
    git_run("config", "user.email", "bot@mesa-brooks")
    git_run("add", str(report_path), "data/journal.csv")

    diff = git_run("diff", "--cached", "--quiet")
    if diff.returncode == 0:
        print("[auto_analysis] nada a commitar (relatório idêntico ao anterior)")
        sys.exit(0)

    git_run("commit", "-m", commit_msg, check=True)

    # Push with retry on conflict
    for attempt in range(4):
        push = git_run("push", "-u", "origin", "main")
        if push.returncode == 0:
            print(f"[auto_analysis] push OK — {commit_msg}")
            break
        print(f"[auto_analysis] push falhou (tentativa {attempt+1}/4), fazendo pull --rebase...")
        git_run("pull", "--rebase", "origin", "main")
    else:
        print("[auto_analysis] push falhou após 4 tentativas")
        sys.exit(1)


if __name__ == "__main__":
    main()
