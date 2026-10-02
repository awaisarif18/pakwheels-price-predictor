"""Exercise contamination, missingness, and field meaning through parse_car."""

import json
import unittest

import scraper

URL = scraper.BASE_URL + "/used-cars/toyota-corolla-2013-for-sale-in-lahore-11998010"


def listing_html(details="", comments="", title="Toyota Corolla GLi Automatic 1.6 VVTi 2013", product=None):
    if product is None:
        product = {"@type": "Product", "brand": {"name": "Toyota"}, "model": "Corolla", "offers": {"url": URL}}
    return (
        f'<html><body><h1>{title}</h1><div>PKR 33.5 lacs | 199,128 km | Petrol | Automatic | 1600 cc</div>'
        f'<ul id="scroll_car_detail">{details}</ul><h2 id="scroll_seller_comments">Seller\'s Comments</h2><div>{comments}</div>'
        f'<script type="application/ld+json">{json.dumps(product)}</script></body></html>'
    )


class CollectionFieldsTests(unittest.TestCase):
    def test_main_price_box_wins_over_recommendation_prices(self):
        html = (
            '<html><body><h1>Honda Civic 1.8 i-VTEC CVT 2019</h1>'
            '<ul><li class="similar-ads"><div>PKR 3,095,000</div></li></ul>'
            '<div>2019 | 35,000 km | Petrol | Automatic</div>'
            '<div class="price-box"><strong>PKR 48.5 <span>lacs</span></strong></div>'
            '</body></html>'
        )
        row, _ = scraper.parse_car(html, URL)
        self.assertEqual(row["price_pkr"], 4_850_000)

    def test_call_for_price_is_not_replaced_with_another_cars_price(self):
        html = (
            '<html><body><h1>Toyota Prado TX 2020</h1><div>2020 | 35,000 km | Petrol | Automatic</div>'
            '<div>PKR 3,600,000</div><div class="price-box"><strong>Call for price</strong></div>'
            '</body></html>'
        )
        row, _ = scraper.parse_car(html, URL)
        self.assertIsNone(row["price_pkr"])
        self.assertEqual(row["parse_status"], "incomplete")

    def test_phev_is_collected_without_relabeling_it_as_petrol(self):
        html = '<html><body><h1>Haval H6 PHEV 2025</h1><div>PKR 1.26 crore | 15,690 km | PHEV | Automatic</div></body></html>'
        row, _ = scraper.parse_car(html, URL)
        self.assertEqual(row["fuel"], "PHEV")

    def test_labeled_fields_identity_and_updated_date(self):
        html = listing_html(
            '<li class="ad-data">Assembly</li><li>Local</li>'
            '<li class="ad-data">Body Type</li><li><a>Sedan</a></li>'
            '<li class="ad-data">Last Updated:</li><li>Oct 01, 2026</li>',
            'Manufacture 2013<br>Registered 2015<br>Excellent condition',
        )
        row, _ = scraper.parse_car(html, URL)
        self.assertEqual((row["make"], row["model"], row["variant"]), ("Toyota", "Corolla", "GLi Automatic 1.6 VVTi"))
        self.assertEqual((row["assembly"], row["body_type"]), ("Local", "Sedan"))
        self.assertEqual((row["listing_date"], row["listing_date_type"]), ("2026-10-01", "updated"))
        self.assertEqual((row["year"], row["registration_year"], row["registration_year_meaning"]), (2013, 2015, "unknown"))
        self.assertEqual(row["identity_status"], "extracted_pending_review")
        self.assertNotIn("Excellent", row["field_provenance"])

    def test_recommended_products_do_not_supply_identity(self):
        other = {"@type": "Product", "brand": {"name": "Honda"}, "model": "City", "bodyType": "Hatchback", "offers": {"url": URL + "1"}}
        row, _ = scraper.parse_car(listing_html(product={"@graph": [other]}), URL)
        self.assertIsNone(row["make"])
        self.assertIsNone(row["body_type"])
        self.assertEqual(row["parse_status"], "complete")

    def test_conflicting_current_products_do_not_choose_a_brand(self):
        first = {"@type": "Product", "brand": {"name": "Toyota"}, "model": "Corolla", "offers": {"url": URL}}
        second = {**first, "model": "Yaris"}
        row, _ = scraper.parse_car(listing_html(product=[first, second]), URL)
        self.assertIsNone(row["make"])

    def test_missing_registration_is_not_filled_from_model_or_transfer_year(self):
        for text in ["Manufacture 2013", "Transferred 2015", "Registration Punjab", "Perfect condition", ""]:
            with self.subTest(text=text):
                row, _ = scraper.parse_car(listing_html(comments=text), URL)
                self.assertIsNone(row["registration_year"])
                self.assertEqual(row["registration_year_status"], "not_stated")
                self.assertEqual(row["parse_status"], "complete")

    def test_registration_conflicts_and_explicit_jurisdictions(self):
        cases = [
            ("Registered 2014<br>Registered 2015", None, None, "conflicting"),
            ("First registration in Pakistan: 2015", 2015, "first_pakistan_registration", "extracted"),
            ("First registration in Japan: 2014", 2014, "first_registration_other_jurisdiction", "extracted"),
        ]
        for text, year, meaning, status in cases:
            with self.subTest(text=text):
                row, _ = scraper.parse_car(listing_html(comments=text), URL)
                self.assertEqual((row["registration_year"], row["registration_year_meaning"], row["registration_year_status"]), (year, meaning, status))

    def test_unparseable_displayed_date_retains_evidence(self):
        row, _ = scraper.parse_car(listing_html('<li class="ad-data">Last Updated:</li><li>Yesterday</li>'), URL)
        self.assertIsNone(row["listing_date"])
        self.assertEqual(row["listing_date_type"], "updated")
        self.assertEqual(json.loads(row["field_provenance"])["listing_date"]["displayed"], "Yesterday")

    def test_title_disagreement_preserves_family_without_inventing_variant(self):
        row, _ = scraper.parse_car(listing_html(title="Toyota Yaris ATIV 2013"), URL)
        self.assertEqual(row["model"], "Corolla")
        self.assertIsNone(row["variant"])
        self.assertEqual(row["identity_status"], "family_extracted_variant_unmatched")


if __name__ == "__main__":
    unittest.main()
