const EYT_API_BASE = window.EYT_CONFIG?.apiBase || '/api/v1';

function authHeaders() {
  const token = window.EYT_CONFIG?.accessToken;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function persistSession(session) {
  window.EYT_CONFIG = window.EYT_CONFIG || {};
  window.EYT_CONFIG.accessToken = session?.accessToken || null;
  window.EYT_CONFIG.customerId = session?.customerId || null;
  window.EYT_CONFIG.accountId = session?.accountId || null;
  window.EYT_CONFIG.accountCode = session?.accountCode || null;
  if (session?.accessToken) sessionStorage.setItem('EYT_CUSTOMER_SESSION', JSON.stringify(session));
  else sessionStorage.removeItem('EYT_CUSTOMER_SESSION');
}

async function parseResponse(response) {
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `خطای API: ${response.status}`);
  return body;
}

export async function customerLogin({ accountCode, password }) {
  const response = await fetch(`${EYT_API_BASE}/customer-portal/login`, {
    method: 'POST', credentials: 'include',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ accountCode, password })
  });
  const session = await parseResponse(response);
  persistSession(session);
  return session;
}

export async function customerMe() {
  if (!window.EYT_CONFIG?.accessToken) return null;
  const response = await fetch(`${EYT_API_BASE}/customer-portal/me`, {
    credentials: 'include', headers: { Accept: 'application/json', ...authHeaders() }
  });
  return parseResponse(response);
}

export async function customerLogout() {
  if (!window.EYT_CONFIG?.accessToken) return { status: 'logged_out' };
  const response = await fetch(`${EYT_API_BASE}/customer-portal/logout`, {
    method: 'POST', credentials: 'include', headers: { Accept: 'application/json', ...authHeaders() }
  });
  const result = await parseResponse(response);
  persistSession(null);
  updateAuthUI(null);
  return result;
}

export async function customerPrices({ productId, limit = 200 } = {}) {
  if (!window.EYT_CONFIG?.accessToken) throw new Error('ابتدا وارد حساب مشتری شوید');
  const query = new URLSearchParams({ limit: String(limit) });
  if (productId) query.set('product_id', productId);
  const response = await fetch(`${EYT_API_BASE}/customer-portal/prices?${query}`, {
    credentials: 'include', headers: { Accept: 'application/json', ...authHeaders() }
  });
  return parseResponse(response);
}

export async function customerOrders(limit = 50) {
  if (!window.EYT_CONFIG?.accessToken) throw new Error('ابتدا وارد حساب مشتری شوید');
  const response = await fetch(`${EYT_API_BASE}/customer-portal/orders?limit=${encodeURIComponent(limit)}`, {
    credentials: 'include', headers: { Accept: 'application/json', ...authHeaders() }
  });
  return parseResponse(response);
}

export async function customerOrder(orderNo) {
  if (!window.EYT_CONFIG?.accessToken) throw new Error('ابتدا وارد حساب مشتری شوید');
  const response = await fetch(`${EYT_API_BASE}/customer-portal/orders/${encodeURIComponent(orderNo)}`, {
    credentials: 'include', headers: { Accept: 'application/json', ...authHeaders() }
  });
  return parseResponse(response);
}

export async function createLiveOrder({ customerId, warehouseCode = 'MAIN', items, notes = '', idempotencyKey }) {
  const effectiveCustomerId = customerId || window.EYT_CONFIG?.customerId;
  if (!effectiveCustomerId) throw new Error('ابتدا وارد حساب مشتری شوید');
  if (!window.EYT_CONFIG?.accessToken) throw new Error('نشست مشتری معتبر نیست');
  const response = await fetch(`${EYT_API_BASE}/orders`, {
    method: 'POST', credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...authHeaders(), ...(idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {}) },
    body: JSON.stringify({ customer_id: effectiveCustomerId, warehouse_code: warehouseCode, channel: 'WEBSITE', notes, items })
  });
  return parseResponse(response);
}

export async function getLiveOrder(orderNo) {
  return customerOrder(orderNo);
}

export function orderStage(status) {
  const map = { DRAFT: 0, PENDING_CONFIRMATION: 1, CONFIRMED: 1, RESERVED: 2, PREPARING: 3, READY_TO_SHIP: 5, SHIPPED: 6, DELIVERED: 7, FULFILLED: 7, CANCELLED: 0, RETURNED: 0 };
  return map[status] ?? 0;
}

function updateAuthUI(me) {
  const host = document.getElementById('eytCustomerAuth');
  if (!host) return;
  if (me) {
    host.innerHTML = `<span class="eyt-auth-user">${escapeHtml(me.customerName || me.accountCode || 'مشتری')}</span><button type="button" id="eytLogoutBtn">خروج</button>`;
    document.getElementById('eytLogoutBtn').onclick = () => customerLogout().catch(e => alert(e.message));
  } else {
    host.innerHTML = '<button type="button" id="eytLoginBtn">ورود مشتری</button>';
    document.getElementById('eytLoginBtn').onclick = openLogin;
  }
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));
}

function openLogin() {
  let modal = document.getElementById('eytLoginModal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'eytLoginModal';
    modal.innerHTML = `<div class="eyt-login-box"><button class="eyt-close" type="button">×</button><h2>ورود مشتری E.Y.T</h2><p>برای دیدن قیمت اختصاصی و ثبت سفارش آنلاین وارد حساب خود شوید.</p><form id="eytLoginForm"><label>کد حساب</label><input name="accountCode" required autocomplete="username"><label>رمز عبور</label><input name="password" type="password" required autocomplete="current-password"><div id="eytLoginError"></div><button class="eyt-login-submit" type="submit">ورود</button></form></div>`;
    document.body.appendChild(modal);
    modal.querySelector('.eyt-close').onclick = () => modal.remove();
    modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });
    modal.querySelector('form').onsubmit = async e => {
      e.preventDefault();
      const form = e.currentTarget, error = modal.querySelector('#eytLoginError');
      const btn = form.querySelector('button[type=submit]'); btn.disabled = true; error.textContent = '';
      try {
        const session = await customerLogin({ accountCode: form.accountCode.value.trim(), password: form.password.value });
        const profile = await customerMe();
        updateAuthUI(profile || session);
        modal.remove();
        window.dispatchEvent(new CustomEvent('eyt:customer-login', { detail: profile || session }));
      } catch (err) { error.textContent = err.message; }
      finally { btn.disabled = false; }
    };
  }
}

function addAuthStyles() {
  if (document.getElementById('eytAuthStyles')) return;
  const style = document.createElement('style'); style.id = 'eytAuthStyles';
  style.textContent = `#eytCustomerAuth{display:flex;align-items:center;gap:7px}#eytCustomerAuth button{border:0;background:#991b1b;color:#fff;border-radius:8px;padding:8px 11px;cursor:pointer;font-weight:700}.eyt-auth-user{font-size:12px;color:#fff;max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.eyt-auth-user+button{background:#374151!important}.eyt-close{position:absolute;left:12px;top:10px;background:#e5e7eb!important;color:#111!important;font-size:20px}.eyt-login-box{position:relative;background:#fff;width:min(420px,92vw);padding:24px;border-radius:16px;box-shadow:0 15px 60px #0004}.eyt-login-box h2{margin-top:0}.eyt-login-box label{display:block;margin:12px 0 5px;font-size:12px;color:#475569}.eyt-login-box input{width:100%;padding:11px;border:1px solid #d1d5db;border-radius:8px}.eyt-login-submit{width:100%;margin-top:16px;border:0;background:#991b1b;color:#fff;padding:11px;border-radius:8px;font-weight:700}.eyt-login-box p{font-size:12px;color:#64748b}.eyt-login-box #eytLoginError{color:#991b1b;font-size:12px;margin-top:10px}.eyt-login-box form{display:block}#eytLoginModal{position:fixed;inset:0;background:#0008;display:flex;align-items:center;justify-content:center;z-index:9999;padding:16px}`;
  document.head.appendChild(style);
}

function mountCustomerAuth() {
  addAuthStyles();
  const top = document.querySelector('.top');
  if (!top || document.getElementById('eytCustomerAuth')) return;
  const host = document.createElement('div'); host.id = 'eytCustomerAuth'; top.appendChild(host);
  let session = null;
  try { session = JSON.parse(sessionStorage.getItem('EYT_CUSTOMER_SESSION') || 'null'); } catch (_) {}
  if (session?.accessToken) persistSession(session);
  customerMe().then(me => updateAuthUI(me)).catch(() => { persistSession(null); updateAuthUI(null); });
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mountCustomerAuth, { once: true });
else mountCustomerAuth();
