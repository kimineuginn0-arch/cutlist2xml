# cutlist2xml

Turn a JSON cut list into an editable timeline for **Premiere Pro**, **DaVinci Resolve** or **Final Cut Pro 7** (FCP7 XML / xmeml v4).

Let a script, a transcript tool or an AI decide *where to cut*, then open the result in a real editor and finish it by hand: every cut stays a separate, trimmable clip.

- One Python file, standard library only (Python 3.10+)
- Cuts from one or many source files, placed back to back with their audio
- Optional overlay track (titles, PNGs, B-roll) and extra audio tracks (music, SFX)
- 29.97 / 23.976 / 59.94 fps handled as NTSC rates

## Install

```sh
pip install git+https://github.com/kimineuginn0-arch/cutlist2xml
```

Or just copy `cutlist2xml.py`; it has no dependencies.

## Usage

```sh
cutlist2xml example/edit.json                       # writes example/edit.xml
python cutlist2xml.py example/edit.json            # same, without installing
python cutlist2xml.py edit.json -o rough-cut.xml
```

Then import the XML:

- **Premiere Pro:** File > Import
- **DaVinci Resolve:** File > Import > Timeline
- **Final Cut Pro 7:** File > Import > XML

## Cut list format

All times are in **seconds**. File paths are relative to the JSON file (absolute paths also work).

```json
{
  "name": "My first rough cut",
  "fps": 30,
  "width": 1920,
  "height": 1080,
  "cuts": [
    {"file": "interview.mp4", "in": 12.0, "out": 18.5},
    {"file": "interview.mp4", "in": 41.2, "out": 47.0}
  ],
  "overlays": [
    {"file": "title.png", "start": 0.5, "end": 3.5}
  ],
  "audio": [
    {"file": "music.wav", "start": 0, "end": 12.3}
  ]
}
```

| Key | Meaning |
|---|---|
| `cuts[]` | `in`/`out` are positions in the source file. Cuts are laid back to back on V1, with their sound on A1. |
| `overlays[]` | `start`/`end` are positions on the timeline (V2). Optional `in` for video overlays. |
| `audio[]` | `start`/`end` on the timeline, each on its own audio track. Optional `in`. |
| `name`, `fps`, `width`, `height` | Sequence settings. Defaults: `cutlist2xml`, 30, 1920, 1080. |

## Use as a library

```python
from xml.etree.ElementTree import ElementTree
from cutlist2xml import build

root = build({"cuts": [{"file": "a.mp4", "in": 1, "out": 4}]}, base_dir=".")
ElementTree(root).write("a.xml", encoding="utf-8", xml_declaration=True)
```

## Tests

```sh
python -m unittest
```

## Limitations

- Source file length is not probed; the XML declares the furthest frame the cut list uses. Editors relink and read the real length on import.
- No transitions, speed changes or effects yet. Pull requests are welcome.

---

## 한국어

JSON으로 적은 컷 목록을 프리미어 프로 / 다빈치 리졸브 / 파이널 컷 7에서 바로 열리는 XML 타임라인으로 바꿔 줍니다. 스크립트나 AI가 자를 위치를 정하면, 사람은 편집 프로그램에서 컷 하나하나를 그대로 다듬을 수 있습니다.

```sh
python cutlist2xml.py example/edit.json
```

## License

MIT
