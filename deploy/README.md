# Production Deployment

This deployment runs the full ArSL platform on one VM:

- Caddy terminates HTTPS for `arsl.hadighazi.com`.
- Nginx serves the built React frontend.
- FastAPI serves `/api/*` for inference, auth, history, and audio files.
- PostgreSQL stores users and prediction history.
- Model checkpoints stay on the VM under `models/` and are mounted into the API container.

## 1. DNS

Create this DNS record wherever `hadighazi.com` is managed:

```text
Type: A
Name: arsl
Value: <VM_EXTERNAL_IP>
TTL: 300
```

The VM must allow inbound TCP `80` and `443`. Caddy will request and renew the TLS certificate automatically.

## 2. First VM Bootstrap

SSH into the VM and run:

```bash
cd ~
curl -fsSL https://raw.githubusercontent.com/ArSl-Translator/arsl-translator/main/deploy/bootstrap_vm.sh | bash
newgrp docker
```

If the repo is already cloned, run the local script instead:

```bash
cd ~/arsl-translator
bash deploy/bootstrap_vm.sh
newgrp docker
```

Edit production secrets:

```bash
cd ~/arsl-translator
nano .env.production
```

Required values:

```text
APP_DOMAIN=arsl.hadighazi.com
ACME_EMAIL=<your-email>
POSTGRES_USER=arsl_user
POSTGRES_PASSWORD=<long-random-password>
POSTGRES_DB=arsl_db
JWT_SECRET_KEY=<output-of-openssl-rand-hex-32>
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
KARSL_MEDIAPIPE_MIRROR_INPUT=true
```

Generate strong values on the VM:

```bash
openssl rand -hex 32
```

## 3. Model Files

Make sure these files exist on the VM:

```text
~/arsl-translator/models/karsl_mediapipe_bilstm_best.pt
~/arsl-translator/models/arabsign_best_model.pt
~/arsl-translator/outputs/index/label2text.json
~/arsl-translator/outputs/index/text2label.json
```

The raw-frame KArSL model is optional. If it is missing, `/health` will show `karsl.loaded=false`, which is fine when using `karsl_mediapipe`.

## 4. Manual Production Deploy

```bash
cd ~/arsl-translator
bash deploy/deploy.sh
```

Open:

```text
https://arsl.hadighazi.com
https://arsl.hadighazi.com/api/health
```

## 5. GitHub Actions CI/CD

Add these repository secrets in GitHub:

```text
DEPLOY_HOST=<VM_EXTERNAL_IP>
DEPLOY_USER=<VM_SSH_USERNAME>
DEPLOY_SSH_KEY=<private SSH key allowed to SSH into the VM>
DEPLOY_PORT=22
DEPLOY_PATH=/home/<VM_SSH_USERNAME>/arsl-translator
```

After that, every push to `main` will:

1. Build the frontend.
2. Validate `docker-compose.prod.yml`.
3. SSH into the VM.
4. Pull the latest code.
5. Rebuild and restart production containers.

You can also trigger the workflow manually from GitHub Actions -> Deploy -> Run workflow.

## 6. Useful Commands

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production ps
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f api
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f caddy
docker compose -f docker-compose.prod.yml --env-file .env.production down
```
