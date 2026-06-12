# Equação do Trader, Edges e Gestão

## A equação

```
Retorno × P(ganho) > Risco × (1 − P(ganho))
```

- **Risco:** distância até o stop — conhecida.
- **Retorno:** distância até o alvo — conhecida.
- **Probabilidade:** a variável difícil; estimada pela leitura. A maioria dos setups fica entre 40% e 60%.

### Matriz de decisão

| Relação R/R | Tipo | Probabilidade alta (≥60%) | Probabilidade baixa |
|---|---|---|---|
| 1:1 | Scalp | OK | **NUNCA** |
| ≥2:1 | Swing | OK | OK (a relação compensa) |

**Regra absoluta: nunca operar com retorno menor que o risco.** Em dúvida sobre a probabilidade, usar plano 2:1 — a matemática do 2:1 é positiva mesmo com acerto modesto.

### Compensação entre variáveis

Mexeu numa variável, paga nas outras: stop mais curto → probabilidade menor → exige retorno maior. Stop mal posicionado = operação mal estruturada (não adianta encurtar risco artificialmente).

## Onde está o edge (melhores trades por ciclo)

- **BC → MTR no extremo:** probabilidade baixa mas aceitável pelo retorno; checar se a retomada contra não é forte demais.
- **BC → correções a favor da retomada (WT):** probabilidade de retomada > reversão; risco menor que operar rompimento.
- **TR (não estreito) → segundas entradas em reversões dos extremos (BLSH):** paciência por boas entradas.
- **Rompimentos em contexto que leva a MM:** retomadas após correção em tendência forte; BO saindo de BOM.
- **A favor da tendência sempre:** probabilidade de retomada > reversão, exceto com múltiplos sinais de fim.
- **≥50% de correção em tendência:** risco≈retorno com probabilidade a favor da retomada.

## Stops

- **Técnicos (preferir):** atrás da barra de sinal, topo/fundo anterior, início do rompimento, além da linha rompida.
- **Financeiros:** % do saldo, tamanho de barra média/perna média.
- Stop curto só em contexto excelente (RB excepcional, pequeno BO). Em barras sobrepostas/pequenas ou muito espaço de oscilação → stop padrão maior (2x barra de sinal, MM do TTR, início da perna).
- O stop também serve para **dispensar** trades: se o stop necessário não couber no risco máximo da sessão, não há trade.

## Alvos e ajustes pós-entrada

- Alvo inicial nunca menor que o stop. Padrão na dúvida: 2:1.
- Alvos por price action: nível chave seguinte, MM, extremo do range.
- **Trailing em swing:** mover stop atrás de cada novo fundo/topo majoritário na direção do trade.
- Se a premissa morrer (FT decepciona, mercado lateraliza), proteger o resultado — não esperar o stop cheio.
- Se estiver contra a tendência e ela for retomada (H2/L2 forte a favor da tendência, barra coringa contra a posição), **sair imediatamente**.

## Plano padrão (default da Mesa)

1. **Equação:** com stop e alvo definidos, a equação fecha?
2. **Risco fixo:** risco máximo por trade = `saldo × risco_pct` do config.yaml. Tamanho de posição derivado do stop, nunca o contrário.
3. **Timing:** entrada SÓ com gatilho (rompimento da barra de sinal; BO de TTR/triângulo; FBO no extremo do range; falha na EMA 20). Contexto certo sem gatilho = aguardar.
4. Setups perfeitos não existem: probabilidade real raramente passa de 60%. O plano protege contra os 40%.
