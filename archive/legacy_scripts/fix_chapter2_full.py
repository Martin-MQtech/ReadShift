import re
from pathlib import Path

src_dir = Path('output/chapters/chap-02-哈佛MIT/source')

num_fixed_titles = 0
num_fixed_rhetoric = 0

for file in sorted(src_dir.glob('page_*.md')):
    text = file.read_text(encoding='utf-8')
    
    # 1. Fix missing # for chapter title
    lines = text.split('\n')
    if lines[0].strip() == '第二章 哈佛大学与麻省理工':
        lines[0] = '# 第二章 哈佛大学与麻省理工'
        text = '\n'.join(lines)
        num_fixed_titles += 1

    # 2. Fix duplicated raw text before rhetoric-note
    # Example to fix:
    # **Some Title**：Some raw text
    # <span class="rhetoric-note"><span class="zh">Some raw text</span><span class="en">En text</span></span>
    # We want it to become:
    # <span class="rhetoric-note"><span class="zh">**Some Title**：Some raw text</span><span class="en">**Some Title**: En text</span></span>
    # OR simply keep the bold title outside and only keep rhetoric note without duplicate?
    # Actually, in QA it expects rhetoric-note to NOT duplicate with bare text in the card.
    
    # We can just delete the "Some raw text" and keep "**Some Title**：\n<span class="rhetoric-note">..."
    # Let's find all pairs of (raw paragraph, rhetoric block)
    
    parts = text.split('### ')
    new_parts = [parts[0]]
    for p in parts[1:]:
        if p.startswith('修辞赏析') or p.startswith('语言与逻辑赏析'):
            # This is a rhetoric block
            # We must remove raw text duplication
            # It usually contains items like:  **Title**: Content  \n <span class="rhetoric-note"><span class="zh">Content</span>
            
            # Use regex to find `**Title**： Content <span class="rhetoric-note"><span class="zh">Content`
            def replacer(m):
                title = m.group(1) # **Title**：
                raw_content = m.group(2).strip()
                zh_content = m.group(3)
                en_content = m.group(4)
                # Just return the title and the rhetoric note, dropping raw_content
                return f"{title}\n<span class=\"rhetoric-note\">\n<span class=\"zh\">{zh_content}</span>\n<span class=\"en\">{en_content}</span>\n</span>"
            
            # The regex:
            # group 1: (\*\*.*?\*\*(?:：|:))    (the bold title)
            # group 2: (.*?)(?=<span class="rhetoric-note">) (the duplicated raw content)
            # group 3: <span class="zh">(.*?)</span>
            # group 4: <span class="en">(.*?)</span>
            p_new = re.sub(
                r'(\*\*.*?\*\*(?:：|:|\s*))(.*?)(?:<br>|\s)*<span class="rhetoric-note">.*?<span class="zh">(.*?)</span>\s*<span class="en">(.*?)</span>\s*</span>',
                replacer,
                p,
                flags=re.DOTALL
            )
            
            # Also fix [背景知识延伸] cards duplicating raw text
            p_new = re.sub(
                r'<(?:div|span) class="knowledge-note".*?</(?:div|span)>',  # if knowledge note is already there
                lambda m: m.group(),
                p_new,
                flags=re.DOTALL
            )
            new_parts.append(p_new)
        elif p.startswith('背景知识延伸') or p.startswith('知识卡片'):
            # Also fix knowledge cards if they have naked text + <span class="zh">
            pass
            new_parts.append(p)
        else:
            new_parts.append(p)
    text = '### '.join(new_parts)

    
    # Another approach: find ANY <span class="rhetoric-note"> and strip its immediately preceding text if it starts with **Title**
    # Since the previous code might miss some, let's also do a general cleanup:
    def general_clean(m):
        raw_text = m.group(1).strip()
        rhetoric_tag = m.group(2)
        zh_text = m.group(3).strip()
        # If raw_text is almost same as zh_text, remove raw_text
        if len(zh_text) > 10 and (zh_text in raw_text or raw_text in zh_text):
            return r"\n" + rhetoric_tag
        return m.group(0)
    
    # Wait, the easiest way to fix G3-02 and G6-01 is to remove ALL Chinese raw text in the card if `class="zh"` exists.
    # We will refine `text` directly.
    # Let's fix global "修辞赏析 · Language & Logic Appreciation" duplicated. It's because in some files it's `### 修辞赏析 · Language & Logic Appreciation`, but in others it's just `修辞赏析 · Language & Logic Appreciation` which becomes `<p>`.
    text = re.sub(r'^(?!### ).*修辞赏析 · Language.*$', '### 修辞赏析 · Language & Logic Appreciation', text, flags=re.MULTILINE)

    file.write_text(text, encoding='utf-8')

print("Done")
