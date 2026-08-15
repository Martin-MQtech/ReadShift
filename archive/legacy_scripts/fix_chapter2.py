import os, re
from pathlib import Path

src_dir = Path('output/chapters/chap-02-哈佛MIT/source')

num_fixed_titles = 0
num_fixed_rhetoric = 0
num_fixed_cards = 0

for file in sorted(src_dir.glob('page_*.md')):
    text = file.read_text(encoding='utf-8')
    
    # 1. Fix missing # for chapter title
    lines = text.split('\n')
    if lines[0].strip() == '第二章 哈佛大学与麻省理工':
        lines[0] = '# 第二章 哈佛大学与麻省理工'
        text = '\n'.join(lines)
        num_fixed_titles += 1

    # 2. Fix duplicated raw text before rhetoric-note
    # Pattern: Some text ending with \n<span class="rhetoric-note"><span class="zh">THE SAME TEXT...
    # We will use regex to find `<span class="rhetoric-note">` and see if the preceding text is duplicated.
    def clean_rhetoric(match):
        raw_before = match.group(1).strip()
        zh_text = match.group(2).strip()
        # If the raw text is almost identical to zh_text, or contains the zh_text
        if len(zh_text) > 10 and (zh_text in raw_before or raw_before in zh_text):
            # Return only the rhetoric-note
            return '\n<span class="rhetoric-note"><span class="zh">' + zh_text + '</span>' + match.group(3)
        return match.group(0)

    # First, let's just find anything like:
    # **Some Title**: Some duplicated text...
    # <span class="rhetoric-note"><span class="zh">Some duplicated text...</span><span class="en">...</span></span>
    
    # Let's write a regex that matches a paragraph (with or without bold title) followed by a rhetoric-note
    new_text = re.sub(
        r'(?:(?:^|\n)(?:\*\*.*?\*\*.*?|.*?) *?\n+)?<span class="rhetoric-note">\s*<span class="zh">(.*?)</span>(.*?</span>\s*</span>)',
        clean_rhetoric,
        text,
        flags=re.DOTALL
    )
    # Wait, the clean_rhetoric regex might be tricky if it matches blindly. Let's do it safer.
    
    # A safer approach is to find all rhetoric-notes.
    # And then look backwards for the text.
    # Actually, often it's:
    # **Title**: Raw text \n <span class="rhetoric-note"><span class="zh">Raw text...
    
    pass

