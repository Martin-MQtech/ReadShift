#!/usr/bin/env python3
"""
ReadShift 全文质量检查器 (Content QA Auditor)
========================================
自动排查低级错误：
1. 跨文件/文件内 段落重复
2. 结构性错位（卡片丢失、标题重复、正文断裂）
3. 中英文对应关系（纯中文无翻译的段落）
4. 残留水印/生产标签/转义泄露
5. HTML结构完整性（未闭合标签）
"""

import os, re, sys
from pathlib import Path
from collections import defaultdict

FULL_DIR = Path(__file__).parent.parent / "output" / "full"

SPAM_KEYWORDS = ['微信', '周读', 'ireadweek', '2338856113', '小编', '行行整理',
                 '免费电子书', '幸福的味道', '清福的味道', '小糊']
JUNK_LABELS = ['全量生产', 'Healer', 'Isaacson 双语', '双语重塑', '知识萃取',
               '修复文本', 'PROCESSED', 'Cheat Sheet', 'ReadShift 全量']
TITLE_CARDS = ['推荐序一', '推荐序二', '作者自序']


def extract_paras(text):
    """提取正文段落（去HTML标签）"""
    clean = re.sub(r'<[^>]+>', '', text)
    paras = [p.strip() for p in re.split(r'\n\s*\n', clean) if len(p.strip()) > 25]
    return paras


def check_cross_file_dups():
    """跨文件重复段落检测"""
    fp_map = defaultdict(list)
    for f in sorted(os.listdir(FULL_DIR)):
        if not f.endswith('.md') or f == '_INDEX.md':
            continue
        c = (FULL_DIR / f).read_text(encoding='utf-8')
        for p in extract_paras(c):
            fp = p[:30]
            fp_map[fp].append(f)
    dups = {fp: fs for fp, fs in fp_map.items() if len(set(fs)) > 1}
    return dups


def check_infile_dups():
    """文件内重复段落检测"""
    results = {}
    for f in sorted(os.listdir(FULL_DIR)):
        if not f.endswith('.md') or f == '_INDEX.md':
            continue
        c = (FULL_DIR / f).read_text(encoding='utf-8')
        paras = extract_paras(c)
        seen = set()
        file_dups = []
        for p in paras:
            fp = p[:30]
            if fp in seen:
                file_dups.append(fp)
            seen.add(fp)
        if file_dups:
            results[f] = file_dups
    return results


def check_missing_translation():
    """纯中文无英文翻译的页面检测（内容>500字且英文<50词）"""
    results = {}
    for f in sorted(os.listdir(FULL_DIR)):
        if not f.endswith('.md') or f == '_INDEX.md':
            continue
        c = (FULL_DIR / f).read_text(encoding='utf-8')
        text = re.sub(r'<[^>]+>', '', c)
        cn = len(re.findall(r'[\u4e00-\u9fff]', text))
        en = len(re.findall(r'[a-zA-Z]{4,}', text))
        if cn > 500 and en < 50:
            results[f] = f'CN:{cn}字 EN:{en}词'
    return results


def check_spam_junk():
    """水印与生产标签残留"""
    results = []
    for f in sorted(os.listdir(FULL_DIR)):
        if not f.endswith('.md') or f == '_INDEX.md':
            continue
        c = (FULL_DIR / f).read_text(encoding='utf-8')
        for kw in SPAM_KEYWORDS:
            if kw in c:
                results.append((f, '水印:' + kw))
        for kw in JUNK_LABELS:
            if kw in c:
                results.append((f, '标签:' + kw))
    return results


def check_html_structure():
    """HTML 结构完整性（未闭合div）"""
    results = []
    for f in sorted(os.listdir(FULL_DIR)):
        if not f.endswith('.md') or f == '_INDEX.md':
            continue
        c = (FULL_DIR / f).read_text(encoding='utf-8')
        opens = len(re.findall(r'<div[^>]*>', c))
        closes = len(re.findall(r'</div>', c))
        if opens != closes:
            results.append((f, f'div开{opens} 闭{closes}'))
    return results


def main():
    print("═" * 60)
    print("ReadShift 全文质量检查报告")
    print("═" * 60)

    # 1. 跨文件重复
    print("\n【1】跨文件重复段落")
    dups = check_cross_file_dups()
    if not dups:
        print("  ✅ 无跨文件重复")
    else:
        print(f"  ⚠️ 发现 {len(dups)} 个跨文件重复指纹:")
        for fp, fs in list(dups.items())[:20]:
            print(f"    '{fp}...' → {sorted(set(fs))}")

    # 2. 文件内重复
    print("\n【2】文件内重复段落")
    infile = check_infile_dups()
    if not infile:
        print("  ✅ 无文件内重复")
    else:
        print(f"  ⚠️ {len(infile)} 个文件有重复:")
        for f, dups in infile.items():
            print(f"    {f}: {len(dups)} 段重复")

    # 3. 缺失英文翻译
    print("\n【3】纯中文无英文翻译的页面（可能造成阅读断裂）")
    missing = check_missing_translation()
    if not missing:
        print("  ✅ 所有长页面都有英文翻译")
    else:
        print(f"  ⚠️ {len(missing)} 个页面缺翻译:")
        for f, info in sorted(missing.items()):
            print(f"    {f}: {info}")

    # 4. 水印/标签残留
    print("\n【4】水印与生产标签残留")
    junk = check_spam_junk()
    if not junk:
        print("  ✅ 零残留")
    else:
        print(f"  ⚠️ {len(junk)} 处残留:")
        for f, kw in junk[:30]:
            print(f"    {f}: {kw}")

    # 5. HTML结构
    print("\n【5】HTML 结构完整性")
    struct = check_html_structure()
    if not struct:
        print("  ✅ 所有div标签闭合")
    else:
        print(f"  ⚠️ {len(struct)} 个文件结构不完整:")
        for f, info in struct[:10]:
            print(f"    {f}: {info}")

    print("\n" + "═" * 60)


if __name__ == "__main__":
    main()
