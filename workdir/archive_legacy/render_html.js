/**
 * ReBook HTML 渲染器 v2
 * - 渲染双语书页
 * - 自动识别 Cheat Sheet 中的词汇，转换为可点击的 interactive-term
 */
const ejs = require('ejs');
const MarkdownIt = require('markdown-it');
const fs = require('fs');
const path = require('path');

const md = new MarkdownIt({ html: true, linkify: true, typographer: true });

const templatePath = path.join(__dirname, '..', 'src', 'templates', 'template.ejs');
const template = fs.readFileSync(templatePath, 'utf8');

// 收集所有书页
const previewDir = path.join(__dirname, '..', 'output', 'preview');
const files = fs.readdirSync(previewDir).filter(f => f.endsWith('.md')).sort();

let bodyContent = '';
let termsCount = 0;
for (const file of files) {
    let content = fs.readFileSync(path.join(previewDir, file), 'utf8');
    
    // 提取 Cheat Sheet 词条: **Word/Phrase**: 中文解释
    const terms = [];
    const termRegex = /\*\*([^*\n]+)\*\*[:：]\s*([^\n(]+)/g;
    let m;
    while ((m = termRegex.exec(content)) !== null) {
        if (m[1].length > 2 && m[1].length < 40) {
            terms.push({ term: m[1].trim(), meaning: m[2].trim() });
        }
    }
    
    // 将正文中出现的词条转换为 interactive-term (跳过表头等)
    for (const t of terms) {
        const escaped = t.term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const re = new RegExp(`(?<![\\w])(${escaped})(?![\\w])`, 'g');
        content = content.replace(re, (match) => {
            return `<span class="interactive-term" @click="slideOverOpen=true; activeTerm='${t.term.replace(/'/g, "\\'")}'; activeMeaning='${t.meaning.replace(/'/g, "\\'")}'; activeContext='知识卡片：${t.term}（${t.meaning}）—— 点击查看完整背景。'">${match}</span>`;
        });
    }
    
    bodyContent += content + '\n\n';
    termsCount += termsCount;
}

const html = ejs.render(template, {
    title: '张忠谋自传 · 序言精读',
    body_content: bodyContent,
    current_mode: 'The Isaacson Mode · DeepSeek V4 Flash',
});

const outDir = path.join(__dirname, '..', 'output');
const outFile = path.join(outDir, 'preview_book.html');
fs.writeFileSync(outFile, html, 'utf8');
console.log(`✅ 已生成: output/preview_book.html (${files.length} 页, ${(html.length/1024).toFixed(0)} KB, ${termsCount} 个互动词)`);
