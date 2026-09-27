# Data Dictionary: Synthetic Cisco Network Devices

## File: `data/synthetic/devices.csv`

**Entity:** Cisco Network Device Asset Inventory  
**Classification:** `SYNTHETIC` (Simulated enterprise test dataset)  
**Row Count:** 100 records  
**Primary Key:** `device_id`  
**Unique Alternate Keys:** `serial_number`, `hostname`  

---

## Field Specifications

| Column Name | Data Type | Nullable | Domain / Constraints | Description & Purpose | Example Value |
|---|---|---|---|---|---|
| `device_id` | `VARCHAR(16)` | No | Pattern: `^DEV-CSCO-\d{4}$` | Unique synthetic inventory asset identifier | `DEV-CSCO-0001` |
| `hostname` | `VARCHAR(64)` | No | Fully qualified network naming convention | Internal DNS hostname representing site, role, and chassis index | `nyc-acc-sw-001.corp.internal` |
| `vendor` | `VARCHAR(16)` | No | Constant: `Cisco` | Hardware manufacturing vendor | `Cisco` |
| `model` | `VARCHAR(64)` | No | Real Cisco platform models: Catalyst 9200/9300/9500, Nexus 9300, ISR 4451, Catalyst 8300, ASR 1001-X, Firepower 2130 | Hardware platform and chassis type | `Cisco Catalyst 9300-48UXM` |
| `serial_number` | `VARCHAR(16)` | No | Cisco 11-char serial regex: `^[A-Z]{3}\d{4}[A-Z0-9]{4}$` | Hardware chassis serial number; indicates factory, build year, week, and unique unit code | `JAE2409RPW2` |
| `firmware_version` | `VARCHAR(32)` | No | Real Cisco train formats: IOS-XE (`17.x.x`), NX-OS (`10.x(x)M`), FTD (`7.x.x`) | Active operating system firmware release | `17.09.04a` |
| `location` | `VARCHAR(64)` | No | Enterprise datacenter, colocation, or campus site name | Physical installation site | `New York Data Center` |
| `region` | `VARCHAR(32)` | No | Values: `AMER-EAST`, `AMER-WEST`, `AMER-CENTRAL`, `EMEA-WEST`, `EMEA-CENTRAL`, `APAC-SOUTH`, `APAC-EAST` | Global operational region | `AMER-EAST` |
| `device_type` | `VARCHAR(32)` | No | Values: `Access Switch`, `Core Switch`, `Distribution Switch`, `Data Center Switch`, `Data Center Spine`, `WAN Router`, `SD-WAN Edge Router`, `Aggregation Router`, `Security Gateway` | Functional network infrastructure role | `Access Switch` |
| `criticality` | `VARCHAR(16)` | No | Values: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` | Business operational impact rating if the device fails | `CRITICAL` |
| `interface_count` | `INTEGER` | No | Range: `1` to `128` (Matches hardware platform specs) | Total physical ports provisioned on the chassis | `48` |
| `last_patch_date` | `DATE` | No | Format: `YYYY-MM-DD` (Within 180 days prior to baseline start date) | Date when OS firmware or security maintenance was last applied | `2025-12-04` |
| `customer` | `VARCHAR(64)` | No | Fictional enterprise names (e.g. `Apex Global Logistics`, `Zenith Retail Group`) | Multi-tenant or enterprise business unit ownership | `Zenith Retail Group` |
| `network_segment` | `VARCHAR(32)` | No | Values: `CORE-BACKBONE`, `CAMPUS-ACCESS`, `WAN-EDGE`, `DC-FABRIC`, `DMZ-SECURITY`, `BRANCH-OFFICE` | Architectural network zone / VRF | `BRANCH-OFFICE` |

---

## Integrity & Quality Validation Rules

1. **Uniqueness:**
   - `device_id` must be unique across all records.
   - `hostname` must be unique across all records.
   - `serial_number` must be unique across all records.
2. **Referential & Format Consistency:**
   - Every `model` belongs to a known Cisco platform archetype with matching `interface_count` and valid `firmware_version` releases.
   - Every `serial_number` conforms to Cisco's 11-character factory serial format.
3. **Date Consistency:**
   - `last_patch_date` must not be in the future relative to the generator's `start_date`.
4. **Synthetic Transparency:**
   - All records are generated programmatically using pseudorandom generators seeded deterministically (`random_seed=42`).
   - Customer names are strictly fictional.
