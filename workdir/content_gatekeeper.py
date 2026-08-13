#!/usr/bin/env python3
"""
ReBook Tier 0: 内容守门员 (Content Gatekeeper)
==============================================
核心能力：语义级内容审判——识别"夹带私货"。

单一页面可能包含：
  ✅ 正文（作者原书内容）
  🚫 盗版广告页（微信号、书单推广、下载网站）
  🚫 目录页
  🚫 版权声明页
  🚫 纯图片页
  🚫 混合页（正文+水印混排 → 需要净化正文部分）

用法:
  python3 content_gatekeeper.py --page 8       # 审查单页
  python3 content_gatekeeper.py --scan         # 全量扫描 PDF
  python3 content_gatekeeper.py --audit-full   # 审查已产出 MD
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


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def call_llm(system_prompt, user_content, provider="deepseek", model="deepseek-v4-flash", max_retries=3, timeout=60):
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
        "max_tokens": 500,
        "temperature": 0.1
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
                if result:
                    return result
        except Exception as e:
            wait = min(3 * (attempt + 1), 15)
            print(f"    ⚠️ 重试 ({attempt+1}/{max_retries}): {e}", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError("All retries failed")


# 内容审判 Prompt：语义级判断，不是关键词匹配
PROMPT_JUDGE = """你是图书内容审判员（Content Judge）。你的任务是对一本书的扫描页面做语义级内容鉴别。

《张忠谋自传》是一本正经的商业人物传记。页面中可能"夹带私货"——盗版电子书网站强行植入的推广内容。

请判断该页属于以下哪种类型，并严格按 JSON 输出（不要输出任何其他文字）：

{
  "type": "正文 | 广告页 | 目录页 | 版权声明页 | 纯图片页 | 混合页",
  "is_ad_content": true/false,
  "ad_ratio": 0到1之间的小数（广告内容占整页比例）,
  "reason": "一句话判断理由",
  "正文部分": "如果type是混合页，请输出应保留的正文部分（完整保留原文，繁转简）；其他类型输出空字符串"
}

判断标准：
1. "正文"：张忠谋的人生叙述、商业思考、时代背景、人物描写——这是我们要的
2. "广告页"：微信号/QQ推广、书单推荐（如"幸福的味道"、"周读"、豆瓣/当当/亚马逊书单）、电子书下载网站、免费电子书推广、关注公众号——整页都是这些内容
3. "目录页"：全书章节标题列表
4. "版权声明页"：仅供个人学习、请勿用于商业用途、本书由XX整理等声明
5. "纯图片页"：无有效文字
6. "混合页"：既有正文又有植入广告（如正文下方贴着微信号广告）——此时必须把广告剔除，只保留正文

特别注意：广告可能伪装成任何形式（正文段落里穿插、翻译成英文、用引号包裹），要用语义判断而非关键词匹配。"""


def judge_page_text(text: str) -> dict:
    """对单页文本做内容审判"""
    result = call_llm(PROMPT_JUDGE, f"请审判这一页内容：\n\n{text}")
    # 提取 JSON
    try:
        start = result.find('{')
        end = result.rfind('}') + 1
        if start >= 0 and end > start:
            return json.loads(result[start:end])
    except Exception:
        pass
    return {"type": "未知", "is_ad_content": False, "ad_ratio": 0, "reason": result[:100]}


def audit_existing_md():
    """审查已产出的 MD 文件，标记夹带私货的页面"""
    results = []
    for f in sorted(os.listdir(OUTPUT_DIR)):
        if not f.endswith('.md') or f == '_INDEX.md':
            continue
        path = OUTPUT_DIR / f
        content = path.read_text(encoding='utf-8')
        if len(content) < 200:
            continue
        # 抽样判断（截取前800字）
        sample = content[:800]
        print(f"🔍 审查 {f}...", file=sys.stderr)
        verdict = judge_page_text(sample)
        verdict['file'] = f
        results.append(verdict)
        time.sleep(0.5)

    print(f"\n=== 已产出内容审查报告 ===")
    for r in results:
        flag = "🚫" if r.get('is_ad_content') else "✅"
        print(f"{flag} {r['file']}: {r.get('type')} (ad_ratio={r.get('ad_ratio', 0)}) | {r.get('reason', '')[:60]}")


def scan_pdf():
    """全量扫描 PDF 每页"""
    import fitz
    doc = fitz.open(str(PDF_PATH))
    total = len(doc)
    print(f"📖 PDF 共 {total} 页，开始内容审判...")
    for p in range(1, total + 1):
        text = doc.load_page(p - 1).get_text().strip()
        if len(text) < 30:
            print(f"  ⏭️ 第{p}页: 无有效文字（{'纯图片' if doc.load_page(p-1).get_images() else '空白'}）")
            continue
        verdict = judge_page_text(text[:600])
        flag = "🚫" if verdict.get('is_ad_content') else "✅"
        print(f"  {flag} 第{p}页 ({len(text)}字): {verdict.get('type')} | {verdict.get('reason', '')[:50]}")
        time.sleep(0.3)
    doc.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--page", type=int, help="审判单页")
    parser.add_argument("--scan", action="store_true", help="全量扫描 PDF")
    parser.add_argument("--audit-full", action="store_true", help="审查已产出 MD")
    args = parser.parse_args()

    if args.page:
        import fitz
        doc = fitz.open(str(PDF_PATH))
        text = doc.load_page(args.page - 1).get_text().strip()
        doc.close()
        if len(text) < 30:
            print(f"第{args.page}页无有效文字")
            return
        print(f"=== 第{args.page}页内容审判 ===")
        verdict = judge_page_text(text)
        print(json.dumps(verdict, ensure_ascii=False, indent=2))
    elif args.scan:
        scan_pdf()
    elif args.audit_full:
        audit_existing_md()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
