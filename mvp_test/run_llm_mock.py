import json

raw_text = """是 我 的 青 春 。
是 半 导 体 业 的 青 春 。
也 是 美 国 成 为 超 级 强 国 后 的 青 春 。
即 使 在 古 老 的 中 国 , 在 抗 戢 线 年 中 , 也 嗅 到 了 强 烈 的 青 春 气 息 。
守 传 的 逸 因 与 近 因
近美霹的愤念′ 弧 不 足 以 使 我 提 笔 穹 自 传 。 提 笔 的 决 定 仍 有 它 的 速 因 和 近 因 。
违 因 是 少 年 时 代 的 作 家 蔬 。在 香 港 的 小 学 、 重 庆 和 上 海 的 中 学 里 , 有
六 七 年 的 幼 少 年 光 隆 , 痴 心 想 以 冠 作 为 终 身 工 作 。"""

print("============== [ 引擎启动: The Healer (语义修复层) ] ==============")
print("正在读取乱码文字，并施加 LLM 上下文纠错魔法...\n")
print("""【清洗结果】：
是我的青春。
是半导体业的青春。
也是美国成为超级强国后的青春。
即使在古老的中国，在抗战那些年中，也嗅到了强烈的青春气息。

自传的远因与近因：
近来的念头，并不足以使我提笔写自传。提笔的决定仍有它的远因和近因。
远因是少年时代的作家梦。在香港的小学、重庆和上海的中学里，有六七年的幼少年光阴，痴心想以写作作为终身工作。""")

print("\n============== [ 引擎启动: The Bilingual Architect (双语重塑层) ] ==============")
print("正在注入高端商业语境指令(HBR Style)，生成段落级双语...\n")
print("""| 繁华重塑 (Enhanced Chinese) | 商业美风 (Modern Business English) |
| :--- | :--- |
| 是我的青春。<br>是半导体业的青春。<br>也是美国成为超级强国后的青春。<br>即使在古老的中国，在抗战那些年中，也嗅到了强烈的青春气息。 | It was my youth.<br>It was the youth of the global semiconductor industry.<br>And it was the youth of America in its post-war ascent as a superpower.<br>Yet, even within an ancient China embroiled in wartime struggles, one could scent the visceral, unmistakable vitality of youth. |
| **自传的远因与近因：**<br>近来的念头，并不足以使我提笔写自传。提笔的决定仍有它的远因和近因。 | **The Catalyst for an Autobiography:**<br>Recent fleeting thoughts were not substantial enough to compel me to document my life's journey. The decision to take up the pen inevitably traces back to both immediate triggers and profound, distant origins. |
| 远因是少年时代的作家梦。在香港的小学、重庆和上海的中学里，有六七年的幼少年光阴，痴心想以写作作为终身工作。 | The distant origin lies in a boyhood dream of becoming a writer. Throughout my elementary days in Hong Kong, and across my middle school years navigating Chongqing and Shanghai, there were six or seven formative years where I harbored a fervent, steadfast ambition to make writing my lifelong vocation. |""")

print("\n============== [ 引擎启动: The Cheat Sheet Generator (知识榨汁机) ] ==============")
print("正在提取高阶表达...\n")
print("""💡 **Chapter 1 - Business & Literary Vocabulary** 
- **Semiconductor Industry**: 半导体产业 (Context: The foundation of modern computing).
- **Post-war Ascent**: 战后崛起 (Usage: "America in its post-war ascent as a superpower"). 
- **Visceral Vitality**: 强烈的生机/活力 (Usage: "The visceral, unmistakable vitality of youth").
- **Compel**: 驱使，强迫 (Advanced usage over "make/force").
- **Formative Years**: 形成性格的关键岁月/幼少年光阴 (Crucial vocabulary in autobiographical contexts).
- **Lifelong Vocation**: 终身职业/志向。""")
