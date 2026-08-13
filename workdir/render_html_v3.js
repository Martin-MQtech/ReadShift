/**
 * ReBook HTML 渲染器 v3
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

// 收集所有书页
const fullDir = path.join(__dirname, '..', 'output', 'full');
const files = fs.readdirSync(fullDir).filter(f => f.endsWith('.md')).sort();
console.log('Processing pages:', files.join(', '));

let bodyContent = '';
let totalTerms = 0;

for (const file of files) {
    let content = fs.readFileSync(path.join(fullDir, file), 'utf8');

    // 提取 Cheat Sheet 词条
    // 实际格式：**1. laying the strategic groundwork**  \n*中文解释*：...  （注意末尾有空格）
    const terms = [];
    const termRegex = /\*\*(?:\d+\.\s*)([^*]+?)\*\*\s*\n\s*\*中文解释\*\*[：:]\s*([^\n]+)/g;
    let m;
    while ((m = termRegex.exec(content)) !== null) {
        const term = m[1].trim();
        const meaning = m[2].trim();
        if (term.length > 2 && term.length < 60) {
            terms.push({ term, meaning });
        }
    }

    // 处理每一行，只在正文段落中做高亮（跳过表格和标题）
    const lines = content.split('\n');
    let resultLines = [];
    let inTable = false;

    for (const line of lines) {
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
        if (line.startsWith('#') || line.startsWith('##') || line.startsWith('###')) {
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
