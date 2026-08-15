#!/usr/bin/env python3
"""
ReadShift 有声书 TTS 生成脚本（v3 · 双层并发：双轨 × 段级）

用法:
    python3 make_tts.py                # 双轨并行，每轨默认 4 worker 段级并行
    python3 make_tts.py zh             # 只合成中文
    python3 make_tts.py zh 6           # 单轨，6 worker 段级并行
    python3 make_tts.py en 8           # 单轨，8 worker

读取对应文字稿, 跳过标题/音效/注释行, 段级并发 edge-tts 合成, 段间插入静音后按序拼接。
v2: 双轨并行（线程池，临时目录按语言隔离）。
v3: 段级并行——每轨内段落多 worker 并发合成，总耗时进一步下降。
    注意: edge-tts 为免费在线接口, worker 过高可能触发限流; 脚本内置 4 次退避重试兜底。
"""
import re
import subprocess
import sys
import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.abspath(__file__))

VOICES = {
    "zh": "zh-CN-YunjianNeural",      # 沉稳男声
    "en": "en-US-ChristopherNeural",  # 沉稳美音男声
}
FILES = {
    "zh": os.path.join(BASE, "中文文字稿.md"),
    "en": os.path.join(BASE, "英文文字稿.md"),
}
OUT = {
    "zh": os.path.join(BASE, "中文音频.mp3"),
    "en": os.path.join(BASE, "英文音频.mp3"),
}
PAUSE = 0.7  # 段间静音秒数
DEFAULT_WORKERS = 4  # 每轨段级并发的 worker 数


def clean_segments(text: str):
    """提取可朗读段落, 去掉标题/音效/引用/分隔线; 清理 markdown 符号。"""
    lines = text.splitlines()
    segs = []
    cur = []
    for line in lines:
        s = line.strip()
        # 跳过标题/引用/分隔线/音效标记(中文【】与英文 [SFX]/[Narrator])
        if re.match(r"^#{1,6}\s", s):
            continue
        if s.startswith(">"):
            continue
        if re.match(r"^-{3,}$", s):
            continue
        if re.match(r"^【|^\[SFX|^\[Main\s+narrator|^\[Narrator|^\[主叙述者", s):
            continue
        if not s:
            if cur:
                segs.append(" ".join(cur))
                cur = []
            continue
        cur.append(s)
    if cur:
        segs.append(" ".join(cur))
    out = []
    for s in segs:
        s = s.replace("**", "").replace("__", "")
        s = re.sub(r"\s+", " ", s).strip()
        if s:
            out.append(s)
    return out


def tts(text: str, voice: str, out_path: str):
    for attempt in range(4):
        try:
            subprocess.run(
                ["edge-tts", "--voice", voice, "--text", text, "--write-media", out_path],
                check=True, capture_output=True,
            )
            return
        except subprocess.CalledProcessError:
            if attempt == 3:
                raise
            time.sleep(2 + attempt * 2)


def silence(seconds: float, out_path: str, sr: int = 24000):
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r={sr}:cl=mono",
         "-t", f"{seconds}", "-q:a", "4", out_path],
        check=True, capture_output=True,
    )


def concat(parts, out_path, work):
    with open(os.path.join(work, "list.txt"), "w") as f:
        for p in parts:
            f.write(f"file '{os.path.abspath(p)}'\n")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i",
         os.path.join(work, "list.txt"), "-c:a", "libmp3lame", "-q:a", "3", out_path],
        check=True, capture_output=True,
    )


def synthesize(lang: str, workers: int = DEFAULT_WORKERS):
    """合成单轨音频; 段级并行, 临时目录按语言隔离, 供双轨并行调用。"""
    if lang not in VOICES:
        raise SystemExit("lang must be zh or en")
    work = os.path.join(BASE, f"_tmp_audio_{lang}")
    os.makedirs(work, exist_ok=True)
    text = open(FILES[lang], encoding="utf-8").read()
    segs = clean_segments(text)
    n = len(segs)
    print(f"[{lang}] 提取 {n} 个朗读段落, {workers} worker 段级并行", flush=True)

    # 预先合成段间静音（所有段共用）
    sil = os.path.join(work, "pause.mp3")
    silence(PAUSE, sil)

    # 段级并发合成, 保持顺序
    def synth_one(idx_seg):
        i, seg = idx_seg
        p = os.path.join(work, f"seg_{i:03d}.mp3")
        tts(seg, VOICES[lang], p)
        return p

    with ThreadPoolExecutor(max_workers=workers) as pool:
        paths = list(pool.map(synth_one, enumerate(segs, 1)))

    parts = []
    for p in paths:
        parts.append(p)
        parts.append(sil)
    print(f"[{lang}] 拼接 {len(parts)} 个片段 -> {OUT[lang]}", flush=True)
    concat(parts, OUT[lang], work)
    dur = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", OUT[lang]],
        capture_output=True, text=True,
    ).stdout.strip()
    print(f"[{lang}] 完成: {OUT[lang]}  时长 {float(dur):.1f}s", flush=True)
    shutil.rmtree(work, ignore_errors=True)


def main():
    args = sys.argv[1:]
    lang = args[0] if args and args[0] in ("zh", "en") else None
    workers = DEFAULT_WORKERS
    if lang and len(args) > 1:
        workers = int(args[1])
    elif not lang and len(args) > 0:
        workers = int(args[0])

    if lang:
        synthesize(lang, workers)
    else:
        # 无参数: 中英双轨并行, 每轨再段级并行
        t0 = time.time()
        print(f"== 双层并发: 双轨并行 × 每轨 {workers} worker ==", flush=True)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(synthesize, l, workers) for l in ("zh", "en")]
            for f in futures:
                f.result()
        print(f"== 双轨完成, 总耗时 {time.time() - t0:.1f}s ==", flush=True)


if __name__ == "__main__":
    main()
