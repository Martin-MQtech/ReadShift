---
name: readshift
description: ReadShift 杂志级双语电子书排版引擎与三维平行叙事工具包。支持从 Markdown 源料一键生成具备两级目录导航、双语章标题卡、二创卡片（Cheat Sheet/修辞赏析/背景知识延伸）的离线 HTML 电子书，并内嵌全量深层质量审计门禁 (QA Auditor v3.0)。
triggers:
  - "/readshift"
  - "readshift build"
  - "readshift qa"
  - "readshift check"
  - "双语电子书排版"
  - "平行叙事生成"
---

# Skill: ReadShift 双语电子书排版与平行叙事引擎

ReadShift 是一个将纯文本重塑为杂志级双语 HTML 电子书的开源排版引擎与 AIGC 平行叙事工具包。

## 核心命令入口

### 1. 初始化项目骨架 (`readshift init`)
```bash
python3 cli/readshift.py init --book-name "我的双语电子书"
```
自动建立规范的 D0/D1/D2 三层数据目录：
- `raw_source/` (D0 原料)
- `source/` (D1 编辑源)
- `output/` (D2 编译产物)

### 2. Markdown 编译为双语 HTML (`readshift build`)
```bash
python3 cli/readshift.py build --input source/ --output output/book.html
```
- 自动解析 `## ` 小节标题并注入双语副标题与两级目录导航。
- 自动渲染三块式二创卡片：`Cheat Sheet · 商业语汇`、`语言与逻辑赏析`（`.rhetoric-note`）、`背景知识延伸`（`.knowledge-note`）。
- 注入陶土橙边线、Baskerville 衬线英文字体与纸质暖调配色的 Tschichold 比例排版。

### 3. 深层质量审计门禁 (`readshift qa`)
```bash
python3 cli/readshift.py qa --html output/book.html
```
启动基于 HTMLParser 的 14 项严格门禁检测：
- 零转义泄露 (`[G1-01]`)
- DIV/SPAN 标签绝对闭合 (`[G1-02/03]`)
- 相邻与全局段落重复度检查 (`[G3-01..03]`)
- 目录锚点可达性与完整性 (`[G4-01/02]`)
- 二创卡片双语匹配与品牌统一 (`[G5/G6]`)

### 4. D1 源料资产体检 (`readshift check`)
```bash
python3 cli/readshift.py check --source source/
```
扫描 MD 源文件中的未闭合标签、占位符、小节标题缺失英文与脏数据。

---

## 三维平行叙事方法论 (3D Parallel Narrative Engine)

利用 ReadShift 进行 100% 自主版权 AI 二创的黄金法则：

1. **锚点 (The Anchor)**：以灵感母本的人物生平或重大事件为时间线坐标（如 1948 年上海）。
2. **内圈交集 (First-Person ➔ Third-Person Observer)**：采用第三方旁白视角重新解读经典抉择时刻（不说“我做了什么”，而说“他在那一刻面对了什么”）。
3. **外圈拓展 (The Era & Community)**：跳出传主个人视角，展开同时代的商业风云、科技突破（如集成电路的发明、英特尔三巨头）与社会大势。
4. **两条主线**：
   - 显性：商业精神（奋斗不息 · 寻找商机 · 拓宽能力边界）
   - 隐性：跨文明之旅（学习 · 挑战 · 适应 · 自愈）
5. **单集脚本 SOP**：
   `开场钩子 ➔ 锚点立身 ➔ 内圈抉择 ➔ 外圈展开 ➔ 思想升华金句 ➔ 知识延伸卡 ➔ 下集预告`
