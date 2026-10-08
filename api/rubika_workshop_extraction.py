from __future__ import annotations

import re
from typing import Any

PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


def normalize_digits(value: str) -> str:
    return value.translate(PERSIAN_DIGITS).replace(",", "").replace("٬", "")


def first_int(text: str) -> int | None:
    match = re.search(r"(?<![\d])([0-9]+(?:[.,٬][0-9]{3})*)(?![\d])", normalize_digits(text))
    return int(match.group(1).replace(".", "")) if match else None


def classify(text: str) -> str:
    t = text.lower()
    if any(x in t for x in ("پرداخت", "واریز", "هزینه", "خرج", "تومان")):
        return "PAYMENT"
    if any(x in t for x in ("تولید", "تعداد", "تزریق", "پخت")):
        return "PRODUCTION"
    if any(x in t for x in ("مواد", "لاستیک", "کامپاند", "چسب", "لوله")):
        return "MATERIAL"
    if any(x in t for x in ("خرید", "سفارش", "قیمت خرید")):
        return "PURCHASE"
    if any(x in t for x in ("مشکل", "خراب", "نشد", "کمبود", "ایراد")):
        return "ISSUE"
    return "GENERAL"


def extract_message(message_text: str, message_type: str | None = None) -> dict[str, Any]:
    text = message_text.strip()
    kind = message_type or classify(text)
    quantity = first_int(text)
    amount = None
    if kind == "PAYMENT":
        amount = quantity
        quantity = None
    return {
        "schema_version": "rubika-workshop-extraction-v1",
        "message_type": kind,
        "text": text,
        "quantity": quantity,
        "amount_toman": amount,
        "entity_candidates": [],
        "action": "REVIEW_REQUIRED",
        "confidence": 0.55 if kind != "GENERAL" else 0.25,
        "erp_mutation": False,
    }
