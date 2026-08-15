/**
 * ReBook HTML 渲染器 v6
 * - 渲染书籍级排版 HTML
 * - 兼容三种词条格式
 * - 自动修正 markdown-it 转义问题
 * - 中文段落首行缩进 2 字符（em）
 */
const ejs = require('ejs');
const MarkdownIt = require('markdown-it');
const fs = require('fs');
const path = require('path');

const md = new MarkdownIt({ html: true, linkify: true, typographer: true });

const templatePath = path.join(__dirname, '..', 'src', 'templates', 'template.ejs');
const template = fs.readFileSync(templatePath, 'utf8');

const fullDir = path.join(__dirname, '..', 'output', 'full');
const files = fs.readdirSync(fullDir).filter(f => f.endsWith('.md') && f !== '_INDEX.md').sort();
console.log('Pages:', files.join(', '));

let bodyContent = '';
let totalTerms = 0;

function extractTerms(content) {
    const lines = content.split('\n');
    const terms = [];
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        // Format 1: **1. term**  \n *中文解释*：...
        const f1 = line.match(/^\*\*(?:\d+\.\s*)([^*]+?)\*\*$/);
        if (f1 && i+1 < lines.length) {
            const m = lines[i+1].trim().match(/^\*中文解释\*[：:]\s*(.+)$/);
            if (m) terms.push({ term: f1[1].replace(/^\d+\.\s*/, '').trim(), meaning: m[1].trim() });
            continue;
        }
        // Format 2: 1. **term**  \n **中文解释**：...
        const f2 = line.match(/^(\d+\.*)\s*\*\*([^*]+?)\*\*/);
        if (f2 && i+1 < lines.length) {
            const m = lines[i+1].trim().match(/^\*\*中文解释\*\*[：:]\s*(.+)$/);
            if (m) terms.push({ term: f2[2].trim(), meaning: m[1].trim() });
            continue;
        }
        // Format 3: table | **term** | ...
        const f3 = line.match(/^\|\s*\*\*([^*]+?)\*\*\s*\|/);
        if (f3 && i+1 < lines.length && lines[i+1].trim().match(/^\|[-:\s|]+\|/)) {
            let j = i + 2;
            while (j < lines.length && lines[j].trim().match(/^\|[-:\s|]+\|/)) j++;
            if (j < lines.length) {
                const m = lines[j].trim().match(/^\|[^|]*\*\*([^*]+?)\*\*/);
                if (m) terms.push({ term: f3[1].trim(), meaning: m[1].trim() });
            }
            continue;
        }
    }
    return terms;
}

for (const file of files) {
    let content = fs.readFileSync(path.join(fullDir, file), 'utf8');
    const terms = extractTerms(content);

    // 处理每一行：只在正文段落中做词条高亮，添加中文首行缩进
    const lines = content.split('\n');
    const resultLines = [];
    let inTable = false;
    let inTermSection = false; // 是否在 Cheat Sheet 区域

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];

        if (line.startsWith('|')) { inTable = true; resultLines.push(line); continue; }
        if (inTable && line.trim() === '---') { inTable = false; resultLines.push(line); continue; }
        if (line.startsWith('#') || line.startsWith('##') || line.startsWith('###')) { inTable = false; }

        // 检测 Cheat Sheet 区域
        if (/Cheat Sheet|商业语汇|知识萃取/.test(line)) { inTermSection = true; }
        if (line.startsWith('<!-- PROCESSED -->')) { inTermSection = false; }
        if (line.startsWith('---') && !line.startsWith('|')) { /* separator */ }

        // 表格行和列表项不做高亮和缩进
        if (inTable || inTermSection || line.match(/^(\d+\.|[-*]\s)/)) {
            resultLines.push(line);
            continue;
        }

        // 对正文段落做词条高亮 + 中文首行缩进
        let processed = line;

        // 高亮词条
        for (const t of terms) {
            const escaped = t.term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const re = new RegExp('(' + escaped + ')', 'g');
            processed = processed.replace(re, (match) => {
                totalTerms++;
                // 用单引号避免双引号与markdown-it冲突导致转义
                return "<span class='interactive-term' data-term='" + t.term.replace(/'/g,"\\'") + "' data-meaning='" + t.meaning.replace(/'/g,"\\'") + "'>" + match + "</span>";
            });
        }

        // 中文段落首行缩进 2em
        // 检测是否包含中文字符
        if (/[\u4e00-\u9fff]/.test(processed) && !processed.startsWith('<')) {
            processed = '<span class="cn-indent">' + processed + '</span>';
        }

        resultLines.push(processed);
    }

    bodyContent += resultLines.join('\n') + '\n\n';
    console.log('  ' + file + ': ' + terms.length + ' terms');
}

const htmlBody = md.render(bodyContent);

// 修复 markdown-it 可能转义的 span 标签
const fixedHtml = htmlBody.replace(/&lt;span class=['"]interactive-term['"]/g, '<span class="interactive-term">');

const finalHtml = ejs.render(template, {
    title: '张忠谋自传 · Reading Sample',
    body_content: fixedHtml,
    current_mode: 'DeepSeek V4 + Agnes 2.5 Flash',
});

const outDir = path.join(__dirname, '..', 'output');
fs.writeFileSync(path.join(outDir, 'preview_book.html'), finalHtml, 'utf8');
console.log('\n✅ ' + path.join(outDir, 'preview_book.html')
    + ' (' + files.length + ' pages, ' + totalTerms + ' terms, ' + (finalHtml.length/1024).toFixed(0) + ' KB)');
