#!/usr/bin/env python3
"""
ReBook 生产管线 — 页 101-126 (双引擎版)
Tier 1: Gemini 3.6 Flash (OCR修复)
Tier 2: Agnes 2.5 Flash (双语重塑 + 知识萃取)
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
START_PAGE = 101
END_PAGE = 126

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def call_llm(system_prompt, user_content, provider_key, model, max_retries=3, timeout=90):
    cfg = load_config()
    pkg = cfg.get("provider", {}).get(provider_key, {})
    api_key = pkg.get("options", {}).get("apiKey", "")
    base_url = pkg.get("options", {}).get("baseURL", "")
    if not api_key:
        raise ValueError(f"No apiKey for {provider_key}")

    url = f"{base_url}/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "max_tokens": 8192,
        "temperature": 0.3
    }).encode("utf-8")

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
            print(f"    ⚠️ 重试 ({attempt+1}/{max_retries}): {e}", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"All retries failed for {provider_key}/{model}")

PROMPT_HEALER = """你是"疗愈者"(The Healer)，专门修复OCR文本。任务：
1. 去掉字间多余空格（OCR常见错误）
2. 纠正明显错别字（如：囯→国、汙→污、硏→研等）
3. 补全截断标点
4. 保持繁体中文原貌（不要转简体）
5. 彻底过滤并删除任何微信/QQ/公众号/广告/水印/联系方式等垃圾信息
6. 只输出修复后的纯净文本，不要任何解释或说明"""

PROMPT_ARCHITECT = """你是双语架构师，仿沃尔特·艾萨克森(Walter Isaacson)传记风格（《Steve Jobs》《爱因斯坦传》《达芬奇传》）。

任务：将以下繁体中文文本处理为：
1. 将繁体转为简体中文
2. 逐段中英对照输出
3. 英文翻译要优雅、克制、有叙事感，像Isaacson写传记那样精确而有力

格式严格如下：
[简体中文段落]
---
[English translation in Isaacson style]
---
[下一段简体中文]
---
[下一段英文]
...

### 📌 商业语汇提炼
列出3-5个有价值的英文表达，每个包含：
**expression**
**中文解释**：...
**商业造句**：...

### 🎯 修辞赏析
分析文本的修辞手法与文学价值。

### 🌐 外链知识窗
提供与文本内容相关的背景知识链接或注释。"""

def get_pdf_text(page_num):
    import fitz
    doc = fitz.open(str(PDF_PATH))
    text = doc.load_page(page_num - 1).get_text()
    doc.close()
    return text.strip()

def process_page(p):
    raw_text = get_pdf_text(p)
    if len(raw_text) < MIN_TEXT_LEN:
        print(f"  ⏭️ 第 {p} 页文本过短 ({len(raw_text)} 字)，跳过", file=sys.stderr)
        return False

    print(f"📄 开始处理第 {p} 页 ({len(raw_text)} 字)...", file=sys.stderr)

    # Tier 1: Gemini 3.6 Flash - OCR修复
    print(f"  Tier 1: Gemini 3.6 Flash (OCR修复)...", file=sys.stderr)
    healed = call_llm(
        PROMPT_HEALER, raw_text,
        "053c6d95-41ee-4af4-bc18-dacc1d31b2cb",
        "gemini-3.6-flash-high",
        timeout=60
    )
    print(f"  ✅ Tier 1 完成，修复后 {len(healed)} 字", file=sys.stderr)

    # Tier 2: Agnes 2.5 Flash - 双语重塑 + 知识萃取
    print(f"  Tier 2: Agnes 2.5 Flash (双语重塑)...", file=sys.stderr)
    bilingual = call_llm(
        PROMPT_ARCHITECT, healed,
        "agnes",
        "agnes-2.5-flash",
        timeout=120
    )
    print(f"  ✅ Tier 2 完成", file=sys.stderr)

    # 构建最终Markdown
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
    print(f"  ✅ 第 {p} 页已保存 → {out_file.name}", file=sys.stderr)
    return True

def main():
    if not PDF_PATH.exists():
        print(f"❌ PDF不存在: {PDF_PATH}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    done = sorted([int(f.stem.split("_")[-1]) for f in OUTPUT_DIR.glob("page_*.md") if f.name != "_INDEX.md"])

    pending = [p for p in range(START_PAGE, END_PAGE + 1) if p not in done]

    print(f"🚀 开始双引擎流水线 (pages {START_PAGE}-{END_PAGE})：待处理 {len(pending)} 页", file=sys.stderr)
    print(f"   已存在: {sorted(done)}, 跳过: {set(range(START_PAGE, END_PAGE+1)) - set(pending)}", file=sys.stderr)

    success_count = 0
    for p in pending:
        try:
            if process_page(p):
                success_count += 1
            time.sleep(0.5)  # 避免API限流
        except Exception as e:
            print(f"  ❌ 第 {p} 页处理失败: {e}", file=sys.stderr)

    print(f"\n🎉 批处理完成！成功 {success_count}/{len(pending)} 页。", file=sys.stderr)

    # 刷新 HTML
    print("🔄 正在刷新 HTML 渲染...", file=sys.stderr)
    os.system(f'node "{BASE_DIR}/workdir/render_html_v8.js"')

if __name__ == "__main__":
    main()
