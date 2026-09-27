"""Unit tests for the deterministic RCA engine."""

from app.rca.engine import DeterministicRCAEngine
from app.rca.parser import ParsedDiagnostic


def get_base_diag():
    return ParsedDiagnostic(
        rca_file_id="INC-test",
        raw_command_output="test",
        cpu_utilization=10.0,
        memory_utilization=40.0,
        packet_loss=0.0,
        crc_errors=0,
        interface_flaps=0,
        interface_status="UP",
        bgp_status="ESTABLISHED"
    )

def test_device_unreachable():
    engine = DeterministicRCAEngine()
    diag = get_base_diag()
    diag.interface_status = "DOWN"
    diag.packet_loss = 100.0

    res = engine.evaluate("INC-001", diag)
    assert res is not None
    assert res.probable_rca == "Device unreachable"
    assert res.evidence["interface_status"] == "DOWN"
    assert res.evidence["packet_loss"] == "100.0%"

def test_high_cpu():
    engine = DeterministicRCAEngine()
    diag = get_base_diag()
    diag.cpu_utilization = 95.0

    res = engine.evaluate("INC-002", diag)
    assert res is not None
    assert res.probable_rca == "High CPU"
    assert res.evidence["cpu_utilization"] == "95.0%"

def test_memory_pressure():
    engine = DeterministicRCAEngine()
    diag = get_base_diag()
    diag.memory_utilization = 99.0

    res = engine.evaluate("INC-003", diag)
    assert res is not None
    assert res.probable_rca == "Memory pressure"
    assert res.evidence["memory_utilization"] == "99.0%"

def test_routing_instability():
    engine = DeterministicRCAEngine()
    diag = get_base_diag()
    diag.bgp_status = "IDLE"

    res = engine.evaluate("INC-004", diag)
    assert res is not None
    assert res.probable_rca == "Routing instability"
    assert res.evidence["bgp_status"] == "IDLE"

def test_wan_degradation():
    engine = DeterministicRCAEngine()
    diag = get_base_diag()
    diag.packet_loss = 15.0
    diag.interface_status = "DEGRADED"

    res = engine.evaluate("INC-005", diag)
    assert res is not None
    assert res.probable_rca == "WAN degradation"
    assert res.evidence["packet_loss"] == "15.0%"

def test_interface_degradation():
    engine = DeterministicRCAEngine()
    diag = get_base_diag()
    diag.crc_errors = 1500
    diag.interface_flaps = 10

    res = engine.evaluate("INC-006", diag)
    assert res is not None
    assert res.probable_rca == "Interface degradation"
    assert res.evidence["crc_errors"] == "1500"
    assert res.evidence["interface_flaps"] == "10"
    assert res.evidence["bgp_status"] == "ESTABLISHED"

def test_no_rule_match():
    engine = DeterministicRCAEngine()
    diag = get_base_diag()
    # Healthy base diagnostic
    res = engine.evaluate("INC-007", diag)
    assert res is None
