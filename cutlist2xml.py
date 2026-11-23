#!/usr/bin/env python3
"""Turn a JSON cut list into an FCP7 XML (xmeml v4) timeline.

The XML opens in Adobe Premiere Pro (File > Import), DaVinci Resolve
(File > Import > Timeline) and Final Cut Pro 7, so a script or an AI can
decide the cuts and a human can finish the edit in a real editor.

Usage: python cutlist2xml.py edit.json [-o edit.xml]
"""
import argparse
import json
import sys
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree, indent

__version__ = "0.1.0"


def _el(parent, name, value=None, **attrs):
    e = SubElement(parent, name, attrs)
    if value is not None:
        e.text = str(value)
    return e


def _rate(parent, fps):
    r = _el(parent, "rate")
    _el(r, "timebase", round(fps))
    # 29.97 / 23.976 / 59.94 are written as timebase 30/24/60 with ntsc TRUE
    _el(r, "ntsc", "TRUE" if abs(fps - round(fps)) > 1e-6 else "FALSE")


def _video_format(parent, plan):
    sc = _el(parent, "samplecharacteristics")
    _rate(sc, plan["fps"])
    _el(sc, "width", plan["width"])
    _el(sc, "height", plan["height"])
    _el(sc, "anamorphic", "FALSE")
    _el(sc, "pixelaspectratio", "square")
    _el(sc, "fielddominance", "none")


def _frames(seconds, fps):
    return round(float(seconds) * fps)


def build(plan, base_dir="."):
    """Return the xmeml root Element for a cut-list dict."""
    plan = {"name": "cutlist2xml", "fps": 30, "width": 1920, "height": 1080,
            "overlays": [], "audio": [], **plan}
    fps = float(plan["fps"])
    if fps <= 0:
        raise ValueError("fps must be positive")
    if not plan.get("cuts"):
        raise ValueError("cut list needs at least one entry in 'cuts'")
    base = Path(base_dir)
    files = {}  # path -> file id; FCP7 wants the full <file> once, then references
    file_len = {}

    def path_of(entry, where):
        if "file" not in entry:
            raise ValueError(f"{where}: missing 'file'")
        return (base / entry["file"]).resolve()

    # shortcut: file duration is the furthest frame the plan uses, not probed; editors only need it >= used range
    for kind in ("cuts", "overlays", "audio"):
        for e in plan[kind]:
            p = path_of(e, kind)
            end = _frames(e.get("out", e.get("end", 0)) if kind == "cuts" else
                          e.get("in", 0) + e["end"] - e["start"], fps)
            file_len[p] = max(file_len.get(p, 0), end)

    def clip(track, ident, path, start, end, src_in, media="video", still=False):
        c = _el(track, "clipitem", id=ident)
        _el(c, "name", path.stem)
        _el(c, "enabled", "TRUE")
        _el(c, "duration", file_len[path])
        _rate(c, fps)
        for k, v in (("start", start), ("end", end), ("in", src_in), ("out", src_in + end - start)):
            _el(c, k, v)
        if still:
            _el(c, "alphatype", "straight")
        if path in files:
            _el(c, "file", id=files[path])
        else:
            files[path] = f"file-{len(files) + 1}"
            f = _el(c, "file", id=files[path])
            _el(f, "name", path.name)
            _el(f, "pathurl", path.as_uri())
            _rate(f, fps)
            _el(f, "duration", file_len[path])
            m = _el(f, "media")
            if still:
                _el(f, "stillframe", "TRUE")
                _video_format(_el(m, "video"), plan)
            else:
                _video_format(_el(m, "video"), plan)
                a = _el(m, "audio")
                _el(a, "channelcount", 2)
        if media == "audio":
            src = _el(c, "sourcetrack")
            _el(src, "mediatype", "audio")
            _el(src, "trackindex", 1)
        return c

    root = Element("xmeml", version="4")
    seq = _el(root, "sequence", id="sequence-1")
    _el(seq, "name", plan["name"])
    media = _el(seq, "media")
    video = _el(media, "video")
    _video_format(_el(video, "format"), plan)
    v1 = _el(video, "track")
    audio = _el(media, "audio")
    _el(audio, "numOutputChannels", 2)
    a1 = _el(audio, "track")

    # Cuts go back to back on V1, with their own sound on A1.
    cursor = 0
    for i, cut in enumerate(plan["cuts"], 1):
        src_in, src_out = _frames(cut["in"], fps), _frames(cut["out"], fps)
        if src_out <= src_in:
            raise ValueError(f"cuts[{i - 1}]: 'out' must be after 'in'")
        p = path_of(cut, f"cuts[{i - 1}]")
        end = cursor + src_out - src_in
        clip(v1, f"cut-{i}", p, cursor, end, src_in)
        clip(a1, f"cut-{i}-audio", p, cursor, end, src_in, media="audio")
        cursor = end

    if plan["overlays"]:
        v2 = _el(video, "track")
        for i, o in enumerate(sorted(plan["overlays"], key=lambda o: o["start"]), 1):
            start, end = _frames(o["start"], fps), _frames(o["end"], fps)
            if end <= start:
                raise ValueError(f"overlays[{i - 1}]: 'end' must be after 'start'")
            p = path_of(o, f"overlays[{i - 1}]")
            still = p.suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".psd"}
            clip(v2, f"overlay-{i}", p, start, end, _frames(o.get("in", 0), fps), still=still)

    for i, a in enumerate(plan["audio"], 1):
        start, end = _frames(a["start"], fps), _frames(a["end"], fps)
        if end <= start:
            raise ValueError(f"audio[{i - 1}]: 'end' must be after 'start'")
        clip(_el(audio, "track"), f"audio-{i}", path_of(a, f"audio[{i - 1}]"),
             start, end, _frames(a.get("in", 0), fps), media="audio")

    _el(seq, "duration", max([cursor] + [_frames(x["end"], fps) for x in plan["overlays"] + plan["audio"]]))
    _rate(seq, fps)
    indent(root)
    return root


def main(argv=None):
    ap = argparse.ArgumentParser(description="JSON cut list -> Premiere / Resolve XML (FCP7 xmeml)")
    ap.add_argument("plan", type=Path, help="cut list JSON")
    ap.add_argument("-o", "--output", type=Path, help="output .xml (default: next to the JSON)")
    ap.add_argument("--version", action="version", version=__version__)
    args = ap.parse_args(argv)
    try:
        plan = json.loads(args.plan.read_text(encoding="utf-8"))
        root = build(plan, args.plan.parent)
    except (OSError, ValueError, KeyError) as e:
        sys.exit(f"cutlist2xml: {e}")
    out = args.output or args.plan.with_suffix(".xml")
    ElementTree(root).write(out, encoding="utf-8", xml_declaration=True)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
