# Weaver — Deployment & Usage Guide

This document explains how to run the Weaver application locally and how to deploy it to an Ubuntu Server (>= 24.04). It covers prerequisites, environment variables, a systemd service example, Nginx reverse-proxy and TLS, Prometheus scraping, and troubleshooting tips.

## Overview

- App entry: `uvicorn src.weaver.main:app`
- HTTP server: FastAPI + Uvicorn
- Rate limiter: Redis-backed with in-memory fallback
- DB: MongoDB (Beanie / Motor)
- Metrics: Prometheus (`/metrics` endpoint)

## Quick local development

Prerequisites:

- Python 3.12 installed
- Git

Commands:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# run tests
.venv/bin/python -m pytest -q
# run dev server with auto-reload
.venv/bin/uvicorn src.weaver.main:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 for the API. Metrics are at `/metrics`. Health endpoints are available under `/health`.

## Environment variables

Configure these environment variables for production. Values shown are examples.

- `SECRET_KEY` — cryptographic secret (required in production when `REQUIRE_SECRET_IN_PRODUCTION` is true)
- `ENV` — `production` or `development`
- `REQUIRE_SECRET_IN_PRODUCTION` — `true`/`false`
- `REDIS_URL` — e.g. `redis://localhost:6379/0`
- `MONGO_URI` or `MONGODB_URL` — MongoDB connection string (follow your config naming)
- `ALLOWED_HOSTS` — comma-separated hosts for TrustedHostMiddleware
- `CORS_ALLOWED_ORIGINS` — comma-separated list of allowed origins
- `FORCE_HTTPS` — `true`/`false` (enable HTTPS redirect)
- `HSTS_MAX_AGE`, `HSTS_INCLUDE_SUBDOMAINS`, `HSTS_PRELOAD` — HSTS options
- SMTP settings (if email sending is required): `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_USE_TLS`

Store production environment values in a secure location. Systemd `EnvironmentFile` examples are below.

## Ubuntu Server (>= 24.04) deployment

This section outlines a straightforward server deployment using systemd and Nginx.

1. Prepare the server

```bash
sudo apt update
sudo apt install -y git python3.12-venv build-essential nginx certbot python3-certbot-nginx redis-server
# Install MongoDB via official instructions for Ubuntu or use a managed MongoDB service
```

2. Create app user and directory

```bash
sudo useradd --system --create-home --home-dir /opt/weaver -s /usr/sbin/nologin weaver
sudo mkdir -p /opt/weaver
sudo chown weaver:weaver /opt/weaver
sudo -u weaver git clone <your-repo-url> /opt/weaver/app
cd /opt/weaver/app
sudo -u weaver python3.12 -m venv /opt/weaver/venv
sudo -u weaver /opt/weaver/venv/bin/pip install -r requirements.txt
```

3. Environment file

Create `/etc/weaver/weaver.env` (root-owned, not world-readable):

```
# /etc/weaver/weaver.env
ENV=production
SECRET_KEY=long-random-secret
REDIS_URL=redis://127.0.0.1:6379/0
MONGO_URI=mongodb://127.0.0.1:27017/weaver
ALLOWED_HOSTS=example.com,www.example.com
FORCE_HTTPS=true
# SMTP_* as needed
```

Protect the file:

```bash
sudo chown root:weaver /etc/weaver/weaver.env
sudo chmod 640 /etc/weaver/weaver.env
```

4. Systemd service

Create `/etc/systemd/system/weaver.service`:

```
[Unit]
Description=Weaver FastAPI application
After=network.target

[Service]
User=weaver
Group=weaver
WorkingDirectory=/opt/weaver/app
EnvironmentFile=/etc/weaver/weaver.env
ExecStart=/opt/weaver/venv/bin/uvicorn src.weaver.main:app \
  --host 127.0.0.1 --port 8000 --workers 4 --proxy-headers
Restart=on-failure
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

Reload systemd and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now weaver.service
sudo systemctl status weaver.service
sudo journalctl -u weaver -f
```

Systemd hardening (recommended)

You can add a few simple hardening options to the `[Service]` section to reduce the impact of a compromise. Add these lines to `/etc/systemd/system/weaver.service` inside the `[Service]` block:

```
ProtectSystem=full
ProtectHome=true
PrivateTmp=true
NoNewPrivileges=true
# Drop additional capabilities if not needed; keep minimal privileges
AmbientCapabilities=
```

These options help isolate the process, prevent access to most of the filesystem, and disable privilege escalation. Keep `EnvironmentFile=/etc/weaver/weaver.env` as shown above (root-owned, 640) so secrets remain protected.

5. Nginx reverse proxy and TLS (example)

Create an Nginx site file `/etc/nginx/sites-available/weaver`:

```
server {
    listen 80;
    server_name example.com www.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $http_connection;
        proxy_read_timeout 120s;
    }

    # Expose metrics to localhost/prometheus server only if desired
    location /metrics {
        proxy_pass http://127.0.0.1:8000/metrics;
        allow 127.0.0.1;
        # Add allow <prometheus-ip>; deny all; if Prometheus is remote
    }
}
```

Enable and test:

```bash
sudo ln -s /etc/nginx/sites-available/weaver /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
# Obtain cert with certbot
sudo certbot --nginx -d example.com -d www.example.com
```

6. Firewall (UFW) example

```bash
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

## Prometheus scraping

Add a job to your `prometheus.yml`:

```yaml
- job_name: 'weaver'
  static_configs:
    - targets: ['127.0.0.1:8000']
      labels:
        service: weaver
```

Prometheus will scrape `/metrics` automatically.

## CI and automated checks

- This repository contains `.github/workflows/ci.yml` which runs `ruff`, `bandit`, and the test suite, and verifies the `/metrics` endpoint in CI. Keep CI secrets in GitHub Actions secrets.

## Running database migrations / startup tasks

- If your app requires DB initialization (Beanie models), ensure the app's startup lifespan initializes connections. The app's lifespan code already attempts to initialize DB and Redis on startup.

## Troubleshooting

- Check logs: `sudo journalctl -u weaver -f`
- Check service status: `sudo systemctl status weaver`
- Check Redis: `redis-cli ping` (should reply `PONG`)
- Check MongoDB: `mongo --eval 'db.runCommand({ping:1})'`
- Verify metrics: `curl http://127.0.0.1:8000/metrics | head`

## Security notes

- Ensure `SECRET_KEY` is set and not checked into source control.
- Use `ALLOWED_HOSTS` and `TrustedHostMiddleware` to restrict accepted host headers.
- Enable `FORCE_HTTPS` and HSTS in production.

## Next steps and optional improvements

- Use a process manager (e.g., systemd) as shown, or containerize with Docker + Kubernetes for larger deployments.
- Add health-check endpoints to your load balancer to use `/health/redis-optional` or admin health endpoints.
- Integrate Sentry or other observability as needed.

---
Documentation created for basic production deployment and local usage.
