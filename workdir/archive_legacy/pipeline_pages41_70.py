#!/usr/bin/env python3
"""
ReBook 生产管线 - 处理第41-70页
使用 Gemini 3.6 Flash (Tier 1) + Agnes 2.5 Flash (Tier 2+3 合并)
输出严格遵循用户指定的格式
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

def call_llm(system_prompt: str, user_content: str, provider: str, model: str, max_retries=3, timeout=120) -> str:
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
            wait = min(3 * (attempt + 1), 15)
            print(f"    ⚠️ P{provider}/{model} 重试 ({attempt+1}/{max_retries}): {e}", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"All retries failed for {provider}/{model}")

PROMPT_HEALER = """你是"疗愈者"(The Healer)。修复OCR文本：
1. 去掉字间多余空格
2. 纠正明显错别字
3. 补全截断标点
4. 保持原意，繁体保留
5. 彻底过滤并删除任何微信、QQ、公众号、扫描件广告、页眉页脚水印、联系方式、交流群等垃圾广告信息
6. 只输出修复后的文本，不要解释"""

PROMPT_BILINGUAL = """你是双语架构师，仿沃尔特·艾萨克森(Walter Isaacson)传记风格（《Steve Jobs》《爱因斯坦传》）。

任务：将以下中文段落改写为逐段中英对照的双语版本。

英文风格要求：
- 克制、精确、叙事感强
- 用词优雅但不浮夸
- 符合英文自传文学传统
- 保留原文的亲切感和自传叙事语气

**严格输出格式**（必须逐字遵守）：

首先写一个标题行：
## 双语重塑

然后对每一个自然段落，按以下格式输出（中文段落，换行，英文翻译，换行，再---分隔下一段）：

[中文段落内容]
---
[英文翻译]
---
[下一个中文段落]
---
[下一个英文翻译]
...

在最后加：

### 商业语汇提炼
（列出3-5个有价值的英文表达，每个格式如下）
1. **expression**
   **中文解释**：...
   **商业造句**：...

### 修辞赏析
（分析原文的修辞手法、逻辑结构）

### 外链知识窗
（补充背景知识链接或注释）

注意：
- 不要输出任何其他标题（如"## 1. 修复文本"、"## 3. 知识萃取"等）
- 不要使用表格
- 只输出要求的格式
- 繁体转简体在修复阶段已完成，此处输入为简体"""

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

        # Tier 1: Gemini 3.6 Flash - 修复文本
        healed = call_llm(PROMPT_HEALER, raw_text, "053c6d95-41ee-4af4-bc18-dacc1d31b2cb", "gemini-3.6-flash-high")

        # Tier 2: Agnes 2.5 Flash - 双语重塑 (合并翻译+词汇+赏析)
        bilingual = call_llm(PROMPT_BILINGUAL, healed, "agnes", "agnes-2.5-flash", timeout=120)

        # 确保双语部分有正确的前缀标题
        if "## 双语重塑" not in bilingual:
            bilingual = "## 双语重塑\n\n" + bilingual

        full_md = f"""# 《张忠谋自传》第{p}页

---

## 修复文本

{healed}

---

## 双语重塑

{bilingual}

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
    parser.add_argument("--start", type=int, default=41)
    parser.add_argument("--end", type=int, default=70)
    parser.add_argument("--force", action="store_true", help="强制覆盖已存在页面")
    parser.add_argument("--workers", type=int, default=3, help="并发线程数")
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

    print(f"🚀 开始处理第 {start}-{end} 页：待处理 {len(pending)} 页", file=sys.stderr)
    if pending:
        print(f"   缺失页面: {pending}", file=sys.stderr)

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

    print(f"\n🎉 批处理完成！成功 {success_count}/{len(pending)} 页。", file=sys.stderr)
    print(f"🔄 正在刷新 HTML 渲染 preview_book.html ...")
    os.system("node /Users/martin/Documents/20260812MartinGitHub\\ /20260812\\ 电子书二创工具/workdir/render_html_v8.js")

if __name__ == "__main__":
    main()
