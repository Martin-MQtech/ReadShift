# ReBook 视觉设计体系方案 (Design System Plan)

> **设计哲学**："一本书级的阅读体验，从纸感与墨香开始。"
> 融合西方经典书籍排版传统（Tschichold、企鹅出版社、New Yorker）与 AI 时代交互美学（Tailwind、Alpine）。

---

## 一、色彩体系 (Color System)

### 1.1 书籍纸感色系（默认主题 · "墨页"）
| 角色 | 色值 | 用途 |
|------|------|------|
| 纸感底 Paper | `#faf8f3` | 全局背景（米白纸感） |
| 墨黑 Ink | `#1c1917` | 正文主色 |
| 次级墨 InkSoft | `#44403c` | 次级文字 |
| 弱化墨 InkMute | `#78716c` | 页眉/注释 |
| 分隔线 Rule | `#e7e0d3` | 边框、分隔 |
| 点睛陶土 Accent | `#9a3412` | 强调、下划线、装饰 |
| 浅陶土 AccentSoft | `#fed7aa` | 选中态、浅底 |
| 深墨块 Deep | `#292524` | 遮罩、深色块 |

**设计逻辑**：借鉴企鹅出版社经典平装的克制用色——纸感底 + 墨黑 + 单一强调色，全篇不超过 4 个主角色。

### 1.2 备选主题（从 gzh-design 主题库平移）
| 主题 | 主色 | 气质 | 适用 |
|------|------|------|------|
| 石墨极简 | `#52525B` | 理性克制 | 商业分析类 |
| 橄榄手记 | `#1e1f23`+橙`#ed7b2f` | 编辑部内刊 | 深度纪实 |
| 禅意留白 | `#4A5D52` | 呼吸感 | 随笔散文 |

---

## 二、字体系统 (Typography System)

### 2.1 双字体引擎
- **正文 (衬线体)**：`Source Serif 4` / `Georgia` / `Songti SC` / `SimSun`
  - 中文环境自动回退到宋体系（书感）
  - 英文阅读体验对标 New Yorker 的衬线正文
- **标题/界面 (无衬线)**：`IBM Plex Sans` / `PingFang SC`
  - 借鉴 HBR 的信息层级：无衬线标题 + 衬线正文

### 2.2 字号阶梯（书籍印刷体）
| 层级 | 字号 | 说明 |
|------|------|------|
| 扉页标题 | 5xl-6xl (48-60px) | 书名级 |
| 章节标题 | 3xl (30px) | 章首 |
| 正文 | lg (18px) | 印刷感 |
| 双语英文侧 | 1.1rem | 衬线加大 |
| 书眉/尾注 | 0.72rem + 0.18em 字距 | 页眉页脚 |

### 2.3 版面比例（Tschichold 黄金规范）
- 版心最大宽度：`48rem`（约 768px，两侧留白）
- 行高：`1.9`（书籍级舒适行距）
- 段落间距：`1.75rem`
- 页边距比例参考 `2:3:4:6`（内:上:外:下）

---

## 三、书籍级版面元素 (Book Elements)

| 元素 | 设计 | 用途 |
|------|------|------|
| **扉页 Title Page** | 居中大字 + 装饰分隔 + 引语 | 每本书的开篇仪式感 |
| **书眉 Running Head** | 顶部固定，小字距大写 | 章节导航感 |
| **首字下沉 Drop Cap** | 首字 4.2em 陶土色衬线 | 章节开头仪式感 |
| **装饰分隔 Ornament** | ✦ ❖ 居中 + 细线 | 段落大分隔 |
| **章首设计** | 大标题 + 编号 | 章节识别 |
| **双语分栏** | 左中右右英，英文衬线加大 | 沉浸式学习 |
| **尾花 Colophon** | 页脚装饰 + 签名 | 全书收尾 |
| **互动词卡** | 陶土色下划线词 → 侧滑知识窗 | AI 时代延伸 |

---

## 四、交互元素 (AI-Era Interaction)

### 4.1 知识侧滑窗 (Slide-over)
- 点击 `interactive-term` 高亮词 → 右侧滑出知识抽屉
- 内含：概念释义（陶土标签）+ 背景延伸（衬线正文）
- Alpine.js 驱动，零依赖，离线可用

### 4.2 待引入（Phase 4.5）
- [ ] 阅读进度条（顶部细线）
- [ ] 深色模式（纸感 ↔ 墨夜）
- [ ] 词汇表索引页（全书 Cheat Sheet 汇总）
- [ ] 章节导航抽屉（目录）
- [ ] 字体大小调节器（A- A+）

---

## 五、落地架构

```
output/
├── book.html          # 单页交互式书籍 (本次交付)
├── book.epub          # Kindle/Apple Books (Pandoc)
└── book.pdf           # 打印版 (WeasyPrint)

src/templates/
└── template.ejs       # 唯一模板源 (EJS + Tailwind + Alpine)
```

**主题切换机制**：模板接受 `theme` 参数（paper/graphite/olive/zen），渲染时注入对应色值变量 —— 与 gzh-design 的"主题注册表"模式对齐。

---

## 六、参考来源

1. Jan Tschichold《The Form of the Book》—— 页边距比例、版心规范
2. Penguin Books 经典三色平装 —— 克制用色
3. The New Yorker —— 衬线正文、专栏结构
4. Harvard Business Review —— 信息层级、图表体系
5. gzh-design 主题库（本机 skills）—— 公众号排版语言
6. Tailwind CSS Typography —— Web 排版基建
