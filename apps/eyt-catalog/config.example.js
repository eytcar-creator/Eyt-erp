// Copy to a deployment-specific config.js and load it before index.html's module script.
// Never commit real customer IDs, access tokens, or other secrets to Git.
window.EYT_CONFIG = {
  customerId: 'CUSTOMER-UUID-FROM-ERP',
  warehouseCode: 'MAIN',
  productIds: {
    'EYT-ARI-TRE-001': 'PRODUCT-UUID-FROM-ERP',
    'EYT-S7-EM-001': 'PRODUCT-UUID-FROM-ERP',
    'EYT-M315-KIT-001': 'PRODUCT-UUID-FROM-ERP',
    'EYT-X22-BJ-001': 'PRODUCT-UUID-FROM-ERP',
    'EYT-S5-BJ-001': 'PRODUCT-UUID-FROM-ERP',
    'EYT-X33-KIT-001': 'PRODUCT-UUID-FROM-ERP'
  },
  accessToken: null
};
