import re
from pathlib import Path

def clean_file(filepath):
    text = filepath.read_text(encoding='utf-8')
    
    # 1. Fix G7-01: missing hash for chapter title
    lines = text.split('\n')
    if len(lines) > 0 and lines[0].strip() == '第二章 哈佛大学与麻省理工':
        lines[0] = '# 第二章 哈佛大学与麻省理工'
        text = '\n'.join(lines)
    
    # Also standardize ### 修辞赏析
    text = re.sub(r'^(?!### ).*修辞赏析 · Language.*$', '### 修辞赏析 · Language & Logic Appreciation', text, flags=re.MULTILINE)
    text = re.sub(r'^(?!### ).*语言与逻辑赏析.*$', '### 修辞赏析 · Language & Logic Appreciation', text, flags=re.MULTILINE)
    
    # Also standardize ### 背景知识延伸
    text = re.sub(r'^(?!### ).*背景知识延伸.*$', '### 背景知识延伸', text, flags=re.MULTILINE)
    
    # 2. Fix duplicated raw text for rhetoric-note
    # The duplicate logic: sometimes it's `**Title**: raw_text \n <span class="rhetoric-note">...`
    # We want to keep `**Title**:\n<span class="rhetoric-note">...` and discard `raw_text`
    
    def replacer_rhetoric(m):
        title = m.group(1).strip()
        zh_text = m.group(2).strip()
        en_text = m.group(3).strip()
        
        # We ensure it's formatted without the raw_text duplicate
        return f"{title}\n<span class=\"rhetoric-note\">\n<span class=\"zh\">{zh_text}</span>\n<span class=\"en\">{en_text}</span>\n</span>"
    
    text = re.sub(
        r'(\*\*.*?\*\*(?:：|:|\s*))(.*?)(?:<br>|\s)*<span class="rhetoric-note">.*?<span class="zh">(.*?)</span>.*?<span class="en">(.*?)</span>\s*</span>',
        replacer_rhetoric,
        text,
        flags=re.DOTALL
    )

    # 3. Fix duplicated raw text for knowledge-note
    # Often formatted as `**Title**: raw_text \n <div class="knowledge-note">...`
    # However we might not want to strip the bold title inside knowledge note? Wait, in knowledge-note, the title is usually inside the zh and en!
    # Let's check if the raw text is just an exact duplicate.
    def replacer_knowledge(m):
        raw_text = m.group(1).strip()
        zh_text = m.group(2).strip()
        
        # If raw_text contains the same text, return only the knowledge-note block
        if len(zh_text) > 10 and (zh_text.replace("*", "") in raw_text.replace("*", "") or raw_text.replace("*", "") in zh_text.replace("*", "")):
            pass # it's duplicate
        return m.group(0) # Not implementing a generic text replacer yet, let's just forcefully remove any text before `<div class="knowledge-note">` if it has the same bold title!
        
    # An easier regex for knowledge-note:
    # (.*?) <div class="knowledge-note">.*?<span class="zh">(.*?)</span>
    
    # Let's just find ANY block of text right before <div class="knowledge-note"> or <span class="rhetoric-note"> 
    # that is substantially similar to the <span class="zh"> content.
    
    # A brutal but effective approach:
    # Just parse out all **Title** + raw text which is clearly duplicated.
    # Actually, in knowledge-note, the `**Title**:` is INSIDE the `.zh` span already, e.g. `<span class="zh">**埃玛·拉扎勒斯与《新巨人》**：文中提及...`
    # So if there is `**埃玛·拉扎勒斯与《新巨人》**：文中提及...` just BEFORE the `<div class="knowledge-note">`, we just delete it!
    
    blocks = text.split('\n\n')
    new_blocks = []
    i = 0
    while i < len(blocks):
        b = blocks[i]
        # if this block is just plain text and the next block is a note containing this text
        if i + 1 < len(blocks):
            next_b = blocks[i+1]
            if '<span class="rhetoric-note">' in next_b or '<div class="knowledge-note">' in next_b or '<span class="knowledge-note">' in next_b:
                # check if there's significant overlap
                from difflib import SequenceMatcher
                clean_b = re.sub(r'<[^>]+>', '', b).strip().replace('*', '')
                clean_next = re.sub(r'<[^>]+>', '', next_b).strip().replace('*', '')
                
                # Check containment
                if len(clean_b) > 15 and (clean_b in clean_next or clean_next in clean_b):
                    # It's a duplicate, we skip adding this block!
                    i += 1
                    continue
                # If they share a long substring, also skip
                match = SequenceMatcher(None, clean_b, clean_next).find_longest_match(0, len(clean_b), 0, len(clean_next))
                if match.size > 20:
                    # skip
                    i += 1
                    continue
        
        # Check if the duplicate is inside the same block!
        # Sometimes it's `**Title**: raw \n <div...`
        if ('<span class="rhetoric-note">' in b or '<div class="knowledge-note">' in b):
            # Try to see if the first half is just raw text of the second half
            # Split by the tag
            parts = re.split(r'(<span class="rhetoric-note">|<div class="knowledge-note">)', b, maxsplit=1)
            if len(parts) == 3:
                raw_part = parts[0].strip()
                tag_part = parts[1] + parts[2]
                
                clean_raw = re.sub(r'<[^>]+>', '', raw_part).strip().replace('*', '')
                clean_tag = re.sub(r'<[^>]+>', '', tag_part).strip().replace('*', '')
                
                # Keep **Title**: if it's rhetoric note and it's not inside the ZH!
                # Wait, if raw_part has **Title** but tag_part does NOT, we should keep Title.
                if len(clean_raw) > 15 and clean_raw in clean_tag:
                    b = tag_part
                elif len(clean_raw) > 15:
                    match = SequenceMatcher(None, clean_raw, clean_tag).find_longest_match(0, len(clean_raw), 0, len(clean_tag))
                    if match.size > 20:
                        # Extract just the title if any
                        m_title = re.match(r'^(\*\*.*?\*\*(?:：|:|\s*))', raw_part)
                        if m_title and m_title.group(1).replace('*', '') not in tag_part.replace('*', ''):
                            b = m_title.group(1) + '\n' + tag_part
                        else:
                            b = tag_part
        
        new_blocks.append(b)
        i += 1
        
    text = '\n\n'.join(new_blocks)
    
    # 4. G6-02 requires rhetoric-note to be structured perfectly.
    # It must have exactly one `.zh` and one `.en`.
    # Let's ensure `<span class="rhetoric-note">` is closed properly.
    # If the file has `<span class="rhetoric-note">` but no `</span>` it will fail.
    
    filepath.write_text(text, encoding='utf-8')

for f in sorted(Path('output/chapters/chap-02-哈佛MIT/source').glob('page_*.md')):
    clean_file(f)

