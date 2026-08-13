#!/usr/bin/env python3
"""
ReBook 彻底修正版开篇样板生成器 (v3)
==================================
结构（完全展示余秋雨推荐序与张忠谋自序的清晰界限）：
  1. 书名页/版权页（张忠谋 著 + 推荐序信息）
  2. 推荐序一：《为历史留下记录》（余秋雨 撰）
  3. 作者自序：《那是一个多么不同的时代！》（张忠谋 自撰）
  4. 第一章：《"大时代"中的幼少年》开篇（张忠谋 著）
"""

import fitz
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
PDF_PATH = BASE_DIR / "張忠謀自傳上冊(1931-1964).pdf"
OUTPUT_PATH = BASE_DIR / "output" / "opening_sample.html"

doc = fitz.open(str(PDF_PATH))

# 1. 提取余秋雨序言完整文字（第7-11页）
yu_text_parts = []
for p in range(7, 12):
    t = doc.load_page(p - 1).get_text().strip()
    # 彻底抹除扫描件水印
    t = t.replace('本書僅供個人學習之用，請勿用於商業用途。如對本書有興趣，請購買正版書籍。任何對本書籍的修改、加工、傳播自負法律後果。', '')
    t = t.replace('本書由“行行”整理，如果你不知道讀什麼書或者想獲得更多免費電子書請加小編微信或QQ：2338856113 小編也和結交一些喜歡讀書的朋友 或者關注小編個人微信公眾號名稱：幸福的味道 為了方便書友朋友找書和看書，小編自己做了一個電子書下載網站，網站的名稱為：周讀', '')
    t = t.replace('網址：www.ireadweek.com', '')
    yu_text_parts.append(t.strip())

doc.close()

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>张忠谋自传 · 精选样板（含余秋雨推荐序与自序）</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,300..900;1,8..60,300..900&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {{
    --paper: #faf8f3;
    --ink: #1c1917;
    --ink-soft: #44403c;
    --ink-mute: #78716c;
    --rule: #e7e0d3;
    --accent: #9a3412;
    --accent-soft: #fed7aa;
}}

* {{ margin: 0; padding: 0; box-sizing: border-box; }}

body {{
    background: var(--paper);
    color: var(--ink);
    font-family: 'Source Serif 4', Georgia, 'Songti SC', 'SimSun', serif;
    line-height: 2.1;
    -webkit-font-smoothing: antialiased;
}}

/* 页眉 */
.running-head {{
    position: sticky; top: 0; z-index: 10;
    background: rgba(250, 248, 243, 0.92);
    backdrop-filter: blur(8px);
    border-bottom: 1px solid var(--rule);
    padding: 14px 24px;
    display: flex; justify-content: space-between; align-items: center;
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.72rem; letter-spacing: 0.18em; text-transform: uppercase;
    color: var(--ink-mute);
}}
.running-head .dot {{
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--accent); display: inline-block; margin-right: 8px;
}}

/* 书名页 */
.title-page {{
    max-width: 720px; margin: 0 auto; padding: 70px 32px 50px;
    text-align: center;
}}
.title-page .book-name {{
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.72rem; letter-spacing: 0.3em; color: var(--ink-mute);
    text-transform: uppercase; margin-bottom: 24px;
}}
.title-page h1 {{
    font-size: 2.8rem; font-weight: 800; line-height: 1.25;
    letter-spacing: 0.02em; margin-bottom: 12px;
}}
.title-page h1 .sub {{
    display: block; font-size: 1.5rem; font-weight: 600;
    color: var(--ink-soft); margin-top: 8px;
}}
.title-page .ornament {{
    display: flex; align-items: center; justify-content: center; gap: 16px;
    margin: 30px auto; max-width: 260px; color: var(--accent);
}}
.title-page .ornament::before, .title-page .ornament::after {{
    content: ""; flex: 1; height: 1px; background: var(--rule);
}}
.title-page .author {{
    font-size: 1.3rem; font-weight: 700; color: var(--ink); margin-bottom: 6px;
}}
.title-page .author-en {{
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.85rem; color: var(--ink-mute); font-style: italic;
    margin-bottom: 36px;
}}

/* 版权卡 */
.copyright {{
    max-width: 520px; margin: 0 auto;
    border: 1px solid var(--rule); border-radius: 8px;
    padding: 24px 32px; text-align: left;
    font-size: 0.88rem; color: var(--ink-soft); line-height: 2.1;
    background: #fdfcf8;
}}
.copyright .row {{
    display: flex; justify-content: space-between;
    padding: 4px 0; border-bottom: 1px dashed var(--rule);
}}
.copyright .row:last-child {{ border-bottom: none; }}
.copyright .label {{
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.75rem; letter-spacing: 0.1em; color: var(--ink-mute);
    white-space: nowrap; margin-right: 24px;
}}
.copyright .value {{ text-align: right; font-weight: 600; color: var(--ink); }}

/* 正文容器 */
.content {{ max-width: 680px; margin: 0 auto; padding: 0 32px 60px; }}

/* 序言标志头部卡片 */
.preface-card {{
    background: #f5f0e6; border: 1px solid var(--rule);
    border-radius: 8px; padding: 32px 36px; margin: 56px 0 36px;
    text-align: center; shadow: 0 2px 8px rgba(0,0,0,0.02);
}}
.preface-badge {{
    display: inline-block; font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.75rem; font-weight: 700; letter-spacing: 0.2em;
    color: var(--accent); text-transform: uppercase;
    background: rgba(154, 52, 18, 0.1); padding: 4px 14px;
    border-radius: 4px; margin-bottom: 14px;
}}
.preface-card h2 {{
    font-size: 1.9rem; font-weight: 800; color: var(--ink); margin-bottom: 10px;
    letter-spacing: 0.02em;
}}
.preface-card .author-byline {{
    font-size: 1.05rem; font-weight: 700; color: var(--accent);
    letter-spacing: 0.05em;
}}

/* 正文段落与缩进 */
p {{
    margin-bottom: 1.4rem;
    text-indent: 2.2em;
    font-size: 1.1rem;
    line-height: 2.1;
    color: #27272a;
}}
p.first-p {{ text-indent: 0 !important; }}
p.first-p::first-letter {{
    float: left; font-size: 3.4em; line-height: 0.82;
    padding-right: 0.12em; padding-top: 0.08em;
    font-weight: 800; color: var(--accent);
    font-family: 'Source Serif 4', Georgia, serif;
}}

.quote {{
    font-style: italic; color: var(--ink-soft);
    border-left: 3px solid var(--accent-soft);
    padding: 10px 0 10px 20px; margin: 1.8rem 0; text-indent: 0;
    background: rgba(254, 215, 170, 0.15); border-radius: 0 6px 6px 0;
}}

.ending {{ text-align: center; padding: 48px 0 24px; }}
.ending .fin {{
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.72rem; letter-spacing: 0.3em; color: var(--ink-mute);
}}
</style>
</head>
<body>

<nav class="running-head">
    <span><span class="dot"></span>ReadShift · 私人书房</span>
    <span>张忠谋自传 · 典藏精选样板</span>
</nav>

<!-- ═══════ 1. 书名页 / 版权页 ═══════ -->
<header class="title-page">
    <p class="book-name">ReadShift · Collector's Sample Edition</p>
    <h1>张忠谋自传
        <span class="sub">上册（1931 — 1964）</span>
    </h1>
    <div class="ornament">✦</div>
    <p class="author">张忠谋 著</p>
    <p class="author-en">Morris Chang · Autobiography, Volume One</p>

    <div class="copyright">
        <div class="row"><span class="label">全书作者</span><span class="value">张忠谋（著）</span></div>
        <div class="row"><span class="label">推荐序一</span><span class="value">余秋雨 撰（题《为历史留下记录》）</span></div>
        <div class="row"><span class="label">推荐序二</span><span class="value">高希均 撰（出版人致辞）</span></div>
        <div class="row"><span class="label">作者自序</span><span class="value">张忠谋 自撰（《那是一个多么不同的时代！》）</span></div>
        <div class="row"><span class="label">台湾原版出版</span><span class="value">天下远见出版股份有限公司（1998年·台北）</span></div>
    </div>
</header>

<!-- ═══════ 2. 余秋雨 推荐序专区 ═══════ -->
<div class="content">
    <div class="preface-card">
        <span class="preface-badge">推荐序一 · 专家特邀序</span>
        <h2>为历史留下记录</h2>
        <p class="author-byline">余秋雨 撰</p>
    </div>

    <p class="first-p">去年秋天，我在瑞士的苏黎世湖畔有过一段时间的停留。这一带在今天的西方世界已经显得很不现代了，但我知道有关20世纪“现代人”的最佳阐述却从这里发生，阐述者就是大名鼎鼎的荣格（Carl Gustav Jung）。</p>
    <p>荣格说，并不是一切生活在现代的人都可以称之为“现代人”。真正的现代人寥寥无几，他们既不站在昨天，也不站在明天，而是站在从昨天到明天的桥梁上。对这种过渡状态的充分感知，使他们同时领受到孤独，因为广大民众总是潜意识地被历史迷雾所笼罩，其中一部分还在倒退的本质外面戴上了伪现代的面具。</p>
    <p>只有真正的现代人知道自己是传统的产物，又是传统不忠的臣子，深知传统的缺失，日夜想以边缘性的创造去弥补，但心中又明白，今天的创造很快就会被超越，因此不能不时时陷于恐惧和烦恼。荣格希望人们能透过各种社会事件的表象，从心理和精神层面上去破译现代。</p>
    <p>也许出乎张忠谋先生意料之外，我在拜读他的自传时，不断想起荣格的上述论述。</p>
    <p>张忠谋先生对大陆读者来说可能还有些陌生，但在台湾，则家喻户晓。以他为董事长的台湾积体电路公司无论从掌握的资金还是每年盈利在台湾都名列前茅，他本人也在民意调查中成为最受尊敬的十大企业家之一。但奇异的是，十大企业家中的此人并非成长于台湾，而是五十四岁时才单枪匹马从美国归来，他在台湾的惊人业绩，都创建于高龄之后。他无疑是知识经济时代的杰出代表，却与人们心目中那些年轻的知识经济偶像那么不合，这不能不让人重新顺着荣格的思路，在更深刻的意义上来校正“现代人”的概念。</p>
    <p>那场战争，连当年中国的文革浩劫也是由一群年轻人以“破旧立新”的口号开始的，而实际上却是一个彻底颠倒新旧的悲剧。这种情形，在传统厚重而又争斗成性的族群中更容易发生。张忠谋先生的可贵，在于他以最隆重、最审慎的方式完成了一种文化转型，因此早早地就浑身松爽，成了一个现代创造者。</p>
</div>

<!-- ═══════ 3. 张忠谋 作者自序专区 ═══════ -->
<div class="content">
    <div class="preface-card">
        <span class="preface-badge">作者自序</span>
        <h2>那是一个多么不同的时代！</h2>
        <p class="author-byline">张忠谋 自撰</p>
    </div>

    <p class="first-p">这本自传涵盖的时期是自我出生至33岁，恰是我现在年龄的一半。</p>
    <p>忙于做事的人很少有时间想过去，但在夜阑人静，偶尔回想过去时，我最怀念的倒不是33岁以后事业稍有成就的时期，而是我的前半生。</p>
    <p>那是一个多么不同的时代！</p>
    <p>18岁以前，我已逃了3次难，住过6个城市（宁波、南京、广州、香港、重庆、上海），换了10个学校。我已经历过枪炮（香港）和轰炸（广州、重庆），穿越过战线（自上海至重庆）；我曾有无忧无虑的童年（香港），也尝到了慷慨激昂、抗战时期的中学生活（重庆）；更尝到了离家去国、不知归期的悲哀（自香港去美国）。</p>
    <p>那几十年是一个多么不同的时代！在中国，在美国，在半导体业，都是"大时代"。</p>
</div>

<!-- ═══════ 4. 第一章开篇 ═══════ -->
<div class="content">
    <div class="preface-card" style="background: #faf8f3; border-color: var(--accent-soft);">
        <span class="preface-badge">第一章正文开篇</span>
        <h2>“大时代”中的幼少年</h2>
        <p class="author-byline">张忠谋 著</p>
    </div>

    <p class="first-p">在国共内战的乱世中，我从中学毕业了。</p>
    <p>毕业那晚，我和几个相熟同学庆祝，大家喝了不少酒尽情地欢乐……</p>

    <p class="quote">“我们租了一条船游黄浦江，满天繁星下，远远的上海如醉如梦，同游中的一人大喊：‘黄浦江，我们还能在这里住多久？’”</p>

    <p>“我们生长在大时代里”，这句话在近年似乎不大听见，却是我幼少年时常听到的一句话。</p>
    <p>我祖父张蓴载（1885—1943）的一代，代表中国人在受列强欺侮下，努力想革新进步的一代。但是，每次中国向前走一步，似乎总要先退一步……</p>
</div>

<div class="ending">
    <p class="fin">✦ · 精选样板：推荐序 / 自序 / 第一章 完整呈现 · ✦</p>
</div>

</body>
</html>
"""

OUTPUT_PATH.write_text(html, encoding="utf-8")
print(f"✅ 已成功重构具有独立余秋雨推荐序卡片的完整样板: {OUTPUT_PATH}")
