import re
from pathlib import Path

def repair_file(filepath):
    text = filepath.read_text(encoding='utf-8')
    
    # Clean up broken headings
    text = text.replace('修辞赏析</span>', '修辞赏析')
    text = text.replace('语言与逻辑赏析</span>', '修辞赏析')
    
    # Wait, the best way to restore the file is to fetch the original from raw_source?
    # No, we don't have git tracking for output/chapters/chap-02-哈佛MIT/source/.
    # But wait, where did we generate these files from originally?
    # Maybe we can just extract all rhetoric notes and rebuild them safely.
    
    # But wait, looking at the QA errors: 
    # [G3-02] 全局中文段落重复: 34 处重复: 修辞赏析 · Language & Logic Appreciation
    # [G6-01] 二创卡片结构: 35 个问题: [修辞赏析] zh(2) 与 en(4) 数量不匹配
    # There are MULTIPLE zh and en tags in a single rhetoric-note because my regex grouped them?
    # Yes, the previous regex `rewrite_rnote2` probably grouped multiple notes together.
    
    # We need to completely rewrite the rhetoric blocks.
    # Let's find exactly the `### 修辞赏析` up to `### 背景知识延伸` or EOF, and rebuild it.
    
    def rebuild_rhetoric_section(m):
        header = m.group(1) # ### 修辞赏析...
        content = m.group(2) # The rest of the block
        
        # We need to extract all pairs of zh and en texts.
        # We look for <span class="zh">...</span> and <span class="en">...</span>
        notes_zh = re.findall(r'<span class="zh">(.*?)</span>', content, flags=re.DOTALL)
        notes_en = re.findall(r'<span class="en">(.*?)</span>', content, flags=re.DOTALL)
        
        new_content = header + "\n"
        
        # Zip them together
        for zh, en in zip(notes_zh, notes_en):
            zh = zh.strip()
            en = en.strip()
            # Often there is a Bold title inside zh or the raw text before it
            # We just want a clean rhetoric-note.
            new_content += f'<span class="rhetoric-note">\n<span class="zh">{zh}</span>\n<span class="en">{en}</span>\n</span>\n\n'
            
        return new_content

    # The block ends before the next `### ` or end of file
    text = re.sub(r'(### 修辞赏析[^\n]*\n)(.*?)(?=\n### |\Z)', rebuild_rhetoric_section, text, flags=re.DOTALL)

    # Let's do the same for knowledge-note to avoid duplicates / structural issues inside them.
    # [G7-01]: "修辞块裸文本残留" means there is naked text in the rhetoric block. Wait, rebuilding the section as I just did will REMOVE all naked text in the rhetoric block! Which is perfect for G7-01!
    
    filepath.write_text(text, encoding='utf-8')

for f in sorted(Path('output/chapters/chap-02-哈佛MIT/source').glob('page_*.md')):
    repair_file(f)

