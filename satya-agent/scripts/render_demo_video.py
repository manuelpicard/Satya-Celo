#!/usr/bin/env python3
"""Assemble a short, real-UI Satya demo from record_demo.py output."""
from __future__ import annotations

import math
import os
import subprocess
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(os.environ.get("SATYA_DEMO_DIR", Path(__file__).resolve().parents[1] / "demo-video"))
RAW = OUT / "satya-demo-raw.webm"
REGISTER = OUT / "register-result.png"
WORK = OUT / "render_work"
FINAL = OUT / "satya-demo.mp4"
FPS = 25
W, H = 1280, 720
BG = (243, 246, 236)
GREEN = (31, 72, 49)
ACCENT = (159, 213, 85)
DARK = (26, 39, 29)
MUTED = (101, 116, 96)


def ffmpeg(args: list[str]) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def font(bold: bool, size: int) -> ImageFont.FreeTypeFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    for path in [f"/usr/share/fonts/truetype/dejavu/{name}", f"/usr/share/fonts/truetype/liberation2/{name}"]:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def fit_crop(img: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    x0, y0, x1, y1 = box
    return img.crop(box).resize((x1 - x0, y1 - y0), Image.Resampling.LANCZOS)


def create_cards() -> tuple[Path, Path]:
    if not REGISTER.exists():
        raise FileNotFoundError(f"Live-Register-Standbild fehlt: {REGISTER}")
    source = Image.open(REGISTER).convert("RGB")
    card = fit_crop(source, (640, 490, 1214, 1125))

    opening = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(opening)
    # quiet frame and brand mark
    d.rounded_rectangle((45, 36, 1235, 684), radius=24, outline=(225, 231, 216), width=2)
    d.ellipse((75, 68, 121, 114), fill=ACCENT)
    d.text((87, 72), "S", font=font(True, 28), fill=GREEN)
    d.text((135, 71), "satya.", font=font(True, 31), fill=DARK)
    d.text((75, 154), "CONTENT PROVENANCE · LIVE AUF CELO", font=font(True, 12), fill=MUTED)
    d.multiline_text((75, 204), "Eine Aussage.\nOn-chain prüfbar.", font=font(True, 48), fill=DARK, spacing=8)
    d.rounded_rectangle((75, 365, 540, 422), radius=12, fill=(232, 240, 219))
    d.ellipse((93, 381, 122, 410), fill=ACCENT)
    d.text((101, 383), "✓", font=font(True, 20), fill=GREEN)
    d.text((136, 381), "1 aktive Registererklärung", font=font(True, 17), fill=GREEN)
    d.text((75, 451), "Als KI-generiert erklärt —", font=font(True, 18), fill=GREEN)
    d.text((75, 480), "kein unabhängiger Herkunftsbeweis.", font=font(False, 16), fill=MUTED)
    d.line((75, 552, 540, 552), fill=(214, 222, 204), width=2)
    d.text((75, 573), "CELO SEPOLIA  ·  TESTNET", font=font(True, 12), fill=MUTED)

    # Rounded screenshot crop from the actual live app.
    x, y, cw, ch = 618, 47, 590, 626
    d.rounded_rectangle((x + 8, y + 10, x + cw + 8, y + ch + 10), radius=18, fill=(221, 226, 216))
    mask = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, cw - 1, ch - 1), radius=18, fill=255)
    crop = card.resize((cw, ch), Image.Resampling.LANCZOS)
    opening.paste(crop, (x, y), mask)
    opening_path = OUT / "satya-demo-opening.png"
    opening.save(opening_path)

    closing = Image.new("RGB", (W, H), BG)
    cd = ImageDraw.Draw(closing)
    cd.rectangle((0, 0, W, 12), fill=ACCENT)
    cd.rounded_rectangle((75, 78, 1205, 642), radius=22, fill=(250, 251, 247), outline=(225, 231, 216), width=2)
    cd.rounded_rectangle((75, 78, 92, 642), radius=8, fill=ACCENT)
    cd.ellipse((135, 145, 201, 211), fill=ACCENT)
    cd.text((151, 150), "S", font=font(True, 40), fill=GREEN)
    cd.text((225, 148), "satya.", font=font(True, 47), fill=DARK)
    cd.multiline_text((135, 263), "Herkunft prüfen.\nNicht raten.", font=font(True, 48), fill=DARK, spacing=8)
    cd.text((135, 398), "Live-Demo · Celo Sepolia · Testnet", font=font(False, 20), fill=GREEN)
    cd.line((135, 451, 1135, 451), fill=(222, 229, 212), width=2)
    cd.text((135, 482), "SELF AGENT ID  ·  CELO SEPOLIA  ·  x402 TESTNET", font=font(True, 13), fill=GREEN)
    cd.text((135, 526), "Test-USDC · keine Mainnet-Zahlung · Wallet-Freigabe bleibt beim Nutzer", font=font(False, 14), fill=MUTED)
    cd.text((135, 575), "Prototyp-Demo · keine Aussage ist ein unabhängiger Herkunftsbeweis", font=font(False, 14), fill=MUTED)
    closing_path = OUT / "satya-demo-outro.png"
    closing.save(closing_path)
    return opening_path, closing_path


def encode_still(image: Path, output: Path, duration: float) -> None:
    ffmpeg([
        "-loop", "1", "-framerate", str(FPS), "-i", str(image),
        "-vf", f"zoompan=z='min(zoom+0.00035,1.025)':d=1:s={W}x{H}:fps={FPS},format=yuv420p",
        "-t", str(duration), "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-r", str(FPS), "-movflags", "+faststart", str(output),
    ])


def encode_screen(start: float, duration: float, speed: float, output: Path) -> None:
    ffmpeg([
        "-ss", str(start), "-t", str(duration), "-i", str(RAW),
        "-vf", f"setpts=(PTS-STARTPTS)/{speed},fps={FPS},scale={W}:{H}:flags=lanczos,format=yuv420p",
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", str(FPS),
        "-movflags", "+faststart", str(output),
    ])


def probe_duration(path: Path) -> float:
    value = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)
    ], text=True).strip()
    return float(value)


def stamp(seconds: float) -> str:
    ms = round(seconds * 1000)
    hh, rem = divmod(ms, 3_600_000)
    mm, rem = divmod(rem, 60_000)
    ss, milli = divmod(rem, 1000)
    return f"{hh:02}:{mm:02}:{ss:02},{milli:03}"


def make_srt(path: Path, t_action: float, t_result: float, t_quote: float, t_end: float) -> None:
    blocks = [
        (t_action + 0.1, t_result - 0.15, "Bild lokal gehasht · Live-Abfrage auf Celo Sepolia"),
        (t_result + 0.15, t_quote - 0.2, "1 aktive Aussage im Register · keine Garantie über Herkunft"),
        (t_quote + 0.15, t_end - 0.15, "0,01 Test-USDC · Empfänger vor Wallet-Freigabe sichtbar"),
    ]
    content = "\n\n".join(f"{i}\n{stamp(a)} --> {stamp(b)}\n{text}" for i, (a, b, text) in enumerate(blocks, 1)) + "\n"
    path.write_text(content, encoding="utf-8")


def create_sfx(path: Path, total: float, events: list[tuple[float, str]]) -> None:
    rate = 48_000
    samples = int(rate * total)
    mix = [0.0] * samples

    def tone(at: float, duration: float, frequencies: tuple[float, ...], level: float) -> None:
        begin = int(at * rate)
        count = min(int(duration * rate), samples - begin)
        for n in range(max(0, count)):
            t = n / rate
            attack = min(1.0, t / 0.008)
            release = max(0.0, 1.0 - t / duration)
            envelope = attack * release * release
            sample = sum(math.sin(2 * math.pi * f * t) for f in frequencies) / len(frequencies)
            mix[begin + n] += level * envelope * sample

    for at, kind in events:
        if kind == "click":
            tone(at, 0.045, (1750.0,), 0.18)
        elif kind == "result":
            tone(at, 0.52, (784.0, 988.0, 1175.0), 0.12)
        elif kind == "brand":
            tone(at, 0.72, (659.0, 880.0, 1047.0), 0.10)

    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = bytearray()
        for value in mix:
            s = max(-1.0, min(1.0, value))
            pcm = int(s * 32767).to_bytes(2, "little", signed=True)
            frames.extend(pcm); frames.extend(pcm)
        w.writeframes(frames)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True); WORK.mkdir(parents=True, exist_ok=True)
    if not RAW.exists(): raise FileNotFoundError(f"Rohvideo fehlt: {RAW}")
    opening, closing = create_cards()
    segments = [WORK / f"segment-{n}.mp4" for n in range(5)]
    encode_still(opening, segments[0], 2.0)
    encode_screen(1.35, 5.5, 1.35, segments[1])
    encode_screen(7.5, 4.4, 1.0, segments[2])
    encode_screen(12.8, 3.15, 1.0, segments[3])
    encode_still(closing, segments[4], 3.0)

    durations = [probe_duration(p) for p in segments]
    starts = [0.0]
    for d in durations[:-1]: starts.append(starts[-1] + d)
    action_start, result_start, quote_start, end_start = starts[1], starts[2], starts[3], starts[4]
    total = sum(durations)
    srt = OUT / "satya-demo.de.srt"
    make_srt(srt, action_start, result_start, quote_start, end_start)
    audio = WORK / "ui-sfx.wav"
    create_sfx(audio, total, [
        (action_start + 0.25, "click"),
        (result_start + 0.2, "result"),
        (quote_start + 0.25, "click"),
        (end_start + 0.2, "brand"),
    ])

    inputs: list[str] = []
    for p in segments: inputs += ["-i", str(p)]
    inputs += ["-i", str(audio)]
    concat = "".join(f"[{i}:v]" for i in range(5))
    vf = f"{concat}concat=n=5:v=1:a=0,format=yuv420p[v]"
    ffmpeg([
        *inputs, "-filter_complex", vf, "-map", "[v]", "-map", "5:a:0",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
        "-shortest", "-movflags", "+faststart", str(FINAL),
    ])
    poster = OUT / "satya-demo-poster.png"
    Image.open(opening).save(poster)
    print(f"Video: {FINAL}")
    print(f"Duration: {probe_duration(FINAL):.2f}s | 1280x720 | 25 fps | MP4/H.264 + AAC UI-SFX")
    print(f"Optional German subtitles: {srt}")

if __name__ == "__main__":
    main()
