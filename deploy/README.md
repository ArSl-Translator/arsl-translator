# Production Deployment

This deployment runs the full ArSL platform on one VM:

- Caddy terminates HTTPS for `arsl.hadighazi.com`.
- Nginx serves the built React frontend.
- FastAPI serves `/api/*` for inference, auth, history, and audio files.
- PostgreSQL stores users and prediction history.
- MLflow serves experiment and model tracking at `/mlflow`.
- Ollama runs a small local open-source language model for Assistive Message Studio.
- Model checkpoints stay on the VM under `models/` and are mounted into the API container.
- The notebook RAG sign index stays on the VM under `models/rag_sign_index/` and is mounted into the API container.

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
ASSISTANT_MODEL=qwen25-healthcare
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
~/arsl-translator/models/rag_sign_index/chroma.sqlite3
~/arsl-translator/outputs/index/label2text.json
~/arsl-translator/outputs/index/text2label.json
```

The raw-frame KArSL model is optional. If it is missing, `/health` will show `karsl.loaded=false`, which is fine when using `karsl_mediapipe`.

The Arabic Alphabet RAG model is also optional. If `sign_index.zip` is on the VM, install it like this:

```bash
cd ~/arsl-translator
rm -rf models/rag_sign_index
mkdir -p models/rag_sign_index
unzip -o ~/Downloads/sign_index.zip -d models/rag_sign_index
find models/rag_sign_index -name chroma.sqlite3 -print
```

The API searches recursively under `models/rag_sign_index`, so it is okay if the zip expands into a nested `sign_index/` folder.

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

Check that the RAG model is visible:

```bash
curl https://arsl.hadighazi.com/api/health
```

Look for:

```json
"arsl_rag": {"loaded": true}
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

The production stack includes Ollama for the optional AI writing assistant used by the Android app.

### Fine-Tuned Model

The current fine-tuned assistant is registered in Ollama as:

```text
qwen25-healthcare
```

It is a Q4_K_M GGUF export of a LoRA fine-tune of `Qwen/Qwen2.5-1.5B-Instruct`, trained for healthcare communication, deaf-to-hearing rewriting, hearing-to-deaf simplification, and ready-to-send chat suggestions.

After downloading or copying the GGUF to the VM, register it:

```bash
cd ~/arsl-translator
bash scripts/assistant_finetune/deploy_to_vm.sh ~/Downloads/qwen25-healthcare-finetuned-q4.gguf
```

The script copies the GGUF into the `arsl_ollama_prod` container, runs `ollama create qwen25-healthcare`, updates `.env.production`, and restarts the API.

The API also applies an output cleanup guardrail. If the fine-tuned model leaks prompt text or example annotations, FastAPI trims that text before returning it to the Android app and reports:

```json
{"source": "ollama_cleaned"}
```

### Base Model Fallback

If you do not want the fine-tuned model, pull the base model once after deployment:

```bash
cd ~/arsl-translator
docker compose -f docker-compose.prod.yml --env-file .env.production up -d ollama
docker compose -f docker-compose.prod.yml --env-file .env.production exec ollama \
  ollama pull qwen2.5:1.5b
```

Then set:

```text
ASSISTANT_MODEL=qwen2.5:1.5b
```

Test the API endpoint:

```bash
curl -X POST https://arsl.hadighazi.com/api/ai/assist \
  -H "Content-Type: application/json" \
  -d '{"text":"I did not understand the doctor","mode":"hearing_to_deaf","context":"clinic","language":"auto"}'
```

The Android app still works without this model; only the optional AI writing assistant needs internet access to the deployed API.

### Host The Optional Offline Android Model

The Android app can offer an optional offline AI download without increasing the APK size. Host the GGUF from the VM:

```bash
cd ~/arsl-translator
mkdir -p hosted_models
cp ~/Downloads/qwen25-healthcare-finetuned-q4.gguf hosted_models/
sha256sum hosted_models/qwen25-healthcare-finetuned-q4.gguf
docker compose -f docker-compose.prod.yml --env-file .env.production up -d caddy
curl -I https://arsl.hadighazi.com/models/qwen25-healthcare-finetuned-q4.gguf
```

Expected model URL:

```text
https://arsl.hadighazi.com/models/qwen25-healthcare-finetuned-q4.gguf
```

Current SHA-256:

```text
d976297d8777616e8b297b544751a6a48155a3e2dada070e60f4a82fbd4f784a
```

The `hosted_models/` folder is ignored by Git and mounted read-only into the Caddy container.

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
