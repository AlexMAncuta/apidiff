"""
Tests for the breaking-change comparator.

Each planted change in the mock API has one assertion here, so the rules
are verified rather than merely demonstrated.
"""

import json
import unittest
from pathlib import Path

from app.comparator import compare_specs

PROJECT_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE = PROJECT_ROOT / "knowledge"


def load(name: str) -> dict:
    return json.loads((KNOWLEDGE / name).read_text(encoding="utf-8"))


class ComparatorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v1 = load("openapi-v1.json")
        cls.v2 = load("openapi-v2.json")
        cls.result = compare_specs(cls.v1, cls.v2)
        cls.findings = cls.result["findings"]

    def rules(self) -> set[str]:
        return {f["rule"] for f in self.findings}

    def find(self, rule: str, location_contains: str = "") -> list[dict]:
        return [
            f
            for f in self.findings
            if f["rule"] == rule and location_contains in f["location"]
        ]

    # -- planted breaking changes ------------------------------------

    def test_deleted_endpoint_is_breaking(self):
        matches = self.find("ENDPOINT_REMOVED", "DELETE /api/products/{id}")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["severity"], "BREAKING")

    def test_parameter_became_required(self):
        matches = self.find("PARAM_NOW_REQUIRED", "GET /api/products")
        self.assertTrue(matches)
        self.assertEqual(matches[0]["severity"], "BREAKING")

    def test_enum_value_removed_from_parameter(self):
        matches = self.find("PARAM_ENUM_VALUE_REMOVED", "GET /api/products")
        self.assertTrue(matches)
        self.assertIn("BOOKS", matches[0]["detail"])

    def test_response_field_removed(self):
        matches = self.find("RESPONSE_FIELD_REMOVED")
        self.assertTrue(matches)
        self.assertTrue(
            any("description" in f["detail"] for f in matches)
        )

    def test_request_field_removed(self):
        matches = self.find("REQUEST_FIELD_REMOVED")
        self.assertTrue(matches)
        self.assertTrue(
            any("description" in f["detail"] for f in matches)
        )

    def test_type_change_is_detected_through_format(self):
        """Double -> BigDecimal changes only 'format', not 'type'."""
        matches = self.find("RESPONSE_FIELD_TYPE_CHANGED")
        self.assertTrue(matches)
        detail = next(f["detail"] for f in matches if "price" in f["detail"])
        self.assertIn("number/double", detail)

    # -- planted safe changes ---------------------------------------

    def test_new_endpoint_is_safe(self):
        matches = self.find("ENDPOINT_ADDED", "GET /api/products/search")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["severity"], "SAFE")

    def test_new_response_field_is_safe(self):
        matches = self.find("RESPONSE_FIELD_ADDED")
        self.assertTrue(matches)
        self.assertTrue(all(f["severity"] == "SAFE" for f in matches))
        self.assertTrue(any("currency" in f["detail"] for f in matches))

    # -- overall verdict --------------------------------------------

    def test_summary_marks_upgrade_incompatible(self):
        self.assertFalse(self.result["summary"]["compatible"])
        self.assertGreater(self.result["summary"]["breaking"], 0)

    def test_comparing_a_spec_with_itself_is_compatible(self):
        result = compare_specs(self.v1, self.v1)
        self.assertTrue(result["summary"]["compatible"])
        self.assertEqual(result["findings"], [])

    def test_reverse_comparison_reports_different_breaks(self):
        """v2 -> v1 re-adds the deleted endpoint, so that one is safe."""
        result = compare_specs(self.v2, self.v1)
        rules = {f["rule"] for f in result["findings"]}
        self.assertIn("ENDPOINT_ADDED", rules)
        self.assertIn("ENDPOINT_REMOVED", rules)  # /search disappears

    # -- structure ---------------------------------------------------

    def test_every_finding_has_the_expected_shape(self):
        for f in self.findings:
            self.assertIn(f["severity"], {"BREAKING", "WARNING", "SAFE"})
            self.assertTrue(f["rule"])
            self.assertTrue(f["location"])
            self.assertTrue(f["detail"])

    def test_result_is_json_serialisable(self):
        """The tool output is handed to the model, so it must serialise."""
        json.dumps(self.result)


if __name__ == "__main__":
    unittest.main(verbosity=2)