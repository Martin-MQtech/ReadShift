import sys
with open('workdir/qa_gate_v3.py', 'r') as f:
    text = f.read()

text = text.replace(
    'src in sorted((BASE_DIR / "output" / "full").glob("page_*.md"))',
    'src in sorted(Path(args.source_dir).glob("page_*.md"))' if 'args.source_dir' in text else 'src in sorted(source_dir.glob("page_*.md"))'
)
# We need to change the function signature of audit_sources to accept args
text = text.replace('def audit_sources(report):', 'def audit_sources(report, source_dir):')
text = text.replace('src in sorted((BASE_DIR / "output" / "full").glob("page_*.md")):', 'src in sorted(source_dir.glob("page_*.md")):')
text = text.replace('audit_sources(report)', 'audit_sources(report, Path(args.source_dir) if args.source_dir else BASE_DIR / "output" / "full")')

if 'ap.add_argument("--source-dir"' not in text:
    text = text.replace('ap.add_argument("--skip-sources"', 'ap.add_argument("--source-dir", help="指定源文件目录")\n    ap.add_argument("--skip-sources"')

with open('workdir/qa_gate_v3.py', 'w') as f:
    f.write(text)
