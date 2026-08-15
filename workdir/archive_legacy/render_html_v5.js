/**
 * ReBook HTML 渲染器 v5
 * - 渲染书籍级排版 HTML
 * - 自动识别 Cheat Sheet 词汇 → interactive-term 高亮
 * - 兼容三种词条格式：
 *   1. **1. term**\n*中文解释*：...  (page_017 风格)
 *   2. 1. **term**\n**中文解释**：...  (page_016 风格)
 *   3. | **term** | 释义 | 造句 |  (page_018 表格风格)
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
console.log('Processing pages:', files.join(', '));

let bodyContent = '';
let totalTerms = 0;

function extractTermsFromContent(content) {
    const terms = [];
    const lines = content.split('\n');

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();

        // Format 1: **1. term**  \n *中文解释*：...
        const f1Match = line.match(/^\*\*(?:\d+\.\s*)([^*]+?)\*\*$/);
        if (f1Match && i + 1 < lines.length) {
            const nextLine = lines[i + 1].trim();
            const mMatch = nextLine.match(/^\*中文解释\*[：:]\s*(.+)$/);
            if (mMatch) {
                terms.push({ term: f1Match[1].replace(/^\d+\.\s*/, '').trim(), meaning: mMatch[1].trim() });
            }
            continue;
        }

        // Format 2: 1. **term**  \n **中文解释**：...
        const f2Match = line.match(/^(\d+\.*)\s*\*\*([^*]+?)\*\*/);
        if (f2Match && i + 1 < lines.length) {
            const nextLine = lines[i + 1].trim();
            const mMatch = nextLine.match(/^\*\*中文解释\*\*[：:]\s*(.+)$/);
            if (mMatch) {
                terms.push({ term: f2Match[2].trim(), meaning: mMatch[1].trim() });
            }
            continue;
        }

        // Format 3: Table row | **term** | meaning | sentence |
        const f3Match = line.match(/^\|+\s*\*\*([^*]+?)\*\*\s*\|/);
        if (f3Match && i + 1 < lines.length && lines[i + 1].trim().match(/^\|[-:\s|]+\|/)) {
            // This is a table row, find the meaning in the next non-separator row
            let j = i + 2;
            while (j < lines.length && lines[j].trim().match(/^\|[-:\s|]+\|/)) j++;
            if (j < lines.length) {
                const meaningMatch = lines[j].trim().match(/^\|[^|]*\*\*([^*]+?)\*\*/);
                if (meaningMatch) {
                    terms.push({ term: f3Match[1].trim(), meaning: meaningMatch[1].trim() });
                }
            }
            continue;
        }
    }

    return terms;
}

for (const file of files) {
    let content = fs.readFileSync(path.join(fullDir, file), 'utf8');
    const terms = extractTermsFromContent(content);

    // Process each line: highlight terms in body text, skip tables/headers/lists
    let resultLines = [];
    let inTable = false;

    for (let i = 0; i < content.split('\n').length; i++) {
        const line = content.split('\n')[i];

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

        // Skip tables and list items for highlighting
        if (inTable || line.match(/^(\d+\.|[-*]\s)/)) {
            resultLines.push(line);
            continue;
        }

        // Highlight terms in body paragraphs
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
