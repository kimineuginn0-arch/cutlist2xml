import unittest

from cutlist2xml import build


def texts(root, path):
    return [e.text for e in root.iterfind(path)]


class BuildTest(unittest.TestCase):
    plan = {
        "fps": 30,
        "cuts": [{"file": "a.mp4", "in": 10, "out": 12}, {"file": "a.mp4", "in": 20, "out": 21}],
        "overlays": [{"file": "title.png", "start": 0.5, "end": 1.5}],
        "audio": [{"file": "music.wav", "start": 0, "end": 3}],
    }

    def test_cuts_are_back_to_back_with_source_ranges(self):
        root = build(self.plan)
        v1 = root.find("sequence/media/video/track")
        self.assertEqual(texts(v1, "clipitem/start"), ["0", "60"])
        self.assertEqual(texts(v1, "clipitem/end"), ["60", "90"])
        self.assertEqual(texts(v1, "clipitem/in"), ["300", "600"])
        self.assertEqual(root.find("sequence/duration").text, "90")

    def test_same_source_file_is_defined_once(self):
        root = build(self.plan)
        self.assertEqual(len(root.findall(".//file/pathurl")), 3)  # a.mp4, title.png, music.wav

    def test_overlay_and_audio_tracks(self):
        root = build(self.plan)
        self.assertEqual(len(root.findall("sequence/media/video/track")), 2)
        self.assertEqual(len(root.findall("sequence/media/audio/track")), 2)

    def test_ntsc_rate(self):
        root = build({**self.plan, "fps": 29.97})
        self.assertEqual(root.find("sequence/rate/timebase").text, "30")
        self.assertEqual(root.find("sequence/rate/ntsc").text, "TRUE")

    def test_rejects_bad_ranges(self):
        with self.assertRaises(ValueError):
            build({"cuts": [{"file": "a.mp4", "in": 5, "out": 5}]})
        with self.assertRaises(ValueError):
            build({"cuts": []})


if __name__ == "__main__":
    unittest.main()
