# AWS EC2 Deployment

Target architecture:

```text
Elastic IP + Domain + HTTPS
EC2 t3.medium
Docker Compose
├─ caddy: HTTPS reverse proxy
├─ app: FastAPI + React SPA
└─ postgres: local PostgreSQL volume
```

## 1. GitHub / GHCR

Recommended repository name:

```text
phishguard-soc
```

The GHCR image will be:

```text
ghcr.io/<owner>/phishguard-soc:latest
```

The workflow file is `.github/workflows/ghcr.yml`.

## 2. EC2 Files

Create the runtime directory:

```bash
sudo mkdir -p /opt/phishguard
sudo chown -R ubuntu:ubuntu /opt/phishguard
cd /opt/phishguard
```

Required files on EC2:

```text
/opt/phishguard/
├─ docker-compose.prod.yml
├─ Caddyfile
├─ .env
└─ models/
   ├─ url_model.pkl
   └─ bert/
      ├─ config.json
      ├─ model.safetensors
      ├─ tokenizer.json
      └─ ...
```

Models are not included in the Docker image. Upload them directly:

```bash
scp -r backend/models ubuntu@<EC2_IP>:/opt/phishguard/models
```

## 3. Environment

Copy `.env.prod.example` to `.env` and replace every placeholder.

Important production values:

```env
APP_IMAGE=ghcr.io/<owner>/phishguard-soc:latest
DOMAIN=soc.example.com
FRONTEND_URL=https://soc.example.com
GOOGLE_REDIRECT_URI=https://soc.example.com/auth/callback
DATABASE_URL=postgresql://soc:<password>@postgres:5432/soc_phishing
NLP_MODEL_PATH=/app/models/bert
URL_MODEL_PATH=/app/models/url_model.pkl
```

## 4. Security Group

Allow:

- `22/tcp`: your IP only
- `80/tcp`: public
- `443/tcp`: public

Do not expose:

- `5432/tcp`
- `8000/tcp`

## 5. Start

```bash
docker login ghcr.io
docker compose --env-file .env -p phishguard -f docker-compose.prod.yml pull
docker compose --env-file .env -p phishguard -f docker-compose.prod.yml up -d
docker compose -p phishguard -f docker-compose.prod.yml ps
```

## 6. Backup

```bash
mkdir -p backups
docker compose -p phishguard -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backups/soc_$(date +%Y%m%d_%H%M%S).sql
```

## 7. Stop For Cost Control

Before stopping EC2:

```bash
docker compose -p phishguard -f docker-compose.prod.yml ps
```

Then stop the instance from AWS Console. Keep the Elastic IP attached so DNS,
Google OAuth redirect URI, and Pub/Sub push URL remain stable.

After the presentation, terminate EC2 and release Elastic IP / EBS volumes if no
longer needed.
