# 10-CELL KAGGLE: SmolLM2-135M-Instruct -> ~250M SOLAR upscale (n30 m2 s56) + 6 modes
# Budget: ~2hr T4, target: GGUF Q4_K_M ctx512 for Render 512MB/0.1CPU
# Datasets: /kaggle/input/datasets/shakkhorpaul/new-data-with-nsft + /kaggle/input/datasets/hurutta/bangla-wikipedia-dataset
# Modes: 1 Bangla_Chat 2 English_Chat 3 Code 4 Creative_BN 5 Creative_EN 6 Naughty(18+ consensual adult only, gated)

# ============ CELL 1: setup (5 min) ============
# !pip -q install transformers==4.42.3 peft==0.12.0 trl==0.9.6 datasets==2.20.0 accelerate bitsandbytes
import torch, os, gc
print(torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU")
# !nvidia-smi

# ============ CELL 2: inspect — PASTE YOUR PATHS HERE WHILE PIP RUNS ============
NSFT_PATH = "/kaggle/input/datasets/shakkhorpaul/new-data-with-nsft"  # edit if needed
WIKI_PATH = "/kaggle/input/datasets/hurutta/bangla-wikipedia-dataset"
import os, glob
for p in [NSFT_PATH, WIKI_PATH]:
    print("==", p, os.path.exists(p))
    if os.path.exists(p):
        fs = glob.glob(os.path.join(p, "**/*"), recursive=True)[:30]
        for f in fs: print(" ", f)
        # preview first csv/json/txt
        import itertools
        cands = [f for f in glob.glob(os.path.join(p,"**/*.*"), recursive=True) if f.endswith((".csv",".json",".jsonl",".txt",".parquet"))][:3]
        for c in cands:
            print("---", c, os.path.getsize(c))
            try:
                with open(c, encoding="utf-8", errors="ignore") as fh:
                    for line in itertools.islice(fh, 5): print(line[:500])
            except Exception as e: print("preview err", e)

# ============ CELL 3: SOLAR upscale 30L -> 56L (~245M) ============
from transformers import AutoModelForCausalLM, AutoTokenizer
BASE = "HuggingFaceTB/SmolLM2-135M-Instruct"
tok = AutoTokenizer.from_pretrained(BASE)
if tok.pad_token is None: tok.pad_token = tok.eos_token
model = AutoModelForCausalLM.from_pretrained(BASE, torch_dtype=torch.bfloat16, device_map="auto")
n = model.config.num_hidden_layers  # 30
m = 2; s = 2*(n-m)  # 56
print(f"n={n} m={m} s={s}")
layers = model.model.layers
orig = list(layers)
bottom = orig[:n-m]   # first 28
top = orig[m:]        # last 28
# rebuild: bottom + top (weight sharing refs, will be cloned on save/heal)
import torch.nn as nn
model.model.layers = nn.ModuleList(bottom + top)
model.config.num_hidden_layers = s
model.save_pretrained("/kaggle/working/smollm-250M-init")
tok.save_pretrained("/kaggle/working/smollm-250M-init")
print("saved init, params:", sum(p.numel() for p in model.parameters())/1e6, "M")
del model; gc.collect(); torch.cuda.empty_cache()

# ============ CELL 4: heal-LoRA on Bangla wiki (25 min, ~800 steps max) ============
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model
import glob
MODEL_INIT = "/kaggle/working/smollm-250M-init"
tok = AutoTokenizer.from_pretrained(MODEL_INIT)
if tok.pad_token is None: tok.pad_token = tok.eos_token
model = AutoModelForCausalLM.from_pretrained(MODEL_INIT, torch_dtype=torch.bfloat16, device_map="auto")
model.config.use_cache = False
model.gradient_checkpointing_enable()
# load wiki text files
files = glob.glob(WIKI_PATH+"/**/*.txt", recursive=True) + glob.glob(WIKI_PATH+"/**/*.csv", recursive=True) + glob.glob(WIKI_PATH+"/**/*.json*", recursive=True)
print("wiki files:", len(files))
ds = load_dataset("text", data_files={"train": [f for f in files if f.endswith(".txt")] or files}, split="train") if files else None
MAXL=512
def tok_fn(b): return tok(b["text"], truncation=True, max_length=MAXL)
if ds is not None:
    ds = ds.filter(lambda x: x["text"] and len(x["text"])>50).map(tok_fn, batched=True, remove_columns=["text"]).select(range(min(20000, len(ds))))
    ds = ds.map(lambda x: {"labels": x["input_ids"]}, batched=False)
peft_cfg = LoraConfig(r=16, lora_alpha=32, target_modules=["q_proj","v_proj"], lora_dropout=0.05, task_type="CAUSAL_LM")
model = get_peft_model(model, peft_cfg)
args = TrainingArguments("/kaggle/working/heal", per_device_train_batch_size=4, gradient_accumulation_steps=4,
    max_steps=800, learning_rate=5e-5, warmup_ratio=0.1, lr_scheduler_type="cosine",
    bf16=True, logging_steps=50, save_steps=400, save_total_limit=1, report_to="none")
Trainer(model, args, train_dataset=ds, tokenizer=tok).train()
model.save_pretrained("/kaggle/working/smollm-250M-healed"); tok.save_pretrained("/kaggle/working/smollm-250M-healed")

# ============ CELL 5: format 6 modes + SFW/NSFW split ============
# Expects NSFT as csv/json with text/instruction/response. Adjust col names after Cell2 preview.
import pandas as pd, glob, re
cands = glob.glob(NSFT_PATH+"/**/*.*", recursive=True)
print(cands[:10])
# EDIT column names to match your file:
df = None
for c in cands:
    if c.endswith(".csv"):
        try: df = pd.read_csv(c, nrows=50000); print(df.columns.tolist()); break
        except Exception as e: print(e)
# Normalize -> columns: prompt, response, tag
# Heuristic auto-tag:
def auto_mode(prompt, resp):
    t = (str(prompt)+str(resp)).lower()
    if re.search(r"def |import |for \(|SELECT|function|class |print\(", t): return "Code"
    return "English_Chat"
# TODO: replace with your real mapping, keep Naughty <=8% and ADULT-CONSENSUAL ONLY
# Drop minors/non-consensual/violent:
BLOCK = re.compile(r"child|minor|teen[^a-z]|schoolgirl|schoolboy|force|rape|incest|bestial", re.I)
def is_blocked(t): return bool(BLOCK.search(str(t)))
# Build ChatML: <|mode|>X <|im_start|>user ... <|im_start|>assistant
# Save: /kaggle/working/sfw.jsonl (modes 1-5) + /kaggle/working/nsfw.jsonl (mode 6 only, gated)
# (Full mapping code expanded in notebook — keep balance 25/20/20/15/12/8)

# ============ CELL 6: tune-A SFW modes 1-5 (35 min) ============
from datasets import load_dataset as LD
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from trl import SFTTrainer
from peft import LoraConfig
HEALED="/kaggle/working/smollm-250M-healed"
tok=AutoTokenizer.from_pretrained(HEALED); tok.pad_token=tok.eos_token
mdl=AutoModelForCausalLM.from_pretrained(HEALED, torch_dtype=torch.bfloat16, device_map="auto")
mdl.config.use_cache=False; mdl.gradient_checkpointing_enable()
ds=LD("json", data_files="/kaggle/working/sfw.jsonl", split="train")
cfg=LoraConfig(r=16, lora_alpha=32, target_modules=["q_proj","v_proj"], task_type="CAUSAL_LM")
SFTTrainer(model=mdl, train_dataset=ds, tokenizer=tok, peft_config=cfg,
    args=TrainingArguments("/kaggle/working/tuneA", per_device_train_batch_size=4, gradient_accumulation_steps=4,
    max_steps=1000, learning_rate=2e-4, warmup_ratio=0.05, bf16=True, logging_steps=50, save_total_limit=1, report_to="none"),
    max_seq_length=512, dataset_text_field="text").train()
mdl.save_pretrained("/kaggle/working/tuneA"); tok.save_pretrained("/kaggle/working/tuneA")

# ============ CELL 7: tune-B NSFW separate adapter, mode 6 only (15 min) ============
# Loads tuneA base, trains LoRA-B ONLY on nsfw.jsonl. Never merge into base.
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
from trl import SFTTrainer
from peft import LoraConfig
BASE_A="/kaggle/working/tuneA"
tok=AutoTokenizer.from_pretrained(BASE_A)
mdl=AutoModelForCausalLM.from_pretrained(BASE_A, torch_dtype=torch.bfloat16, device_map="auto")
mdl.config.use_cache=False; mdl.gradient_checkpointing_enable()
from datasets import load_dataset as LD2
ds=LD2("json", data_files="/kaggle/working/nsfw.jsonl", split="train")
cfg=LoraConfig(r=8, lora_alpha=16, target_modules=["q_proj","v_proj"], task_type="CAUSAL_LM")
SFTTrainer(model=mdl, train_dataset=ds, tokenizer=tok, peft_config=cfg,
    args=TrainingArguments("/kaggle/working/tuneB-nsfw", per_device_train_batch_size=4, gradient_accumulation_steps=4,
    max_steps=300, learning_rate=1e-4, bf16=True, logging_steps=25, save_total_limit=1, report_to="none"),
    max_seq_length=512, dataset_text_field="text").train()
mdl.save_pretrained("/kaggle/working/adapterB-nsfw")  # adapter only, gated by 18+ flag

# ============ CELL 8: eval 6 prompts ============
from transformers import pipeline
gen = pipeline("text-generation", model="/kaggle/working/tuneA", tokenizer="/kaggle/working/tuneA", device_map="auto", max_new_tokens=80)
MODES = {"Bangla_Chat":"তুমি কেমন আছো? সংক্ষেপে বলো।","English_Chat":"Say hi briefly.",
"Code":"Write python add function.","Creative_BN":"এক লাইনের কবিতা লেখো।","Creative_EN":"One-line poem about rain."}
for k,p in MODES.items():
    pr = f"<|mode|>{k}<|im_start|>user\n{p}<|im_start|>assistant\n"
    print(k, ":", gen(pr, do_sample=False)[0]["generated_text"][-200:])

# ============ CELL 9: quantize GGUF Q4_K_M (10 min) ============
# !git clone https://github.com/ggerganov/llama.cpp /kaggle/working/llama.cpp
# !pip -q install gguf
# !python /kaggle/working/llama.cpp/convert_hf_to_gguf.py /kaggle/working/tuneA --outfile /kaggle/working/smollm-250M-f16.gguf --outtype f16
# !cmake -S /kaggle/working/llama.cpp -B /kaggle/working/llama.cpp/build -DLLAMA_CURL=OFF -DCMAKE_BUILD_TYPE=Release && cmake --build /kaggle/working/llama.cpp/build -j
# !/kaggle/working/llama.cpp/build/bin/llama-quantize /kaggle/working/smollm-250M-f16.gguf /kaggle/working/smollm-250M-Q4_K_M.gguf Q4_K_M
# !ls -lh /kaggle/working/*.gguf
# Fallback if OOM: use Q3_K_M instead

# ============ CELL 10: render-pack ctx512 + 18+ gate ============
# Writes app.py + Dockerfile for Render 512MB/0.1CPU (llama-server, no transformers at runtime)
APP = '''
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import subprocess, os
GGUF = os.getenv("GGUF","/models/smollm-250M-Q4_K_M.gguf")
ADAPTER = os.getenv("NSFW_ADAPTER","/models/adapterB-nsfw")
PORT = int(os.getenv("PORT","10000"))
app = FastAPI()
SYS = {"Bangla_Chat":"You reply in Bangla, short.","English_Chat":"You reply in English, short.",
"Code":"You write tiny correct code only.","Creative_BN":"You write short Bangla poem/story.",
"Creative_EN":"You write short English poem/story.","Naughty":"ADULT CONSENSUAL ONLY. Refuse minors/non-consensual."}
class Req(BaseModel):
    mode: str; prompt: str; nsfw_confirm_18: bool=False
@app.post("/chat")
def chat(r: Req):
    if r.mode not in SYS: raise HTTPException(400,"bad mode")
    if r.mode=="Naughty" and not r.nsfw_confirm_18: raise HTTPException(403,"18+ confirm required")
    # call llama-server binary: /usr/local/bin/llama-server -m GGUF --ctx-size 512 --port 8080 (run as sidecar)
    return {"mode": r.mode, "system": SYS[r.mode], "note": "wire to llama-server /completion with prompt"}
'''
open("/kaggle/working/app.py","w").write(APP)
open("/kaggle/working/Dockerfile","w").write('FROM ghcr.io/ggerganov/llama.cpp:server\\nCOPY smollm-250M-Q4_K_M.gguf /models/\\nCOPY app.py /app/\\nCMD ["llama-server","-m","/models/smollm-250M-Q4_K_M.gguf","--ctx-size","512","--port","8080"]\\n')
print("wrote app.py + Dockerfile")
