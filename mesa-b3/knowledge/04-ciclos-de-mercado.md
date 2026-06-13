# Ciclos de Mercado

## A sequência

O mercado alterna entre fases num ciclo que se repete em todo timeframe:

```
BO (rompimento/spike) → TC (canal estreito) → BC (canal amplo) → TR (lateralidade) → novo BO...
```

- **BO / Spike:** barras de tendência consecutivas, corpos grandes, pouca sobreposição. Momento de maior convicção.
- **TC (canal estreito / tight channel):** tendência continua mas com correções mínimas. Pullbacks são rasos (H1/L1).
- **BC (canal amplo / broad channel):** correções profundas, duas pernas, sobe-e-desce dentro de uma inclinação. Ambos os lados operam.
- **TR (trading range / lateralidade):** equilíbrio. Topo e fundo definidos, leitura bilateral.
- **TTR (tight trading range):** lateralidade estreita — barras sobrepostas, sem espaço. NÃO operar dentro.

## Como operar cada fase

| Fase | Modelo operacional | O que evitar |
|---|---|---|
| **BO/Spike** | A favor, em qualquer pausa pequena (H1/L1). Probabilidade ≥60% a favor | Contra-tendência (falha ~80%) e esperar correção profunda que não vem |
| **TC** | A favor em pullbacks pequenos; segurar swing | Reversões; rompimento de linha do canal falha ~75% |
| **BC** | Correções a favor da retomada (WT). MTR só no extremo, com os 4 requisitos | Comprar topo/vender fundo do canal |
| **TR** | BLSH: comprar baixa, vender alta, com segunda entrada (ver [09-lateralidades.md](09-lateralidades.md)) | Operar rompimento sem confirmação (maioria falha → FBO) |
| **TTR** | Não operar dentro. Aguardar BO com fechamento forte fora | Qualquer ordem a mercado dentro do range |

## Transições — o que observar

- **Spike → canal:** primeira correção depois do spike define a inclinação do canal que vem.
- **Canal → TR:** quando uma correção rompe a linha do canal E a tentativa de retomada falha (segunda perna não faz novo extremo).
- **TR → BO:** acumulação perto de um dos extremos do range, barras de tendência aparecendo no rompimento.

## Implicação para o protocolo

O Passo B (H4) deve nomear a fase explicitamente. A fase determina QUAL setup do playbook é elegível:
- Impulso/TC → só Pullback com Tendência.
- TR largo → Breakout de Range (na confirmação) ou BLSH com segunda entrada.
- BC no extremo → único contexto onde Reversão em Extremo é aceitável.
