import unittest
from decimal import Decimal
from costing_engine import haima_s7_qarqari_example
from costing_pricing_service import calculate_price_book

class CostingTests(unittest.TestCase):
    def test_haima_s7_actual_cost(self):
        sheet = haima_s7_qarqari_example()
        self.assertEqual(sheet.actual_cost(), Decimal("399000"))

    def test_floor_price_protection(self):
        sheet = haima_s7_qarqari_example()
        book = calculate_price_book(sheet, pricing_coefficient=Decimal("1.4"))
        self.assertEqual(book["mrp"], Decimal("558600"))
        self.assertEqual(book["floor_price"], Decimal("458850"))
        self.assertEqual(book["channels"]["representative"], Decimal("458850"))
        self.assertEqual(book["channels"]["provincial_representative_volume"], Decimal("458850"))

if __name__ == "__main__":
    unittest.main()
