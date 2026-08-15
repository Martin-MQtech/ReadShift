#!/usr/bin/env python3
"""
ReBook Agnes-only pipeline - pages 73-100 (when Gemini is unavailable)
Sequential processing to avoid rate limits on free Agnes API.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

CONFIG_PATH = Path.home() / ".zcode" / "v2" / "config.json"
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output" / "full"
PDF_PATH = BASE_DIR / "張忠謀自傳上冊(1931-1964).pdf"
MIN_TEXT_LEN = 150

PAGES = [73, 74, 75, 76, 77, 79, 81, 82, 83, 84, 85, 86, 88, 89, 90, 91, 96]

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def call_agnes(system_prompt, user_content, max_tokens=4096, timeout=90):
    cfg = load_config()
    pkg = cfg.get("provider", {}).get("agnes", {})
    api_key = pkg.get("options", {}).get("apiKey", "")
    base_url = pkg.get("options", {}).get("baseURL", "")
    url = f"{base_url}/chat/completions"
    payload = json.dumps({
        "model": "agnes-2.5-flash",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.3
    }).encode()
    for attempt in range(3):
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
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = min(10 * (attempt + 1), 30)
                print(f"    ⚠️ 429 rate limit, waiting {wait}s...", file=sys.stderr)
                time.sleep(wait)
                continue
            raise
        except Exception as e:
            wait = min(5 * (attempt + 1), 20)
            print(f"    ⚠️ Error: {e}, retrying in {wait}s...", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError("All retries exhausted")

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

def get_pdf_text(page_num):
    import fitz
    doc = fitz.open(str(PDF_PATH))
    text = doc.load_page(page_num - 1).get_text()
    doc.close()
    return text

def process_page(p):
    try:
        raw_text = get_pdf_text(p).strip()
        if len(raw_text) < MIN_TEXT_LEN:
            print(f"  ⏭️ 第 {p} 页文本过短 ({len(raw_text)} 字)，跳过", file=sys.stderr)
            return False

        print(f"📄 开始处理第 {p} 页 ({len(raw_text)} 字)...", file=sys.stderr)

        # Tier 1: Healer (Agnes)
        print(f"  🔧 Tier 1: 修复文本...", file=sys.stderr)
        healed = call_agnes(PROMPT_HEALER, raw_text, max_tokens=2048, timeout=60)

        # Tier 2: Architect (Agnes)
        print(f"  🏗️ Tier 2: 双语重塑...", file=sys.stderr)
        bilingual = call_agnes(PROMPT_ARCHITECT, healed, max_tokens=4096, timeout=90)

        # Tier 3: Extractor (Agnes)
        print(f"  📦 Tier 3: 知识萃取...", file=sys.stderr)
        extracted = call_agnes(PROMPT_EXTRACTOR, bilingual, max_tokens=2048, timeout=60)

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
        print(f"  ✅ 第 {p} 页已完成 → {out_file.name}", file=sys.stderr)
        return True
    except Exception as e:
        print(f"  ❌ 第 {p} 页处理失败: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    if not PDF_PATH.exists():
        print(f"❌ PDF不存在: {PDF_PATH}", file=sys.stderr)
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    done = sorted([int(f.stem.split("_")[-1]) for f in OUTPUT_DIR.glob("page_*.md") if f.name != "_INDEX.md"])
    pending = [p for p in PAGES if p not in done]

    print(f"🚀 Agnes-only 流水线：待处理 {len(pending)} 页 (跳過已存在的 {len(PAGES)-len(pending)} 页)", file=sys.stderr)

    success = 0
    for p in pending:
        if process_page(p):
            success += 1
        time.sleep(2)  # Rate limit protection

    print(f"\n🎉 完成！成功 {success}/{len(pending)} 页。", file=sys.stderr)
