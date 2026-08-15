# ⚡ 01 · 核心能力：ReadShift Agent Skill (即插即用 AI 技能插件)

> **“赋能每一位开发者与创作者，一键获得出版级做书与多模态再造能力。”**

`ReadShift Agent Skill` 是本项目的 **01 号核心能力产物**。无论你使用的是 **ZCode / Claude Code / Codex / Cursor / OpenCode / AutoGPT**，均可直接挂载本技能插件，实现从泛黄旧书到双语典藏应用与视听二创的全流程闭环。

---

## 📦 一键调用指令族

```bash
/readshift                                                # 交互式唤醒技能总览
python3 cli/readshift.py init --book-name "我的重制读物"   # 初始化 D0/D1/D2 三层资产架构
python3 cli/readshift.py build --input source/            # 编译为自包含交互 HTML 母版
python3 cli/readshift.py epub --input source/             # 编译为出版级 EPUB 3.0 流式电子书
python3 cli/readshift.py qa --html 私域产物/book.html     # 启动 14 项严格自动化质量门禁
bash docs/HEALTHCHECK.sh                                  # 扫描 D1 Markdown 源料纯净度
```

---

## 🛠️ 技能定义文件
* 核心技能定义规范位于本目录下的 **[`SKILL.md`](./SKILL.md)**，遵循标准 Agent Skills 协议规范。
