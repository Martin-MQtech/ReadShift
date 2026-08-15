---
name: readshift
description: ReadShift 广义文化内容再造与多模态 AIGC 进化型技能插件。支持从书籍/古籍/书法/口述/胶片等多源介质出发，输出出版级双语 HTML/EPUB 电子书、广播级双轨音频播客、矢量书法重构与多模态数码衍生品。
triggers:
  - "/readshift"
  - "readshift build"
  - "readshift epub"
  - "readshift audio"
  - "readshift art"
  - "readshift qa"
  - "双语电子书排版"
  - "出版级EPUB制作"
  - "多模态内容再造"
---

# ⚡ Skill: ReadShift 广义内容再造与多模态进化型 Agent 引擎

> **“狭义内容起步，广义内容进化；工具随领域生长，潜能归于无限。”**

`ReadShift` 不仅是一个静态的代码脚本集，而是一个**具备模块化、可生长生命力的多模态能力矩阵（Evolutionary Skill Architecture）**。

---

## 🧭 狭义 Content 与广义 Content 的能力演进图谱

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        READSHIFT 技能能力生命周期与模块化演进                           │
├──────────────────────────────────────────┬─────────────────────────────────────────────┤
│ 📖 当前已就位能力 (Narrow Content)        │ 🚀 正在生长与规划能力 (Broad Content)        │
├──────────────────────────────────────────┼─────────────────────────────────────────────┤
│ • 结构化文本提纯 (Markdown D1 主源)      │ • 🖌️ 书法碑帖与古籍善本矢量化 (SVG 重构)    │
│ • 艾萨克森体双语对齐与动态语域平衡       │ • 🎨 AIGC 叙事插画与时代感水彩生成           │
│ • 自包含离线交互 HTML 典藏母版编译       │ • 🎬 历史分镜脚本与视觉叙事短片 (MP4)       │
│ • 出版级 EPUB 3.0 流式跨端电子书封装     │ • 📱 交互式人物/时间线图谱与离线 PWA 微应用  │
│ • 双轨神经拟真语音播客/广播剧合成 (MP3)  │ • 🏛️ 3D 文化展品与数字藏品生成               │
└──────────────────────────────────────────┴─────────────────────────────────────────────┘
```

---

## 🛠️ 模块化指令集与能力矩阵

### 1. 结构与三层数据治理 (`readshift init` / `check`)
```bash
python3 cli/readshift.py init --book-name "我的重制项目"   # 初始化 D0/D1/D2
bash docs/HEALTHCHECK.sh                                  # D1 源料健康检查
```

### 2. 双语精排与交互 HTML 应用 (`readshift build`)
```bash
node workdir/render_html_v9.js --chapter 1                # 单章编译
node workdir/render_html_v9.js --chapters 1,2,3,4,5,6    # 全书母版合成
```
* **核心特性**：Tschichold 黄金比例、双层悬浮目录随动高亮、三块式二创卡片（Cheat Sheet/修辞/背景）、零 CDN 单文件封装。

### 3. 出版级 EPUB 3.0 跨端流式封装 (`readshift epub`)
```bash
python3 workdir/build_epub.py
```
* **核心特性**：OCF 两阶段物理封包、`mimetype` 零压缩置顶、两级双语目录树（`nav.xhtml` + `toc.ncx`）、全透明自适应底色、全链路 `page-break` 防撕裂保护。

### 4. 双轨广播级音频与播客合成 (`readshift audio`)
```bash
python3 02-平行叙事衍生创作_Parallel_Universe/00-官方标杆：台积电张忠谋·传记时间线的声音世界/tools/make_tts.py
```
* **核心特性**：中英双语分轨神经语音合成（Edge-TTS）、音量归一化、ID3 标签写入。

### 5. 多模态艺术与书法重构 (`readshift art` · 模块生长中)
* **核心特性**：古籍善本高清图像去噪与切片、书法拓片文字 OCR 释读、笔画骨架矢量化（SVG）与动态书写轨迹生成。

### 6. 多维质量门禁自动化断言 (`readshift qa`)
```bash
python3 workdir/qa_gate_v3.py --chapter 1
python3 workdir/qa_gate_v3.py --html 私域产物/Samples/全书母版.html
```
* **核心特性**：XML 严格实体语法断言、标签闭合性、目录可达性、双语 1:1 段落配对检测。
