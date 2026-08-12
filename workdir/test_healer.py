"""用真实 OCR 文本测试 DeepSeek V4 Flash 的 Healer 修复能力（带重试）"""
import json, os, time

with open(os.path.expanduser('~/.zcode/v2/config.json')) as f:
    config = json.load(f)
zenmux = config['provider']['zenmux']
api_key = zenmux['options']['apiKey']
base_url = zenmux['options']['baseURL']

from openai import OpenAI
client = OpenAI(api_key=api_key, base_url=base_url, timeout=120, max_retries=3)
MODEL = "deepseek/deepseek-v4-flash"

# 取第8页 OCR 文本前 500 字（缩小输入，提高成功率）
raw = open('workdir/quality_check/ocr_full/page_008.txt', encoding='utf-8').read()
raw = raw[:500]
print(f"📥 原始 OCR 文本 (前500字):\n{raw}\n")

system = """你是一位拥有近乎强迫症的顶级文字编辑与语境还原专家。
我将给你受损严重的 OCR 文本，充满错别字、乱码、字间空格和粘连段落。
请根据中文语言逻辑和上下文，完美修复还原：
1. 吃掉所有字间空格和多余换行
2. 修复 OCR 错别字（如"饰秋雨"→"余秋雨"）
3. 纠正标点，合理分段
4. 保持原意，不增删、不翻译
直接输出修复后的文本。"""

# 带重试循环
for attempt in range(4):
    try:
        print(f"🔄 第 {attempt+1} 次尝试...")
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": raw}],
            temperature=0.3,
        )
        fixed = resp.choices[0].message.content
        print(f"✅ 修复成功!\n{fixed}\n")
        os.makedirs('output', exist_ok=True)
        open('output/page_008_fixed.md', 'w', encoding='utf-8').write(fixed)
        print("💾 已保存: output/page_008_fixed.md")
        break
    except Exception as e:
        print(f"⚠️ 失败: {type(e).__name__}: {str(e)[:120]}")
        if attempt < 3:
            wait = 10 * (attempt + 1)
            print(f"   等待 {wait}s 后重试...")
            time.sleep(wait)
        else:
            print("❌ 重试4次均失败，请检查网络或模型配额")
