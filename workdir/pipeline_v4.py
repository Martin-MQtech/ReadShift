#!/usr/bin/env python3
"""
ReBook 生产管线 v4 - 稳健版（双免费引擎）
Healer: DeepSeek V4 Flash   |   Architect & Extractor: Agnes 2.5 Flash
增强的重试机制和超时处理
"""

import argparse
import json
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


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def call_llm(system_prompt, user_content, provider, model, max_retries=5, base_timeout=120):
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
            with urllib.request.urlopen(req, timeout=base_timeout + attempt * 10) as resp:
                data = json.loads(resp.read())
                result = data["choices"][0]["message"]["content"].strip()
                if result and len(result) > 30:
                    return result
                print(f"    ⚠️ 响应过短({len(result)}字)，重试...", file=sys.stderr)
        except (urllib.error.URLError, TimeoutError, ConnectionError, ssl.SSLError) as e:
            wait = min(8 * (attempt + 1), 45)
            print(f"    ⚠️ 网络错误({e})，{wait}s后重试 ({attempt+1}/{max_retries})", file=sys.stderr)
            time.sleep(wait)
        except Exception as e:
            print(f"    ⚠️ 未知错误: {e}，重试...", file=sys.stderr)
            time.sleep(5)
    raise RuntimeError(f"所有 {max_retries} 次重试均失败")


import ssl
_PROMPT_HEALER = """你是"疗愈者"(The Healer)。修复OCR文本：
1. 去掉字间多余空格
2. 纠正明显错别字（不改语义）
3. 补全截断标点
4. 保持原意，繁体保留
5. 只输出修复后的文本，不要解释"""

_PROMPT_ARCHITECT = """你是双语架构师，仿沃尔特·艾萨克森(Walter Isaacson)传记风格。
任务：将以下中文段落改写为逐段中英对照的双语版本。
英文风格：克制、精确、叙事感强（像《Steve Jobs》）。
格式：每段中文后紧跟 "---"，然后英文翻译，再 "---"。
最后写：### 商业语汇提炼 (Cheat Sheet) — 3~5个英文表达+中文解释+真实商业造句。
最后写：### 修辞与逻辑赏析 和 ### 外链知识窗。
注意：每一段中文都必须配上英文翻译，不要省略。"""

_PROMPT_EXTRACTOR = """从以下双语文本中提取知识卡片：
1. 商业语汇（Cheat Sheet）：英文表达+中文解释+商业造句
2. 修辞赏析
3. 外链知识窗（50字背景科普）
若输入太短，输出：<EMPTY_INPUT>"""


def get_pdf_text(page_num):
    import fitz
    doc = fitz.open(str(PDF_PATH))
    text = doc.load_page(page_num - 1).get_text()
    doc.close()
    return text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=None)
    args = parser.parse_args()

    if not PDF_PATH.exists():
        print(f"❌ PDF不存在: {PDF_PATH}"); sys.exit(1)

    done = sorted([int(f.stem.split("_")[-1]) for f in OUTPUT_DIR.glob("page_*.md") if f.name != "_INDEX.md"])
    print(f"📖 已产出({len(done)}页): {done[:5]}...{done[-3:] if len(done)>3 else ''}")

    import fitz
    total = len(fitz.open(str(PDF_PATH)))
    fitz.open(str(PDF_PATH)).close()
    end = args.end or total
    start = max(args.start, 1)
    pending = [p for p in range(start, end + 1) if p not in done]
    if not pending:
        print("🎉 全部完成！"); return

    print(f"🚀 待处理: {len(pending)}页 ({pending[0]}-{pending[-1]})")
    print("   Healer=DeepSeek V4 Flash | Architect=Agnes 2.5 Flash | Extractor=Agnes 2.5 Flash\n")

    for page_num in pending:
        try:
            text = get_pdf_text(page_num)
            text_clean = text.strip()
            if len(text_clean) < MIN_TEXT_LEN:
                print(f"   ⏭️ 第{page_num}页({len(text_clean)}字)过短，跳过"); continue

            print(f"\n📄 第{page_num}页({len(text_clean)}字)...", file=sys.stderr)

            print("   📝 Healer...", file=sys.stderr)
            healed = call_llm(_PROMPT_HEALER, text_clean, "deepseek", "deepseek-v4-flash", max_retries=3)

            print("   🌐 Architect...", file=sys.stderr)
            bilingual = call_llm(_PROMPT_ARCHITECT, healed, "agnes", "agnes-2.5-flash", max_retries=5)

            print("   🔍 Extractor...", file=sys.stderr)
            extractor = call_llm(_PROMPT_EXTRACTOR, bilingual, "agnes", "agnes-2.5-flash", max_retries=3)
            if extractor == "<EMPTY_INPUT>":
                extractor = "（文本较短，暂无法萃取）"

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
            (OUTPUT_DIR / f"page_{page_num:03d}.md").write_text(full_md, encoding="utf-8")
            print(f"   ✅ 第{page_num}页完成", file=sys.stderr)
            time.sleep(2)

        except Exception as e:
            print(f"   ❌ 第{page_num}页失败: {e}", file=sys.stderr)
            continue

    done_now = sorted([int(f.stem.split("_")[-1]) for f in OUTPUT_DIR.glob("page_*.md") if f.name != "_INDEX.md"])
    print(f"\n🎉 当前产出({len(done_now)}页): {done_now}")


if __name__ == "__main__":
    main()
