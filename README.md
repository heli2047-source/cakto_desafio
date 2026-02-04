# Cakto Mini Split Engine

Projeto que implementa um mini split engine conforme o desafio.

**Como rodar**:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

API:
- `POST /api/v1/checkout/quote` - retorna cálculo sem persistir.
- `POST /api/v1/payments` - confirma pagamento, persiste `Payment`, `LedgerEntry` e `OutboxEvent`.

Request (exemplo):

```
{
  "amount": "297.00",
  "currency": "BRL",
  "payment_method": "card",
  "installments": 3,
  "splits": [
    { "recipient_id": "producer_1", "role": "producer", "percent": 70 },
    { "recipient_id": "affiliate_9", "role": "affiliate", "percent": 30 }
  ]
}
```

Response (exemplo):

```
{
  "payment_id": "pmt_123",
  "status": "captured",
  "gross_amount": "297.00",
  "platform_fee_amount": "26.70",
  "net_amount": "270.30",
  "receivables": [
    { "recipient_id": "producer_1", "role": "producer", "amount": "189.21" },
    { "recipient_id": "affiliate_9", "role": "affiliate", "amount": "81.09" }
  ],
  "outbox_event": {
    "type": "payment_captured",
    "status": "pending"
  }
}
```

**Decisões técnicas**
- Precisão: usei `Decimal` com 2 casas decimais para todos cálculos financeiros.
- Arredondamento: platform fee e net quantizados com `ROUND_HALF_UP`. Distribuição dos recebedores usa `ROUND_DOWN` para cada parcela e a sobra (diferença de centavos) é atribuída ao recebedor com `role="producer"`. Se não existir producer, vai para o recebedor com maior percentual.
- Idempotência: o endpoint `/payments` aceita header `Idempotency-Key`. Se uma `Payment` com a mesma chave existir e o `request_body` for igual, retorna o mesmo resultado sem duplicar (200). Se a chave existir com payload diferente retorna `409 Conflict`.
- Split calculator: criado como abstração `SplitCalculatorInterface` em `app/services/split_calculator.py` e implementado `SimpleSplitCalculator`. O core depende de abstrações, seguindo DIP.
- Persistência mínima: modelos `Payment`, `LedgerEntry`, `OutboxEvent` em `app/models.py`.
- Testes: adicionei testes em `app/tests/test_payments.py` cobrindo PIX, cartão 3x, regra de centavo e idempotência.

O que faria com mais tempo:
- Externalizar publicador da outbox para realmente publicar eventos (Kafka, RabbitMQ).
- Adicionar logs estruturados e métricas de latência/equivocação.
- Melhorar autenticação/autorização e coverage de testes.

Uso de IA: usei assistência de geração para rascunhar código e testes, revisando e adaptando manualmente.
