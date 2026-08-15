import sys, re

with open('workdir/render_html_v9.js', 'r') as f:
    text = f.read()

# Remove the faulty block
faulty_block = r"""let fullDir = path\.join\(__dirname, '\.\.', 'output', 'full'\);
if \(chapterArg\) \{
    // If chapter 2, use chap-02-哈佛MIT/source
    if \(chapterArg === '2'\) \{
        fullDir = path\.join\(__dirname, '\.\.', 'output', 'chapters', 'chap-02-哈佛MIT', 'source'\);
    \}
\}
const files = fs\.readdirSync\(fullDir\)\.filter\(f => f\.endsWith\('\.md'\) && f !== '_INDEX\.md'\)\.sort\(\);"""

text = re.sub(faulty_block, "", text, flags=re.DOTALL)

# Insert after chapterArg extraction
replace_insert = """const chapterArg = argVal('--chapter', '');
let fullDir = path.join(__dirname, '..', 'output', 'full');
if (chapterArg === '2') {
    fullDir = path.join(__dirname, '..', 'output', 'chapters', 'chap-02-哈佛MIT', 'source');
}
const files = fs.readdirSync(fullDir).filter(f => f.endsWith('.md') && f !== '_INDEX.md').sort();
"""
text = text.replace("const chapterArg = argVal('--chapter', '');", replace_insert)

with open('workdir/render_html_v9.js', 'w') as f:
    f.write(text)
