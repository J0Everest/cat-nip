from django.test import TestCase
from apps.scenario.services import parse_scenario_query, compute_confidence, models_for_peril, industry_peril_clause
from apps.scenario.catalogs import MODEL_CATALOG, PERIL_DB_CODES, PERIL_OPTIONS


class ParseScenarioQueryTest(TestCase):
    def test_hurricane_miami(self):
        r = parse_scenario_query("Category 5 hurricane near Miami, $5-15B industry loss")
        self.assertEqual(r["peril"], "TC")
        self.assertEqual(r["zone"], "Zone 03 FL")
        self.assertEqual(r["loss_lo"], 5.0)
        self.assertEqual(r["loss_hi"], 15.0)

    def test_earthquake_japan(self):
        r = parse_scenario_query("Earthquake in Japan, magnitude 7-9")
        self.assertEqual(r["peril"], "EQ")
        self.assertEqual(r["zone"], "Asia  Japan")

    def test_wildfire_california(self):
        r = parse_scenario_query("Wildfire in California")
        self.assertEqual(r["peril"], "Fire / Wildfire")
        self.assertEqual(r["zone"], "Zone 08")

    def test_winter_storm_northeast(self):
        r = parse_scenario_query("Winter storm hitting the northeast")
        self.assertEqual(r["peril"], "Winter Storm")
        self.assertEqual(r["zone"], "Zone 01")

    def test_flood_uk(self):
        r = parse_scenario_query("Flood in UK")
        self.assertEqual(r["peril"], "Flood")
        self.assertEqual(r["zone"], "Europe  UK")

    def test_typhoon_philippines(self):
        r = parse_scenario_query("Typhoon near Philippines")
        self.assertEqual(r["peril"], "TC")
        self.assertEqual(r["zone"], "Asia  Philippines")

    def test_bushfire_australia(self):
        r = parse_scenario_query("Bushfire in Australia")
        self.assertEqual(r["peril"], "Fire / Wildfire")
        self.assertEqual(r["zone"], "AusNZ  Australia")

    def test_empty_string(self):
        r = parse_scenario_query("")
        self.assertIsNone(r["peril"])
        self.assertIsNone(r["zone"])

    def test_ambiguous_in_resolved_correctly(self):
        r = parse_scenario_query("Earthquake in Indiana")
        self.assertEqual(r["zone"], "Zone 05 and 06")

    def test_magnitude_parsed(self):
        r = parse_scenario_query("earthquake magnitude 7.2-8.5")
        self.assertEqual(r["mag_lo"], 7.2)
        self.assertEqual(r["mag_hi"], 8.5)


class ConfidenceTest(TestCase):
    def test_high_confidence(self):
        parsed = {"peril": "TC", "zone": "FL", "loss_lo": 5.0, "loss_hi": 15.0}
        level, parts, total = compute_confidence(parsed)
        self.assertEqual(level, "high")
        self.assertEqual(parts, 3)

    def test_partial_confidence(self):
        parsed = {"peril": "EQ", "zone": None, "loss_lo": None, "loss_hi": None}
        level, parts, total = compute_confidence(parsed)
        self.assertEqual(level, "partial")
        self.assertEqual(parts, 1)

    def test_needs_refinement(self):
        parsed = {"peril": None, "zone": None, "loss_lo": None, "loss_hi": None}
        level, parts, total = compute_confidence(parsed)
        self.assertEqual(level, "needs_refinement")


class CatalogTest(TestCase):
    def test_model_catalog_has_entries(self):
        self.assertGreater(len(MODEL_CATALOG), 30)

    def test_peril_options_valid(self):
        self.assertIn("All", PERIL_OPTIONS)
        self.assertIn("EQ", PERIL_OPTIONS)
        self.assertIn("TC", PERIL_OPTIONS)
        self.assertNotIn("Flood", PERIL_OPTIONS)

    def test_peril_db_codes_tc(self):
        codes = PERIL_DB_CODES["TC"]
        self.assertIn("TC", codes)
        self.assertIn("ST+WD", codes)

    def test_models_for_peril_eq(self):
        models = models_for_peril("EQ")
        self.assertIn(11, models)
        self.assertIn(52, models)
        self.assertNotIn(5, models)

    def test_models_for_peril_all(self):
        models = models_for_peril("All")
        self.assertEqual(models, set(MODEL_CATALOG.keys()))

    def test_industry_peril_clause_tc(self):
        clause = industry_peril_clause("TC")
        self.assertIn("TC", clause)
        self.assertIn("ST+WD", clause)
        self.assertIn("IN", clause)

    def test_industry_peril_clause_eq(self):
        clause = industry_peril_clause("EQ")
        self.assertEqual(clause, "AND iu.Peril = 'EQ'")

    def test_industry_peril_clause_flood_empty(self):
        clause = industry_peril_clause("Flood")
        self.assertEqual(clause, "")

    def test_industry_peril_clause_all_empty(self):
        clause = industry_peril_clause("All")
        self.assertEqual(clause, "")
