import unittest
from decimal import Decimal
from billing_core import Invoice, InvoiceLine
from inventory_core import StockItem
from inventory_transactions import InventoryTransaction, apply_transaction
from production_core import ProductionOrder
from dashboard_service import build_management_snapshot
from agency_management import Agency

class OperationalFlowTests(unittest.TestCase):
    def test_production_to_sale_to_collection(self):
        stock = StockItem("EYT-HS7-QARQARI-001","MAIN",Decimal("0"),Decimal("0"),Decimal("100"))
        po = ProductionOrder("PO-001",stock.sku,Decimal("1000")).start().complete(1000,0)
        apply_transaction(stock, InventoryTransaction(stock.sku,"MAIN","production_receipt",po.produced_quantity))
        self.assertEqual(stock.on_hand, Decimal("1000"))

        invoice = Invoice("INV-001","AG-ISF-001",[
            InvoiceLine(stock.sku,Decimal("100"),Decimal("500000"))
        ])
        apply_transaction(stock, InventoryTransaction(stock.sku,"MAIN","sales_issue",Decimal("100")))
        invoice.receive(Decimal("20000000"))
        self.assertEqual(invoice.status, "partially_paid")
        invoice.receive(Decimal("30000000"))
        self.assertEqual(invoice.status, "paid")

        agency = Agency("AG-ISF-001","اصفهان","اصفهان")
        agency.evaluate(.9,.95,.8)
        snapshot = build_management_snapshot([invoice],[stock],[agency])
        self.assertEqual(snapshot["sales"], Decimal("50000000"))
        self.assertEqual(snapshot["receivables"], Decimal("0"))

if __name__ == "__main__":
    unittest.main()
