#!/usr/bin/env python3
"""
ReadShift 质量审计系统 v3.0 (Deep QA Auditor)
=====================================================================
v3 相对 v2 的四大升级（吸收 2026-08 血泪教训）:

1. 【单章交付物审计】--html 参数可指定任一 第X章.html / chapter-0X.html；
   不传参数时自动扫描所有 part-0X-*/第X章.html。不再写死 preview_book.html。

2. 【全段落重复检测】不再限定 class="cn-para"（渲染器实际输出普通 <p>）：
   - 相邻段落 100% 重复（两段连排）
   - 全局中文段落规范化去重（>15 字）
   - 相邻中英/英英段落高度重合预警

3. 【卡片内部重复检测】逐个 rebook-card 检查:
   - 卡片内裸文本段 与 <span class="zh"> 内容重复（修辞赏析历史病根）
   - zh 与 en 完全相同（无翻译）

4. 【二创结构完整性 + 源文件审计】:
   - rhetoric-note 计数法校验（每 note 恰 1 zh + 1 en + 3 闭合）
   - knowledge-note 结构校验
   - 「英文翻译。」等字面占位符检测
   - 源文件 source/*.md 孤立短行缺英文检测（真实小节标题漏网）

用法:
    python3 workdir/qa_gate_v3.py                     # 自动扫描全部单章 HTML + 全部源文件
    python3 workdir/qa_gate_v3.py --html 第一章.html  # 指定单章
    python3 workdir/qa_gate_v3.py --skip-sources      # 只查 HTML 不查源文件
退出码: 0=通过可出货 | 1=存在 FAIL 禁止出货
"""
import sys, re, argparse, json
from pathlib import Path
from html.parser import HTMLParser

BASE_DIR = Path(__file__).parent.parent


class _BlockParser(HTMLParser):
    """按 class 精确切分嵌套 HTML 块，替代脆弱的正则（根治卡片/note 边界误判）。

    用法: 给定 target_class，返回该 class 每个顶层块的完整内部文本（含嵌套标签）。
    """
    def __init__(self, target_class):
        super().__init__(convert_charrefs=True)
        self.target = target_class
        self.depth = 0          # 当前是否处于目标块内（0=块外）
        self.blocks = []        # 每个目标块的完整原文
        self._buf = []

    def handle_starttag(self, tag, attrs):
        cls = dict(attrs).get('class', '')
        if self.depth == 0:
            if tag == 'div' and self.target in cls.split():
                self.depth = 1
                self._buf = []
                return
        elif tag == 'div':
            self.depth += 1
            self._buf.append(self.get_starttag_text() or f'<{tag}>')
            return
        if self.depth > 0:
            self._buf.append(self.get_starttag_text() or f'<{tag}>')

    def handle_endtag(self, tag):
        if self.depth == 0:
            return
        if tag == 'div':
            if self.depth == 1:
                self.blocks.append(''.join(self._buf))
                self.depth = 0
                self._buf = []
                return
            self.depth -= 1
            self._buf.append(f'</{tag}>')
        else:
            self._buf.append(f'</{tag}>')

    def handle_data(self, data):
        if self.depth > 0:
            self._buf.append(data)


def extract_blocks(html, target_class, tag='div'):
    """返回所有 class==target_class 的顶层 <div> 块的完整内部原文（含嵌套）。"""
    if tag != 'div':
        return []
    p = _BlockParser(target_class)
    p.feed(html)
    return p.blocks


class QAReport:
    def __init__(self):
        self.results = []

    def add(self, level, code, title, message):
        self.results.append({'level': level, 'code': code, 'title': title, 'message': message})

    @property
    def passed(self):
        return not any(r['level'] == 'FAIL' for r in self.results)

    def print_summary(self, target_label):
        print("\n" + "═" * 68)
        print(f"   ReadShift 高阶质量审计系统 (Deep QA Auditor v3.0)")
        print(f"   审计对象: {target_label}")
        print("═" * 68)

        ok_count = sum(1 for r in self.results if r['level'] == 'OK')
        warn_count = sum(1 for r in self.results if r['level'] == 'WARN')
        fail_count = sum(1 for r in self.results if r['level'] == 'FAIL')

        for r in self.results:
            icon = "  ✅" if r['level'] == 'OK' else ("  ⚠️" if r['level'] == 'WARN' else "  ❌")
            print(f"{icon} [{r['code']}] {r['title']}: {r['message']}")

        print("─" * 68)
        print(f"统计: {ok_count} 通过 | {warn_count} 警告 | {fail_count} 失败")
        if self.passed:
            print("🎉 结论: 最终质量达标，允许出货！")
        else:
            print("🚫 结论: 存在致命缺陷，禁止出货！")
        print("═" * 68 + "\n")


def norm_text(s):
    """规范化文本：去 HTML、去标点空白，保留中文/英文/数字"""
    s = re.sub(r'<[^>]+>', '', s)
    s = re.sub(r'[\s\u3000\u00a0]+', '', s)
    s = re.sub(r'[，。！？；：“”‘’（）《》「」—…·,.;:!?"\'()\[\]{}<>~`@#$%^&*_+=|\\/\-]', '', s)
    return s.strip()


# ═══════════════ G1 结构与转义 ═══════════════
def audit_structure_and_escaping(report, html):
    escaped = re.findall(r'&lt;(div|span|p|h[1-6]|ul|li|a)\b', html)
    report.add('FAIL' if escaped else 'OK', 'G1-01', 'HTML转义泄露',
               f'发现 {len(escaped)} 处被转义标签' if escaped else '0 处转义泄露')

    div_o, div_c = html.count('<div'), html.count('</div>')
    span_o = len(re.findall(r'<span[\s>]', html))
    span_c = html.count('</span>')
    report.add('FAIL' if div_o != div_c else 'OK', 'G1-02', 'DIV标签闭合',
               f'div {div_o} vs {div_c} 不匹配' if div_o != div_c else f'div 完全对齐 ({div_o} 对)')
    report.add('FAIL' if span_o != span_c else 'OK', 'G1-03', 'SPAN标签闭合',
               f'span {span_o} vs {span_c} 不匹配' if span_o != span_c else f'span 完全对齐 ({span_o} 对)')

    # [G1-04] 模型/工具泄漏与中间态标记检测
    leakages = re.findall(r'(<longcat[^>]*>|longcat_arg_value|@@RNOTE\d+@@|__PROCESSED__)', html)
    report.add('FAIL' if leakages else 'OK', 'G1-04', '模型与工具标记泄漏',
               f'发现 {len(leakages)} 处未清理的模型/工具标记: {leakages[:2]}' if leakages else '0 处工具/模型中间态标记泄漏')


# ═══════════════ G2 纯净度 ═══════════════
def audit_purity(report, html):
    junk = [r'微信', r'周读', r'ireadweek', r'幸福的味道', r'小编', r'QQ群',
            r'Healer 修复文本', r'Isaacson 双语', r'知识萃取', r'全量生产',
            r'<!-- PROCESSED -->', r'《?张忠谋自传》?\s*第?\s*\d+\s*页',
            r'#+\s*第\s*\d+\s*页', r'英文翻译。']
    found = [p for p in junk if re.search(p, html)]
    report.add('FAIL' if found else 'OK', 'G2-01', '内容纯净度',
               f'垃圾/占位符: {", ".join(found)}' if found else '零水印、零内部标签残余')

    trad = re.findall(r'[灣國體電學歷樂簡觀辦時轉愛業實發](?![们我们])', html)
    report.add('FAIL' if len(trad) > 5 else 'OK', 'G2-02', '繁体字残留',
               f'{len(trad)} 处繁体残余' if len(trad) > 5 else '全书 100% 规范简体')


# ═══════════════ G3 重复检测（v3 核心升级） ═══════════════
def audit_duplication(report, html):
    # 1) 全段落提取（不限 class，捕获所有 <p>）
    raw_ps = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
    ps = [(re.sub(r'<[^>]+>', '', p).strip(), i) for i, p in enumerate(raw_ps)]
    ps = [(t, i) for t, i in ps if len(t) > 15]

    # 1a) 相邻段落 100% 重复
    adj_dup = []
    for k in range(len(ps) - 1):
        if ps[k][0] == ps[k + 1][0]:
            adj_dup.append(ps[k][0][:40])
    report.add('FAIL' if adj_dup else 'OK', 'G3-01', '相邻段落重复',
               f'{len(adj_dup)} 处相邻完全相同: {adj_dup[:2]}' if adj_dup else '相邻段落 0 重复')

    # 1b) 全局中文规范化重复
    seen, dup = {}, []
    for t, i in ps:
        if not re.search(r'[\u4e00-\u9fff]', t):
            continue
        nt = norm_text(t)
        if len(nt) < 15:
            continue
        if nt in seen:
            dup.append((seen[nt], i, t[:40]))
        else:
            seen[nt] = i
    report.add('FAIL' if dup else 'OK', 'G3-02', '全局中文段落重复',
               f'{len(dup)} 处重复: {dup[0][2]}...' if dup else '全局中文段落 0 重复')

    # 1c) 相邻段落高度重合（>60% 前30字重合）
    overlap = []
    for k in range(len(ps) - 1):
        a, b = norm_text(ps[k][0]), norm_text(ps[k + 1][0])
        if len(a) > 30 and len(b) > 30 and (a[:30] in b or b[:30] in a) and a != b:
            overlap.append((ps[k][0][:30], ps[k + 1][0][:30]))
    report.add('WARN' if overlap else 'OK', 'G3-03', '相邻段落高度重合预警',
               f'{len(overlap)} 处疑似重复: {overlap[:2]}' if overlap else '无异常段落重叠')

    # [G3-04] 叠字与标点错乱检测（拦截类似 奖」。奖」。、。。、，， 等拼接瑕疵）
    stutter_p = re.findall(r'([^\s\d]{2,10}[。！？\?!\.」”])\s*\1', html)
    stutter_issues = len(stutter_p)
    report.add('FAIL' if stutter_issues > 0 else 'OK', 'G3-04', '叠字错乱检测',
               f'发现 {stutter_issues} 处叠字拼接错误: {stutter_p[:2]}' if stutter_issues > 0 else '0 处叠字错乱')
    report.add('WARN' if overlap else 'OK', 'G3-03', '相邻段落高度重合预警',
               f'{len(overlap)} 处疑似重复: {overlap[:2]}' if overlap else '无高度重合段落')


# ═══════════════ G6 二创卡片结构（v3 核心升级） ═══════════════
def audit_cards(report, html):
    # 用 HTMLParser 精确切分每张 rebook-card（正确跨过 knowledge-note 的嵌套 div），
    # 替代脆弱正则 re.findall(r'<div class="rebook-card">(.*?)</div>\s*</div>')
    cards = extract_blocks(html, 'rebook-card')
    issues = []

    for ci, card in enumerate(cards):
        title_m = re.search(r'rebook-card__title">(.*?)<', card)
        ctitle = title_m.group(1) if title_m else f'卡片{ci+1}'

        # 卡片内所有 zh / en span
        zh_spans = re.findall(r'<span class="zh">(.*?)</span>', card, re.DOTALL)
        en_spans = re.findall(r'<span class="en">(.*?)</span>', card, re.DOTALL)

        # 卡片内裸文本（非 rhetoric-note / knowledge-note 且非 zh/en span 内）
        # 先移除二创注记块（rhetoric-note 结构固定为 zh+en 两个内层 span），再移除 zh/en span
        card_no_note = re.sub(r'<span class="rhetoric-note"><span class="zh">.*?</span><span class="en">.*?</span></span>',
                              '', card, flags=re.DOTALL)
        card_no_note = re.sub(r'<div class="knowledge-note">[\s\S]*?</div>\s*</div>', '',
                              card_no_note, flags=re.DOTALL)
        card_no_span = re.sub(r'<span class="zh">.*?</span>', '', card_no_note, flags=re.DOTALL)
        card_no_span = re.sub(r'<span class="en">.*?</span>', '', card_no_span, flags=re.DOTALL)
        bare_text = norm_text(card_no_span)

        # 裸文本与 zh 重复（修辞赏析历史病根）
        for z in zh_spans:
            nz = norm_text(z)
            if len(nz) > 15 and nz in bare_text:
                issues.append(f'[{ctitle}] 卡片内裸文本与 zh 重复: {z[:30]}...')
                break

        # zh == en
        if len(zh_spans) == len(en_spans):
            for z, e in zip(zh_spans, en_spans):
                nz, ne = norm_text(z), norm_text(e)
                if nz and nz == ne:
                    issues.append(f'[{ctitle}] zh 与 en 完全相同（无翻译）')
                    break

        # 卡片内 zh/en 数量失衡
        if zh_spans and len(zh_spans) != len(en_spans):
            issues.append(f'[{ctitle}] zh({len(zh_spans)}) 与 en({len(en_spans)}) 数量不匹配')

    report.add('FAIL' if issues else 'OK', 'G6-01', '二创卡片结构',
               f'{len(issues)} 个问题: {issues[0]}' if issues else f'{len(cards)} 个卡片结构完好')

    # rhetoric-note 计数法校验：精确切分每个 rhetoric-note，不能与相邻 knowledge-note 越界
    # rhetoric-note 结构固定为 <span class="rhetoric-note"><span class="zh">X</span><span class="en">Y</span></span>
    bad_notes = 0
    note_total = 0
    for card in cards:
        # 用 span 深度配对切分每个 rhetoric-note：找到起始后，数到 rhetoric-note 自己的闭合
        pos = 0
        while True:
            start = card.find('<span class="rhetoric-note">', pos)
            if start == -1:
                break
            note_total += 1
            # 从起始处扫描，配对嵌套的 span，找到 rhetoric-note 的闭合 </span>
            depth = 0
            i = start + len('<span class="rhetoric-note">')
            end = -1
            while i < len(card):
                open_m = card.find('<span', i)
                close_m = card.find('</span>', i)
                # 取更早出现的那个
                if close_m == -1 or (open_m != -1 and open_m < close_m):
                    depth += 1
                    i = open_m + len('<span')
                else:
                    if depth == 0:
                        end = close_m
                        break
                    depth -= 1
                    i = close_m + len('</span>')
            note_body = card[start:end] if end != -1 else card[start:]
            if note_body.count('<span class="zh">') != 1 or note_body.count('<span class="en">') != 1:
                bad_notes += 1
            pos = end if end != -1 else len(card)
    report.add('FAIL' if bad_notes else 'OK', 'G6-02', 'rhetoric-note 结构',
               f'{bad_notes} 个 note 结构异常' if bad_notes else f'{note_total} 个 rhetoric-note 结构完好')


# ═══════════════ G4 目录锚点与小节完整性 ═══════════════
def audit_toc(report, html):
    hrefs = re.findall(r'<a href="#([^"]+)"', html)
    hrefs = [h for h in hrefs if 'javascript' not in h]
    missing = [h for h in hrefs if f'id="{h}"' not in html]
    report.add('FAIL' if missing else 'OK', 'G4-01', '目录锚点可达性',
               f'断头链接: {missing}' if missing else f'{len(hrefs)} 个锚点 100% 可达')

    # G4-02 目录小节条目完整性（必须提取出>=1个小节节点，防止空目录/空导航栏）
    sub_m = re.search(r'var subsections = (\[.*?\]) \|\| \[\];', html, re.DOTALL)
    sub_count = 0
    if sub_m:
        try:
            subs = json.loads(sub_m.group(1))
            sub_count = len(subs)
        except Exception:
            pass
    report.add('FAIL' if sub_count == 0 else 'OK', 'G4-02', '目录小节条目完整性',
               '致命缺陷: 侧边/下拉目录为空 (subsections 为 0)' if sub_count == 0 else f'目录提取完好 ({sub_count} 个小节节点)')


# ═══════════════ G5 双语框架 ═══════════════
def audit_bilingual(report, html):
    trans = html.count('rebook-translation')
    report.add('FAIL' if trans == 0 else 'OK', 'G5-01', '双语翻译框架',
               '未检测到翻译块' if trans == 0 else f'{trans} 个 ReadShift 翻译块')
    report.add('FAIL' if ('ReadShift' not in html) else 'OK', 'G5-02', '品牌规范',
               '品牌标识缺失' if 'ReadShift' not in html else '品牌标识统一为 ReadShift')


# ═══════════════ G7 源文件审计（v3 核心升级） ═══════════════
def audit_sources(report, source_dir):
    issues = []
    total_notes, bad_notes = 0, 0
    for src in sorted(source_dir.glob("page_*.md")):
        content = src.read_text(encoding="utf-8")
        fn = src.name
        # 字面占位符
        if '英文翻译。' in content:
            issues.append(f'{fn}: 字面占位符「英文翻译。」')
        # rhetoric-note 计数法（限定修辞块内）
        m = re.search(r'### (?:修辞赏析|语言与逻辑赏析)\s*\n([\s\S]*?)(?=\n### |\n---|\Z)', content)
        if m:
            block = m.group(1)
            notes = block.split('<span class="rhetoric-note">')[1:]
            for note in notes:
                total_notes += 1
                if note.count('<span class="zh">') != 1 or note.count('<span class="en">') != 1:
                    bad_notes += 1
            # 裸文本残留
            rest = re.sub(r'<span class="rhetoric-note">.*?</span>\s*</span>', '', block, flags=re.DOTALL)
            t = re.sub(r'<[^>]+>', '', rest).strip()
            if t and len(t) > 10:
                issues.append(f'{fn}: 修辞块裸文本残留 [{t[:30]}...]')
        # 孤立短行缺英文（真实小节标题漏网）
        # 先标记 rhetoric-note span 内部的行号（跳过，避免误报）
        rn_lines = set()
        for rn_match in re.finditer(r'<span class="rhetoric-note">[\s\S]*?</span>\s*</span>', content):
            start_line = content[:rn_match.start()].count('\n')
            end_line = content[:rn_match.end()].count('\n')
            rn_lines.update(range(start_line, end_line + 1))
        lines = content.split('\n')
        for i, l in enumerate(lines):
            if i in rn_lines:
                continue
            tl = l.strip()
            if 2 <= len(tl) <= 14 and not tl.startswith(('#', '<', '-', '1.', '2.', '>', '|', '*')) \
               and re.search(r'[\u4e00-\u9fff]', tl) and not tl.endswith(('。', '！', '？', '，', '：', ';')):
                j = i + 1
                while j < len(lines) and lines[j].strip() == '':
                    j += 1
                nxt = lines[j].strip() if j < len(lines) else ''
                if nxt and not nxt.startswith('<div class="rebook-translation"') and not nxt.startswith('#'):
                    issues.append(f'{fn}: 疑似小节标题缺英文「{tl}」→ 后跟 {nxt[:20]}...')

    report.add('FAIL' if issues else 'OK', 'G7-01', '源文件审计',
               f'{len(issues)} 个问题: {issues[0]}' if issues else '源文件 0 占位符、0 裸文本、0 标题缺英文')
    report.add('FAIL' if bad_notes else 'OK', 'G7-02', '源文件 note 结构',
               f'{bad_notes}/{total_notes} 个 note 异常' if bad_notes else f'{total_notes} 个 note 结构完好')


def discover_chapter_htmls():
    """自动发现所有 part-0X-*/第X章.html 交付物"""
    found = []
    for d in sorted(BASE_DIR.glob("part-0*")):
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.html")):
            if f.stem.startswith("第") and f.stem.endswith("章"):
                found.append(f)
    return found


def run_audit(args):
    report = QAReport()
    targets = []
    if args.html:
        p = Path(args.html)
        if not p.is_absolute():
            p = BASE_DIR / p
        targets.append(p)
    else:
        targets = discover_chapter_htmls()
        if not targets:
            print("❌ 未发现任何 part-0X-*/第X章.html 交付物")
            return 1

    ok_targets, fail_targets = [], []
    for t in targets:
        if not t.exists():
            print(f"❌ 找不到文件: {t}")
            fail_targets.append(str(t))
            continue
        html = t.read_text(encoding="utf-8")
        audit_structure_and_escaping(report, html)
        audit_purity(report, html)
        audit_duplication(report, html)
        audit_cards(report, html)
        audit_toc(report, html)
        audit_bilingual(report, html)
        if report.passed:
            ok_targets.append(t.name)
        else:
            fail_targets.append(t.name)
        report.print_summary(str(t))
        # 每章后重置报告
        report = QAReport()

    if not args.skip_sources:
        report.add
        audit_sources(report, Path(args.source_dir) if args.source_dir else BASE_DIR / "output" / "full")
        report.print_summary("全部源文件 (output/full/page_*.md)")
        if report.passed and not fail_targets:
            return 0
        return 1

    return 0 if not fail_targets else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="ReadShift Deep QA Auditor v3")
    ap.add_argument("--chapter", help="单章编号（如 2）")
    ap.add_argument("--html", help="指定单章 HTML 文件（相对项目根或绝对路径）")
    ap.add_argument("--source-dir", help="指定源文件目录")
    ap.add_argument("--skip-sources", action="store_true", help="跳过源文件审计")
    args = ap.parse_args()

    if args.chapter:
        ch_num = args.chapter.zfill(2)
        ch_dirs = list((BASE_DIR / "output" / "chapters").glob(f"chap-{ch_num}-*"))
        if ch_dirs:
            ch_dir = ch_dirs[0]
            cn_nums = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九']
            num_str = cn_nums[int(args.chapter)] if args.chapter.isdigit() and int(args.chapter) < len(cn_nums) else args.chapter
            # 附录章使用权威命名（project.json 规定）
            is_appendix = '附录' in ch_dir.name
            html_name = '附录-Appendix.html' if is_appendix else f"第{num_str}章-Chapter-{args.chapter}.html"
            args.html = str(ch_dir / html_name)
            args.source_dir = str(ch_dir / "source")

    sys.exit(run_audit(args))
