from __future__ import annotations

import base64
import json
import os
from pathlib import Path

import requests

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
OPENAI_FILES_URL = "https://api.openai.com/v1/files"

INVOICE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "documentType": {"type": "string", "enum": ["PURCHASE_INVOICE", "OTHER"]},
        "supplierCode": {"type": ["string", "null"]},
        "invoiceNo": {"type": ["string", "null"]},
        "invoiceDate": {"type": ["string", "null"]},
        "dueDate": {"type": ["string", "null"]},
        "currency": {"type": "string"},
        "subtotal": {"type": ["number", "null"]},
        "discountAmount": {"type": ["number", "null"]},
        "taxAmount": {"type": ["number", "null"]},
        "totalAmount": {"type": ["number", "null"]},
        "confidence": {"type": ["number", "null"]},
        "lines": {"type": "array", "items": {"type": "object", "additionalProperties": False, "properties": {
            "lineNo": {"type": "integer"},
            "rawDescription": {"type": ["string", "null"]},
            "productCode": {"type": ["string", "null"]},
            "quantity": {"type": ["number", "null"]},
            "unit": {"type": ["string", "null"]},
            "unitPrice": {"type": ["number", "null"]},
            "discountAmount": {"type": "number"},
            "taxAmount": {"type": "number"},
            "lineTotal": {"type": ["number", "null"]},
            "matchConfidence": {"type": ["number", "null"]},
            "extractedData": {"type": "object", "additionalProperties": True}
        }, "required": ["lineNo","rawDescription","productCode","quantity","unit","unitPrice","discountAmount","taxAmount","lineTotal","matchConfidence","extractedData"]}}
    },
    "required": ["documentType","supplierCode","invoiceNo","invoiceDate","dueDate","currency","subtotal","discountAmount","taxAmount","totalAmount","confidence","lines"]
}

def _headers():
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return {"Authorization": f"Bearer {key}"}

def _prompt():
    return (
        "Read this invoice/document. Extract only what is visibly supported by the source. "
        "Do not invent supplier codes or product SKUs. If a field is unclear, return null. "
        "For each line preserve the raw description and calculate no values that are not present. "
        "Return structured JSON matching the schema. Persian and Arabic numerals are acceptable."
    )

def extract_invoice(path: str) -> dict:
    model = os.getenv("DOCUMENT_AI_MODEL", "gpt-5.6-luna")
    file_path = Path(path)
    mime = "application/pdf" if file_path.suffix.lower() == ".pdf" else "image/jpeg"
    if mime.startswith("image/"):
        data_url = f"data:{mime};base64," + base64.b64encode(file_path.read_bytes()).decode()
        content = [{"type": "input_text", "text": _prompt()}, {"type": "input_image", "image_url": data_url}]
    else:
        with file_path.open("rb") as fh:
            upload = requests.post(OPENAI_FILES_URL, headers=_headers(), files={"file": (file_path.name, fh, mime)}, data={"purpose": "user_data"}, timeout=120)
        upload.raise_for_status()
        file_id = upload.json()["id"]
        content = [{"type": "input_text", "text": _prompt()}, {"type": "input_file", "file_id": file_id}]
    payload = {
        "model": model,
        "input": [{"role": "user", "content": content}],
        "text": {"format": {"type": "json_schema", "name": "invoice_extraction", "strict": True, "schema": INVOICE_SCHEMA}},
    }
    response = requests.post(OPENAI_RESPONSES_URL, headers={**_headers(), "Content-Type": "application/json"}, json=payload, timeout=180)
    response.raise_for_status()
    body = response.json()
    output_text = body.get("output_text")
    if not output_text:
        raise RuntimeError("OpenAI response did not contain output_text")
    return json.loads(output_text)