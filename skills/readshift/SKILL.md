---
name: readshift
description: ReadShift 出版级双语排版、EPUB 3.0 编译器与 AIGC 多模态文化再造通用技能插件。支持从 Markdown/OCR 源料一键生成具备两级目录导航、双语章标题卡、二创卡片（Cheat Sheet/修辞赏析/背景窗）的自包含离线 HTML 电子书，支持按国际 OCF 规范编译出版级 EPUB 3.0 流式电子书，并内嵌全量深层质量审计门禁 (QA Gate v3.0)。
triggers:
  - "/readshift"
  - "readshift build"
  - "readshift epub"
  - "readshift qa"
  - "readshift check"
  - "双语电子书排版"
  - "出版级EPUB制作"
  - "平行叙事生成"
---

# ⚡ Skill: ReadShift 经典重塑与 AIGC 多模态内容再造通用引擎

`ReadShift` 是一个即插即用的 AI Agent 技能插件（Skill）。它赋予任何 Coding Agent（ZCode / Claude Code / Codex / Cursor / OpenCode / AutoGPT）以**工业级做书、双语精排、出版级 EPUB 编译与多模态二创**的强大能力。

---

## 🛠️ 核心能力与命令入口

### 1. 初始化项目骨架 (`readshift init`)
```bash
python3 cli/readshift.py init --book-name "我的重制读物"
```
自动建立规范的 D0/D1/D2 三层数据治理目录：
* `raw_source/` (D0 只读原始证据)
* `source/` (D1 纯净编辑主源)
* `私域产物/` (D2 本地生成物)

### 2. 编译自包含交互 HTML (`readshift build`)
```bash
# 单章编译
node workdir/render_html_v9.js --chapter 1

# 多章聚合成全书母版
node workdir/render_html_v9.js --chapters 1,2,3,4,5,6
```
* 自动解析 `## ` 小节标题并注入两级目录随动高亮；
* 渲染三块式二创卡片：`Cheat Sheet`、`修辞赏析`（`.rhetoric-note`）、`背景知识延伸`（`.knowledge-note`）；
* 纸书纸感配色（`#faf8f3` + `#1c1917`）与 Tschichold 黄金比例排版，全离线单文件封装。

### 3. 编译出版级 EPUB 3.0 电子书 (`readshift epub`)
```bash
python3 workdir/build_epub.py
```
* **双层双语目录树**：`nav.xhtml`（EPUB 3）与 `toc.ncx`（EPUB 2）深度嵌套二级小节；
* **移动端防撕裂**：标题注入 `page-break-after: avoid`，卡片与插图注入 `page-break-inside: avoid`；
* **全主题自适应**：底色全局透明，完美适配 Apple Books / 微信读书的夜间、羊皮纸与护眼绿模式；
* **OCF 物理封装**：`mimetype` 零压缩置顶（`-0` 存储模式）+ XML 严格实体解析断言。

### 4. 多维自动化质量审计门禁 (`readshift qa`)
```bash
python3 workdir/qa_gate_v3.py --chapter 1
python3 workdir/qa_gate_v3.py --html 私域产物/Samples/全书母版.html
```
启动基于 HTMLParser 的 14 项严格门禁断言：
* XML 实体与转义安全 (`[G1-01]`)
* DIV / SPAN / Note 标签绝对闭合 (`[G1-02/03]`)
* 目录锚点可达性与小节条目完整性 (`[G4-01/02]`)
* 二创卡片结构与双语段落配对检查

### 5. D1 源料资产健康体检 (`readshift check`)
```bash
bash docs/HEALTHCHECK.sh
```
扫描 D1 Markdown 文件中的未闭合标签、占位符、多空行与孤立大标题。

---

## 🎙️ AIGC 平行叙事与多模态衍生方法论

利用 ReadShift 进行 100% 自主版权 AI 二创的黄金法则：
1. **锚点 (The Anchor)**：以灵感母本的时间线与历史事实为骨架；
2. **第三人称视角重构**：跳出第一人称局限，以第三方客观旁白重述抉择时刻；
3. **双轨广播级音频**：调用神经语音合成（Edge-TTS），生成中英双轨 MP3 广播剧与独立剧本。
