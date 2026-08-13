#!/usr/bin/env python3
"""
ReadShift CLI Unified Entrance (命令行统一入口)
用法:
  python3 cli/readshift.py build [--chapter N | --chapters 1,2,3 | --input DIR --output FILE]
  python3 cli/readshift.py qa [--chapter N | --html FILE]
  python3 cli/readshift.py check [--chapter N | --source-dir DIR]
  python3 cli/readshift.py init --book-name "NAME"
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def run_build(args):
    cmd = ["node", str(BASE_DIR / "workdir" / "render_html_v9.js")]
    if args.chapter:
        cmd.extend(["--chapter", str(args.chapter)])
    elif args.chapters:
        cmd.extend(["--chapters", str(args.chapters)])
    elif args.input and args.output:
        cmd.extend(["--full-dir", str(args.input), "--out-file", str(args.output)])
    
    print(f"🚀 执行 ReadShift 杂志级排版渲染: {' '.join(cmd)}")
    return subprocess.call(cmd)

def run_qa(args):
    cmd = [sys.executable, str(BASE_DIR / "workdir" / "qa_gate_v3.py")]
    if args.chapter:
        cmd.extend(["--chapter", str(args.chapter)])
    elif args.html:
        cmd.extend(["--html", str(args.html)])
    
    print(f"🛡️ 执行 ReadShift 深层质量审计 (QA Auditor v3.0): {' '.join(cmd)}")
    return subprocess.call(cmd)

def run_check(args):
    cmd = ["bash", str(BASE_DIR / "docs" / "HEALTHCHECK.sh")]
    print(f"🩺 执行 ReadShift D1 资产健康体检: {' '.join(cmd)}")
    return subprocess.call(cmd)

def run_init(args):
    book_dir = Path.cwd() / args.book_name
    print(f"✨ 正在初始化 ReadShift 双语电子书工程: {book_dir}")
    (book_dir / "raw_source").mkdir(parents=True, exist_ok=True)
    (book_dir / "source").mkdir(parents=True, exist_ok=True)
    (book_dir / "output").mkdir(parents=True, exist_ok=True)
    
    # 写入示例 page_001.md
    sample_md = """# 第一章 · 开启双语新篇

<div class="rebook-translation">
<span class="rebook-translation__label">ReadShift 双语翻译</span>
<p class="en-para">Chapter 1 · Opening a New Chapter in Bilingual Reading</p>
</div>

这是一个利用 ReadShift 引擎创建的示例段落。

<div class="rebook-translation">
<span class="rebook-translation__label">ReadShift 双语翻译</span>
<p class="en-para">This is a sample paragraph created using the ReadShift Engine.</p>
</div>

## 一、双语融合

<div class="rebook-translation">
<span class="rebook-translation__label">ReadShift 双语翻译</span>
<p class="en-para">Bilingual Integration</p>
</div>

### Cheat Sheet · 商业语汇
1. **bilingual edition** — 双语版本；指采用两种语言对照排版的典藏著作。
**商业造句**：The publisher released a bilingual edition of the CEO's memoir for global markets.

### 语言与逻辑赏析
<span class="rhetoric-note"><span class="zh">首段以简练语言切入，中英文呈平行流动之势。</span><span class="en">The opening passage starts with concise language, flowing in parallel between Chinese and English.</span></span>

### 背景知识延伸
<div class="knowledge-note">
  <span class="zh">**ReadShift**：开源双语电子书与排版引擎。</span>
  <span class="en">**ReadShift**: Open-source bilingual book and typography engine.</span>
</div>
"""
    (book_dir / "source" / "page_001.md").write_text(sample_md, encoding="utf-8")
    print(f"✅ 工程创建完成！示例源文件置于 {book_dir / 'source' / 'page_001.md'}")
    return 0

def main():
    parser = argparse.ArgumentParser(description="ReadShift CLI - 双语电子书排版与平行叙事引擎")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # build 命令
    p_build = subparsers.add_parser("build", help="编译 Markdown 为杂志级双语 HTML")
    p_build.add_argument("--chapter", help="单章编号（如 1）")
    p_build.add_argument("--chapters", help="多章合成（如 1,2,3）")
    p_build.add_argument("--input", help="源文件目录")
    p_build.add_argument("--output", help="输出 HTML 文件路径")

    # qa 命令
    p_qa = subparsers.add_parser("qa", help="执行 QA 质量门禁审计")
    p_qa.add_argument("--chapter", help="单章编号（如 1）")
    p_qa.add_argument("--html", help="HTML 文件路径")

    # check 命令
    p_check = subparsers.add_parser("check", help="D1 源料体检")
    p_check.add_argument("--source", help="源目录")

    # init 命令
    p_init = subparsers.add_parser("init", help="初始化新电子书工程")
    p_init.add_argument("--book-name", required=True, help="书名/工程目录名")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "build":
        sys.exit(run_build(args))
    elif args.command == "qa":
        sys.exit(run_qa(args))
    elif args.command == "check":
        sys.exit(run_check(args))
    elif args.command == "init":
        sys.exit(run_init(args))

if __name__ == "__main__":
    main()
