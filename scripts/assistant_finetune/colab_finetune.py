# ============================================================
# Fine-tune qwen2.5:1.5b with LoRA for Healthcare Chat
# Run this in Google Colab (free T4 GPU)
# Runtime -> Change runtime type -> T4 GPU
# ============================================================

# ── CELL 1: Install dependencies ────────────────────────────
# !pip install -q transformers datasets peft accelerate bitsandbytes trl torch sentencepiece

# ── CELL 2: Imports ─────────────────────────────────────────
import json
import torch
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, TaskType
from trl import SFTTrainer

print(f"GPU available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

# ── CELL 3: Upload dataset ───────────────────────────────────
# Upload dataset.jsonl via the Files panel on the left in Colab
# or run this to load from your drive:
# from google.colab import files
# uploaded = files.upload()  # select dataset.jsonl

DATASET_PATH = "dataset.jsonl"   # change if uploaded elsewhere

# ── CELL 4: Load and format dataset ─────────────────────────
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
            "حافظ على المعنى والفاعل. لا تعكس المعنى. لا تتحدث مع المريض."
        ),
        "en": (
            "Rewrite the following message in clear, natural English. "
            "Preserve the exact meaning and speaker. Do not reverse the meaning. "
            "Do not address the user — only rewrite their message."
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
            "كل رسالة يجب أن تكون من وجهة نظر المريض، وليس الطاقم الطبي. رقّم الاقتراحات."
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
    # Qwen2.5 chat template format
    prompt = (
        f"<|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>\n"
        f"<|im_start|>user\n{user_content}<|im_end|>\n"
        f"<|im_start|>assistant\n{sample['output']}<|im_end|>"
    )
    return prompt

# Load JSONL
raw = []
with open(DATASET_PATH, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            raw.append(json.loads(line))

# Format
formatted = [{"text": build_prompt(s)} for s in raw]
dataset = Dataset.from_list(formatted)

# 90/10 train/eval split
split = dataset.train_test_split(test_size=0.1, seed=42)
train_dataset = split["train"]
eval_dataset  = split["test"]

print(f"Train: {len(train_dataset)} | Eval: {len(eval_dataset)}")
print("\nSample prompt:\n")
print(train_dataset[0]["text"][:600])

# ── CELL 5: Load model in 4-bit ──────────────────────────────
MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
)

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
)
model.config.use_cache = False
model.config.pretraining_tp = 1

print("Model loaded.")
print(f"Parameters: {sum(p.numel() for p in model.parameters()) / 1e6:.1f}M")

# ── CELL 6: Apply LoRA ───────────────────────────────────────
lora_config = LoraConfig(
    r=16,                          # rank — higher = more capacity, more VRAM
    lora_alpha=32,                 # scaling factor (usually 2x rank)
    target_modules=[               # which layers to train
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    lora_dropout=0.05,
    bias="none",
    task_type=TaskType.CAUSAL_LM,
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
# Expected: ~1-3% of total params trainable — that is correct for LoRA

# ── CELL 7: Training arguments ───────────────────────────────
OUTPUT_DIR = "./qwen25-healthcare-lora"

training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=5,            # more epochs = better on small dataset
    per_device_train_batch_size=2,
    per_device_eval_batch_size=2,
    gradient_accumulation_steps=4, # effective batch = 2*4 = 8
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_ratio=0.1,
    fp16=True,                     # T4 supports fp16
    logging_steps=5,
    eval_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    report_to="none",              # disable wandb
    optim="paged_adamw_8bit",      # memory-efficient optimizer
    max_grad_norm=0.3,
    weight_decay=0.001,
)

# ── CELL 8: Train ────────────────────────────────────────────
trainer = SFTTrainer(
    model=model,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    args=training_args,
    dataset_text_field="text",
    max_seq_length=512,
            packing=False,
)

print("Starting training...")
trainer.train()
print("Training complete.")

# ── CELL 9: Save LoRA adapter ────────────────────────────────
ADAPTER_DIR = "./qwen25-healthcare-adapter"
trainer.model.save_pretrained(ADAPTER_DIR)
tokenizer.save_pretrained(ADAPTER_DIR)
print(f"Adapter saved to {ADAPTER_DIR}")

# ── CELL 10: Quick inference test before merging ─────────────
from peft import PeftModel

def test_inference(input_text: str, mode: str, lang: str):
    instruction = MODE_INSTRUCTIONS[mode][lang]
    user_content = f"{instruction}\n\n{input_text}"
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_content},
    ]
    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=150,
            temperature=0.01,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )
    response = tokenizer.decode(
        outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True
    )
    return response.strip()

# Run before-after tests
tests = [
    ("انا الم بطني قوي",          "deaf_to_hearing", "ar"),
    ("دكتور انا ما فهم كلام دواء", "deaf_to_hearing", "ar"),
    ("راسي يدور ما قادر اوقف",    "deaf_to_hearing", "ar"),
    ("stomach hurt bad cant stand","deaf_to_hearing", "en"),
    ("انا في المستشفى واريد اسأل عن موعدي", "suggestions", "ar"),
    (
        "يجب أن تتناول الدواء بعد الأكل مرتين يومياً وإذا استمر الألم راجع الطبيب",
        "hearing_to_deaf", "ar"
    ),
]

print("\n" + "="*60)
print("FINE-TUNED MODEL OUTPUTS")
print("="*60)
for inp, mode, lang in tests:
    result = test_inference(inp, mode, lang)
    print(f"\n[{mode} | {lang}]")
    print(f"  Input:  {inp}")
    print(f"  Output: {result}")

# ── CELL 11: Merge LoRA into base model and export as GGUF ───
# This merges adapter weights into the full model for deployment.
# Then converts to GGUF format so Ollama can serve it.

# Step 1: Merge
print("\nMerging LoRA adapter into base model...")

from peft import AutoPeftModelForCausalLM

merged_model = AutoPeftModelForCausalLM.from_pretrained(
    ADAPTER_DIR,
    device_map="cpu",              # merge on CPU to save VRAM
    torch_dtype=torch.float16,
    trust_remote_code=True,
)
merged_model = merged_model.merge_and_unload()

MERGED_DIR = "./qwen25-healthcare-merged"
merged_model.save_pretrained(MERGED_DIR, safe_serialization=True)
tokenizer.save_pretrained(MERGED_DIR)
print(f"Merged model saved to {MERGED_DIR}")

# Step 2: Convert to GGUF using llama.cpp
# !git clone https://github.com/ggerganov/llama.cpp
# !cd llama.cpp && pip install -r requirements.txt
# !python llama.cpp/convert_hf_to_gguf.py ./qwen25-healthcare-merged \
#     --outfile qwen25-healthcare-finetuned-q4.gguf \
#     --outtype q4_k_m
# print("GGUF export complete: qwen25-healthcare-finetuned-q4.gguf")

# Step 3: Download the GGUF file from Colab
# from google.colab import files
# files.download("qwen25-healthcare-finetuned-q4.gguf")

print("\nDone! Next steps:")
print("1. Uncomment the GGUF cells above and run them")
print("2. Download qwen25-healthcare-finetuned-q4.gguf")
print("3. Follow deploy_to_vm.sh to add it to Ollama on your VM")
