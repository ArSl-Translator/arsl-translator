# Assistant Fine-Tuning Workflow

This folder contains the optional fine-tuning workflow for Assistive Message Studio, the chat-integrated generative AI layer used by the Android Bluetooth app.

The assistant is served by:

```text
POST /api/ai/assist
```

It is used by:

- Android message action: `Make clearer`
- Android message action: `Simplify`
- Android composer suggestions

## Current Models

Base model:

```env
ASSISTANT_MODEL=qwen2.5:1.5b
```

Fine-tuned model:

```env
ASSISTANT_MODEL=qwen25-healthcare
```

The fine-tuned model is a LoRA fine-tune of:

```text
Qwen/Qwen2.5-1.5B-Instruct
```

The Colab script merges the LoRA adapter into the base model, converts it to GGUF, quantizes it to Q4_K_M, and registers it with Ollama on the VM.

## Files

```text
scripts/assistant_finetune/
  dataset.jsonl          Supervised examples for the 3 assistant modes
  colab_finetune.py      One-cell Google Colab LoRA fine-tuning script
  before_after_eval.py   Live API evaluator for base vs fine-tuned behavior
  deploy_to_vm.sh        VM script that registers the GGUF model with Ollama
```

## Assistant Modes

| Mode | User flow | Expected behavior |
|---|---|---|
| `deaf_to_hearing` | Assisted user sends rough wording to a hearing person | Rewrite the same meaning as clear natural language |
| `hearing_to_deaf` | Hearing person sends a longer message to the assisted user | Simplify into short direct language |
| `suggestions` | User taps the composer sparkle button | Produce 3 to 5 ready-to-send messages from the user's voice |

The model must preserve the speaker and direction. For example, if the user writes that they did not understand the doctor, the model must not reverse it into "the doctor did not understand me."

## Dataset Goal

The dataset targets observed production bugs:

- Arabic input sometimes produced English or Chinese output.
- Arabic `deaf_to_hearing` sometimes produced helper-style replies instead of rewrites.
- Suggestions sometimes sounded like hospital staff, not the patient.
- The model sometimes reversed who understood whom.
- The model sometimes leaked prompt text or training annotations.

Examples:

```text
Input: انا الم بطني قوي
Expected: أشعر بألم شديد في بطني.

Input: دكتور انا ما فهم كلام دواء
Expected: دكتور، لم أفهم تعليمات الدواء. من فضلك اشرحها لي بطريقة أبسط.

Input: انا في المستشفى واريد اسأل عن موعدي
Expected:
1. متى موعدي؟
2. أين أنتظر؟
3. هل تأخر موعدي؟
```

Important dataset hygiene:

- Do not include arrows such as `←` in target outputs.
- Do not include comments like "good", "bad", "correct", or "wrong" in target outputs.
- Do not include explanations of why an answer is correct.
- Target outputs should contain only the final user-facing message.

## Step 1: Capture Baseline On The VM

```bash
cd ~/arsl-translator
git pull origin main
python3 scripts/assistant_finetune/before_after_eval.py > baseline_results.txt
cat baseline_results.txt
```

The evaluator calls:

```text
https://arsl.hadighazi.com/api/ai/assist
```

To evaluate a local API instead:

```bash
ASSIST_EVAL_URL=http://localhost:8000/api/ai/assist \
python3 scripts/assistant_finetune/before_after_eval.py
```

## Step 2: Fine-Tune In Google Colab

Use Colab because a free T4 GPU can run the LoRA fine-tune while the VM is not sized for GPU training.

1. Open <https://colab.research.google.com>.
2. Create a new notebook.
3. Runtime -> Change runtime type -> `T4 GPU`.
4. Upload:

```text
scripts/assistant_finetune/dataset.jsonl
```

5. Open:

```text
scripts/assistant_finetune/colab_finetune.py
```

6. Paste the whole file into one Colab cell.
7. Run it.

The script installs dependencies, trains, runs quick inference tests, merges the adapter, converts to GGUF, quantizes to Q4_K_M, and downloads:

```text
qwen25-healthcare-finetuned-q4.gguf
```

Training settings used:

```text
Base model: Qwen/Qwen2.5-1.5B-Instruct
Technique: LoRA supervised fine-tuning
LoRA rank: 16
LoRA alpha: 32
Epochs: 5
Batch size: 2
Gradient accumulation: 4
Learning rate: 2e-4
Quantized export: Q4_K_M GGUF
```

The successful Colab run used 529 examples:

```text
Train: 476
Eval:  53
Runtime: about 30 minutes on T4
Best validation loss: about 0.300 at epoch 2
```

Later epochs reduced training loss but increased validation loss, so future runs should consider fewer epochs or early stopping.

## Step 3: Upload GGUF To The VM

From Windows PowerShell:

```powershell
gcloud compute scp .\qwen25-healthcare-finetuned-q4.gguf `
  arsl-karsl-train:~/qwen25-healthcare-finetuned-q4.gguf `
  --zone us-central1-a
```

If SCP is unstable, upload through Chrome Remote Desktop or Google Drive. The file only needs to exist somewhere on the VM, for example:

```text
~/Downloads/qwen25-healthcare-finetuned-q4.gguf
```

## Step 4: Register The Model With Ollama

On the VM:

```bash
cd ~/arsl-translator
git pull origin main
bash scripts/assistant_finetune/deploy_to_vm.sh ~/Downloads/qwen25-healthcare-finetuned-q4.gguf
```

The deploy script:

1. Starts the `ollama` Docker service if needed.
2. Copies the GGUF into the `arsl_ollama_prod` container.
3. Creates an Ollama model named `qwen25-healthcare`.
4. Updates `.env.production`:

```env
ASSISTANT_MODEL=qwen25-healthcare
```

5. Restarts the API container.

## Step 5: Evaluate

```bash
cd ~/arsl-translator
python3 scripts/assistant_finetune/before_after_eval.py > finetuned_results.txt
cat finetuned_results.txt
diff baseline_results.txt finetuned_results.txt || true
```

The evaluator intentionally fails on:

- API errors
- Chinese/CJK output
- leaked prompt text such as `←`, `الإجابة:`, or instruction fragments
- obvious role reversal patterns

## Production Guardrail

The backend keeps the fine-tuned model usable by cleaning output before returning it to the Android app:

- stops generation on markers such as `←`, `Input:`, `Answer:`, `الإجابة:`
- trims leaked instruction text after generation
- removes helper-voice suggestions
- falls back to deterministic suggestions when the model output is empty or wrong-script

When the API modifies a model response, the response uses:

```json
{
  "source": "ollama_cleaned"
}
```

If Ollama fails, the response uses:

```json
{
  "source": "fallback"
}
```

## Manual API Tests

```bash
curl -X POST https://arsl.hadighazi.com/api/ai/assist \
  -H "Content-Type: application/json" \
  -d '{"text":"انا الم بطني قوي","mode":"deaf_to_hearing","context":"chat","language":"ar"}'
```

```bash
curl -X POST https://arsl.hadighazi.com/api/ai/assist \
  -H "Content-Type: application/json" \
  -d '{"text":"انا في المستشفى واريد اسأل عن موعدي","mode":"suggestions","context":"chat","language":"ar"}'
```

## Rollback

If the fine-tuned model becomes too slow or worse than the base model:

```bash
cd ~/arsl-translator
sed -i 's/^ASSISTANT_MODEL=.*/ASSISTANT_MODEL=qwen2.5:1.5b/' .env.production
docker compose -f docker-compose.prod.yml --env-file .env.production up -d api
```

## Presentation Evidence

Show:

```text
baseline_results.txt
finetuned_results.txt
```

Suggested table:

```text
Model                  Dataset                         Result
qwen2.5:1.5b           General instruction model       baseline score
qwen25-healthcare      Deaf-healthcare SFT dataset     fine-tuned score
qwen25-healthcare      With API cleanup guardrail      production behavior
```
