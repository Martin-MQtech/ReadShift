#!/usr/bin/env python3
"""ReBook 翻译批次脚本：调用 agnes API，将中文段落译为艾萨克森风格英文。

用法: python3 translate_batches.py <input.json> <output.json>
input.json: {"page": "036", "paragraphs": ["...", ...]}
输出: {"page": "036", "translations": ["...", ...]}
重试策略: SSL/网络错误等待 20 秒重试，最多 4 次。
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
import ssl

BASE_URL = os.environ.get("AGNES_BASE_URL", "https://apihub.agnes-ai.com/v1/chat/completions")
API_KEY = os.environ.get("AGNES_API_KEY", "")
MODEL = os.environ.get("AGNES_MODEL", "agnes-2.5-flash")

SYSTEM_PROMPT = (
    "你是一位精通中英双语的文学译者，专长是人物传记翻译。"
    "你翻译的对象是台积电创始人张忠谋《张忠谋自传》的正文段落。"
    "翻译风格严格模仿沃尔特·艾萨克森（Walter Isaacson）的传记笔法：克制、精确、有叙事感，"
    "句子凝练有力，用词地道自然，避免华丽辞藻、避免逐字直译的翻译腔；"
    "保留原意、细节与情感分寸，时态用一般过去时叙述，人名地名采用通用英译。"
    "短标题类段落（如“六、生活品質”）译为简洁的英文小标题。"
    "若中文以省略号（……）结尾，表示原文在此处截断，英文译文也应以省略号（…）结尾。"
    "你只输出译文本身，不输出任何解释、前言或编号。"
)

def call_api(user_text, max_tokens=6000):
    if not API_KEY:
        raise RuntimeError("缺少 AGNES_API_KEY 环境变量，拒绝发送未认证请求")

    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.4,
    }).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + API_KEY,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.loads(r.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()


def translate_paragraphs(paragraphs, page_label):
    import re
    n = len(paragraphs)
    numbered = "\n\n".join(f"【段落{i+1}】\n{p}" for i, p in enumerate(paragraphs))
    total_chars = sum(len(p) for p in paragraphs)
    user_text = (
        f"下面是要翻译的《张忠谋自传》第{page_label}页中文正文，共 {n} 段，"
        f"总字数约 {total_chars} 字。请逐段翻译为艾萨克森风格英文。\n"
        f"输出要求：每一段译文之前独占一行写上形如 ===1=== 的分隔标记（编号与输入段号一一对应），"
        f"标记行之后紧跟该段英文译文；标记之间不要空行；不要输出任何其他文字、解释或 markdown 代码块。\n\n"
        + numbered
    )

    last_err = None
    for attempt in range(1, 5):
        try:
            raw = call_api(user_text)
            # 按 ===N=== 标记解析，天然容忍译文内部换行
            marker_re = re.compile(r"===(\d+)===\s*(.*?)(?====\d+===|$)", re.S)
            found = marker_re.findall(raw)
            if not found:
                raise ValueError(f"未找到 ===N=== 标记，原始输出前200字: {raw[:200]!r}")
            parts = []
            for num, text in found:
                idx = int(num)
                while len(parts) < idx:
                    parts.append("")
                parts[idx - 1] = text.strip()
            parts = [p for p in parts if p]
            if len(parts) != n:
                raise ValueError(f"段落数不符: 期望 {n}, 实际 {len(parts)}")
            return parts
        except (urllib.error.URLError, ssl.SSLError, TimeoutError, ConnectionError, ValueError) as e:
            last_err = e
            print(f"  [attempt {attempt}/4] 失败: {type(e).__name__}: {e}", flush=True)
            if attempt < 4:
                print("  等待 20 秒后重试…", flush=True)
                time.sleep(20)
    raise RuntimeError(f"翻译失败（4 次重试均未成功）: {last_err}")


def main():
    in_path, out_path = sys.argv[1], sys.argv[2]
    with open(in_path, encoding="utf-8") as f:
        job = json.load(f)
    paras = job["paragraphs"]
    print(f"开始翻译第 {job['page']} 页：{len(paras)} 段，"
          f"{sum(len(p) for p in paras)} 字", flush=True)
    t0 = time.time()
    trans = translate_paragraphs(paras, job["page"])
    print(f"完成，耗时 {time.time()-t0:.0f}s", flush=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"page": job["page"], "translations": trans},
                  f, ensure_ascii=False, indent=2)
    for i, t in enumerate(trans):
        print(f"  [{i+1}] ({len(t)} 词) {t[:60]}…" if len(t) > 60 else f"  [{i+1}] {t}")


if __name__ == "__main__":
    main()
