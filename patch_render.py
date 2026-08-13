import sys, re

with open('workdir/render_html_v9.js', 'r') as f:
    text = f.read()

# Add --chapter logic
if '--chapter' not in text:
    text = text.replace(
        "const outFileArg = argVal('--out', '');",
        "const outFileArg = argVal('--out', '');\nconst chapterArg = argVal('--chapter', '');"
    )
    
    replace_fullDir = """
let fullDir = path.join(__dirname, '..', 'output', 'full');
if (chapterArg) {
    // If chapter 2, use chap-02-哈佛MIT/source
    if (chapterArg === '2') {
        fullDir = path.join(__dirname, '..', 'output', 'chapters', 'chap-02-哈佛MIT', 'source');
    }
}
const files = fs.readdirSync(fullDir).filter(f => f.endsWith('.md') && f !== '_INDEX.md').sort();
"""
    text = re.sub(r'const fullDir = path\.join\(__dirname, \'\.\.\', \'output\', \'full\'\);\nconst files = fs\.readdirSync\(fullDir\)\.filter.+?sort\(\);\n', replace_fullDir, text, flags=re.DOTALL)
    
    replace_outPath = """
let outPath = outFileArg
    ? path.resolve(process.cwd(), outFileArg)
    : path.join(__dirname, '..', 'output', 'preview_book.html');
if (!outFileArg && chapterArg === '2') {
    outPath = path.join(__dirname, '..', 'output', 'chapters', 'chap-02-哈佛MIT', '第二章-Chapter-2.html');
}
"""
    text = re.sub(r'const outPath = outFileArg\s*\n\s*\? path\.resolve\(process\.cwd\(\), outFileArg\)\n\s*: path\.join\(__dirname, \'\.\.\', \'output\', \'preview_book\.html\'\);', replace_outPath, text, flags=re.DOTALL)

with open('workdir/render_html_v9.js', 'w') as f:
    f.write(text)
