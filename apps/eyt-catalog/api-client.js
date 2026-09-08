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

export async function customerLogin({ accountCode, password }) {
  const response = await fetch(`${EYT_API_BASE}/customer-portal/login`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ accountCode, password })
  });
  const session = await parseResponse(response);
  window.EYT_CONFIG = window.EYT_CONFIG || {};
  window.EYT_CONFIG.accessToken = session.accessToken;
  window.EYT_CONFIG.customerId = session.customerId;
  window.EYT_CONFIG.accountId = session.accountId;
  window.EYT_CONFIG.accountCode = session.accountCode;
  return session;
}

export async function customerMe() {
  if (!window.EYT_CONFIG?.accessToken) return null;
  const response = await fetch(`${EYT_API_BASE}/customer-portal/me`, {
    credentials: 'include',
    headers: { Accept: 'application/json', ...authHeaders() }
  });
  return parseResponse(response);
}

export async function customerLogout() {
  if (!window.EYT_CONFIG?.accessToken) return { status: 'logged_out' };
  const response = await fetch(`${EYT_API_BASE}/customer-portal/logout`, {
    method: 'POST',
    credentials: 'include',
    headers: { Accept: 'application/json', ...authHeaders() }
  });
  const result = await parseResponse(response);
  window.EYT_CONFIG.accessToken = null;
  window.EYT_CONFIG.customerId = null;
  window.EYT_CONFIG.accountId = null;
  window.EYT_CONFIG.accountCode = null;
  return result;
}

export async function createLiveOrder({ customerId, warehouseCode = 'MAIN', items, notes = '', idempotencyKey }) {
  const effectiveCustomerId = customerId || window.EYT_CONFIG?.customerId;
  if (!effectiveCustomerId) throw new Error('ابتدا وارد حساب مشتری شوید');
  if (!window.EYT_CONFIG?.accessToken) throw new Error('نشست مشتری معتبر نیست');
  const response = await fetch(`${EYT_API_BASE}/orders`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
      ...(idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {})
    },
    body: JSON.stringify({
      customer_id: effectiveCustomerId,
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
