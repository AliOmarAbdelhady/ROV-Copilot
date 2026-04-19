import unittest

from threat_logic import assess_mission, parse_coordinate, parse_heading, parse_keel_depth


EXAMPLES = {
    "A": {
        "input": ("47o39’00” North", "48o37’00” West", "158o", "99 meters"),
        "platform": {
            "Hibernia": "Green",
            "Hebron": "Green",
            "Sea Rose": "Red",
            "Terra Nova": "Green",
        },
        "subsea": {
            "Hibernia": "Green",
            "Hebron": "Red",
            "Sea Rose": "Red",
            "Terra Nova": "Red",
        },
    },
    "B": {
        "input": ("47o58’00” North", "48o50’00” West", "180o", "78 meters"),
        "platform": {
            "Hibernia": "Red",
            "Hebron": "Green",
            "Sea Rose": "Green",
            "Terra Nova": "Green",
        },
        "subsea": {
            "Hibernia": "Red",
            "Hebron": "Yellow",
            "Sea Rose": "Green",
            "Terra Nova": "Yellow",
        },
    },
    "C": {
        "input": ("47o53’00” North", "47o51’00” West", "188o", "112 meters"),
        "platform": {
            "Hibernia": "Green",
            "Hebron": "Green",
            "Sea Rose": "Red",
            "Terra Nova": "Green",
        },
        "subsea": {
            "Hibernia": "Green",
            "Hebron": "Green",
            "Sea Rose": "Red",
            "Terra Nova": "Green",
        },
    },
    "D": {
        "input": ("47o40’00” North", "49o25’00” West", "152o", "60 meters"),
        "platform": {
            "Hibernia": "Red",
            "Hebron": "Red",
            "Sea Rose": "Green",
            "Terra Nova": "Red",
        },
        "subsea": {
            "Hibernia": "Yellow",
            "Hebron": "Green",
            "Sea Rose": "Green",
            "Terra Nova": "Green",
        },
    },
    "E": {
        "input": ("47o45’00” North", "48o29’00” West", "198o", "84 meters"),
        "platform": {
            "Hibernia": "Yellow",
            "Hebron": "Green",
            "Sea Rose": "Green",
            "Terra Nova": "Green",
        },
        "subsea": {
            "Hibernia": "Red",
            "Hebron": "Red",
            "Sea Rose": "Green",
            "Terra Nova": "Green",
        },
    },
    "F": {
        "input": ("47o56’00” North", "47o45’00” West", "181o", "126 meters"),
        "platform": {
            "Hibernia": "Green",
            "Hebron": "Green",
            "Sea Rose": "Green",
            "Terra Nova": "Green",
        },
        "subsea": {
            "Hibernia": "Green",
            "Hebron": "Green",
            "Sea Rose": "Green",
            "Terra Nova": "Green",
        },
    },
}


class ThreatLogicTests(unittest.TestCase):
    def test_coordinate_parser_accepts_decimal_and_dms(self):
        self.assertAlmostEqual(parse_coordinate("47o39’00” North", "latitude"), 47.65)
        self.assertAlmostEqual(parse_coordinate("48o37’00” West", "longitude"), -48.6166666667)
        self.assertAlmostEqual(parse_coordinate("-48.4", "longitude"), -48.4)

    def test_heading_and_keel_depth_parsers(self):
        self.assertEqual(parse_heading("518o"), 158.0)
        self.assertEqual(parse_keel_depth("99 meters"), 99.0)

    def test_official_examples_match_expected_outputs(self):
        for example_name, example in EXAMPLES.items():
            latitude, longitude, heading, keel_depth = example["input"]
            assessments = assess_mission(
                parse_coordinate(latitude, "latitude"),
                parse_coordinate(longitude, "longitude"),
                parse_heading(heading),
                parse_keel_depth(keel_depth),
            )
            platform_lookup = {item.platform.name: item.platform_threat for item in assessments}
            subsea_lookup = {item.platform.name: item.subsea_threat for item in assessments}
            self.assertEqual(platform_lookup, example["platform"], msg=f"Platform mismatch for example {example_name}")
            self.assertEqual(subsea_lookup, example["subsea"], msg=f"Subsea mismatch for example {example_name}")


if __name__ == "__main__":
    unittest.main()
