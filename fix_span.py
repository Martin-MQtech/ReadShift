import re
from pathlib import Path

for f in sorted(Path('output/chapters/chap-02-哈佛MIT/source').glob('page_*.md')):
    text = f.read_text(encoding='utf-8')
    
    # 1. Fix G3-02: corrupted titles
    text = text.replace('修辞赏析</span>', '修辞赏析')
    text = text.replace('语言与逻辑赏析</span>', '修辞赏析')
    
    # 2. Fix G6-01 & G1-03: Ensure <span> are balanced inside rhetoric-note
    # Let's count spans. A rhetoric note should look like:
    # <span class="rhetoric-note">\n<span class="zh">...</span>\n<span class="en">...</span>\n</span>
    # If it's missing the final </span>, we add it.

    def fix_rnote(m):
        block = m.group(0)
        open_count = block.count('<span')
        close_count = block.count('</span')
        
        # If we have 3 opens and only 2 closes (missing the final one)
        if open_count > close_count:
            return block + '\n</span>' * (open_count - close_count)
        elif close_count > open_count: # Too many closing tags?
            # Actually just force it to properly structured
            zh = re.search(r'<span class="zh">(.*?)</span>', block, re.DOTALL)
            en = re.search(r'<span class="en">(.*?)</span>', block, re.DOTALL)
            if zh and en:
                return f'<span class="rhetoric-note">\n<span class="zh">{zh.group(1)}</span>\n<span class="en">{en.group(1)}</span>\n</span>'
        return block

    # We will just rewrite all rhetoric notes using a regex that extracts zh and en.
    def rewrite_rnote(m):
        zh_m = re.search(r'<span class="zh">(.*?)</span>', m.group(0), re.DOTALL)
        en_m = re.search(r'<span class="en">(.*?)</span>', m.group(0), re.DOTALL)
        if zh_m and en_m:
            zh_text = zh_m.group(1).strip()
            en_text = en_m.group(1).strip()
            # If the zh text contains "**Title**: ", we pull it OUTSIDE!
            # Wait, the prompt says "naked text with zh duplicate". 
            # If the zh text has it, the raw text should not exist. We already deleted raw text.
            title_m = re.match(r'^(\*\*.*?\*\*(?:：|:|))', zh_text)
            title = ""
            # Actually, standard is to put the bold title ABOVE the rhetoric note or keep it inside zh/en.
            # Let's just output the perfect structure.
            return f'<span class="rhetoric-note">\n<span class="zh">{zh_text}</span>\n<span class="en">{en_text}</span>\n</span>'
        return m.group(0)
        
    text = re.sub(r'<span class="rhetoric-note">.*?</span>\s*</span>', rewrite_rnote, text, flags=re.DOTALL)
    
    # Wait, some rhetoric notes might be missing the final </span>, so the regex above won't match!
    # Let's match starting from `<span class="rhetoric-note">` to `<span class="en">...</span>`
    def rewrite_rnote2(m):
        zh_text = m.group(1).strip()
        en_text = m.group(2).strip()
        return f'<span class="rhetoric-note">\n<span class="zh">{zh_text}</span>\n<span class="en">{en_text}</span>\n</span>'
        
    text = re.sub(r'<span class="rhetoric-note">.*?<span class="zh">(.*?)</span>.*?<span class="en">(.*?)</span>(?:\s*</span>)*', rewrite_rnote2, text, flags=re.DOTALL)
    
    # 3. Check for any remaining duplicates in knowledge-note 
    # Just in case `fix_all_notes.py` missed some
    def strip_duplicate_knowledge(m):
        raw_text = m.group(1).strip()
        note = m.group(2)
        if not raw_text: return note
        
        clean_raw = re.sub(r'<[^>]+>', '', raw_text).replace('*', '')
        if len(clean_raw) > 10 and clean_raw in re.sub(r'<[^>]+>', '', note).replace('*', ''):
            return note
        return m.group(0)
    
    text = re.sub(r'(?:\*\*.*?\*\*(?:：|:|\s*)[^\n]+)\n+(<div class="knowledge-note">)', strip_duplicate_knowledge, text, flags=re.DOTALL)

    f.write_text(text, encoding='utf-8')

