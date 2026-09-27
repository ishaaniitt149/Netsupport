"""Unit tests for the RCA parser."""

from app.rca.parser import CiscoRCAParser


def test_rca_parser_full():
    parser = CiscoRCAParser()
    raw_text = """
    --------------------------------------------------
    RCA Diagnostic Report for DEV-001
    --------------------------------------------------
    
    >> show interfaces Gi0/1
    Interface is UP
    CRC errors: 1450
    Input errors: 1510
    Output errors: 23
    Interface flaps: 8
    
    >> show processes cpu
    CPU utilization: 42.5%
    
    >> show memory
    Memory utilization: 51%
    
    >> show ip bgp summary
    Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
    10.0.0.2        4        65001    1434    1435      142    0    0 23:14:02        1
    
    >> show ip ospf neighbor
    Neighbor ID     Pri   State           Dead Time   Address         Interface
    192.168.1.2       1   FULL/BDR        00:00:32    10.1.1.2        GigabitEthernet0/1
    
    >> show logging
    Syslog logging: enabled
    """

    parsed = parser.parse("INC-123_rca.txt", raw_text)

    assert parsed.rca_file_id == "INC-123_rca.txt"
    assert parsed.cpu_utilization == 42.5
    assert parsed.memory_utilization == 51.0
    assert parsed.interface_status == "UP"
    assert parsed.crc_errors == 1450
    assert parsed.input_errors == 1510
    assert parsed.output_errors == 23
    assert parsed.interface_flaps == 8
    assert parsed.bgp_status == "ESTABLISHED"
    assert parsed.ospf_status == "FULL"
    assert "Syslog logging: enabled" in parsed.relevant_logs


def test_rca_parser_missing_fields():
    parser = CiscoRCAParser()
    # Missing all data except CPU and bgp idle
    raw_text = """
    >> show processes cpu
    CPU utilization: 99%
    
    >> show ip bgp summary
    Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd
    10.0.0.2        4        65001    1434    1435      142    0    0 23:14:02        Active
    """

    parsed = parser.parse("INC-456_rca.txt", raw_text)

    assert parsed.cpu_utilization == 99.0
    assert parsed.memory_utilization is None
    assert parsed.interface_status is None
    assert parsed.bgp_status == "ACTIVE"
    assert parsed.ospf_status is None
    assert parsed.relevant_logs is None
