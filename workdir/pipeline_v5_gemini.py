#!/usr/bin/env python3
"""
ReBook 生产管线 v5 - 极速双引擎版 (并发加速版)
Tier 1 (Healer): Gemini 3.6 Flash (2.7s 极速 OCR 粗洗 + 彻底过滤微信/QQ/公众号/水印等垃圾广告)
Tier 2 (Architect): Agnes 2.5 Flash (Isaacson 双语精塑)
Tier 3 (Extractor): Agnes 2.5 Flash (三维知识萃取)
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

CONFIG_PATH = Path.home() / ".zcode" / "v2" / "config.json"
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output" / "full"
PDF_PATH = BASE_DIR / "張忠謀自傳上冊(1931-1964).pdf"
MIN_TEXT_LEN = 150

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def call_llm(system_prompt: str, user_content: str, provider: str, model: str, max_retries=5, timeout=60) -> str:
    cfg = load_config()
    pkg = cfg.get("provider", {}).get(provider, {})
    api_key = pkg.get("options", {}).get("apiKey", "")
    base_url = pkg.get("options", {}).get("baseURL", "")
    if not api_key:
        raise ValueError(f"No apiKey for {provider}")

    url = f"{base_url}/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "max_tokens": 4096,
        "temperature": 0.3
    }).encode()

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                url, data=payload,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
                result = data["choices"][0]["message"]["content"].strip()
                if result and len(result) > 10:
                    return result
        except Exception as e:
            wait = 5 * (attempt + 1)
            print(f"    ⚠️ P{provider}/{model} 重试 ({attempt+1}/{max_retries}): {e}, 等待 {wait}s...", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"All retries failed for {provider}/{model}")

PROMPT_HEALER = """你是"疗愈者"(The Healer)。修复OCR文本：
1. 去掉字间多余空格
2. 纠正明显错别字
3. 补全截断标点
4. 保持原意，繁体保留
5. 彻底过滤并删除任何微信、QQ、公众号、扫描件广告、页眉页脚水印、联系方式、交流群等垃圾广告信息
6. 只输出修复后的文本，不要解释"""

PROMPT_ARCHITECT = """你是双语架构师，仿沃尔特·艾萨克森(Walter Isaacson)传记风格（《Steve Jobs》《爱因斯坦传》）。
任务：将以下中文段落改写为逐段中英对照的双语版本。
英文风格：克制、精确、叙事感强。
格式要求：
每段中文后紧跟 "---"，然后英文翻译，再 "---"。
最后写：
### 商业语汇提炼 (Cheat Sheet)
列出 3-5 个有价值的英文表达。
### 修辞与逻辑赏析
### 外链知识窗"""

PROMPT_EXTRACTOR = """从以下双语文本中提取知识卡片：
### 📌 Cheat Sheet：地道商业表达
1. **expression**
   **中文解释**：...
   **商业造句**：...
### 🎯 修辞与逻辑赏析
### 🌐 外链知识窗"""

def get_pdf_text(page_num: int) -> str:
    import fitz
    doc = fitz.open(str(PDF_PATH))
    text = doc.load_page(page_num - 1).get_text()
    doc.close()
    return text

def process_page(p: int) -> bool:
    try:
        raw_text = get_pdf_text(p).strip()
        if len(raw_text) < MIN_TEXT_LEN:
            print(f"  ⏭️ 第 {p} 页文本过短 ({len(raw_text)} 字)，跳过", file=sys.stderr)
            return False

        print(f"📄 开始处理第 {p} 页 ({len(raw_text)} 字)...", file=sys.stderr)

        # Tier 1: Gemini 3.6 Flash
        healed = call_llm(PROMPT_HEALER, raw_text, "053c6d95-41ee-4af4-bc18-dacc1d31b2cb", "gemini-3.6-flash-high")

        # Tier 2: Agnes 2.5 Flash
        bilingual = call_llm(PROMPT_ARCHITECT, healed, "agnes", "agnes-2.5-flash", timeout=90)

        # Tier 3: Agnes 2.5 Flash
        extracted = call_llm(PROMPT_EXTRACTOR, bilingual, "agnes", "agnes-2.5-flash", timeout=60)

        full_md = f"""# 《张忠谋自传》第{p}页

---

## 1. 修复文本

{healed}

---

## 2. 双语重塑

{bilingual}

---

## 3. 知识萃取

{extracted}

<!-- PROCESSED -->
"""
        out_file = OUTPUT_DIR / f"page_{p:03d}.md"
        out_file.write_text(full_md, encoding="utf-8")
        print(f"  ✅ 第 {p} 页已完成并保存 → {out_file.name}", file=sys.stderr)
        return True
    except Exception as e:
        print(f"  ❌ 第 {p} 页处理失败: {e}", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=31)
    parser.add_argument("--end", type=int, default=60)
    parser.add_argument("--force", action="store_true", help="强制覆盖已存在页面")
    parser.add_argument("--workers", type=int, default=5, help="并发线程数")
    args = parser.parse_args()

    if not PDF_PATH.exists():
        print(f"❌ PDF不存在: {PDF_PATH}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    done = sorted([int(f.stem.split("_")[-1]) for f in OUTPUT_DIR.glob("page_*.md") if f.name != "_INDEX.md"])
    
    import fitz
    doc = fitz.open(str(PDF_PATH))
    total = len(doc)
    doc.close()

    end = min(args.end or total, total)
    start = max(args.start, 1)
    
    if args.force:
        pending = list(range(start, end + 1))
    else:
        pending = [p for p in range(start, end + 1) if p not in done]

    print(f"🚀 开始 Gemini Flash + Agnes 极速并发流水线 (workers={args.workers})：待处理 {len(pending)} 页")

    success_count = 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(process_page, p): p for p in pending}
        for future in as_completed(futures):
            p = futures[future]
            try:
                if future.result():
                    success_count += 1
            except Exception as e:
                print(f"  ❌ 线程执行错误 Page {p}: {e}", file=sys.stderr)

    print(f"\n🎉 批处理完成！成功 {success_count}/{len(pending)} 页。")
    print("🔄 正在刷新 HTML 渲染 preview_book.html ...")
    os.system("node workdir/render_html_v6.js")

if __name__ == "__main__":
    main()
