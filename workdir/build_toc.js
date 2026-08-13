/**
 * ReBook 出版级可点击目录与装配脚本 (v10)
 * - 打造完美的 Table of Contents 卡片组件（虚线对齐、锚点跳转、作者标注）
 * - 彻底物理切除 page_007.md 中的所有盗版广告水文
 * - 彻底修复 # 源码泄露问题，确保 Markdown 解析 100% 正确
 */

const ejs = require('ejs');
const MarkdownIt = require('markdown-it');
const fs = require('fs');
const path = require('path');

const md = new MarkdownIt({ html: true, linkify: true, typographer: true });

const fullDir = path.join(__dirname, '..', 'output', 'full');

// 1. 彻底清除 page_007.md 中的广告水文
const page7Path = path.join(fullDir, 'page_007.md');
if (fs.existsSync(page7Path)) {
    let p7 = fs.readFileSync(page7Path, 'utf8');
    // 物理切除盗版广告声明
    p7 = p7.replace(/本書僅供個人學習之用[^\n]+\n?/g, '')
           .replace(/如對本書有興[^\n]+\n?/g, '')
           .replace(/任何對本書籍[^\n]+\n?/g, '')
           .replace(/本書由“行行”整理[^\n]+\n?/g, '')
           .replace(/如果你不知道讀什麼書[^\n]+\n?/g, '')
           .replace(/小編微信或QQ[^\n]+\n?/g, '')
           .replace(/清福的味道[^\n]+\n?/g, '')
           .replace(/周讀[^\n]+\n?/g, '')
           .replace(/網址：www.ireadweek.com[^\n]+\n?/g, '');
    fs.writeFileSync(page7Path, p7, 'utf8');
}

// 2. 彻底重构 page_003.md 为精美出版级可点击目录
const page3Path = path.join(fullDir, 'page_003.md');
const tocMarkdown = `<div class="toc-card">
  <div class="toc-card__header">
    <span class="toc-card__eyebrow">TABLE OF CONTENTS</span>
    <h2 class="toc-card__title">目 录</h2>
    <div class="ornament" style="margin: 1rem auto 0; max-width: 120px;">✦</div>
  </div>
  <ul class="toc-card__list">
    <li class="toc-card__item">
      <a href="#sec-yu-preface" class="toc-card__link">
        <span class="toc-card__name">推荐序一：为历史留下记录</span>
        <span class="toc-card__dots"></span>
        <span class="toc-card__info">余秋雨 撰</span>
      </a>
    </li>
    <li class="toc-card__item">
      <a href="#sec-gao-preface" class="toc-card__link">
        <span class="toc-card__name">推荐序二：出版企业家传记与回忆录的用心</span>
        <span class="toc-card__dots"></span>
        <span class="toc-card__info">高希均 撰</span>
      </a>
    </li>
    <li class="toc-card__item">
      <a href="#sec-self-preface" class="toc-card__link">
        <span class="toc-card__name">作者自序：那是一个多么不同的时代！</span>
        <span class="toc-card__dots"></span>
        <span class="toc-card__info">张忠谋 自撰</span>
      </a>
    </li>
    <li class="toc-card__item">
      <a href="#chap-1" class="toc-card__link">
        <span class="toc-card__name">第一章 “大时代”中的幼少年</span>
        <span class="toc-card__dots"></span>
        <span class="toc-card__info">第 21 页</span>
      </a>
    </li>
    <li class="toc-card__item">
      <a href="#chap-2" class="toc-card__link">
        <span class="toc-card__name">第二章 哈佛大学与麻省理工</span>
        <span class="toc-card__dots"></span>
        <span class="toc-card__info">第 46 页</span>
      </a>
    </li>
    <li class="toc-card__item">
      <a href="#chap-3" class="toc-card__link">
        <span class="toc-card__name">第三章 进入半导体业</span>
        <span class="toc-card__dots"></span>
        <span class="toc-card__info">第 64 页</span>
      </a>
    </li>
    <li class="toc-card__item">
      <a href="#chap-4" class="toc-card__link">
        <span class="toc-card__name">第四章 初试啼声</span>
        <span class="toc-card__dots"></span>
        <span class="toc-card__info">第 78 页</span>
      </a>
    </li>
    <li class="toc-card__item">
      <a href="#chap-5" class="toc-card__link">
        <span class="toc-card__name">第五章 重拎书包</span>
        <span class="toc-card__dots"></span>
        <span class="toc-card__info">第 93 页</span>
      </a>
    </li>
    <li class="toc-card__item">
      <a href="#sec-appendix" class="toc-card__link">
        <span class="toc-card__name">附录与张忠谋大事年表</span>
        <span class="toc-card__dots"></span>
        <span class="toc-card__info">第 101 页</span>
      </a>
    </li>
  </ul>
</div>

<!-- PROCESSED -->
`;
fs.writeFileSync(page3Path, tocMarkdown, 'utf8');

// 3. 为关键章节注入对应的 HTML id 锚点
const anchorMap = {
    'page_007.md': '<div id="sec-yu-preface" class="preface-card"><span class="preface-badge">推荐序一 · 专家特邀序</span><h2>为历史留下记录</h2><p class="author-byline">余秋雨 撰</p></div>\n\n',
    'page_012.md': '<div id="sec-gao-preface" class="preface-card"><span class="preface-badge">推荐序二 · 出版人致辞</span><h2>出版企业家传记与回忆录的用心</h2><p class="author-byline">高希均 撰</p></div>\n\n',
    'page_014.md': '<div id="sec-self-preface" class="preface-card"><span class="preface-badge">作者自序</span><h2>那是一个多么不同的时代！</h2><p class="author-byline">张忠谋 自撰</p></div>\n\n',
    'page_021.md': '<div id="chap-1" class="preface-card" style="background:#faf8f3;border-color:var(--accent-soft);"><span class="preface-badge">第一章正文</span><h2>“大时代”中的幼少年</h2><p class="author-byline">张忠谋 著</p></div>\n\n',
    'page_046.md': '<div id="chap-2" class="preface-card" style="background:#faf8f3;border-color:var(--accent-soft);"><span class="preface-badge">第二章正文</span><h2>哈佛大学与麻省理工</h2><p class="author-byline">张忠谋 著</p></div>\n\n',
    'page_064.md': '<div id="chap-3" class="preface-card" style="background:#faf8f3;border-color:var(--accent-soft);"><span class="preface-badge">第三章正文</span><h2>进入半导体业</h2><p class="author-byline">张忠谋 著</p></div>\n\n',
    'page_078.md': '<div id="chap-4" class="preface-card" style="background:#faf8f3;border-color:var(--accent-soft);"><span class="preface-badge">第四章正文</span><h2>初试啼声</h2><p class="author-byline">张忠谋 著</p></div>\n\n',
    'page_093.md': '<div id="chap-5" class="preface-card" style="background:#faf8f3;border-color:var(--accent-soft);"><span class="preface-badge">第五章正文</span><h2>重拎书包</h2><p class="author-byline">张忠谋 著</p></div>\n\n',
    'page_101.md': '<div id="sec-appendix" class="preface-card"><span class="preface-badge">附录与大事年表</span><h2>张忠谋大事年表 (1931-1998)</h2><p class="author-byline">张忠谋 著</p></div>\n\n',
};

for (const [fname, anchorHtml] of Object.entries(anchorMap)) {
    const fpath = path.join(fullDir, fname);
    if (fs.existsSync(fpath)) {
        let content = fs.readFileSync(fpath, 'utf8');
        // 抹除多余的旧标题
        content = content.replace(/^# [^\n]+\n+/g, '').replace(/### [^\n]+ 撰\n+/g, '');
        if (!content.includes('id=')) {
            content = anchorHtml + content;
            fs.writeFileSync(fpath, content, 'utf8');
        }
    }
}

// 4. 调用主渲染逻辑
require('./render_html_v8.js');
console.log('✅ 出版级可点击目录与锚点集成完成！');
