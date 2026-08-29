import unittest
from decimal import Decimal
from product_master import Product, BOMItem
from costing_pricing_service import calculate_price_book
from inventory_core import StockItem
from sales_core import DealerAccount, SalesLine, SalesOrder
from agency_management import Agency

class EYTCoreTests(unittest.TestCase):
    def test_product_bom_to_pricing(self):
        p = Product(
            sku="EYT-HS7-QARQARI-001",
            name="قرقری هایما S7",
            family="قرقری",
            vehicle="هایما S7",
            bom=[
                BOMItem("MAT-ROD","میله",Decimal("180000"),Decimal("1")),
                BOMItem("MAT-RUB","کائوچو",Decimal("15000"),Decimal("1")),
                BOMItem("MAT-GRE","گریس",Decimal("5000"),Decimal("1")),
                BOMItem("MAT-CUP","فنجانی",Decimal("75000"),Decimal("1")),
            ],
        )
        sheet = p.to_cost_sheet(workshop=100000, packaging=24000)
        self.assertEqual(sheet.actual_cost(), Decimal("399000"))
        book = calculate_price_book(sheet, p.pricing_coefficient)
        self.assertEqual(book["mrp"], Decimal("558600"))

    def test_order_credit(self):
        account = DealerAccount("AG-ISF-001","نمایندگی اصفهان",Decimal("1000000"))
        order = SalesOrder("SO-0001", account, [SalesLine("SKU-1",Decimal("1"),Decimal("500000"))])
        self.assertEqual(order.confirm().status, "confirmed")

    def test_stock_reservation(self):
        stock = StockItem("SKU-1","MAIN",Decimal("10"),Decimal("0"),Decimal("3"))
        stock.reserve(Decimal("7"))
        self.assertTrue(stock.needs_reorder)

    def test_agency_score(self):
        agency = Agency("AG-ISF-001","اصفهان","اصفهان")
        self.assertGreaterEqual(agency.evaluate(.9,.9,.9), Decimal("85"))
        self.assertTrue(agency.qualifies_for_exclusivity())

if __name__ == "__main__":
    unittest.main()
