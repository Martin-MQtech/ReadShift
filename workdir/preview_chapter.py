"""精品样章: 第7-15页(序言部分) 批量全链路处理"""
import json, os, time, sys

with open(os.path.expanduser('~/.zcode/v2/config.json')) as f:
    config = json.load(f)
z = config['provider']['zenmux']

from openai import OpenAI
client = OpenAI(api_key=z['options']['apiKey'], base_url=z['options']['baseURL'], timeout=120, max_retries=3)
MODEL = "deepseek/deepseek-v4-flash"

def call(system, user, temp=0.6):
    for attempt in range(5):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=temp,
            )
            return resp.choices[0].message.content
        except Exception as e:
            wait = 8 * (attempt + 1)
            print(f"    ⚠️ 重试{attempt+1}: {str(e)[:60]} 等{wait}s")
            time.sleep(wait)
    return None

HEALER = "你是一位拥有近乎强迫症的顶级文字编辑与语境还原专家。将受损的OCR文本完美修复：1.吃掉字间空格和多余换行 2.修复错别字 3.纠正标点合理分段 4.保持原意不增删不翻译。直接输出修复后文本。"
ISAACSON = "你是《史蒂夫·乔布斯传》作者沃尔特·艾萨克森。将以下中文重塑为地道优雅的现代商业英语：宏大战略用高阶商用词汇，人物情感保留原生张力；不要机械直译要意译重组；输出格式：每段先中文再英文，用---分隔。"
EXTRACTOR = "你是一位顶尖商学院的客座教授和百科全书式知识博主。扫描双语文本挖掘价值：1.商业语汇提炼(Cheat Sheet):挑3-5个最地道英文表达给中文解释和真实商业造句 2.修辞与逻辑赏析:摘取精彩表述点评为何高级 3.外链知识窗:涉及重大历史事件/人物/时代背景用50字精炼总结。用markdown输出。"

PAGES = range(7, 16)  # 第7-15页
os.makedirs('output/preview', exist_ok=True)

for page in PAGES:
    ocr_file = f'workdir/quality_check/ocr_full/page_{page:03d}.txt'
    if not os.path.exists(ocr_file):
        print(f"⏭️ 跳过第{page}页 (无OCR文件)")
        continue
    raw = open(ocr_file, encoding='utf-8').read().strip()
    if len(raw) < 50:
        print(f"⏭️ 跳过第{page}页 (内容过少: {len(raw)}字)")
        continue
    
    print(f"🔄 第{page}页: 修复中...", flush=True)
    fixed = call(HEALER, raw, 0.3)
    if not fixed:
        print(f"❌ 第{page}页 修复失败，跳过")
        continue
    
    print(f"   ✅ 修复完成 ({len(fixed)}字), 双语重塑中...", flush=True)
    bilingual = call(ISAACSON, fixed, 0.8)
    if not bilingual:
        print(f"❌ 第{page}页 双语失败，保留修复文本")
        bilingual = fixed
    
    print(f"   ✅ 双语完成, 知识萃取中...", flush=True)
    cheat = call(EXTRACTOR, bilingual, 0.6)
    if not cheat:
        cheat = "_（知识萃取失败，可重试）_"
    
    with open(f'output/preview/page_{page:03d}.md', 'w', encoding='utf-8') as f:
        f.write(f"# 第{page}页\n\n---\n\n{fixed}\n\n---\n\n{bilingual}\n\n---\n\n{cheat}\n")
    print(f"✅ 第{page}页完成 → output/preview/page_{page:03d}.md\n", flush=True)

print("🎉 精品样章处理完毕! 产出: output/preview/page_007.md ~ page_015.md")
