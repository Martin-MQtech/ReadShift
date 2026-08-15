# ReadShift 视觉设计与出版级排版体系方案 (Design & Typography System)

> **设计哲学**：“一本书级的阅读体验，从纸感与墨香开始。”  
> 融合西方经典书籍排版传统（Tschichold 比例法则、企鹅出版社克制用色、New Yorker 专栏美学）与现代移动端流式电子书（EPUB 3.0）与自包含 Web 交互应用。

---

## 一、 双重载体与设计定位 (Dual-Vessel Architecture)

ReadShift 的产出并非单一网页，而是面向两种终极阅读场景的“出版级双生载体”：

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        ReadShift 出版级双生载体                          │
├──────────────────────────────────┬─────────────────────────────────────┤
│ 载体 A：单文件自包含 HTML 应用    │ 载体 B：出版级 EPUB 3.0 电子书      │
├──────────────────────────────────┼─────────────────────────────────────┤
│ · 定位：桌面端/大屏沉浸研读       │ · 定位：移动端（手机/iPad/墨水屏）随身 │
│ · 体验：两级交互目录/点击悬浮卡片│ · 体验：仿真翻页/夜间模式/双层原生目录 │
│ · 依赖：零外部 CDN、完全离线可用 │ · 规范：严格 OCF 封包、XML 零解析崩溃   │
└──────────────────────────────────┴─────────────────────────────────────┘
```

---

## 二、 色彩与材质体系 (Color & Texture System)

### 2.1 书籍纸感色系（"墨页" 主题）

| 角色 | 色值 | 作用与规范 |
| :--- | :--- | :--- |
| **纸感底 Paper** | `#faf8f3` | 全局背景（米白纸感），EPUB 端声明为 `transparent` 允许阅读器自适应主题 |
| **墨黑 Ink** | `#1c1917` | 正文主色，温和高对比度 |
| **次级墨 InkSoft** | `#44403c` | 次级文字、英文副标题 |
| **弱化墨 InkMute** | `#78716c` | 英文图注、页脚、版权标注 |
| **分隔线 Rule** | `#e7e0d3` | 章节微分割线、卡片边框 |
| **点睛陶土 Accent** | `#9a3412` / `#ea580c` | 双语左边线、✦ 装饰符、重点词汇下划线 |
| **浅陶土 AccentSoft** | `rgba(154, 52, 18, 0.035)` | 英文翻译块微底纹、词卡聚焦浅底 |

---

## 三、 字体与版面比例 (Typography & Tschichold Layout)

### 3.1 双语字体引擎
- **中文正文（书感衬线）**：`Songti SC` / `SimSun` / `Noto Serif CJK SC` / `serif`
- **英文译文（传记衬线）**：`EB Garamond` / `Georgia` / `Source Serif 4` / `Times New Roman`（斜体稍小字号，与中文形成呼吸律动）
- **界面与导航（现代无衬线）**：`PingFang SC` / `-apple-system` / `sans-serif`

### 3.2 版面黄金比例
- **HTML 版心最大宽**：`48rem`（约 768px，居中自适应两翼留白）
- **行高与行距**：中文行高 `1.85`，段落缩进 `2em`；英文行高 `1.65`，段前留白 `0.3em`，段后留白 `1.2em`
- **首字下沉（Drop Cap）**：每章起始第一段应用 `3.2em` 陶土橙衬线大号首字

---

## 四、 移动端 EPUB 防撕裂与出版级规范 (EPUB Anti-Tearing Standards)

在将 HTML 编译为移动端 EPUB 时，必须强制注入以下防撕裂与排版保护规则：

```css
/* 标题防孤立：禁止标题出现在页底而正文在下一页 */
.chapter-nav--start, .subsection-title, h1, h2, h3 {
    page-break-after: avoid;
    break-after: avoid;
}

/* 卡片与媒体防截断：禁止一张卡片被翻页截成两截 */
.rebook-card, .rhetoric-note, .knowledge-note, .photo-container, figure, table {
    page-break-inside: avoid;
    break-inside: avoid;
}

/* 全局透明底色：完美兼容黑夜/护眼绿/羊皮纸模式 */
body {
    background-color: transparent !important;
}
```

---

## 五、 多模态 AIGC 视觉体系规范 (AIGC Visual System)

1. **终极典藏封面**：纯黑哑光底色 + 晶圆微网格 + 传记核心标识 + 瑞士网格排版，附带 Production Note。
2. **章节全景插画**：**Woodcut & Warm Ink Wash（复古木刻 + 暖色水彩淡彩）**，置于章节起始页头部，与正文历史故事形成呼应。
3. **目录手绘插图**：在导航页面（`nav.xhtml`）嵌入专属手绘插画，强化书籍的典藏仪式感。
