#!/usr/bin/env python3
"""
ReBook 生产管线 v6 - DeepSeek 接茬版 (模型无关的云端多代理续跑)
关键设计：子代理只是"执行器"，模型通过 API 配置动态切换，接茬靠文件契约：
  - 已产出的 page_XXX.md 自动跳过（done 检测）
  - 未产出的正文页自动补齐
Tier 1 (Healer): DeepSeek V4 Flash (免费，中文修复)
Tier 2 (Architect): Agnes 2.5 Flash (Isaacson 双语精塑) 
Tier 3 (Extractor): DeepSeek V4 Flash
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


def call_llm(system_prompt: str, user_content: str, provider: str, model: str, max_retries=4, timeout=90) -> str:
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
            print(f"    ⚠️ {provider}/{model} 重试 ({attempt+1}/{max_retries}): {e}", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"All retries failed for {provider}/{model}")


PROMPT_HEALER = """你是"疗愈者"(The Healer)。修复OCR繁体中文文本：
1. 去掉字间多余空格
2. 纠正明显错别字
3. 补全截断标点
4. 保持原意
5. 输出规范简体中文（繁体自动转简体）
6. 只输出修复后的文本，不要解释

【跨页续句修复规则（关键能力）】
- 如果文本开头是断句残迹（如孤立的"战"、"的"、"了"等半个字/词，或"……"开头接半个词），说明这是上一页被截断后延续下来的残句
- 处理方式：删除开头的残迹（"……"和孤立残词），或根据语义补全为一个完整通顺的句子（补全时只做最小修补，如"战，连当年中国的文革浩劫"补为"那场战争，连当年中国的文革浩劫"）
- 绝不能把残句原样保留在正文里，也不能凭空编造大段内容

【夹带私货剔除规则（关键能力）】
- 识别并剔除盗版水印：微信号/QQ号推广、书单广告（幸福的味道、周读、ireadweek、豆瓣/当当/亚马逊书单）、"本书由XX整理"声明、"仅供个人学习"版权声明、免费电子书下载网站宣传
- 若整页都是广告 → 输出 <AD_PAGE>
- 若广告与正文混排 → 只保留正文，剔除广告部分"""

PROMPT_ARCHITECT = """你是双语架构师，仿沃尔特·艾萨克森(Walter Isaacson)传记风格（《Steve Jobs》《爱因斯坦传》）。
任务：将以下中文段落改写为逐段中英对照的双语版本。
英文风格：克制、精确、叙事感强。
格式要求（严格遵守）：
- 每段中文后紧跟 "---"，然后英文翻译，再 "---"
- 最后写：
### 📌 商业语汇提炼
1. **expression**（中文解释+真实商业造句）
### 🎯 修辞赏析
### 🌐 外链知识窗
注意：每一段中文都必须配上英文翻译，不要省略。"""

PROMPT_ARCHITECT_HANHAN = """你是双语架构师，本段采用【韩寒风格】——80后代表性作家的白描叙事，中英双语皆适用。

【韩寒风格特征】
- 句子短、白描、冷峻，不堆砌形容词
- 用具体的动作和细节代替抒情
- 略带自嘲与黑色幽默，但底色是极度的清醒与真诚
- 语言朴素，接近口语，但节奏感强
- 观点直接，不绕弯子
- 英文翻译同样遵循：短句、直接、有力，避免华丽辞藻
- 示范：中文"我这人，一辈子就在忙，没工夫琢磨什么叫成就感。这钱买不来。"
      英文"I've spent my life doing things. Never had time to wonder what 'sense of achievement' even means. Money can't buy that."

格式要求（严格遵守）：
- 每段中文后紧跟 "---"，然后英文翻译，再 "---"
- 最后写：
### 📌 商业语汇提炼
1. **expression**（中文解释+真实商业造句）
### 🎯 修辞赏析
### 🌐 外链知识窗
注意：每一段中文都必须配上英文翻译，不要省略。"""

PROMPT_EXTRACTOR = """从以下双语文本中提取知识卡片：
### 📌 Cheat Sheet：地道商业表达
1. **expression**
   **中文解释**：...
   **商业造句**：...
### 🎯 修辞与逻辑赏析
### 🌐 外链知识窗
若输入太短，输出：<EMPTY_INPUT>"""


def get_pdf_text(page_num: int) -> str:
    import fitz
    doc = fitz.open(str(PDF_PATH))
    text = doc.load_page(page_num - 1).get_text()
    doc.close()
    return text


def process_page(page_num: int, healer_provider: str, healer_model: str, arch_provider: str, arch_model: str, persona: str = "isaacson") -> bool:
    try:
        raw_text = get_pdf_text(page_num).strip()
        if len(raw_text) < MIN_TEXT_LEN:
            print(f"  ⏭️ 第 {page_num} 页文本过短 ({len(raw_text)} 字)，跳过", file=sys.stderr)
            return False

        print(f"📄 第 {page_num} 页 ({len(raw_text)} 字)...", file=sys.stderr)

        # Tier 1: Healer
        print("  ⚡ Tier 1: 文本修复...", file=sys.stderr)
        healed = call_llm(PROMPT_HEALER, raw_text, healer_provider, healer_model)

        # Tier 2: Architect (可选 Persona 文风)
        print(f"  🎨 Tier 2: 双语重塑 ({persona} 文风)...", file=sys.stderr)
        architect_prompt = PROMPT_ARCHITECT_HANHAN if persona == "hanhan" else PROMPT_ARCHITECT
        bilingual = call_llm(architect_prompt, healed, arch_provider, arch_model, timeout=120)

        # Tier 3: Extractor
        print("  💎 Tier 3: 知识萃取...", file=sys.stderr)
        extracted = call_llm(PROMPT_EXTRACTOR, bilingual, healer_provider, healer_model)
        if extracted == "<EMPTY_INPUT>":
            extracted = "（文本较短，暂无法萃取）"

        full_md = f"""# 《张忠谋自传》第{page_num}页

---

## 修复文本

{healed}

---

## 双语重塑

{bilingual}

---

## 知识萃取

{extracted}

<!-- PROCESSED -->
"""
        out_file = OUTPUT_DIR / f"page_{page_num:03d}.md"
        out_file.write_text(full_md, encoding="utf-8")
        print(f"  ✅ 第 {page_num} 页已保存 → {out_file.name}", file=sys.stderr)
        return True
    except Exception as e:
        print(f"  ❌ 第 {page_num} 页失败: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=126)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--persona", default="isaacson", choices=["isaacson", "hanhan", "default"],
                        help="文风滤镜: isaacson(艾萨克森传记风) | hanhan(韩寒白描风) | default(中性客观)")
    parser.add_argument("--healer-provider", default="deepseek")
    parser.add_argument("--healer-model", default="deepseek-v4-flash")
    parser.add_argument("--arch-provider", default="agnes")
    parser.add_argument("--arch-model", default="agnes-2.5-flash")
    args = parser.parse_args()

    if not PDF_PATH.exists():
        print(f"❌ PDF不存在: {PDF_PATH}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    done = sorted([int(f.stem.split("_")[-1]) for f in OUTPUT_DIR.glob("page_*.md") if f.name != "_INDEX.md"])
    print(f"📖 已产出 {len(done)} 页: {done}")

    import fitz
    doc = fitz.open(str(PDF_PATH))
    total = len(doc)
    doc.close()

    end = min(args.end, total)
    start = max(args.start, 1)
    pending = [p for p in range(start, end + 1) if p not in done]

    # 过滤出有效正文页
    valid_pending = []
    for p in pending:
        t = get_pdf_text(p).strip()
        if len(t) >= MIN_TEXT_LEN:
            valid_pending.append(p)

    if not valid_pending:
        print("🎉 无需处理的页面！")
        return

    print(f"🚀 DeepSeek 接茬管线：待处理 {len(valid_pending)} 页")
    print(f"   Healer: {args.healer_provider}/{args.healer_model}")
    print(f"   Architect: {args.arch_provider}/{args.arch_model} ({args.persona} 文风)")
    print(f"   并发: {args.workers} 路\n")

    # 并发处理
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(process_page, p, args.healer_provider, args.healer_model,
                            args.arch_provider, args.arch_model, args.persona): p
            for p in valid_pending
        }
        for future in as_completed(futures):
            p = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"  ❌ 第 {p} 页线程异常: {e}", file=sys.stderr)

    done_now = sorted([int(f.stem.split("_")[-1]) for f in OUTPUT_DIR.glob("page_*.md") if f.name != "_INDEX.md"])
    print(f"\n🎉 接茬完成！当前产出 {len(done_now)} 页")


if __name__ == "__main__":
    main()
