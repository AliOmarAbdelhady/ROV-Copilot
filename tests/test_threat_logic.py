import unittest

from threat_logic import assess_mission, parse_coordinate, parse_heading, parse_keel_depth, render_report_pdf, render_track_preview_png


EXAMPLES = {
    "A": {
        "input": ("47.39.00", "48.37.00", "158", "99"),
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
        "input": ("47.58.00", "48.50.00", "180", "78"),
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
        "input": ("47.53.00", "47.51.00", "188", "112"),
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
        "input": ("47.40.00", "49.25.00", "152", "60"),
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
        "input": ("47.45.00", "48.29.00", "198", "84"),
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
        "input": ("47.56.00", "47.45.00", "181", "126"),
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
    def test_coordinate_parser_accepts_decimal_and_degree_dot_inputs(self):
        self.assertAlmostEqual(parse_coordinate("47.65", "latitude"), 47.65)
        self.assertAlmostEqual(parse_coordinate("48.4", "longitude"), -48.4)
        self.assertAlmostEqual(parse_coordinate("47.39", "latitude"), 47.65)
        self.assertAlmostEqual(parse_coordinate("48.37.00", "longitude"), -48.6166666667)
        with self.assertRaisesRegex(ValueError, "Latitude must use digits and decimal points only."):
            parse_coordinate("47o39’00” North", "latitude")
        with self.assertRaisesRegex(ValueError, "Longitude must use digits and decimal points only."):
            parse_coordinate("-48.4", "longitude")

    def test_heading_and_keel_depth_parsers(self):
        self.assertEqual(parse_heading("518"), 158.0)
        self.assertEqual(parse_keel_depth("99"), 99.0)
        with self.assertRaisesRegex(ValueError, "Heading must be a decimal number."):
            parse_heading("158o")
        with self.assertRaisesRegex(ValueError, "Keel depth must be a decimal number."):
            parse_keel_depth("99 meters")

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

    def test_plot_and_pdf_renderers_return_binary_outputs(self):
        latitude = parse_coordinate("47.39.00", "latitude")
        longitude = parse_coordinate("48.37.00", "longitude")
        heading = parse_heading("158")
        keel_depth = parse_keel_depth("99")
        assessments = assess_mission(latitude, longitude, heading, keel_depth)

        preview_png = render_track_preview_png(latitude, longitude, heading, assessments)
        report_pdf = render_report_pdf(latitude, longitude, heading, keel_depth, assessments)

        self.assertTrue(preview_png.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertTrue(report_pdf.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
