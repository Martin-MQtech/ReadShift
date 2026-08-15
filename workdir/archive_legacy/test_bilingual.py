"""继续全链路: Isaacson 双语重塑 + 知识萃取 (DeepSeek V4 Flash)"""
import json, os, time

with open(os.path.expanduser('~/.zcode/v2/config.json')) as f:
    config = json.load(f)
zenmux = config['provider']['zenmux']
api_key = zenmux['options']['apiKey']
base_url = zenmux['options']['baseURL']

from openai import OpenAI
client = OpenAI(api_key=api_key, base_url=base_url, timeout=120, max_retries=3)
MODEL = "deepseek/deepseek-v4-flash"

def call(system, user, temp=0.7):
    for attempt in range(4):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=temp,
            )
            return resp.choices[0].message.content
        except Exception as e:
            print(f"⚠️ 尝试{attempt+1}失败: {str(e)[:80]}")
            if attempt < 3:
                time.sleep(8 * (attempt + 1))
    return None

# 读取修复后的文本
fixed = open('output/page_008_fixed.md', encoding='utf-8').read()

# ===== 第2步: Isaacson 双语重塑 =====
print("=" * 60)
print("🔵 [主编层] Isaacson 双语重塑")
print("=" * 60)

isaacson_system = """你是《史蒂夫·乔布斯传》作者沃尔特·艾萨克森 (Walter Isaacson)。
将以下中文重塑为地道、优雅的现代商业英语：
- 讲述宏大战略时用高阶商用词汇；展现人物情感时保留原生张力
- 不要机械直译，要意译与结构重组
- 输出格式: 每个段落先中文、再英文，用 --- 分隔"""

bilingual = call(isaacson_system, fixed, temp=0.8)
if bilingual:
    print(f"✅ 双语重塑结果:\n{bilingual}\n")
    open('output/page_008_bilingual.md', 'w', encoding='utf-8').write(bilingual)

# ===== 第3步: 知识萃取 =====
print("=" * 60)
print("🟣 [主编层] 知识萃取 (Cheat Sheet)")
print("=" * 60)

extractor_system = """你是一位顶尖商学院的客座教授，也是一位百科全书式的知识博主。
请扫描以下中英双语文本，挖掘更深邃的价值：
1. 商业语汇提炼 (Cheat Sheet): 挑 3-5 个最地道的英文表达，给中文解释和真实商业造句
2. 修辞与逻辑赏析: 摘取精彩表述，点评为何高级
3. 外链知识窗: 涉及重大历史事件/人物/时代背景，用50字精炼总结
用 markdown 输出"""

cheat = call(extractor_system, bilingual or fixed, temp=0.6)
if cheat:
    print(f"✅ 知识萃取结果:\n{cheat}\n")
    open('output/page_008_cheatsheet.md', 'w', encoding='utf-8').write(cheat)

# 汇总
if bilingual:
    with open('output/page_008_full.md', 'w', encoding='utf-8') as f:
        f.write("# 《张忠谋自传》第8页 · ReBook 真实重制\n\n---\n\n")
        f.write(fixed + "\n\n---\n\n")
        f.write(bilingual + "\n\n---\n\n")
        if cheat:
            f.write(cheat + "\n")
    print("🎉 全链路完成! 汇总: output/page_008_full.md")
