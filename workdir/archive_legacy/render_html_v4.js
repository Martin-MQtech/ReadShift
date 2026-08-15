/**
 * ReBook HTML 渲染器 v4
 * - 渲染书籍级排版 HTML
 * - 自动识别 Cheat Sheet 词汇 → interactive-term 高亮
 * - 支持 output/full/ 全量页面
 */
const ejs = require('ejs');
const MarkdownIt = require('markdown-it');
const fs = require('fs');
const path = require('path');

const md = new MarkdownIt({ html: true, linkify: true, typographer: true });

const templatePath = path.join(__dirname, '..', 'src', 'templates', 'template.ejs');
const template = fs.readFileSync(templatePath, 'utf8');

// 收集所有书页（排除索引）
const fullDir = path.join(__dirname, '..', 'output', 'full');
const files = fs.readdirSync(fullDir).filter(f => f.endsWith('.md') && f !== '_INDEX.md').sort();
console.log('Processing pages:', files.join(', '));

let bodyContent = '';
let totalTerms = 0;

for (const file of files) {
    let content = fs.readFileSync(path.join(fullDir, file), 'utf8');
    const lines = content.split('\n');

    // 行遍历提取词条（兼容末尾空格和中文标点）
    const terms = [];
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        const tMatch = line.match(/\*\*(\d+\.\s*[^*]+?)\*\*/);
        if (tMatch && i + 1 < lines.length) {
            const nextLine = lines[i + 1].trim();
            const mMatch = nextLine.match(/^\*中文解释\*[：:]\s*(.+)$/);
            if (mMatch) {
                const term = tMatch[1].replace(/^\d+\.\s*/, '').trim(); // strip "1. "
                const meaning = mMatch[1].trim();
                if (term.length > 2 && term.length < 60) {
                    terms.push({ term, meaning });
                }
            }
        }
    }

    // 处理每一行，只在正文段落中做高亮（跳过表格和标题）
    let resultLines = [];
    let inTable = false;

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];

        if (line.startsWith('|')) {
            inTable = true;
            resultLines.push(line);
            continue;
        }
        if (inTable && line.trim() === '---') {
            inTable = false;
            resultLines.push(line);
            continue;
        }
        if (line.startsWith('#')) {
            inTable = false;
        }

        // 表格行和列表项不做高亮
        if (inTable || line.match(/^(\d+\.|[-*]\s)/)) {
            resultLines.push(line);
            continue;
        }

        // 对正文段落做词条高亮
        let processed = line;
        for (const t of terms) {
            const escaped = t.term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const re = new RegExp('(' + escaped + ')', 'g');
            processed = processed.replace(re, (match) => {
                totalTerms++;
                const safeTerm = t.term.replace(/'/g, "\\'");
                const safeMeaning = t.meaning.replace(/'/g, "\\'");
                return '<span class="interactive-term" data-term="' + safeTerm + '" data-meaning="' + safeMeaning + '">' + match + '</span>';
            });
        }
        resultLines.push(processed);
    }

    bodyContent += resultLines.join('\n') + '\n\n';
    console.log('  ' + file + ': ' + terms.length + ' terms');
}

// Markdown → HTML
const htmlBody = md.render(bodyContent);

const finalHtml = ejs.render(template, {
    title: '张忠谋自传 · Reading Sample',
    body_content: htmlBody,
    current_mode: 'Isaacson Bilingual · DeepSeek V4 Flash',
});

const outDir = path.join(__dirname, '..', 'output');
fs.writeFileSync(path.join(outDir, 'preview_book.html'), finalHtml, 'utf8');
console.log('\n✅ Generated: output/preview_book.html ('
    + files.length + ' pages, '
    + totalTerms + ' interactive terms, '
    + (finalHtml.length / 1024).toFixed(0) + ' KB)');
