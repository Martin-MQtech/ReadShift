#!/usr/bin/env python3
"""Retry failed pages 107, 109, 112, 114, 116"""
import json, os, sys, time, urllib.request, urllib.error
from pathlib import Path

CONFIG_PATH = Path.home() / ".zcode" / "v2" / "config.json"
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output" / "full"
PDF_PATH = BASE_DIR / "張忠謀自傳上冊(1931-1964).pdf"

FAILED_PAGES = [107, 109, 112, 114, 116]

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def call_llm(system_prompt, user_content, provider_key, model, max_retries=5, timeout=120):
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
            req = urllib.request.Request(url, data=payload,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
                method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
                result = data["choices"][0]["message"]["content"].strip()
                if result and len(result) > 10:
                    return result
        except Exception as e:
            wait = min(5 * (attempt + 1), 30)
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

for p in FAILED_PAGES:
    raw = get_pdf_text(p)
    if len(raw) < 50:
        print(f"⏭️ 第 {p} 页文本过短 ({len(raw)} 字)，跳过", file=sys.stderr)
        continue

    out_file = OUTPUT_DIR / f"page_{p:03d}.md"

    print(f"📄 重试第 {p} 页 ({len(raw)} 字)...", file=sys.stderr)

    # Tier 1
    print(f"  Tier 1: Gemini...", file=sys.stderr)
    healed = call_llm(PROMPT_HEALER, raw,
        "053c6d95-41ee-4af4-bc18-dacc1d31b2cb", "gemini-3.6-flash-high", timeout=60)
    print(f"  ✅ Tier 1 done ({len(healed)} 字)", file=sys.stderr)

    # Tier 2
    print(f"  Tier 2: Agnes...", file=sys.stderr)
    bilingual = call_llm(PROMPT_ARCHITECT, healed,
        "agnes", "agnes-2.5-flash", timeout=120)
    print(f"  ✅ Tier 2 done", file=sys.stderr)

    full_md = f"""# 《张忠谋自传》第{p}页

---

## 修复文本

{healed}

---

## 双语重塑

{bilingual}

<!-- PROCESSED -->
"""
    out_file.write_text(full_md, encoding="utf-8")
    print(f"  ✅ 第 {p} 页已保存", file=sys.stderr)
    time.sleep(2)

print("\n🔄 刷新 HTML...", file=sys.stderr)
os.system(f'node "{BASE_DIR}/workdir/render_html_v8.js"')
print("✅ 完成")
