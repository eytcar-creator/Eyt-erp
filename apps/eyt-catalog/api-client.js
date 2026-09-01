const EYT_API_BASE = '/api/v1';

export async function createLiveOrder({ customerId, warehouseCode = 'MAIN', items, notes = '', idempotencyKey }) {
  if (!customerId) throw new Error('شناسه مشتری الزامی است');
  const response = await fetch(`${EYT_API_BASE}/orders`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {})
    },
    body: JSON.stringify({
      customer_id: customerId,
      warehouse_code: warehouseCode,
      channel: 'WEBSITE',
      notes,
      items
    })
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `خطای API: ${response.status}`);
  return body;
}

export async function getLiveOrder(orderNo) {
  const response = await fetch(`${EYT_API_BASE}/orders/${encodeURIComponent(orderNo)}`, { headers: { Accept: 'application/json' } });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `خطای API: ${response.status}`);
  return body;
}

export function orderStage(status) {
  const map = {
    DRAFT: 0, PENDING_CONFIRMATION: 1, CONFIRMED: 1, RESERVED: 2,
    PREPARING: 3, READY_TO_SHIP: 5, SHIPPED: 6, DELIVERED: 7,
    CANCELLED: 0, RETURNED: 0
  };
  return map[status] ?? 0;
}
