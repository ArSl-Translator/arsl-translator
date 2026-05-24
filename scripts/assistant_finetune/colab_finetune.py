# ============================================================
# One-cell Colab fine-tune for qwen2.5:1.5b Healthcare Chat
#
# How to use:
# 1. Open Google Colab.
# 2. Runtime -> Change runtime type -> T4 GPU.
# 3. Upload dataset.jsonl, or let this script ask you to upload it.
# 4. Paste this whole file into ONE Colab cell and run it.
#
# Output:
# - qwen25-healthcare-adapter/          LoRA adapter
# - qwen25-healthcare-merged/           merged HF model
# - qwen25-healthcare-finetuned-f16.gguf
# - qwen25-healthcare-finetuned-q4.gguf (if quantization succeeds)
# ============================================================

AUTO_INSTALL = True
AUTO_UPLOAD_DATASET_IF_MISSING = True
RUN_TRAINING = True
RUN_MERGE = True
RUN_GGUF_EXPORT = True
RUN_DOWNLOAD = True

DATASET_PATH = "dataset.jsonl"
MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"
OUTPUT_DIR = "./qwen25-healthcare-lora"
ADAPTER_DIR = "./qwen25-healthcare-adapter"
MERGED_DIR = "./qwen25-healthcare-merged"
GGUF_F16 = "qwen25-healthcare-finetuned-f16.gguf"
GGUF_Q4 = "qwen25-healthcare-finetuned-q4.gguf"


# ── Bootstrap dependencies ──────────────────────────────────
import os
import sys
import subprocess


def run(cmd, cwd=None):
    print(f"\n$ {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=cwd)


if AUTO_INSTALL:
    run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-q",
            "-U",
            "transformers",
            "datasets",
            "peft",
            "accelerate",
            "bitsandbytes",
            "trl",
            "sentencepiece",
            "protobuf",
            "safetensors",
        ]
    )
    # This is a text-only fine-tune. Colab can have mismatched optional packages
    # after package upgrades:
    # - torchvision can trigger `torchvision::nms does not exist`
    # - old torchao can make PEFT fail during merge
    run(
        [
            sys.executable,
            "-m",
            "pip",
            "uninstall",
            "-y",
            "-q",
            "torchvision",
            "torchaudio",
            "torchao",
        ]
    )


# ── Imports ─────────────────────────────────────────────────
import json
import gc
import torch
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, TaskType, AutoPeftModelForCausalLM
from trl import SFTConfig, SFTTrainer

print(f"GPU available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")


# ── Dataset upload/load ─────────────────────────────────────
if not os.path.exists(DATASET_PATH) and AUTO_UPLOAD_DATASET_IF_MISSING:
    try:
        from google.colab import files

        print(f"{DATASET_PATH} not found. Upload it now.")
        files.upload()
    except Exception as exc:
        print(f"Could not open Colab upload dialog: {exc}")

if not os.path.exists(DATASET_PATH):
    raise FileNotFoundError(
        f"{DATASET_PATH} not found. Upload scripts/assistant_finetune/dataset.jsonl "
        "to Colab, or set DATASET_PATH to the correct location."
    )


# ── Prompt formatting ───────────────────────────────────────
SYSTEM_PROMPT = (
    "You are a healthcare communication assistant for deaf and hard-of-hearing users. "
    "You help rewrite messages clearly, simplify complex medical instructions, "
    "and suggest ready-to-send phrases. Always preserve the exact meaning. "
    "Never reverse who is speaking. Respond only in the same language as the input."
)

MODE_INSTRUCTIONS = {
    "deaf_to_hearing": {
        "ar": (
            "أعد صياغة الرسالة التالية بالعربية الواضحة والطبيعية. "
            "حافظ على المعنى والفاعل. لا تعكس المعنى. "
            "لا تتحدث مع المريض ولا تسأله كيف تساعده، فقط أعد صياغة كلامه."
        ),
        "en": (
            "Rewrite the following message in clear, natural English. "
            "Preserve the exact meaning and speaker. Do not reverse the meaning. "
            "Do not address the user; only rewrite their message."
        ),
    },
    "hearing_to_deaf": {
        "ar": (
            "بسّط الرسالة التالية إلى عربية قصيرة ومباشرة لشخص أصم أو ضعيف السمع. "
            "حافظ على المعنى والفاعل."
        ),
        "en": (
            "Simplify the following message into short, direct English "
            "for a deaf or hard-of-hearing person. Preserve the exact meaning and speaker."
        ),
    },
    "suggestions": {
        "ar": (
            "اكتب 3 إلى 5 رسائل جاهزة للإرسال من قِبَل المريض بناءً على السياق التالي. "
            "كل رسالة يجب أن تكون من وجهة نظر المريض، وليس الطاقم الطبي. "
            "لا تكتب: كيف يمكنني مساعدتك؟ لأنها من كلام الطاقم. رقّم الاقتراحات."
        ),
        "en": (
            "Write 3 to 5 ready-to-send messages from the patient based on the context below. "
            "Each message must be from the patient's perspective, not staff. Number the suggestions."
        ),
    },
}


def build_prompt(sample: dict) -> str:
    mode = sample["mode"]
    lang = sample["language"]
    instruction = MODE_INSTRUCTIONS[mode][lang]
    user_content = f"{instruction}\n\n{sample['input']}"
    return (
        f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n"
        f"<|im_start|>user\n{user_content}<|im_end|>\n"
        f"<|im_start|>assistant\n{sample['output']}<|im_end|>"
    )


raw = []
with open(DATASET_PATH, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            raw.append(json.loads(line))

formatted = [{"text": build_prompt(s)} for s in raw]
dataset = Dataset.from_list(formatted)
split = dataset.train_test_split(test_size=0.1, seed=42)
train_dataset = split["train"]
eval_dataset = split["test"]

print(f"Train: {len(train_dataset)} | Eval: {len(eval_dataset)}")
print("\nSample prompt:\n")
print(train_dataset[0]["text"][:700])


# ── Load model in 4-bit ─────────────────────────────────────
gc.collect()
torch.cuda.empty_cache()

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    # Use fp32 compute to avoid Colab T4 AMP/BF16 scaler bugs. The dataset is
    # tiny, so reliability matters more than a small speed difference.
    bnb_4bit_compute_dtype=torch.float32,
)

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    quantization_config=bnb_config,
    device_map="auto",
    torch_dtype=torch.float32,
    trust_remote_code=True,
)
model.config.use_cache = False
model.config.pretraining_tp = 1

print("Model loaded.")
print(f"Parameters: {sum(p.numel() for p in model.parameters()) / 1e6:.1f}M")


# ── Apply LoRA ──────────────────────────────────────────────
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=[
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ],
    lora_dropout=0.05,
    bias="none",
    task_type=TaskType.CAUSAL_LM,
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()


# ── Train ───────────────────────────────────────────────────
training_args = SFTConfig(
    output_dir=OUTPUT_DIR,
    num_train_epochs=5,
    per_device_train_batch_size=2,
    per_device_eval_batch_size=2,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_ratio=0.1,
    # Disable AMP entirely. Some Colab T4 runtimes produce BF16 gradients even
    # when fp16 is requested, which crashes GradScaler during optimizer.step().
    fp16=False,
    bf16=False,
    logging_steps=5,
    eval_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    report_to="none",
    optim="adamw_torch",
    max_grad_norm=0.3,
    weight_decay=0.001,
    dataset_text_field="text",
    max_length=512,
    packing=False,
)

trainer = SFTTrainer(
    model=model,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    args=training_args,
    processing_class=tokenizer,
)

if RUN_TRAINING:
    print("Starting training...")
    trainer.train()
    print("Training complete.")

trainer.model.save_pretrained(ADAPTER_DIR)
tokenizer.save_pretrained(ADAPTER_DIR)
print(f"Adapter saved to {ADAPTER_DIR}")


# ── Quick inference test before merging ─────────────────────
def test_inference(input_text: str, mode: str, lang: str):
    instruction = MODE_INSTRUCTIONS[mode][lang]
    user_content = f"{instruction}\n\n{input_text}"
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=150,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    response = tokenizer.decode(
        outputs[0][inputs["input_ids"].shape[1] :], skip_special_tokens=True
    )
    return response.strip()


tests = [
    ("انا الم بطني قوي", "deaf_to_hearing", "ar"),
    ("دكتور انا ما فهم كلام دواء", "deaf_to_hearing", "ar"),
    ("راسي يدور ما قادر اوقف", "deaf_to_hearing", "ar"),
    ("stomach hurt bad cant stand", "deaf_to_hearing", "en"),
    ("انا في المستشفى واريد اسأل عن موعدي", "suggestions", "ar"),
    (
        "يجب أن تتناول الدواء بعد الأكل مرتين يومياً وإذا استمر الألم راجع الطبيب",
        "hearing_to_deaf",
        "ar",
    ),
]

print("\n" + "=" * 60)
print("FINE-TUNED MODEL OUTPUTS")
print("=" * 60)
for inp, mode, lang in tests:
    result = test_inference(inp, mode, lang)
    print(f"\n[{mode} | {lang}]")
    print(f"  Input:  {inp}")
    print(f"  Output: {result}")


# ── Merge LoRA into base model ──────────────────────────────
if RUN_MERGE:
    print("\nMerging LoRA adapter into base model...")
    del model
    gc.collect()
    torch.cuda.empty_cache()

    merged_model = AutoPeftModelForCausalLM.from_pretrained(
        ADAPTER_DIR,
        device_map="cpu",
        torch_dtype=torch.float16,
        trust_remote_code=True,
    )
    merged_model = merged_model.merge_and_unload()
    merged_model.save_pretrained(MERGED_DIR, safe_serialization=True)
    tokenizer.save_pretrained(MERGED_DIR)
    print(f"Merged model saved to {MERGED_DIR}")


# ── Export GGUF and quantize ────────────────────────────────
if RUN_GGUF_EXPORT:
    print("\nExporting to GGUF with llama.cpp...")
    if not os.path.exists("llama.cpp"):
        run(["git", "clone", "--depth", "1", "https://github.com/ggml-org/llama.cpp"])

    run([sys.executable, "-m", "pip", "install", "-q", "-r", "llama.cpp/requirements.txt"])

    run(
        [
            sys.executable,
            "llama.cpp/convert_hf_to_gguf.py",
            MERGED_DIR,
            "--outfile",
            GGUF_F16,
            "--outtype",
            "f16",
        ]
    )

    print("\nBuilding llama.cpp quantizer...")
    run(["cmake", "-B", "build"], cwd="llama.cpp")
    run(["cmake", "--build", "build", "--config", "Release", "-j", "2"], cwd="llama.cpp")

    quantizers = [
        "llama.cpp/build/bin/llama-quantize",
        "llama.cpp/build/bin/Release/llama-quantize.exe",
        "llama.cpp/build/bin/llama-quantize.exe",
    ]
    quantizer = next((p for p in quantizers if os.path.exists(p)), None)

    if quantizer:
        run([quantizer, GGUF_F16, GGUF_Q4, "Q4_K_M"])
        print(f"Quantized GGUF complete: {GGUF_Q4}")
    else:
        print("Could not find llama-quantize. Keeping f16 GGUF only.")


# ── Download artifacts ──────────────────────────────────────
if RUN_DOWNLOAD:
    try:
        from google.colab import files

        if os.path.exists(GGUF_Q4):
            files.download(GGUF_Q4)
        elif os.path.exists(GGUF_F16):
            files.download(GGUF_F16)
        else:
            print("No GGUF file found to download.")
    except Exception as exc:
        print(f"Download step skipped: {exc}")

print("\nDone.")
print(f"Preferred VM artifact: {GGUF_Q4 if os.path.exists(GGUF_Q4) else GGUF_F16}")
