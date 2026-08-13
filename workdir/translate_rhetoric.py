#!/usr/bin/env python3
"""修辞赏析 → 中英双语 rhetoric-note 转换脚本
用法: python3 workdir/translate_rhetoric.py <file1.md> <file2.md> ...
"""
import json, os, time, re, sys
from pathlib import Path

cfg = json.load(open(os.path.expanduser('~/.zcode/v2/config.json')))
z = cfg['provider']['zenmux']

from openai import OpenAI
client = OpenAI(api_key=z['options']['apiKey'], base_url=z['options']['baseURL'], timeout=300, max_retries=2)

def call(prompt, temp=0.3):
    for attempt in range(5):
        try:
            resp = client.chat.completions.create(
                model="deepseek/deepseek-v4-flash",
                messages=[{"role": "user", "content": prompt}],
                temperature=temp,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"    ⚠️ 重试{attempt+1}: {str(e)[:70]}", flush=True)
            time.sleep(8 * (attempt + 1))
    return None

def convert_block(block):
    """把修辞赏析块转换为中英双语 rhetoric-note 格式"""
    prompt = f"""你是顶级图书编辑。将以下【修辞赏析】内容转换为中英双语注脚格式。

要求：
1. 保留每条赏析的中文标题和中文内容
2. 为每条赏析补充地道优雅的英文翻译（艾萨克森传记风格）
3. 每条赏析输出为以下格式（注意：原文的 "- " 列表符号去掉，改为独立段落）：

**中文标题（English Title）**：中文内容。
<span class="rhetoric-note"><span class="zh">英文翻译。</span><span class="en">English translation.</span></span>

待转换内容：
{block}"""
    return call(prompt)

def process_file(fpath):
    p = Path(fpath)
    content = p.read_text(encoding="utf-8")
    if 'rhetoric-note' in content:
        print(f"⏭️ 跳过 {p.name} (已有 rhetoric-note)", flush=True)
        return
    
    m = re.search(r'(### (?:修辞赏析|语言与逻辑赏析)\s*\n)([\s\S]*?)(?=\n###|\n---|\n<div id=|\n<div class="rebook-translation"|\Z)', content)
    if not m:
        print(f"❌ {p.name}: 解析失败", flush=True)
        return
    
    header, block = m.group(1), m.group(2).strip()
    print(f"🔄 {p.name}: 翻译中...", flush=True)
    result = convert_block(block)
    if result:
        # 清理可能的代码块围栏
        result = re.sub(r'^```\w*\s*', '', result).strip()
        result = re.sub(r'```$', '', result).strip()
        new_content = content[:m.start(2)] + result + "\n\n" + content[m.end(2):]
        p.write_text(new_content, encoding="utf-8")
        print(f"✅ {p.name}: 完成", flush=True)
    else:
        print(f"❌ {p.name}: 翻译失败", flush=True)

if __name__ == '__main__':
    files = sys.argv[1:]
    print(f"处理 {len(files)} 个文件", flush=True)
    for f in files:
        process_file(f)
    print("🎉 全部完成", flush=True)
