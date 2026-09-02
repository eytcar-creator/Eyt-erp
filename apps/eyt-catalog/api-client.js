const EYT_API_BASE = window.EYT_CONFIG?.apiBase || '/api/v1';

function authHeaders() {
  const token = window.EYT_CONFIG?.accessToken;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function parseResponse(response) {
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `خطای API: ${response.status}`);
  return body;
}

export async function createLiveOrder({ customerId, warehouseCode = 'MAIN', items, notes = '', idempotencyKey }) {
  if (!customerId) throw new Error('شناسه مشتری الزامی است');
  const response = await fetch(`${EYT_API_BASE}/orders`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
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
  return parseResponse(response);
}

export async function getLiveOrder(orderNo) {
  const response = await fetch(`${EYT_API_BASE}/orders/${encodeURIComponent(orderNo)}`, {
    credentials: 'include',
    headers: { Accept: 'application/json', ...authHeaders() }
  });
  return parseResponse(response);
}

export function orderStage(status) {
  const map = {
    DRAFT: 0, PENDING_CONFIRMATION: 1, CONFIRMED: 1, RESERVED: 2,
    PREPARING: 3, READY_TO_SHIP: 5, SHIPPED: 6, DELIVERED: 7,
    CANCELLED: 0, RETURNED: 0
  };
  return map[status] ?? 0;
}
