# Assistant Fine-Tuning Workflow

This folder contains the optional fine-tuning workflow for the Assistive Message Studio model used by the Android Bluetooth chat app.

The goal is to improve the local open-source Ollama assistant used by:

- `POST /api/ai/assist`
- Android message actions: `Make clearer`, `Simplify`
- Android composer suggestions

The current production model is usually:

```env
ASSISTANT_MODEL=qwen2.5:1.5b
```

The fine-tuned model name used by these scripts is:

```env
ASSISTANT_MODEL=qwen25-healthcare
```

## Files

```text
scripts/assistant_finetune/
  dataset.jsonl          Small supervised dataset for the 3 assistant modes
  colab_finetune.py      Colab notebook-style script for LoRA fine-tuning
  before_after_eval.py   Live API evaluator for baseline vs fine-tuned model
  deploy_to_vm.sh        VM deployment script for registering GGUF with Ollama
```

## What The Dataset Teaches

The dataset covers the observed bugs:

- Arabic output must stay Arabic.
- English output must stay English.
- The model must not output Chinese/CJK text.
- `deaf_to_hearing` rewrites the patient's words; it must not answer like a helper.
- `suggestions` are ready-to-send messages from the patient/user, not hospital staff replies.
- The model must not reverse meaning.

Examples of bugs the fine-tune is meant to reduce:

```text
Input: انا الم بطني قوي
Bad: I have a strong bladder.
Good: أشعر بألم شديد في بطني.

Input: دكتور انا ما فهم كلام دواء
Bad: The doctor did not understand me.
Good: دكتور، لم أفهم تعليمات الدواء.

Input: انا في المستشفى واريد اسأل عن موعدي
Bad: 请问您的预约时间是什么时候?
Good:
1. متى موعدي؟
2. أين أنتظر؟
3. هل تأخر موعدي؟
```

## Step 1: Capture Baseline On The VM

SSH into the VM or use browser SSH:

```bash
cd ~/arsl-translator
git pull origin main
python3 scripts/assistant_finetune/before_after_eval.py > baseline_results.txt
cat baseline_results.txt
```

This calls the live deployed API:

```text
https://arsl.hadighazi.com/api/ai/assist
```

To evaluate a different URL:

```bash
ASSIST_EVAL_URL=http://localhost:8000/api/ai/assist \
python3 scripts/assistant_finetune/before_after_eval.py
```

Keep `baseline_results.txt` for the presentation.

## Step 2: Fine-Tune In Google Colab

Use Colab because the VM is CPU-only and the model fine-tune needs a GPU.

1. Open <https://colab.research.google.com>
2. Create a new notebook.
3. Runtime -> Change runtime type -> `T4 GPU`.
4. Upload this dataset from the repo:

```text
scripts/assistant_finetune/dataset.jsonl
```

5. Open:

```text
scripts/assistant_finetune/colab_finetune.py
```

6. Paste each `CELL` section into Colab in order.
7. Run all cells.

Expected time on free T4:

```text
20-40 minutes
```

The script fine-tunes:

```text
Qwen/Qwen2.5-1.5B-Instruct
```

using LoRA:

```text
r=16
lora_alpha=32
epochs=5
batch_size=2
gradient_accumulation_steps=4
learning_rate=2e-4
```

The final export should produce:

```text
qwen25-healthcare-finetuned-q4.gguf
```

Download that file from Colab.

## Step 3: Upload GGUF To The VM

From your Windows machine, run this from any PowerShell folder containing the GGUF:

```powershell
gcloud compute scp .\qwen25-healthcare-finetuned-q4.gguf `
  arsl-karsl-train:~/qwen25-healthcare-finetuned-q4.gguf `
  --zone us-central1-a
```

If `gcloud compute scp` is unstable, upload through browser SSH or Chrome Remote Desktop instead. The file only needs to end up here:

```text
~/qwen25-healthcare-finetuned-q4.gguf
```

## Step 4: Register The Model With Ollama On The VM

On the VM:

```bash
cd ~/arsl-translator
git pull origin main
bash scripts/assistant_finetune/deploy_to_vm.sh ~/qwen25-healthcare-finetuned-q4.gguf
```

The script will:

1. Start the `ollama` Docker service if needed.
2. Copy the GGUF into the `arsl_ollama_prod` container.
3. Create an Ollama model named `qwen25-healthcare`.
4. Update `.env.production`:

```env
ASSISTANT_MODEL=qwen25-healthcare
```

5. Restart the API service.

## Step 5: Re-Run Evaluation

```bash
cd ~/arsl-translator
python3 scripts/assistant_finetune/before_after_eval.py > finetuned_results.txt
cat finetuned_results.txt
diff baseline_results.txt finetuned_results.txt || true
```

## Step 6: Manual API Tests

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

## Roll Back

If the fine-tuned model is worse:

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
Model                  Dataset                         Score
qwen2.5:1.5b           General instruction model       X/8
qwen25-healthcare      75 deaf-healthcare samples      Y/8
```

