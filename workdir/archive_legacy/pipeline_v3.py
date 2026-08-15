#!/usr/bin/env python3
"""
ReBook 生产管线 v3 - 免费模型双引擎版
Tier 1 (Healer): DeepSeek V4 Flash - OCR修复快准狠
Tier 2 (Architect): Agnes 2.5 Flash - 英文明美，Isaacson风格
Tier 3 (Extractor): Agnes 2.5 Flash - 知识萃取

所有模型100%免费，适合大规模生产
"""

import argparse
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

MIN_TEXT_LEN = 200
MAX_RETRIES = 5
TIMEOUT = 90


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def call_llm(system_prompt, user_content, provider, model, timeout=90):
    """带重试的 LLM 调用"""
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

    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(
                url, data=payload,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
                result = data["choices"][0]["message"]["content"].strip()
                if result and len(result) > 20:
                    return result
                raise ValueError(f"Empty response (attempt {attempt+1})")
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            wait = min(5 * (attempt + 1), 30)
            print(f"    ⚠️ {e}，{wait}s后重试...", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"All {MAX_RETRIES} retries exhausted")


# ============ Prompts ============

PROMPT_HEALER = """你是"疗愈者"(The Healer)。修复OCR文本：
1. 去掉字间多余空格
2. 纠正明显错别字（不改语义）
3. 补全截断标点
4. 保持原意，繁体保留
5. 只输出修复后的文本，不要解释"""

PROMPT_ARCHITECT = """你是双语架构师，仿沃尔特·艾萨克森(Walter Isaacson)传记风格（《Steve Jobs》《爱因斯坦传》）。

任务：将以下中文段落改写为逐段中英对照的双语版本。

英文翻译要求：
- Isaacson风格：克制、精确、叙事感强，有文学质感但不矫情
- 语境自适应：宏大战略用高阶词（laid the foundations, commanded respect），人物情感保留原生张力
- 该用 make money 就不用 monetize，该用 figure out 就不用 conceptualize
- 句式有节奏感，长短交错

输出格式（严格遵守）：
每段中文后紧跟 "---"，然后英文翻译，再 "---"。
最后写：### 商业语汇提炼 (Cheat Sheet)
列出 3-5 个有价值的英文表达，每个包含：**expression**、中文解释、真实商业造句。
最后写：### 修辞与逻辑赏析 和 ### 外链知识窗。

注意：必须为每一段中文都配上英文翻译，不要省略任何段落。"""

PROMPT_EXTRACTOR = """你是知识萃取专家。从以下双语文本中提取：
1. 商业语汇（Cheat Sheet）：英文表达+中文解释+商业造句
2. 修辞赏析
3. 外链知识窗（50字背景科普）

如果输入为空或太短，请输出：<EMPTY_INPUT>"""


def get_pdf_text(page_num):
    import fitz
    doc = fitz.open(str(PDF_PATH))
    text = doc.load_page(page_num - 1).get_text()
    doc.close()
    return text


def main():
    parser = argparse.ArgumentParser(description="ReBook 生产管线 v3 - 免费双引擎版")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=None)
    args = parser.parse_args()

    if not PDF_PATH.exists():
        print(f"❌ PDF not found: {PDF_PATH}"); sys.exit(1)

    done = sorted([int(f.stem.split("_")[-1]) for f in OUTPUT_DIR.glob("page_*.md") if f.name != "_INDEX.md"])
    print(f"📖 已产出: {done}")

    import fitz
    total = len(fitz.open(str(PDF_PATH)))
    fitz.open(str(PDF_PATH)).close()
    end = args.end or total
    start = max(args.start, 1)

    pending = [p for p in range(start, end + 1) if p not in done]
    if not pending:
        print("🎉 全部完成！"); return

    print(f"🚀 待处理: {len(pending)} 页 ({pending[0]}-{pending[-1]})")
    print(f"   Healer: DeepSeek V4 Flash | Architect: Agnes 2.5 Flash | Extractor: Agnes 2.5 Flash")

    for page_num in pending:
        try:
            text = get_pdf_text(page_num)
            text_clean = text.strip()

            if len(text_clean) < MIN_TEXT_LEN:
                print(f"   ⏭️ 第{page_num}页({len(text_clean)}字)过短，跳过")
                continue

            print(f"\n📄 第{page_num}页 ({len(text_clean)}字)...", file=sys.stderr)

            # Tier 1: Healer (DeepSeek)
            print("   📝 Healer (DeepSeek V4 Flash)...", file=sys.stderr)
            healed = call_llm(PROMPT_HEALER, text_clean, "deepseek", "deepseek-v4-flash")

            # Tier 2: Architect (Agnes 2.5 Flash)
            print("   🌐 Architect (Agnes 2.5 Flash)...", file=sys.stderr)
            bilingual = call_llm(PROMPT_ARCHITECT, healed, "agnes", "agnes-2.5-flash", timeout=120)

            # Tier 3: Extractor (Agnes 2.5 Flash)
            print("   🔍 Extractor (Agnes 2.5 Flash)...", file=sys.stderr)
            extractor = call_llm(PROMPT_EXTRACTOR, bilingual, "agnes", "agnes-2.5-flash")
            if extractor == "<EMPTY_INPUT>":
                extractor = "（输入文本过短，无法萃取）"

            full_md = f"""# 《张忠谋自传》第{page_num}页

---

## 1. 修复文本

{text_clean}

---

## 2. 双语重塑

{bilingual}

---

## 3. 知识萃取

{extractor}

<!-- PROCESSED -->
"""
            out_file = OUTPUT_DIR / f"page_{page_num:03d}.md"
            out_file.write_text(full_md, encoding="utf-8")
            print(f"   ✅ {out_file.name}", file=sys.stderr)
            time.sleep(1)

        except Exception as e:
            print(f"   ❌ 第{page_num}页失败: {e}", file=sys.stderr)
            continue

    done_now = sorted([int(f.stem.split("_")[-1]) for f in OUTPUT_DIR.glob("page_*.md") if f.name != "_INDEX.md"])
    print(f"\n🎉 已产出: {done_now} ({len(done_now)}页)")


if __name__ == "__main__":
    main()
