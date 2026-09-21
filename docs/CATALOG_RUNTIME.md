# E.Y.T Catalog runtime configuration

The catalog is configured to call the ERP API through the same origin at `/api/v1`.

This avoids putting database credentials, JWT secrets, Firebase credentials, or other private configuration in the browser.

For the Docker deployment, nginx proxies `/api/` to the FastAPI service. Therefore the public catalog can be served from the catalog domain without hard-coding a production API hostname.

Production requirements:
- reverse proxy / DNS must point the catalog domain to the deployed catalog service;
- the FastAPI service and PostgreSQL must be running;
- real customer credentials must be provisioned through the ERP, not committed to this repository.
