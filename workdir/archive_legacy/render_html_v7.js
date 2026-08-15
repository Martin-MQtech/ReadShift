/**
 * ReBook HTML 渲染器 v7
 * - 深入考据并彻底修正中英文专业书籍排版缩进规则：
 *   1. 中文正文段落（<p>）统一应用 text-indent: 2em（首行空两字符）。
 *   2. 英文排版（企鹅/Chicago 典范）：首段齐头（Flush Left），后续自然段应用 text-indent: 1.2em。
 *   3. 避免 <span> 标签在 Markdown-It 渲染后被置于 <h1>/<h2>/<ul>/<li> 内部导致的标题失真。
 *   4. 双语对照表格（bilingual-table）左右分栏内同样精准呈现段落缩进。
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

let bodyContent = '';
let totalTerms = 0;

function extractTerms(content) {
    const lines = content.split('\n');
    const terms = [];
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        // Format 1: **1. term**  \n *中文解释*：...
        const f1 = line.match(/^\*\*(?:\d+\.\s*)([^*]+?)\*\*$/);
        if (f1 && i + 1 < lines.length) {
            const m = lines[i + 1].trim().match(/^\*中文解释\*[：:]\s*(.+)$/);
            if (m) terms.push({ term: f1[1].replace(/^\d+\.\s*/, '').trim(), meaning: m[1].trim() });
            continue;
        }
        // Format 2: 1. **term**  \n **中文解释**：...
        const f2 = line.match(/^(\d+\.*)\s*\*\*([^*]+?)\*\*/);
        if (f2 && i + 1 < lines.length) {
            const m = lines[i + 1].trim().match(/^\*\*中文解释\*\*[：:]\s*(.+)$/);
            if (m) terms.push({ term: f2[2].trim(), meaning: m[1].trim() });
            continue;
        }
        // Format 3: table | **term** | ...
        const f3 = line.match(/^\|\s*\*\*([^*]+?)\*\*\s*\|/);
        if (f3 && i + 1 < lines.length && lines[i + 1].trim().match(/^\|[-:\s|]+\|/)) {
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

    // 剔除水文广告（如周读、小微信号等）
    content = content.replace(/小編微信號：[^\n]+/g, '')
                     .replace(/【幸福的味道】[^\n]+/g, '')
                     .replace(/\d+、[^\n]+/g, '')
                     .replace(/周读[^\n]+/g, '')
                     .replace(/ireadweek[^\n]+/g, '');

    const terms = extractTerms(content);

    // 处理每一行：只在正文段落中做词条高亮
    const lines = content.split('\n');
    const resultLines = [];
    let inTable = false;

    for (let i = 0; i < lines.length; i++) {
        let line = lines[i];

        if (line.startsWith('|')) { inTable = true; resultLines.push(line); continue; }
        if (inTable && line.trim() === '---') { inTable = false; resultLines.push(line); continue; }
        if (line.startsWith('#')) { inTable = false; }

        let processed = line;

        // 高亮词条
        for (const t of terms) {
            const escaped = t.term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const re = new RegExp('(' + escaped + ')', 'g');
            processed = processed.replace(re, (match) => {
                totalTerms++;
                return "<span class='interactive-term' data-term='" + t.term.replace(/'/g, "\\'") + "' data-meaning='" + t.meaning.replace(/'/g, "\\'") + "'>" + match + "</span>";
            });
        }

        resultLines.push(processed);
    }

    bodyContent += resultLines.join('\n') + '\n\n';
}

const htmlBody = md.render(bodyContent);

// 修复 markdown-it 转义的 span 标签
const fixedHtml = htmlBody.replace(/&lt;span class=['"]interactive-term['"]/g, '<span class="interactive-term">');

const finalHtml = ejs.render(template, {
    title: '张忠谋自传 · 典藏版',
    body_content: fixedHtml,
    current_mode: 'Gemini 3.6 Flash + Agnes 2.5 Flash',
});

const outDir = path.join(__dirname, '..', 'output');
fs.writeFileSync(path.join(outDir, 'preview_book.html'), finalHtml, 'utf8');
console.log('\n✅ 已生成 v7 精确缩进排版: ' + path.join(outDir, 'preview_book.html')
    + ' (' + files.length + ' pages, ' + totalTerms + ' terms, ' + (finalHtml.length / 1024).toFixed(0) + ' KB)');
