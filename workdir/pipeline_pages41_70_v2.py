#!/usr/bin/env python3
"""
ReBook 生产管线 v2 - 修复版
- 修复双语段落输出格式（无重复标题）
- 串行处理确保稳定性，每页完成后等待1秒
- 只处理第41-70页
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

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def call_llm(system_prompt, user_content, provider, model, max_retries=3, timeout=120):
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
            wait = min(5 * (attempt + 1), 30)
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

对每一个自然段落，按以下格式输出：

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
- 不要输出任何其他标题（如"## 双语重塑"等）
- 不要使用表格
- 不要加"中英对照段落"等引导语
- 直接以第一个中文段落开始
- 繁简统一用简体中文"""

def get_pdf_text(page_num):
    import fitz
    doc = fitz.open(str(PDF_PATH))
    text = doc.load_page(page_num - 1).get_text()
    doc.close()
    return text

def process_page(p):
    raw_text = get_pdf_text(p).strip()
    if len(raw_text) < MIN_TEXT_LEN:
        print(f"  ⏭️ 第 {p} 页文本过短 ({len(raw_text)} 字)，跳过", file=sys.stderr)
        return False

    print(f"📄 第 {p} 页 ({len(raw_text)} 字)...", file=sys.stderr)

    # Tier 1: Gemini 3.6 Flash - 修复文本
    healed = call_llm(PROMPT_HEALER, raw_text, "053c6d95-41ee-4af4-bc18-dacc1d31b2cb", "gemini-3.6-flash-high")
    time.sleep(1)

    # Tier 2: Agnes 2.5 Flash - 双语重塑
    bilingual = call_llm(PROMPT_BILINGUAL, healed, "agnes", "agnes-2.5-flash", timeout=120)
    time.sleep(1)

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
    print(f"  ✅ 第 {p} 页完成 → {out_file.name}", file=sys.stderr)
    return True

def main():
    pages = list(range(41, 71))
    import fitz
    doc = fitz.open(str(PDF_PATH))
    total = len(doc)
    doc.close()
    pages = [p for p in pages if p <= total]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    done = sorted([int(f.stem.split("_")[-1]) for f in OUTPUT_DIR.glob("page_*.md") if f.name != "_INDEX.md"])

    # Process all pages 41-70 (force reprocess)
    pending = pages

    print(f"🚀 开始处理第 {pages[0]}-{pages[-1]} 页，共 {len(pending)} 页（含已存在的强制重处理）", file=sys.stderr)

    success_count = 0
    for p in pending:
        try:
            if process_page(p):
                success_count += 1
        except Exception as e:
            print(f"  ❌ 第 {p} 页处理失败: {e}", file=sys.stderr)
        time.sleep(2)  # 避免API限流

    print(f"\n🎉 批处理完成！成功 {success_count}/{len(pending)} 页。", file=sys.stderr)
    print("🔄 正在刷新 HTML 渲染 preview_book.html ...")
    os.system("node /Users/martin/Documents/20260812MartinGitHub\\ /20260812\\ 电子书二创工具/workdir/render_html_v8.js")

if __name__ == "__main__":
    main()
