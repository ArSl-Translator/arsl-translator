#!/usr/bin/env bash
# Deploy the fine-tuned GGUF assistant model to the production VM.
#
# Run this on the VM from the repository root:
#   bash scripts/assistant_finetune/deploy_to_vm.sh ~/qwen25-healthcare-finetuned-q4.gguf
#
# It matches the current ArSL deployment, where Ollama runs in Docker as the
# `ollama` compose service / `arsl_ollama_prod` container.

set -euo pipefail

GGUF_FILE="${1:-qwen25-healthcare-finetuned-q4.gguf}"
MODEL_NAME="${MODEL_NAME:-qwen25-healthcare}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env.production}"
OLLAMA_CONTAINER="${OLLAMA_CONTAINER:-arsl_ollama_prod}"
TMP_MODEL_PATH="/tmp/$(basename "$GGUF_FILE")"
TMP_MODELFILE="/tmp/Modelfile.${MODEL_NAME}"

if [ ! -f "$GGUF_FILE" ]; then
    echo "GGUF file not found: $GGUF_FILE"
    echo "Pass the file path, for example:"
    echo "  bash scripts/assistant_finetune/deploy_to_vm.sh ~/qwen25-healthcare-finetuned-q4.gguf"
    exit 1
fi

if [ ! -f "$COMPOSE_FILE" ]; then
    echo "Run this from the repository root. Missing $COMPOSE_FILE"
    exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -qx "$OLLAMA_CONTAINER"; then
    echo "Starting Ollama service..."
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d ollama
fi

echo "Copying GGUF into Ollama container..."
docker cp "$GGUF_FILE" "$OLLAMA_CONTAINER:$TMP_MODEL_PATH"

cat > /tmp/arsl-assistant-Modelfile <<EOF
FROM $TMP_MODEL_PATH

SYSTEM """You are a healthcare communication assistant for deaf and hard-of-hearing users.
You rewrite rough messages clearly, simplify complex instructions, and suggest ready-to-send phrases.
Always preserve the exact meaning. Never reverse who is speaking or who understood whom.
For suggestions, write messages from the patient/user, not from hospital staff.
Respond only in the same language and script as the input."""

PARAMETER temperature 0.0
PARAMETER top_p 0.6
PARAMETER num_predict 220
PARAMETER stop "<|im_end|>"
PARAMETER stop "<|im_start|>"
EOF

docker cp /tmp/arsl-assistant-Modelfile "$OLLAMA_CONTAINER:$TMP_MODELFILE"

echo "Creating Ollama model: $MODEL_NAME"
docker exec "$OLLAMA_CONTAINER" ollama create "$MODEL_NAME" -f "$TMP_MODELFILE"

echo "Updating $ENV_FILE to use $MODEL_NAME"
if grep -q '^ASSISTANT_MODEL=' "$ENV_FILE"; then
    sed -i "s/^ASSISTANT_MODEL=.*/ASSISTANT_MODEL=$MODEL_NAME/" "$ENV_FILE"
else
    echo "ASSISTANT_MODEL=$MODEL_NAME" >> "$ENV_FILE"
fi

echo "Restarting API with the fine-tuned assistant model..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d api

echo "Smoke test through Ollama:"
docker exec "$OLLAMA_CONTAINER" ollama run "$MODEL_NAME" "أعد صياغة هذه الرسالة فقط: انا الم بطني قوي"

echo
echo "Done. Run evaluation:"
echo "  python3 scripts/assistant_finetune/before_after_eval.py > finetuned_results.txt"
