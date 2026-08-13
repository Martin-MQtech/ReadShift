#!/usr/bin/env python3
"""
Retry failed pages from 41-70 with longer timeouts and more careful handling.
"""

import json, os, sys, time, urllib.request, urllib.error
from pathlib import Path

CONFIG_PATH = Path.home() / ".zcode" / "v2" / "config.json"
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output" / "full"
PDF_PATH = BASE_DIR / "張忠謀自傳上冊(1931-1964).pdf"

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def call_llm(system_prompt, user_content, provider, model, max_retries=3, timeout=180):
    cfg = load_config()
    pkg = cfg.get("provider", {}).get(provider, {})
    api_key = pkg.get("options", {}).get("apiKey", "")
    base_url = pkg.get("options", {}).get("baseURL", "")
    if not api_key:
        raise ValueError(f"No apiKey for {provider}")
    url = f"{base_url}/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system_prompt},
                     {"role": "user", "content": user_content}],
        "max_tokens": 4096, "temperature": 0.3
    }).encode()
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
            wait = min(8 * (attempt + 1), 30)
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

PROMPT_BILINGUAL = """你是双语架构师，仿沃尔特·艾萨克森(Walter Isaacson)传记风格。

任务：将以下中文段落改写为逐段中英对照的双语版本。

英文风格：克制、精确、叙事感强，符合英文自传文学传统。

**严格输出格式**：
[中文段落]
---
[英文翻译]
---
[下一个中文段落]
---
[下一个英文翻译]
...

最后加：
### 商业语汇提炼
1. **expression**
   **中文解释**：...
   **商业造句**：...

### 修辞赏析
...

### 外链知识窗
...

注意：
- 直接以第一个中文段落开始，不要加任何标题
- 不要输出任何其他标题
- 繁简统一用简体中文"""

def get_pdf_text(page_num):
    import fitz
    doc = fitz.open(str(PDF_PATH))
    text = doc.load_page(page_num - 1).get_text()
    doc.close()
    return text.strip()

def process_page(p):
    raw_text = get_pdf_text(p)
    if len(raw_text) < 150:
        print(f"  ⏭️ 第 {p} 页文本过短 ({len(raw_text)} 字)，跳过", file=sys.stderr)
        return False
    print(f"📄 第 {p} 页 ({len(raw_text)} 字)...", file=sys.stderr)
    try:
        healed = call_llm(PROMPT_HEALER, raw_text, "053c6d95-41ee-4af4-bc18-dacc1d31b2cb", "gemini-3.6-flash-high")
        time.sleep(1)
        bilingual = call_llm(PROMPT_BILINGUAL, healed, "agnes", "agnes-2.5-flash", timeout=180)
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
        print(f"  ✅ 第 {p} 页完成", file=sys.stderr)
        return True
    except Exception as e:
        print(f"  ❌ 第 {p} 页失败: {e}", file=sys.stderr)
        return False

def main():
    # Failed pages from last run
    failed_pages = [42, 47, 50, 54, 56, 57, 59, 63, 64, 65, 66, 68, 69]
    # Skip pages 63, 64 which are too short
    failed_pages = [p for p in failed_pages if p not in [63, 64]]

    print(f"🚀 重试处理 {len(failed_pages)} 页: {failed_pages}", file=sys.stderr)

    success = 0
    for p in failed_pages:
        try:
            if process_page(p):
                success += 1
        except Exception as e:
            print(f"  ❌ 第 {p} 页: {e}", file=sys.stderr)
        time.sleep(3)

    print(f"\n🎉 重试完成！成功 {success}/{len(failed_pages)} 页。", file=sys.stderr)
    print("🔄 正在刷新 HTML ...")
    os.system("node /Users/martin/Documents/20260812MartinGitHub\\ /20260812\\ 电子书二创工具/workdir/render_html_v8.js")

if __name__ == "__main__":
    main()
