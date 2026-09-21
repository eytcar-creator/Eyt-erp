// E.Y.T public catalog runtime configuration.
// Keep this file free of secrets. The API base is relative so the same build
// can run behind nginx, eyt-catalog.ir, or another reverse proxy.
window.EYT_CONFIG = {
  customerId: null,
  accountId: null,
  accountCode: null,
  accessToken: null,
  warehouseCode: 'MAIN',
  apiBase: '/api/v1',
  productIds: {}
};
