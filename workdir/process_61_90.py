#!/usr/bin/env python3
"""
ReBook 批处理脚本 - 61 至 90 页专用
Tier 1 (Healer): Gemini 3.6 Flash (含垃圾广告水印过滤)
Tier 2 (Architect): Agnes 2.5 Flash (Isaacson 双语精塑)
Tier 3 (Extractor): Agnes 2.5 Flash (三维知识萃取)
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
MIN_TEXT_LEN = 20  # 降低门槛，确保不遗漏 63, 64 等页面

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def call_llm_with_fallback(system_prompt: str, user_content: str, primary_provider: str, primary_model: str, fallback_provider: str = None, fallback_model: str = None, max_retries=5, timeout=90) -> str:
    cfg = load_config()
    
    providers_to_try = [(primary_provider, primary_model)]
    if fallback_provider and fallback_model:
        providers_to_try.append((fallback_provider, fallback_model))
        
    for provider, model in providers_to_try:
        pkg = cfg.get("provider", {}).get(provider, {})
        api_key = pkg.get("options", {}).get("apiKey", "")
        base_url = pkg.get("options", {}).get("baseURL", "")
        if not api_key:
            continue

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
                wait = min(4 * (attempt + 1), 20)
                print(f"    ⚠️ {provider}/{model} 重试 ({attempt+1}/{max_retries}): {e}", file=sys.stderr)
                time.sleep(wait)

    raise RuntimeError(f"All providers failed for prompt")

PROMPT_HEALER = """你是"疗愈者"(The Healer)。修复OCR文本：
1. 去掉字间多余空格
2. 纠正明显错别字
3. 补全截断标点
4. 保持原意，繁体保留
5. 彻底过滤并删除任何微信、QQ、公众号、扫描件广告、页眉页脚水印、联系方式、文件名等垃圾广告信息
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

def main():
    if not PDF_PATH.exists():
        print(f"❌ PDF不存在: {PDF_PATH}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 强制覆盖或补充 61 至 90 页
    start_page = 61
    end_page = 90
    
    # 查找目前还未成功生成完整 Markdown 的页面
    needed_pages = []
    for p in range(start_page, end_page + 1):
        f = OUTPUT_DIR / f"page_{p:03d}.md"
        if not f.exists() or f.stat().st_size < 200:
            needed_pages.append(p)

    print(f"🚀 开始批处理《张忠谋自传》第 {start_page} 至 {end_page} 页 (待处理 {len(needed_pages)} 页)")

    success_count = 0
    for p in range(start_page, end_page + 1):
        out_file = OUTPUT_DIR / f"page_{p:03d}.md"
        if out_file.exists() and out_file.stat().st_size >= 200:
            print(f"  ⏭️ 第 {p} 页已存在且完整，跳过")
            success_count += 1
            continue

        try:
            raw_text = get_pdf_text(p).strip()
            if len(raw_text) < MIN_TEXT_LEN:
                print(f"  ⏭️ 第 {p} 页文本过短 ({len(raw_text)} 字)，跳过")
                continue

            print(f"\n📄 处理第 {p} 页 ({len(raw_text)} 字)...", file=sys.stderr)

            # Tier 1: Gemini 3.6 Flash (Primary: 053c6d95-41ee-4af4-bc18-dacc1d31b2cb/gemini-3.6-flash-high, Fallback: freebuff/gemini-3.6-flash)
            print("  ⚡ Tier 1: Gemini 3.6 Flash 文本修复 (含水印广告过滤)...", file=sys.stderr)
            healed = call_llm_with_fallback(
                PROMPT_HEALER, raw_text,
                "053c6d95-41ee-4af4-bc18-dacc1d31b2cb", "gemini-3.6-flash-high",
                "freebuff", "gemini-3.6-flash"
            )

            # Tier 2: Agnes 2.5 Flash (Fallback: deepseek/deepseek-v4-flash)
            print("  🎨 Tier 2: Agnes 2.5 Flash 商务英文重塑...", file=sys.stderr)
            bilingual = call_llm_with_fallback(
                PROMPT_ARCHITECT, healed,
                "agnes", "agnes-2.5-flash",
                "deepseek", "deepseek-v4-flash"
            )

            # Tier 3: Agnes 2.5 Flash (Fallback: deepseek/deepseek-v4-flash)
            print("  💎 Tier 3: Agnes 2.5 Flash 知识萃取...", file=sys.stderr)
            extracted = call_llm_with_fallback(
                PROMPT_EXTRACTOR, bilingual,
                "agnes", "agnes-2.5-flash",
                "deepseek", "deepseek-v4-flash"
            )

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
            out_file.write_text(full_md, encoding="utf-8")
            print(f"  ✅ 第 {p} 页已保存 → {out_file.name}", file=sys.stderr)
            success_count += 1

            # 稍微停顿，防止 API 频率过快导致 503
            time.sleep(1.5)

        except Exception as e:
            print(f"  ❌ 第 {p} 页失败: {e}", file=sys.stderr)

    print(f"\n✨ 批处理完成: 成功 {success_count} / {end_page - start_page + 1} 页")

    # 刷新 HTML 预览
    print("🔄 正在刷新 output/preview_book.html...")
    os.system(f"node {BASE_DIR / 'workdir' / 'render_html_v6.js'}")
    print("✅ 预览页面已成功刷新！")

if __name__ == "__main__":
    main()
