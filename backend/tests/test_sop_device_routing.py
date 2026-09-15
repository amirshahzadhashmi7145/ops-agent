from types import SimpleNamespace

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from app.services.sop_device_routing import choose_sop_process, resolve_device_routing


class _Device:
    def __init__(self, serial: str, model: str):
        self.serial_number = serial
        self.model = model
        self.purchase_date = "2025-03-12"
        self.customer_id = "cust"


class _Customer:
    full_name = "Alex Rivera"
    email = "alex.rivera@example.com"
    phone = "+1-555-0101"


CLASSIC = (
    _Device("NX-BEAM-10001", "Nexar Beam"),
    _Customer(),
    {"camera_family": "classic", "model": "Nexar Beam", "segment": "consumer", "lookup": {}},
)
CONNECT = (
    _Device("NX-ONE-20022", "Nexar One"),
    _Customer(),
    {"camera_family": "connect", "model": "Nexar One", "segment": "consumer", "lookup": {}},
)


def test_account_lookup_does_not_lock_classic_sop(monkeypatch):
    monkeypatch.setattr(
        "app.services.sop_device_routing.find_devices_by_query",
        lambda db, q: [CLASSIC, CONNECT],
    )
    routing = resolve_device_routing(SimpleNamespace(), "Look up alex.rivera@example.com and list their devices.")
    assert routing["preferred_document_title"] is None
    assert routing["preferred_process_hint"] is None
    assert routing["is_connectivity"] is False


def test_lte_issue_locks_connect_sop(monkeypatch):
    monkeypatch.setattr(
        "app.services.sop_device_routing.find_devices_by_query",
        lambda db, q: [
            (
                _Device("NX-BEAM-10088", "Beam2"),
                _Customer(),
                {"camera_family": "connect", "model": "Beam2", "segment": "consumer", "lookup": {}},
            )
        ],
    )
    routing = resolve_device_routing(SimpleNamespace(), "Camera NX-BEAM-10088 has no LTE. What’s going on?")
    assert routing["preferred_process_hint"] == "Sim Triage"
    assert routing["is_connectivity"] is True


def test_choose_sop_does_not_autolock_diagnostic_on_account_lookup(monkeypatch):
    monkeypatch.setattr(
        "app.services.sop_device_routing.search_sop_processes",
        lambda db, query, top_k=None: [
            {"process_id": "classic", "title": "Nexar Classic App Connectivity", "score": 0.95},
            {"process_id": "lookup", "title": "Look up customer devices", "score": 0.70},
        ],
    )
    selection = choose_sop_process(
        SimpleNamespace(),
        "Look up alex.rivera@example.com and list their devices.",
        routing={
            "preferred_document_title": None,
            "preferred_process_hint": None,
            "is_connectivity": False,
            "is_hardware": False,
        },
        threshold=0.5,
        margin=0.08,
    )
    assert selection["best"]["title"] == "Look up customer devices"


def test_devices_lookup_route_not_captured_as_serial():
    sim = APIRouter(prefix="/sim")
    ops = APIRouter(prefix="/sim")

    @sim.get("/devices/{serial_number}")
    def by_serial(serial_number: str) -> dict:
        return {"serial": serial_number}

    @ops.get("/devices/lookup")
    def lookup() -> dict:
        return {"lookup": True}

    app = FastAPI()
    app.include_router(ops, prefix="/api")
    app.include_router(sim, prefix="/api")
    client = TestClient(app)
    assert client.get("/api/sim/devices/lookup").json() == {"lookup": True}
    assert client.get("/api/sim/devices/NX-ONE-20022").json() == {"serial": "NX-ONE-20022"}
