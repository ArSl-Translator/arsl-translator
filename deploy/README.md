# Production Deployment

This deployment runs the full ArSL platform on one VM:

- Caddy terminates HTTPS for `arsl.hadighazi.com`.
- Nginx serves the built React frontend.
- FastAPI serves `/api/*` for inference, auth, history, and audio files.
- PostgreSQL stores users and prediction history.
- MLflow serves experiment and model tracking at `/mlflow`.
- Ollama runs a small local open-source language model for Assistive Message Studio.
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
ASSISTANT_MODEL=qwen2.5:1.5b
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
https://arsl.hadighazi.com/mlflow
```

## 5. MLflow Tracking

Production includes an MLflow tracking server. It stores metadata and model artifacts on the VM under:

```text
~/arsl-translator/mlruns/
```

After the current model files are present in `models/`, log them into MLflow:

```bash
cd ~/arsl-translator
docker compose -f docker-compose.prod.yml --env-file .env.production exec api \
  python scripts/mlflow_log_current_models.py --tracking_uri http://mlflow:5000
```

Then open:

```text
https://arsl.hadighazi.com/mlflow
```

You should see a `serving_models` experiment with runs for the current KArSL MediaPipe and ArabSign checkpoints. If you only want metadata and do not want to upload the checkpoint files into MLflow artifacts, add `--skip_artifacts`.

## 6. Assistive Message Studio

The production stack includes Ollama for the optional AI writing assistant used by the Android app. Pull the model once after deployment:

```bash
cd ~/arsl-translator
docker compose -f docker-compose.prod.yml --env-file .env.production up -d ollama
docker compose -f docker-compose.prod.yml --env-file .env.production exec ollama \
  ollama pull qwen2.5:1.5b
```

Test the API endpoint:

```bash
curl -X POST https://arsl.hadighazi.com/api/ai/assist \
  -H "Content-Type: application/json" \
  -d '{"text":"I did not understand the doctor","mode":"hearing_to_deaf","context":"clinic","language":"auto"}'
```

The Android app still works without this model; only the optional AI writing assistant needs internet access to the deployed API.

## 7. GitHub Actions CI/CD

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

## 8. Useful Commands

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production ps
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f api
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f caddy
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f mlflow
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f ollama
docker compose -f docker-compose.prod.yml --env-file .env.production down
```
