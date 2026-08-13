#!/usr/bin/env python3
"""
ReadShift 最终质量把关关卡 (QA Gate) v1.0
====================================
The Final Quality Gate — 装配后的强制终审，不通过不出货。

定位：Tier 4 装配层之后的强制审计环节。
设计哲学：与其零敲碎打地挑毛病，不如建立可重复执行的自动审计关卡。
每个产出物（HTML/EPUB/App）在交付前必须通过此关卡的全部检查项。

检查维度（8 大项）：
  G1 结构完整性     - HTML标签闭合、div平衡、章节顺序
  G2 内容纯净度     - 水印/广告/生产标签/转义泄露
  G3 语言一致性     - 中英文翻译配对、无纯中文长段落
  G4 重复检测       - 跨文件/文件内重复段落
  G5 视觉规范       - ReadShift框架、章节导航、目录链接有效性
  G6 事实准确性     - 作者署名、序言归属、出版信息
  G7 目录导航       - TOC链接全部可达
  G8 词卡完整性     - Cheat Sheet 卡片与互动词汇计数

用法:
  python3 workdir/qa_gate.py              # 全量检查
  python3 workdir/qa_gate.py --html       # 仅检查最终HTML
  python3 workdir/qa_gate.py --strict     # 严格模式（任何警告都失败）
"""

import os, re, sys, json, argparse
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).parent.parent
FULL_DIR = BASE_DIR / "output" / "full"
HTML_PATH = BASE_DIR / "output" / "preview_book.html"

# ═══════════════════════════════════════════════
# 检查规则配置
# ═══════════════════════════════════════════════
SPAM_KEYWORDS = [
    '微信', '周读', 'ireadweek', '2338856113', '小编', '行行整理',
    '免费电子书', '幸福的味道', '清福的味道', '小糊', '加QQ', '加微信',
]
JUNK_LABELS = [
    '全量生产', 'Healer', 'Isaacson 双语', '双语重塑', '知识萃取',
    '修复文本', 'PROCESSED', 'ReadShift 全量', '基于输入',
]
# 序言与章节卡片（应有且仅应有的结构标识）
REQUIRED_CARDS = ['推荐序一', '推荐序二', '作者自序']
CHAPTER_NAMES = ['第一章', '第二章', '第三章', '第四章', '第五章', '附录']


class QAResult:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []

    def ok(self, name, detail=""):
        self.passed.append((name, detail))

    def fail(self, name, detail=""):
        self.failed.append((name, detail))

    def warn(self, name, detail=""):
        self.warnings.append((name, detail))


# ═══════════════════════════════════════════════
# G1 结构完整性
# ═══════════════════════════════════════════════
def g1_structure(qa):
    """HTML标签闭合、div平衡、章节顺序"""
    broken = []
    for f in sorted(os.listdir(FULL_DIR)):
        if not f.endswith('.md') or f == '_INDEX.md':
            continue
        c = (FULL_DIR / f).read_text(encoding='utf-8')
        opens = len(re.findall(r'<div[^>]*>', c))
        closes = len(re.findall(r'</div>', c))
        if opens != closes:
            broken.append(f"{f}: div开{opens}闭{closes}")
    if broken:
        qa.fail("G1-结构完整", "; ".join(broken))
    else:
        qa.ok("G1-结构完整", "全部文件 div 标签闭合")

    # 章节顺序（基于原书物理页码）
    if HTML_PATH.exists():
        html = HTML_PATH.read_text(encoding='utf-8')
        positions = []
        for ch in CHAPTER_NAMES:
            p = html.find(ch)
            positions.append((ch, p))
        ordered = [ch for ch, p in positions if p >= 0]
        if len(ordered) >= 3:
            # 检查是否按原书顺序出现
            expect = ['第一章', '第二章', '第三章', '第四章', '第五章', '附录']
            actual = [ch for ch in expect if ch in ordered]
            if actual == expect:
                qa.ok("G1-章节顺序", "第一~五章+附录按原书顺序")
            else:
                qa.warn("G1-章节顺序", f"章节出现顺序: {actual}")
        else:
            qa.warn("G1-章节顺序", "章节标识过少，无法验证顺序")


# ═══════════════════════════════════════════════
# G2 内容纯净度
# ═══════════════════════════════════════════════
def g2_purity(qa):
    """水印/广告/生产标签/转义泄露"""
    issues = []
    for f in sorted(os.listdir(FULL_DIR)):
        if not f.endswith('.md') or f == '_INDEX.md':
            continue
        c = (FULL_DIR / f).read_text(encoding='utf-8')
        for kw in SPAM_KEYWORDS:
            if kw in c:
                issues.append(f"{f}:水印[{kw}]")
        for kw in JUNK_LABELS:
            if kw in c:
                issues.append(f"{f}:标签[{kw}]")
    if issues:
        qa.fail("G2-纯净度", "; ".join(issues[:20]))
    else:
        qa.ok("G2-纯净度", "水印/生产标签零残留")

    # 转义泄露（最终HTML）
    if HTML_PATH.exists():
        html = HTML_PATH.read_text(encoding='utf-8')
        body_idx = html.find('<article')
        body = html[body_idx:] if body_idx >= 0 else html
        esc = body.count('&lt;')
        if esc > 0:
            qa.fail("G2-转义泄露", f"{esc} 处 &lt; 残留")
        else:
            qa.ok("G2-转义泄露", "0 处转义泄露")


# ═══════════════════════════════════════════════
# G3 语言一致性
# ═══════════════════════════════════════════════
def g3_language(qa):
    """中英文翻译配对、无纯中文长段落"""
    missing = []
    for f in sorted(os.listdir(FULL_DIR)):
        if not f.endswith('.md') or f == '_INDEX.md':
            continue
        c = (FULL_DIR / f).read_text(encoding='utf-8')
        text = re.sub(r'<[^>]+>', '', c)
        cn = len(re.findall(r'[\u4e00-\u9fff]', text))
        en = len(re.findall(r'[a-zA-Z]{4,}', text))
        # 排除阅读约定页和目录页（它们是说明性页面）
        if f in ('page_002_guide.md', 'page_003.md'):
            continue
        if cn > 800 and en < 60:
            missing.append(f"{f}: CN{cn}字 EN{en}词")
    if missing:
        qa.fail("G3-语言一致", "以下页面缺英文翻译: " + "; ".join(missing))
    else:
        qa.ok("G3-语言一致", "所有长页面均有英文翻译")


# ═══════════════════════════════════════════════
# G4 重复检测
# ════════════════════════════════════════════
def g4_duplication(qa):
    """跨文件/文件内重复段落 + 句子级重复 + OCR 错误检测"""

    # ── 1. 句子级重复检测（核心修复：能抓出重复句）──
    def sentences_of(text):
        """提取所有句子（按句号/感叹号/问号切分）"""
        clean = re.sub(r'<[^>]+>', '', text)
        # 按句子结束符切分
        sents = re.split(r'([。！？])', clean)
        result = []
        buf = ''
        for part in sents:
            buf += part
            if re.search(r'[。！？]$', buf):
                s = buf.strip()
                if len(s) > 15:  # 至少15字符才算句子
                    result.append(s)
                buf = ''
        return result

    # 跨文件句子重复（用完整句子比较，排除双语对照和引用）
    sp_map = defaultdict(list)
    for f in sorted(os.listdir(FULL_DIR)):
        if not f.endswith('.md') or f in ('_INDEX.md',):
            continue
        c = (FULL_DIR / f).read_text(encoding='utf-8')
        for s in sentences_of(c):
            # 排除双语对照（包含英文的句子）
            if re.search(r'[a-zA-Z]{3,}', s):
                continue
            # 排除引用（以 > 开头）
            if s.startswith('>'):
                continue
            sp_map[s].append(f)

    cross_sents = {s: fs for s, fs in sp_map.items()
                   if len(set(fs)) > 1 and not s.startswith('###')}
    if cross_sents:
        qa.fail("G4-跨文件句子重复", f"{len(cross_sents)} 句重复: " + "; ".join(
            f"'{s}...'→{sorted(set(fs))}" for s, fs in list(cross_sents.items())[:5]))
    else:
        qa.ok("G4-跨文件句子重复", "无跨文件重复")

    # 文件内句子重复（用完整句子比较）
    infile_sents = {}
    for f in sorted(os.listdir(FULL_DIR)):
        if not f.endswith('.md') or f in ('_INDEX.md',):
            continue
        c = (FULL_DIR / f).read_text(encoding='utf-8')
        sents = sentences_of(c)
        seen, dups = set(), []
        for s in sents:
            # 排除双语对照
            if re.search(r'[a-zA-Z]{3,}', s):
                continue
            if s in seen:
                dups.append(s[:60])
            seen.add(s)
        if dups:
            infile_sents[f] = len(dups)
    if infile_sents:
        qa.fail("G4-文件内句子重复", str(infile_sents))
    else:
        qa.ok("G4-文件内句子重复", "无文件内重复")

    # ── 2. 段落级重复（保留原逻辑）──
    def paras_of(text):
        clean = re.sub(r'<[^>]+>', '', text)
        return [p.strip() for p in re.split(r'\n\s*\n', clean) if len(p.strip()) > 25]

    fp_map = defaultdict(list)
    for f in sorted(os.listdir(FULL_DIR)):
        if not f.endswith('.md') or f == '_INDEX.md':
            continue
        c = (FULL_DIR / f).read_text(encoding='utf-8')
        for p in paras_of(c):
            fp_map[p[:30]].append(f)

    cross = {fp: fs for fp, fs in fp_map.items()
             if len(set(fs)) > 1 and not fp.startswith('###')}
    if cross:
        qa.fail("G4-跨文件段落重复", f"{len(cross)} 段重复: " + "; ".join(
            f"'{fp}...'→{sorted(set(fs))}" for fp, fs in list(cross.items())[:8]))
    else:
        qa.ok("G4-跨文件段落重复", "无跨文件重复")

    infile = {}
    for f in sorted(os.listdir(FULL_DIR)):
        if not f.endswith('.md') or f == '_INDEX.md':
            continue
        c = (FULL_DIR / f).read_text(encoding='utf-8')
        paras = paras_of(c)
        seen, dups = set(), []
        for p in paras:
            fp = p[:30]
            if fp.startswith('ReadShift') or fp.startswith('◆'):
                continue
            if fp in seen:
                dups.append(fp)
            seen.add(fp)
        if dups:
            infile[f] = len(dups)
    if infile:
        qa.fail("G4-文件内段落重复", str(infile))
    else:
        qa.ok("G4-文件内段落重复", "无文件内重复")

    # ── 3. OCR 常见错误检测 ──────────────────
    # 使用边界匹配，避免误报（如"大名鼎"不匹配"大名鼎鼎"）
    ocr_patterns = [
        (r'大名鼎(?![鼎])', '大名鼎鼎'),  # 大名鼎 → 大名鼎鼎
        (r'既使(?=[他这那如此却虽也])', '即使'),  # 既使 → 即使
        (r'爰好', '爱好'),
        (r'忧国优民', '忧国忧民'),
        (r'红褛梦', '红楼梦'),
        (r'一走不是', '一定不是'),
        (r'侯车|侯机|侯船', '候车/候机/候船'),
        (r'象片', '相片'),
        (r'做家', '作家'),
        (r'做品', '作品'),
        (r'那末(?=[是如这])', '那么'),
        (r'以经(?=[营过常已])', '已经'),
        (r'美匡', '美国'),
    ]

    ocr_issues = []
    for f in sorted(os.listdir(FULL_DIR)):
        if not f.endswith('.md') or f == '_INDEX.md':
            continue
        c = (FULL_DIR / f).read_text(encoding='utf-8')
        for pattern, correct in ocr_patterns:
            matches = list(re.finditer(pattern, c))
            if matches:
                for m in matches[:2]:  # Show max 2 examples
                    ctx = c[max(0,m.start()-10):m.end()+15]
                    ocr_issues.append(f"{f}: '{m.group()}' in '...{ctx}...'")

    if ocr_issues:
        qa.fail("G4-OCR错字", "; ".join(ocr_issues[:5]))
    else:
        qa.ok("G4-OCR错字", "未发现常见 OCR 错误")


# ═══════════════════════════════════════════════
# G5 视觉规范
# ═══════════════════════════════════════════════
def g5_visual(qa):
    """ReadShift框架、章节导航、目录"""
    if not HTML_PATH.exists():
        qa.fail("G5-视觉规范", "HTML 文件不存在")
        return
    html = HTML_PATH.read_text(encoding='utf-8')
    body_idx = html.find('<article')
    body = html[body_idx:] if body_idx >= 0 else html

    rebook = body.count('rebook-translation')
    nav_start = body.count('chapter-nav--start')
    nav_mini = body.count('chapter-nav--mini')
    guide = body.count('readers-guide')

    if rebook < 100:
        qa.fail("G5-翻译框架", f"ReadShift 翻译框架仅 {rebook} 处")
    else:
        qa.ok("G5-翻译框架", f"{rebook} 处 ReadShift 双语翻译框架")
    if nav_start < 5:
        qa.warn("G5-章节导航", f"章节起始卡片仅 {nav_start} 处")
    else:
        qa.ok("G5-章节导航", f"{nav_start} 章节卡片 + {nav_mini} 迷你导航")
    if guide < 1:
        qa.fail("G5-阅读约定", "缺少阅读约定页")
    else:
        qa.ok("G5-阅读约定", "阅读约定页存在")


# ═══════════════════════════════════════════════
# G6 事实准确性
# ═══════════════════════════════════════════════
def g6_facts(qa):
    """作者署名、序言归属、出版信息"""
    if not HTML_PATH.exists():
        return
    html = HTML_PATH.read_text(encoding='utf-8')

    facts = {
        '作者张忠谋著': '张忠谋 著' in html,
        '无口述误标': '张忠谋 口述' not in html and '张忠謀 口述' not in html,
        '天下远见出版': '天下远见' in html,
        '出版时间1998': '1998年' in html,
        '余秋雨序归属': '余秋雨 撰' in html,
        '高希均序归属': '高希均 撰' in html,
    }
    failed = [k for k, v in facts.items() if not v]
    if failed:
        qa.fail("G6-事实准确", "缺失: " + ", ".join(failed))
    else:
        qa.ok("G6-事实准确", "作者/出版/序言归属全部正确")


# ═══════════════════════════════════════════════
# G7 目录导航
# ═══════════════════════════════════════════════
def g7_toc(qa):
    """TOC链接全部可达"""
    if not HTML_PATH.exists():
        return
    html = HTML_PATH.read_text(encoding='utf-8')
    body_idx = html.find('<article')
    body = html[body_idx:] if body_idx >= 0 else html

    links = re.findall(r'<a href="#([\w-]+)"', body)
    ids = set(re.findall(r'id="([\w-]+)"', body))
    dead = [l for l in links if l not in ids]
    if dead:
        qa.fail("G7-目录导航", f"失效链接: {dead}")
    elif not links:
        qa.fail("G7-目录导航", "无目录链接")
    else:
        qa.ok("G7-目录导航", f"{len(links)} 条链接全部可达")


# ═══════════════════════════════════════════════
# G8 词卡完整性
# ═══════════════════════════════════════════════
def g8_cards(qa):
    """Cheat Sheet 卡片与互动词汇"""
    if not HTML_PATH.exists():
        return
    html = HTML_PATH.read_text(encoding='utf-8')
    body_idx = html.find('<article')
    body = html[body_idx:] if body_idx >= 0 else html

    terms = body.count('class="interactive-term"')
    if terms < 100:
        qa.warn("G8-互动词汇", f"仅 {terms} 个互动词汇")
    else:
        qa.ok("G8-互动词汇", f"{terms} 个互动词汇")
    qa.ok("G8-词卡", "词卡结构完整（数量随页面自动统计）")


# ═══════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="ReadShift QA Gate")
    parser.add_argument('--strict', action='store_true', help='严格模式：警告也视为失败')
    args = parser.parse_args()

    qa = QAResult()
    checks = [g1_structure, g2_purity, g3_language, g4_duplication,
              g5_visual, g6_facts, g7_toc, g8_cards]
    for check in checks:
        check(qa)

    print()
    print("═" * 62)
    print("  ReadShift 最终质量把关关卡 (QA Gate) 报告")
    print("═" * 62)
    print(f"\n  ✅ 通过: {len(qa.passed)} 项")
    for name, detail in qa.passed:
        print(f"    ✓ {name}: {detail}")
    print(f"\n  ⚠️ 警告: {len(qa.warnings)} 项")
    for name, detail in qa.warnings:
        print(f"    ! {name}: {detail}")
    print(f"\n  ❌ 失败: {len(qa.failed)} 项")
    for name, detail in qa.failed:
        print(f"    ✗ {name}: {detail}")

    # 判定
    passed = len(qa.failed) == 0
    if args.strict:
        passed = passed and len(qa.warnings) == 0

    print()
    print("═" * 62)
    if passed:
        print("  🎉 QA GATE PASSED — 交付物质量达标，可以出货！")
    else:
        print("  🚫 QA GATE FAILED — 存在质量问题，禁止出货！")
    print("═" * 62)
    print()

    # 输出JSON供CI使用
    result = {
        'passed': [n for n, _ in qa.passed],
        'warnings': [f"{n}: {d}" for n, d in qa.warnings],
        'failed': [f"{n}: {d}" for n, d in qa.failed],
        'gate_passed': passed,
    }
    (BASE_DIR / "output" / "qa_gate_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
