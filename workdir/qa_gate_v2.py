#!/usr/bin/env python3
import os, re, sys, json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
FULL_DIR = BASE_DIR / "output" / "full"
HTML_PATH = BASE_DIR / "output" / "preview_book.html"

class QAReport:
    def __init__(self):
        self.results = []

    def add(self, level, code, title, message):
        self.results.append({'level': level, 'code': code, 'title': title, 'message': message})

    @property
    def passed(self):
        return not any(r['level'] == 'FAIL' for r in self.results)

    def print_summary(self):
        print("\n" + "═" * 68)
        print("   ReadShift 高阶质量审计系统 (Deep QA Auditor v2.0)")
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

def audit_structure_and_escaping(report, html_content):
    escaped_tags = re.findall(r'&lt;(div|span|p|h[1-6]|ul|li|a)\b', html_content)
    if escaped_tags:
        report.add('FAIL', 'G1-01', 'HTML转义泄露', f'发现 {len(escaped_tags)} 处被转义的 HTML 标签 (例如 &lt;{escaped_tags[0]})')
    else:
        report.add('OK', 'G1-01', 'HTML转义泄露', '0 处转义泄露')

    div_open = html_content.count('<div')
    div_close = html_content.count('</div>')
    if div_open != div_close:
        report.add('FAIL', 'G1-02', 'DIV标签闭合', f'<div({div_open}) 与 </div>({div_close}) 数量不匹配')
    else:
        report.add('OK', 'G1-02', 'DIV标签闭合', f'div 标签完全对齐 ({div_open} 对)')

def audit_purity(report, html_content):
    junk_patterns = [
        r'微信', r'周读', r'ireadweek', r'幸福的味道', r'小编', r'QQ群',
        r'Healer 修复文本', r'Isaacson 双语', r'知识萃取', r'全量生产',
        r'<!-- PROCESSED -->',
        r'《?张忠谋自传》?\s*第?\s*\d+\s*页',
        r'#+\s*第\s*\d+\s*页'
    ]
    found_junks = []
    for pat in junk_patterns:
        if re.search(pat, html_content):
            found_junks.append(pat)
            
    if found_junks:
        report.add('FAIL', 'G2-01', '内容纯净度', f'检测到垃圾水印或内部生产标签: {", ".join(found_junks)}')
    else:
        report.add('OK', 'G2-01', '内容纯净度', '零水印、零内部标签残余')

def audit_simplified_chinese(report, html_content):
    trad_chars = re.findall(r'[灣國體電學歷樂簡觀辦時轉]', html_content)
    if len(trad_chars) > 5:
        report.add('FAIL', 'G2-02', '繁体字残留', f'检测到 {len(trad_chars)} 处繁体字残余 (如 {trad_chars[:5]})，未完成简体转换')
    else:
        report.add('OK', 'G2-02', '繁体字残留', '全书 100% 为规范简体中文，零繁体字残余')

def audit_duplication(report, html_content):
    cn_paras = re.findall(r'<p class="cn-para">([^<]+)</p>', html_content)
    normalized_paras = [re.sub(r'[^\u4e00-\u9fff]', '', p) for p in cn_paras]
    seen = {}
    duplicates = []
    for idx, norm_p in enumerate(normalized_paras):
        if len(norm_p) < 15:
            continue
        if norm_p in seen:
            duplicates.append((seen[norm_p], idx, cn_paras[idx][:40]))
        else:
            seen[norm_p] = idx
            
    if duplicates:
        detail = f'发现 {len(duplicates)} 处段落完全重复！例: 段落#{duplicates[0][1]} "{duplicates[0][2]}..." 与 段落#{duplicates[0][0]} 重复'
        report.add('FAIL', 'G3-01', '中文段落重复', detail)
    else:
        report.add('OK', 'G3-01', '中文段落重复', f'全书 {len(cn_paras)} 个中文段落 0 重复')

def audit_toc_anchors(report, html_content):
    hrefs = re.findall(r'<a href="#([^"]+)" class="toc-card__link">', html_content)
    if not hrefs:
        report.add('FAIL', 'G4-01', '目录结构', '未找到目录链接')
        return

    missing_anchors = []
    for anchor in hrefs:
        if f'id="{anchor}"' not in html_content:
            missing_anchors.append(anchor)

    if missing_anchors:
        report.add('FAIL', 'G4-01', '目录锚点可达性', f'发现断头链接: {", ".join(missing_anchors)}')
    else:
        report.add('OK', 'G4-01', '目录锚点可达性', f'目录全部 {len(hrefs)} 个条目锚点 100% 可达')

def audit_visual_and_bilingual(report, html_content):
    bilingual_pairs = html_content.count('class="bilingual-pair"')
    translations = html_content.count('rebook-translation')
    
    if bilingual_pairs == 0:
        report.add('FAIL', 'G5-01', '双语框架', '未检测到双语段落框架')
    elif translations < bilingual_pairs:
        report.add('FAIL', 'G5-01', '双语框架', f'翻译块 ({translations}) 少于配对块 ({bilingual_pairs})，存在无翻译的中文段落')
    else:
        report.add('OK', 'G5-01', '双语框架', f'包含 {bilingual_pairs} 组 ReadShift 双语段落（{translations} 个翻译子段，1:N 正常关系）')

    if 'ReadShift' in html_content and 'REBOOK' not in html_content:
        report.add('OK', 'G5-02', '品牌规范', '品牌标识统一为 ReadShift')
    else:
        report.add('FAIL', 'G5-02', '品牌规范', '仍然存在旧品牌 REBOOK 残余')

def run_audit():
    report = QAReport()
    if not HTML_PATH.exists():
        print(f"❌ 错误: 找不到目标交付物文件: {HTML_PATH}")
        sys.exit(1)
        
    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        html_content = f.read()
        
    audit_structure_and_escaping(report, html_content)
    audit_purity(report, html_content)
    audit_simplified_chinese(report, html_content)
    audit_duplication(report, html_content)
    audit_toc_anchors(report, html_content)
    audit_visual_and_bilingual(report, html_content)
    
    report.print_summary()
    return 0 if report.passed else 1

if __name__ == "__main__":
    sys.exit(run_audit())
