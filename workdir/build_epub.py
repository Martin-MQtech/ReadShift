#!/usr/bin/env python3
"""
ReBook EPUB 3 导出器
====================
将 output/full/ 的 Markdown 资产编译为标准 EPUB 3 电子书。
兼容: Apple Books (iOS/Mac) / Google Play 图书 (Android) / 其他开源阅读器

用法:
  python3 workdir/build_epub.py
"""

import os
import re
import html
from pathlib import Path

from ebooklib import epub

BASE_DIR = Path(__file__).parent.parent
FULL_DIR = BASE_DIR / "output" / "full"
OUTPUT_PATH = BASE_DIR / "output" / "张忠谋自传_上册.epub"

# 章节结构（基于原书物理页码）
CHAPTERS = [
    (1,  "目录与阅读约定", "frontmatter"),
    (7,  "推荐序一：为历史留下记录（余秋雨 撰）", "frontmatter"),
    (12, "推荐序二：出版企业家传记与回忆录的用心（高希均 撰）", "frontmatter"),
    (14, "作者自序：那是一个多么不同的时代！", "frontmatter"),
    (21, "第一章：“大时代”中的幼少年", "chapter"),
    (46, "第二章：哈佛大学与麻省理工", "chapter"),
    (64, "第三章：进入半导体业", "chapter"),
    (78, "第四章：初试啼声", "chapter"),
    (93, "第五章：重拎书包", "chapter"),
    (101, "附录与张忠谋大事年表", "backmatter"),
]


def md_to_html(md_text):
    """极简 Markdown → HTML 转换（EPUB 用）"""
    lines = md_text.split('\n')
    out = []
    in_list = False
    in_table = False

    for line in lines:
        line = line.rstrip()
        # HTML 直通
        if line.strip().startswith('<'):
            # 剥离不适合 EPUB 的类，保留基本结构
            cleaned = re.sub(r'\s+class="[^"]*"', '', line)
            cleaned = re.sub(r'\s+id="[^"]*"', '', cleaned)
            out.append(cleaned)
            continue
        # 标题
        m = re.match(r'^(#{1,4})\s+(.*)', line)
        if m:
            level = len(m.group(1))
            out.append(f'<h{level}>{html.escape(m.group(2))}</h{level}>')
            continue
        # 分隔线
        if line.strip() in ('---', '***'):
            out.append('<hr/>')
            continue
        # 表格行
        if line.strip().startswith('|'):
            if not in_table:
                out.append('<table>')
                in_table = True
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            tag = 'th' if not out[-1].startswith('<tr') and len(out) > 1 and '<tr' not in out[-2:] and all('**' in c for c in cells) else 'td'
            out.append('<tr>' + ''.join(f'<{tag}>{md_inline(c)}</{tag}>' for c in cells) + '</tr>')
            continue
        if in_table and not line.strip():
            out.append('</table>')
            in_table = False
            continue
        # 列表
        m = re.match(r'^(\d+)\.\s+(.*)', line)
        if m:
            if not in_list:
                out.append('<ol>')
                in_list = True
            out.append(f'<li>{md_inline(m.group(2))}</li>')
            continue
        m = re.match(r'^[-*]\s+(.*)', line)
        if m:
            if not in_list:
                out.append('<ul>')
                in_list = True
            out.append(f'<li>{md_inline(m.group(1))}</li>')
            continue
        if in_list and not line.strip():
            out.append('</ol>')
            in_list = False
            continue
        # 空行
        if not line.strip():
            continue
        # 普通段落
        out.append(f'<p>{md_inline(line)}</p>')

    if in_list:
        out.append('</ol>')
    if in_table:
        out.append('</table>')
    return '\n'.join(out)


def md_inline(text):
    """行内 Markdown → HTML"""
    text = html.escape(text, quote=False)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    return text


def main():
    # 收集所有页面文件
    files = sorted([f for f in os.listdir(FULL_DIR)
                    if f.startswith('page_') and f.endswith('.md')],
                   key=lambda f: int(re.search(r'\d+', f).group()))

    # 按章节分组
    book = epub.EpubBook()
    book.set_identifier('readshift-zhangzhongmou-vol1')
    book.set_title('张忠谋自传（上册 1931-1964）')
    book.set_language('zh-CN')
    book.add_author('张忠谋')
    book.add_metadata('DC', 'description',
                      'ReadShift 双语典藏版：保留原书中文，配 Isaacson 风格英文翻译与商业词汇卡片')

    # 添加样式
    css = '''
body { font-family: serif; line-height: 1.9; color: #1c1917; }
p { text-indent: 2em; margin-bottom: 1em; }
h1, h2, h3 { color: #9a3412; font-weight: bold; }
h1 { font-size: 1.8em; text-align: center; }
.en-para { font-style: italic; color: #44403c; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; }
td, th { border: 1px solid #e7e0d3; padding: 0.5em; }
.cheat-card { border: 1px solid #e7e0d3; border-radius: 8px; padding: 1em; margin: 0.8em 0; }
'''
    style = epub.EpubItem(uid='style', file_name='style.css',
                          media_type='text/css', content=css)
    book.add_item(style)

    # 章节
    chapter_files = []
    current_chapter = None
    chapter_items = []
    toc_entries = []

    # 找章节起始页
    chapter_starts = {start: (name, type) for start, name, type in CHAPTERS}

    # 构建：先按页码排序所有文件
    all_items = []
    for f in files:
        page_num = int(re.search(r'(\d+)', f).group())
        content = (FULL_DIR / f).read_text(encoding='utf-8')

        # 清理生产杂质
        content = re.sub(r'<!-- PROCESSED -->', '', content)
        content = re.sub(r'^\s*#\s*《张忠谋自传》第\d+页\s*$', '', content, flags=re.MULTILINE)

        html_content = md_to_html(content)
        all_items.append((page_num, f, html_content))

    # 按原书章节边界分组
    all_items.sort(key=lambda x: x[0])
    boundaries = sorted([s for s, _, _ in CHAPTERS])

    grouped = {}
    for page_num, f, html_content in all_items:
        # 找到所属章节
        ch_idx = 0
        for i, b in enumerate(boundaries):
            if page_num >= b:
                ch_idx = i
        ch_name = CHAPTERS[ch_idx][1]
        grouped.setdefault(ch_name, []).append((page_num, html_content))

    # 生成 EPUB 章节
    for ch_name, pages in grouped.items():
        cid = f'chapter-{len(chapter_items)+1}'
        body = '\n'.join(f'<h3>（原书第{pg}页）</h3>\n{content}' for pg, content in pages)
        chapter = epub.EpubHtml(
            title=ch_name,
            file_name=f'{cid}.xhtml',
            lang='zh-CN'
        )
        chapter_content = f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>{ch_name}</title>
<link rel="stylesheet" type="text/css" href="style.css"/>
</head>
<body>
<h1>{ch_name}</h1>
{body}
</body>
</html>'''
        chapter.set_content(chapter_content.encode('utf-8'))
        book.add_item(chapter)
        chapter_items.append(chapter)
        toc_entries.append(epub.Link(cid, ch_name, cid))

    # 目录
    book.toc = toc_entries
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # 书脊
    book.spine = ['nav'] + chapter_items

    epub.write_epub(str(OUTPUT_PATH), book)
    print(f"✅ EPUB 3 已导出: {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size/1024:.0f} KB)")
    print(f"   章节数: {len(chapter_items)}")


if __name__ == "__main__":
    main()
