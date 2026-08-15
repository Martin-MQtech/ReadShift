# 🚀 ReadShift 快速上手指南 (Quick Start)

> **三分钟跑通“从扫描图/原始文本到双语交互应用与出版级 EPUB”的完整工业化管线。**

---

## 第一步：安装依赖环境

本项目采用 Python 与 Node.js 双引擎协作：

```bash
# 1. 安装 Python 核心依赖 (QA 门禁 / 大模型管线 / EPUB 编译器)
pip install -r requirements.txt

# 2. 安装 Node 核心依赖 (HTML 交互渲染引擎)
npm install
```

---

## 第二步：配置大模型网关密钥

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env，填入 API 密钥
# 支持 DeepSeek / OpenAI / Gemini / 智谱等主流供应商
# 示例：ZENMUX_API_KEY=your_key_here
```

---

## 第三步：运行生产流水线核心指令

### 1. 大模型双语重构与知识提纯 (Pipeline)
```bash
# 运行第 1 章双语重塑（艾萨克森文风 + 商业 CheatSheet 提取）
python3 workdir/pipeline_v6_deepseek.py --chapter 1
```

### 2. 多章聚合与单文件 HTML 编译 (Compiler)
```bash
# 编译单章 HTML
node workdir/render_html_v9.js --chapter 1

# 编译全书 1-6 章为单一交互式 HTML 典藏版
node workdir/render_html_v9.js --chapters 1,2,3,4,5,6
```

### 3. 多维质量门禁自动化检测 (QA Gatekeeper)
```bash
# 检测单章资产健康度
python3 workdir/qa_gate_v3.py --chapter 1

# 扫描全书成书 HTML
python3 workdir/qa_gate_v3.py --html output/Samples/一-六章合成-Chapter-1-6.html
```

### 4. 出版级 EPUB 3.0 电子书打包 (EPUB Packager)
```bash
# 按照 OCF 标准封装包含双层双语目录、防撕裂保护的 EPUB 电子书
python3 workdir/build_epub.py
```

---

## 第四步：交付产物对照

编译成功后，产物位于 `output/` 目录下：

| 产物路径 | 格式与载体 | 适用场景 |
| :--- | :--- | :--- |
| `output/Samples/一-六章合成-Chapter-1-6.html` | 单文件交互式 HTML | 桌面大屏沉浸阅读、术语悬浮、全离线数字书房 |
| `output/张忠谋自传_双语终极典藏插图版.epub` | 流式 EPUB 3.0 | 移动端（手机 / iPad / 墨水屏）随身携带、微信读书、Apple Books |

---

## 🎯 核心规范与进阶指引

* 完整流程与标准作业程序：查阅根目录 `执行手册.md`
* 设计与美学规范：查阅 `docs/DESIGN_PLAN.md`
* Prompt 风格 DLC 矩阵：查阅 `docs/PROMPTS.md`
* 踩坑经验与故障库：查阅 `docs/LESSONS_LEARNED.md`
