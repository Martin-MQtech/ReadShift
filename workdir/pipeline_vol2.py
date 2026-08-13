#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下册章级二创生产管线 (ReadShift Vol.2)
======================================
输入:  workdir/v2_ocr/chapters/*.md   (45 章, 繁体 OCR, 含 <!-- 原書第X頁 --> 注释)
输出:  output/full_v2/page_XXX.md     (页级 markdown, 兼容 render_html_v9.js 渲染契约)
引擎:  Healer = deepseek-v4-flash     (繁转简 + OCR 修复 + 噪音清除)
       Architect/Extractor = agnes-2.5-flash  (Isaacson 双语重塑 + 词卡/赏析/知识窗)
设计:
  - 按章读取, 按页注释保留分页信息, 按 ~2600 字符合并为批
  - 每批: Healer(修复, 保留页注释) -> Architect(双语重塑 + 三区块)
  - 输出按页注释切回页级文件; 三区块附加到批末有内容的页
血泪经验遵守:
  - 不输出任何生产标签 (Healer/双语重塑/知识萃取 等字样绝不出现在成品)
  - 页码只保留 <!-- 原書第X頁 --> 注释
  - OCR 孤立字 / 乱码英文碎片 / 引号错乱 由 Healer 清除
用法:
  python3 workdir/pipeline_vol2.py --chapters 04,09        # 试点指定章(前缀序号)
  python3 workdir/pipeline_vol2.py --all                    # 全部 45 章
  python3 workdir/pipeline_vol2.py --chapters 04 --workers 2
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CHAPTERS_DIR = BASE_DIR / "workdir" / "v2_ocr" / "chapters"
OUTPUT_DIR = BASE_DIR / "output" / "full_v2"
CONFIG_PATH = Path.home() / ".zcode" / "v2" / "config.json"

# 单批目标字符数(中文), 双语输出后控制在 agnes 8192 token 内
BATCH_CHARS = 2600
MAX_RETRIES = 4
TIMEOUT = 150

HEALER_PROVIDER = "deepseek"
HEALER_MODEL = "deepseek-v4-flash"
ARCH_PROVIDER = "agnes"
ARCH_MODEL = "agnes-2.5-flash"

# ── Prompt ──────────────────────────────────────────────────────────
PROMPT_HEALER = """你是「疗愈者」(The Healer)。修复 OCR 繁体中文文本，输出规范简体中文。

任务：
1. 繁体中文 → 简体中文
2. 纠正 OCR 错字（如「開關客戶」→「開發客戶」、「德位」→「德儀」、「錄羽」→「鎩羽」）
3. 修正错乱引号：`!雙極」` `'標準式商品」` `「!MOS,」` 这类残缺引号统一为规范「」
4. 删除孤立噪音字（单独出现在行内或段落间的「中」「回」「嘻」「出」等印刷残留）
5. 清除乱码英文碎片（如 "AGE lad" "SO PTET 移民到326" 中无法识别的乱码 token）
6. 补全截断标点，合并被切断的句子，保持原意，最小修改
7. 段落结构保持原样，不要凭空增删内容

【页码注释规则】输入中的 `<!-- 原書第X頁 -->` 注释必须原样保留在输出中的对应位置，不得删除或移动。

只输出修复后的文本本身，不要任何解释、不要额外标题、不要前后缀。"""

PROMPT_ARCHITECT = """你是双语架构师，仿沃尔特·艾萨克森(Walter Isaacson)传记风格（《Steve Jobs》《爱因斯坦传》）。

将以下简体中文传记文本重塑为逐段中英对照的双语版本：
- 中文：语言精致化但不失真，保留张忠谋第一人称的口吻与叙事节奏
- 英文：克制、精确、地道现代商业英语，叙事感强，有 Isaacson 的文学质感
- 格式：每段中文在前，空一行后紧跟对应英文翻译；段与段之间空一行

【页码注释规则】`<!-- 原書第X頁 -->` 注释必须原样保留在输出中的对应位置。

在双语文本全部完成后，另起部分输出三区块（严格使用以下标题）：
# 📌 商业词汇卡片
1. **expression**（英文表达，中文解释 + 真实商业造句）
（5-8 个，选自本批文本中的地道商业表达）
# 🎯 修辞与逻辑赏析
- （2-4 条，分析本批文本的叙事手法、修辞、结构）
# 🌐 外链知识窗
- （2-3 条，与本批内容相关的真实历史/商业/科技背景知识）

直接输出完整内容，不要任何前后缀说明。"""


# ── LLM 调用 ─────────────────────────────────────────────────────────
def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def call_llm(system_prompt: str, user_content: str, provider: str, model: str) -> str:
    cfg = load_config()
    pkg = cfg.get("provider", {}).get(provider, {})
    opts = pkg.get("options", {})
    api_key = opts.get("apiKey", "")
    base_url = opts.get("baseURL", "")
    if not api_key or not base_url:
        raise ValueError(f"provider {provider} 缺少 apiKey/baseURL")

    url = f"{base_url}/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "max_tokens": 8192,
        "temperature": 0.3,
    }).encode()

    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(
                url, data=payload,
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {api_key}"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                data = json.loads(resp.read())
                result = data["choices"][0]["message"]["content"].strip()
                if result and len(result) > 20:
                    return result
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = min(5 * (attempt + 1), 30)
                print(f"    ⚠️ 429 限流, 等待 {wait}s ({(attempt+1)}/{MAX_RETRIES})", file=sys.stderr)
                time.sleep(wait)
                continue
            wait = min(3 * (attempt + 1), 15)
            print(f"    ⚠️ HTTP {e.code}: {e} 重试 ({(attempt+1)}/{MAX_RETRIES})", file=sys.stderr)
            time.sleep(wait)
        except Exception as e:
            wait = min(3 * (attempt + 1), 15)
            print(f"    ⚠️ {provider}/{model} 重试 ({(attempt+1)}/{MAX_RETRIES}): {e}", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"All retries failed for {provider}/{model}")


# ── 章节解析 ─────────────────────────────────────────────────────────
PAGE_RE = re.compile(r"<!--\s*原書第\s*(\d+)\s*頁\s*-->")


def parse_chapter(path: Path):
    """返回 (章标题, [(page_num, text)])，text 为注释之间的 OCR 文本。"""
    raw = path.read_text(encoding="utf-8", errors="replace")
    lines = raw.split("\n")

    # 章标题 = 第一个 # 行
    title = ""
    for ln in lines:
        m = re.match(r"^#\s+(.+)$", ln.strip())
        if m:
            title = m.group(1).strip()
            break

    # 按页注释切分
    pages = []  # [(page_num, [lines])]
    cur_num = None
    cur_lines = []
    for ln in lines:
        m = PAGE_RE.search(ln)
        if m:
            if cur_num is not None:
                pages.append((cur_num, cur_lines))
            cur_num = int(m.group(1))
            cur_lines = []
            continue
        # 跳过元信息行: 标题、页范围引用
        t = ln.strip()
        if not pages and (t.startswith("> 原書頁碼") or t == title or t.startswith("# ")):
            continue
        cur_lines.append(ln)
    if cur_num is not None:
        pages.append((cur_num, cur_lines))

    # 清洗页内文本
    cleaned = []
    for num, plines in pages:
        text = "\n".join(plines)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = text.strip()
        # 去章节标题重复行
        text = re.sub(rf"^{re.escape(title)}\s*$", "", text, flags=re.M)
        cleaned.append((num, text.strip()))
    return title, [p for p in cleaned if p[1]]


def group_batches(pages, max_chars=BATCH_CHARS):
    """按页注释合并为批, 每批尽量不切断页内文本。返回 [(起始页码, 批文本)]。"""
    batches = []
    buf = []
    buf_chars = 0
    for num, text in pages:
        marker = f"<!-- 原書第{num}頁 -->\n{text}"
        if buf and buf_chars + len(text) > max_chars:
            batches.append((buf[0][0], "\n\n".join(m for _, m in buf)))
            buf = [(num, marker)]
            buf_chars = len(text)
        else:
            buf.append((num, marker))
            buf_chars += len(text)
    if buf:
        batches.append((buf[0][0], "\n\n".join(m for _, m in buf)))
    return batches


# ── 输出切回页级 ─────────────────────────────────────────────────────
def split_back_to_pages(bilingual: str, extras: str, start_page: int):
    """把双语流 + 三区块按页注释切回页级。返回 {page_num: 文本}。"""
    result = {}
    # 三区块之前的双语流
    section_cut = re.split(r"(?=^# 📌 商业词汇卡片)", bilingual, flags=re.M)
    main_flow = section_cut[0]
    # 找到双语流里的页注释位置切分
    parts = PAGE_RE.split(main_flow)
    # parts: [before, num, text, num, text...]
    if len(parts) < 3:
        # 无双语或无法切分
        return {start_page: (main_flow.strip() + "\n\n" + extras).strip()}
    pages = {}
    for i in range(1, len(parts) - 1, 2):
        num = int(parts[i])
        text = parts[i + 1].strip()
        if text:
            pages[num] = text
    # 三区块附加到批内最后一个有内容的页
    if pages and extras.strip():
        last_num = max(pages.keys())
        pages[last_num] = pages[last_num] + "\n\n" + extras.strip()
    elif not pages:
        pages[start_page] = extras.strip()
    return pages


# ── 单章处理 ─────────────────────────────────────────────────────────
def process_chapter(ch_path: Path) -> int:
    title, pages = parse_chapter(ch_path)
    if not pages:
        print(f"⏭️ {ch_path.name}: 无内容页, 跳过")
        return 0
    batches = group_batches(pages)
    total_chars = sum(len(t) for _, t in pages)
    print(f"📖 {ch_path.name} | {title[:30]} | {len(pages)} 页 / {total_chars} 字 / {len(batches)} 批")

    produced = {}
    for bi, (start_num, batch_text) in enumerate(batches):
        print(f"  ⚡ 批 {bi+1}/{len(batches)} (从第{start_num}页起, {len(batch_text)}字)...", file=sys.stderr)
        try:
            healed = call_llm(PROMPT_HEALER, batch_text, HEALER_PROVIDER, HEALER_MODEL)
            print(f"    ✅ Healer 修复完成 ({len(healed)}字)", file=sys.stderr)
            bilingual = call_llm(PROMPT_ARCHITECT, healed, ARCH_PROVIDER, ARCH_MODEL)
            print(f"    ✅ Architect 双语重塑完成 ({len(bilingual)}字)", file=sys.stderr)

            # 分离三区块与双语流
            extras = ""
            flow = bilingual
            for header in ["# 📌 商业词汇卡片", "# 🎯 修辞与逻辑赏析", "# 🌐 外链知识窗"]:
                idx = flow.find(header)
                if idx >= 0:
                    extras = flow[idx:].strip()
                    flow = flow[:idx].strip()
                    break

            page_map = split_back_to_pages(flow, extras, start_num)
            for num, txt in page_map.items():
                if num in produced:
                    produced[num] += "\n\n" + txt
                else:
                    produced[num] = txt
        except Exception as e:
            print(f"    ❌ 批 {bi+1} 失败: {e}", file=sys.stderr)

    # 写页级文件
    written = 0
    for num in sorted(produced):
        out = OUTPUT_DIR / f"page_{num:03d}.md"
        content = f"<!-- 原書第{num}頁 -->\n\n" + produced[num].strip() + "\n"
        out.write_text(content, encoding="utf-8")
        written += 1
    print(f"  ✅ 写出 {written} 个页文件")
    return written


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chapters", default="", help="章前缀序号, 逗号分隔, 如 04,09")
    ap.add_argument("--all", action="store_true", help="处理全部章节")
    ap.add_argument("--workers", type=int, default=2, help="并发章节数")
    args = ap.parse_args()

    ch_files = sorted(CHAPTERS_DIR.glob("*.md"))
    if not args.all:
        wanted = [c.strip() for c in args.chapters.split(",") if c.strip()]
        ch_files = [f for f in ch_files if f.name.split("_")[0] in wanted]

    if not ch_files:
        print("❌ 没有匹配的章节文件")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"🚀 下册二创管线启动: {len(ch_files)} 章")
    print(f"   Healer: {HEALER_PROVIDER}/{HEALER_MODEL}")
    print(f"   Architect: {ARCH_PROVIDER}/{ARCH_MODEL} (Isaacson)")
    print(f"   输出: {OUTPUT_DIR}\n")

    total_pages = 0
    if args.workers > 1 and len(ch_files) > 1:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(process_chapter, f): f for f in ch_files}
            for fut in as_completed(futs):
                try:
                    total_pages += fut.result()
                except Exception as e:
                    print(f"❌ 章节线程异常: {e}", file=sys.stderr)
    else:
        for f in ch_files:
            total_pages += process_chapter(f)

    print(f"\n🎉 完成! 共产出 {total_pages} 个页文件 → {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
