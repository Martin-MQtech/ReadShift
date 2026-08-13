#!/usr/bin/env python3
"""
ReBook 生产管线 - 续跑模式
从第 N 页开始批量处理，直到 PDF 末尾
使用 DeepSeek V4 Flash（已验证连通）
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

# ============ 配置 ============
CONFIG_PATH = Path.home() / ".zcode" / "v2" / "config.json"
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output" / "full"
PDF_PATH = BASE_DIR / "張忠謀自傳上冊(1931-1964).pdf"

# 已完成的页面（跳过）
DONE_PAGES = sorted([
    int(f.stem.split("_")[-1])
    for f in OUTPUT_DIR.glob("page_*.md")
    if f.name != "_INDEX.md"
])

def load_provider_config(provider_name: str):
    """从 ~/.zcode/v2/config.json 读取供应商配置"""
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    return cfg.get("provider", {}).get(provider_name, {})

def call_llm(system_prompt: str, user_content: str, provider: str = "deepseek", model: str = "deepseek-v4-flash") -> str:
    """统一模型调用接口"""
    pkg = load_provider_config(provider)
    api_key = pkg.get("options", {}).get("apiKey", "")
    base_url = pkg.get("options", {}).get("baseURL", "")

    if not api_key:
        raise ValueError(f"No apiKey for provider: {provider}")

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

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        method="POST"
    )

    max_retries = 5
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"]
        except (urllib.error.URLError, TimeoutError) as e:
            wait = min(5 * (attempt + 1), 30)
            print(f"    ⚠️ 重试 {attempt+1}/{max_retries}: {e}，等待 {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"Failed after {max_retries} retries")


# ============ 三层 Prompt ============

PROMPT_HEALER = """你是"疗愈者"(The Healer)。你的任务是把 OCR 粗糙的繁体中文文本修复成干净、连贯的中文。

规则：
1. 去掉字间多余空格（OCR常见问题）
2. 纠正明显的错别字（仅纠正确定性的错误，不改语义）
3. 补全被截断的标点（如"。"变成"。 "）
4. 保持原意，不要改写或添加内容
5. 繁体字保留，不要转简体
6. 只输出修复后的文本，不要任何解释"""

PROMPT_ARCHITECT = """你是"双语架构师"(The Bilingual Architect)，仿沃尔特·艾萨克森(Walter Isaacson)的传记写作风格。

你的任务：对以下中文段落，产出**逐段对照的双语版本**（中文原文 + 英文翻译），然后附上商业语汇提炼和修辞赏析。

**英文翻译风格要求**：
- Isaacson 风格：克制、精确、叙事感强，像《Steve Jobs》《爱因斯坦传》
- 语境自适应：宏大战略用高阶商业词汇，人物情感段落保留原生张力
- 该用 make money 就不用 monetize，该用 figure out 就不用 conceptualize
- 句式有节奏感，长短交错，避免机器翻译腔

**输出格式**：
每段原文后紧跟 "---"，然后英文翻译，再 "---"。
最后附上：
### 商业语汇提炼 (Cheat Sheet)
列出 3-5 个有价值的英文表达，每个包含：**英文表达**、中文解释、真实商业造句。

### 修辞与逻辑赏析
分析 2-3 处精彩的修辞手法。

### 外链知识窗
补充 1-2 个背景知识（50字左右）。"""

PROMPT_EXTRACTOR = """你是"深度挖掘者"(Deep Dive Extractor)。从以下双语文本中萃取知识卡片。

输出格式：
### 📌 Cheat Sheet：地道商业表达
1. **expression**
   **中文解释**：...
   **商业造句**：*English sentence.*

### 🎯 修辞与逻辑赏析
分析修辞手法。

### 🌐 外链知识窗
背景知识科普。"""


def process_page(page_num: int, ocr_text: str) -> str:
    """三阶段处理单页：Healer → Architect → Extractor"""
    print(f"\n🔄 第{page_num}页:")

    # Phase 1: Healer
    print("   📝 修复中...", file=sys.stderr)
    healer_result = call_llm(PROMPT_HEALER, ocr_text)
    print("   ✅ 修复完成", file=sys.stderr)

    # Phase 2: Architect (双语重塑)
    print("   🌐 双语重塑中...", file=sys.stderr)
    architect_result = call_llm(PROMPT_ARCHITECT, healer_result)
    print("   ✅ 双语完成", file=sys.stderr)

    # Phase 3: Extractor (知识萃取)
    print("   🔍 知识萃取中...", file=sys.stderr)
    extractor_result = call_llm(PROMPT_EXTRACTOR, architect_result)
    print("   ✅ 萃取完成", file=sys.stderr)

    # 组装 Markdown
    full_md = f"""# 《张忠谋自传》第{page_num}页 · ReBook 全量生产

---

## 1. Healer 修复文本

{healer_result}

---

## 2. Isaacson 双语重塑

{architect_result}

---

## 3. 知识萃取

{extractor_result}

<!-- PROCESSED -->
"""
    return full_md


def get_ocr_text(page_num: int) -> str:
    """从 PyMuPDF 提取第 page_num 页的 OCR 文本（繁体中文）"""
    import fitz
    doc = fitz.open(str(PDF_PATH))
    page = doc.load_page(page_num - 1)  # 0-indexed
    text = page.get_text()
    doc.close()
    return text


def main():
    parser = argparse.ArgumentParser(description="ReBook 批量生产管线")
    parser.add_argument("--start", type=int, default=1, help="起始页码")
    parser.add_argument("--end", type=int, default=None, help="结束页码（默认到PDF末尾）")
    parser.add_argument("--provider", type=str, default="deepseek", help="模型供应商")
    parser.add_argument("--model", type=str, default="deepseek-v4-flash", help="模型名")
    args = parser.parse_args()

    # 确认 PDF
    if not PDF_PATH.exists():
        print(f"❌ PDF 不存在: {PDF_PATH}")
        sys.exit(1)

    import fitz
    doc = fitz.open(str(PDF_PATH))
    total_pages = len(doc)
    doc.close()
    print(f"📖 PDF 共 {total_pages} 页")
    print(f"✅ 已完成: {sorted(DONE_PAGES)}")

    start = args.start
    end = args.end or total_pages

    # 跳过已完成的
    pages_to_process = [p for p in range(start, end + 1) if p not in DONE_PAGES]
    if not pages_to_process:
        print("🎉 全部页面已完成！")
        return

    print(f"🚀 待处理: {len(pages_to_process)} 页 ({pages_to_process[0]}-{pages_to_process[-1]})")

    for page_num in pages_to_process:
        try:
            ocr_text = get_ocr_text(page_num)
            if not ocr_text.strip():
                print(f"   ⚠️ 第{page_num}页无文本，跳过")
                continue

            result = process_page(page_num, ocr_text)

            out_file = OUTPUT_DIR / f"page_{page_num:03d}.md"
            out_file.write_text(result, encoding="utf-8")
            print(f"   ✅ 已保存: {out_file}")

            # 每页之间稍作停顿，避免限流
            time.sleep(2)

        except Exception as e:
            print(f"   ❌ 第{page_num}页失败: {e}", file=sys.stderr)
            continue

    print(f"\n🎉 生产完成！产出目录: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
