"""Optional TCP checks against the standalone Compose mock APIs."""

import os
from uuid import uuid4

import httpx
import pytest

pytestmark = pytest.mark.integration


async def test_compose_payment_and_shipping_endpoints() -> None:
    if not os.environ.get("AGENTTXN_TEST_TCP"):
        pytest.skip("Set AGENTTXN_TEST_TCP=1 after starting Compose services")
    payment_url = os.environ.get("PAYMENTS_URL", "http://localhost:18001")
    shipment_url = os.environ.get("SHIPPING_URL", "http://localhost:18002")
    operation_id = f"tcp-{uuid4()}"
    request = {"logical_operation_id": operation_id, "order_id": operation_id, "amount_cents": 100}
    async with httpx.AsyncClient(base_url=payment_url) as payment:
        assert (await payment.get("/health")).status_code == 200
        first = await payment.post("/effects", json=request)
        repeated = await payment.post("/effects", json=request)
        assert first.status_code == repeated.status_code == 200
        assert first.json()["receipt_id"] == repeated.json()["receipt_id"]
        truth = await payment.get(f"/operations/{operation_id}")
        assert truth.json()["certainty"] == "CONFIRMED"
    request["amount_cents"] = 0
    async with httpx.AsyncClient(base_url=shipment_url) as shipping:
        assert (await shipping.get("/health")).status_code == 200
        outcome = await shipping.post("/effects", json=request)
        assert outcome.status_code == 200
        assert outcome.json()["certainty"] == "CONFIRMED"
