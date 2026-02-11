import json
import os
import random
import sys
import time

from collections import Counter

print("Hotel Review AI Generator Training  v0.1")
print()
print("Loading support tools . . .")

import torch
import tqdm

from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, PeftModel
from trl import SFTTrainer, SFTConfig

print(f"Python: {sys.version}")
print(f"PyTorch: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"GPU count: {torch.cuda.device_count()}")
print(f"GPU name: {torch.cuda.get_device_name(0)}")

# Test bitsandbytes specifically — this is the one that breaks most often
import bitsandbytes as bnb
print(f"bitsandbytes: {bnb.__version__}")


def create_sample(data_record):

    this_rating = round(data_record['score'])
    stay_latency = data_record['review_elapsed']
    user_request = {
        "rating": this_rating,
        "days_since_stay": stay_latency
    }
    ai_response = f"Positive Review: {data_record['positive']}\n\nNegative Review: {data_record['negative']}"

    final_record = {
        "conversations": [
            {"role": "user", "content": json.dumps(user_request)},
            {"role": "assistant", "content": ai_response}
        ]
    }

    return json.dumps(final_record)

st = time.time()
print("Starting model load . . .")

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)

model = AutoModelForCausalLM.from_pretrained(
    "mistralai/Mistral-7B-Instruct-v0.3",
    quantization_config=bnb_config,
    device_map="auto",
    dtype=torch.float16,
)

tokenizer = AutoTokenizer.from_pretrained("mistralai/Mistral-7B-Instruct-v0.3")
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

print(f"Model dtype: {model.dtype}")
# Also check a specific parameter
for name, param in model.named_parameters():
    print(f"{name} is {param.dtype}")
    break

print(f"Model loading completed in {time.time() - st:.2f}sec")

print("Starting dataset preparation . . .")
st = time.time()
with open("preprocessed_reviews.json","r") as f:
    dataset = [json.loads(s) for s in f.readlines()]

print(f"Total dataset size: {len(dataset)} records.")

TRAIN_SIZE = 75000
VAL_SIZE = 3000

SAMPLE_TOTAL = TRAIN_SIZE + VAL_SIZE
dataset_sample = random.sample(dataset, SAMPLE_TOTAL)

dataset_train = dataset_sample[:TRAIN_SIZE]
dataset_val = dataset_sample[TRAIN_SIZE:]

print(f"Train: {len(dataset_train)} records; Val: {len(dataset_val)} records.")

train_scores = [round(x['score']) for x in dataset_train]
val_scores = [round(x['score']) for x in dataset_val]
train_counts = dict(Counter(train_scores))
val_counts = dict(Counter(val_scores))
print("Train distribution: " + str(train_counts))
print("Val distribution: " + str(val_counts))

# Prepare the training dataset by sampling the available data

dataset_train_file = [create_sample(x) for x in tqdm.tqdm(dataset_train,desc="Prepare train dataset")]
dataset_val_file = [create_sample(x) for x in tqdm.tqdm(dataset_val,desc="Prepare validation dataset")]

open("train.jsonl","w").write("\n".join(dataset_train_file))
open("val.jsonl","w").write("\n".join(dataset_val_file))

dataset = load_dataset("json", data_files={
    "train": "train.jsonl",
    "eval": "val.jsonl",
})

lora_config = LoraConfig(
    r=32,
    lora_alpha=64,
    lora_dropout=0.05,
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    bias="none",
    task_type="CAUSAL_LM",
)

# 4. Configure training
training_config = SFTConfig(
    output_dir="./hotel-review-lora",
    num_train_epochs=2,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=8,
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_steps=100,
    fp16=False,
    bf16=False,
    logging_steps=50,
    eval_strategy="steps",
    eval_steps=500,
    save_strategy="epoch",
    #max_seq_length=768,
    dataset_text_field="text"
)
def format_chat(example):
    messages = example["conversations"]
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=False,
    )
    return {"text": text}

dataset = dataset.map(format_chat, remove_columns=["conversations"])

print(f"Dataset preparation completed in {time.time() - st:.2f}sec")

# Verify it looks right
print("Example data point:")
print(dataset["train"][0])
exit(0)

# Prepare a trainer
trainer = SFTTrainer(
    model=model,
    args=training_config,
    train_dataset=dataset["train"],
    eval_dataset=dataset["eval"],
    peft_config=lora_config,
    processing_class=tokenizer,
)

print("Starting the training!")
st = time.time()
trainer.train()
print(f"Training completed in {time.time() - st:.2f}sec.")

print("Saving model . . .")
st = time.time()
trainer.save_model("./hotel-review-lora")
tokenizer.save_pretrained("./hotel-review-lora")

del trainer
del model
torch.cuda.empty_cache()

# Load base model at full precision for merging
base_model = AutoModelForCausalLM.from_pretrained(
    "mistralai/Mistral-7B-Instruct-v0.3",
    torch_dtype=torch.float16,
    device_map="cpu",  # Merge on CPU to avoid VRAM issues
)

# Apply LoRA adapter
model = PeftModel.from_pretrained(base_model, "./hotel-review-lora")

# Merge weights
merged_model = model.merge_and_unload()

# Save
merged_model.save_pretrained("./Mistral-HotelReviews-7b")
tokenizer = AutoTokenizer.from_pretrained("mistralai/Mistral-7B-Instruct-v0.3")
tokenizer.save_pretrained("./Mistral-HotelReviews-7b")
print(f"Model save completed in {time.time() - st:.2f}sec.")
