import sys, re

with open('workdir/qa_gate_v3.py', 'r') as f:
    text = f.read()

if '--chapter' not in text:
    text = text.replace(
        'ap.add_argument("--html"',
        'ap.add_argument("--chapter", help="单章编号（如 2）")\n    ap.add_argument("--html"'
    )
    
    replace_args = """
    if args.chapter == '2':
        args.html = "output/chapters/chap-02-哈佛MIT/第二章-Chapter-2.html"
        args.source_dir = "output/chapters/chap-02-哈佛MIT/source"
"""
    text = text.replace('args = ap.parse_args()', 'args = ap.parse_args()\n' + replace_args)

with open('workdir/qa_gate_v3.py', 'w') as f:
    f.write(text)
