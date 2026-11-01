"""Generate real AI texts for the evaluation corpus (cached in demo/corpus_src/)."""

from __future__ import annotations

from pathlib import Path

from openai import OpenAI

OUT = Path(__file__).parent / "corpus_src"
PROMPTS = {
    "ki_text_bienen.txt": "Schreibe einen sachlichen Absatz (ca. 90 Wörter) auf Deutsch über die Bedeutung von Wildbienen für die Landwirtschaft. Nur den Absatz, ohne Überschrift.",
    "ki_text_fahrrad.txt": "Schreibe einen Absatz (ca. 90 Wörter) auf Deutsch über die Geschichte des Fahrrads, im Stil eines Schulaufsatzes. Nur den Absatz, ohne Überschrift.",
    "ki_text_herbst.txt": "Schreibe einen stimmungsvollen Absatz (ca. 80 Wörter) auf Deutsch über einen Herbstmorgen im Schwarzwald, in der Ich-Form, so als hätte ihn ein Mensch in sein Tagebuch geschrieben. Nur den Absatz.",
    "ki_text_buergergeld.txt": "Schreibe einen kurzen Meinungsbeitrag (ca. 80 Wörter) auf Deutsch für einen Leserbrief zum Thema Tempolimit auf Autobahnen. Nur den Text.",
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    client = OpenAI()
    for name, prompt in PROMPTS.items():
        p = OUT / name
        if p.exists():
            continue
        r = client.chat.completions.create(model="gpt-5-mini", messages=[{"role": "user", "content": prompt}],
                                           max_completion_tokens=4000)
        text = (r.choices[0].message.content or "").strip()
        if not text:
            raise RuntimeError(f"leere Antwort für {name}")
        p.write_text(text + "\n", encoding="utf-8")
        print(name, len(text), "Zeichen")
    # light paraphrase of one AI text (typical evasion step)
    para = OUT / "ki_text_bienen_paraphrasiert.txt"
    if not para.exists():
        src = (OUT / "ki_text_bienen.txt").read_text(encoding="utf-8")
        r = client.chat.completions.create(model="gpt-5-mini", messages=[{"role": "user", "content":
            "Formuliere den folgenden Absatz leicht um, ohne den Inhalt zu ändern. Gib nur den neuen Absatz aus.\n\n" + src}],
            max_completion_tokens=4000)
        para.write_text((r.choices[0].message.content or "").strip() + "\n", encoding="utf-8")
        print(para.name, "erzeugt")


if __name__ == "__main__":
    main()
