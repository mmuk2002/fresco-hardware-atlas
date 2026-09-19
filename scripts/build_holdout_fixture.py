"""Build prediction-blind labels transcribed from the fixed rendered holdout pages."""
from __future__ import annotations

import json
from pathlib import Path


MISSING = object()


def component(qty, description, catalog_number=MISSING, mfr=MISSING, finish=MISSING):
    value = {"qty": qty, "description": description}
    for key, item in (("catalog_number", catalog_number), ("mfr", mfr), ("finish", finish)):
        if item is not MISSING:
            value[key] = item
    return value


def main() -> None:
    c = component
    gold = [
        {
            "source_path": "81-85 Bridgeport/08-70-00-Hardware-Schedule.pdf", "page": 22,
            "set_number": "37", "status": "active", "components": [
                c(6, "Standard Hinge", 'TA2314 4 1/2" x 4 1/2" C32D NRP', None, "C32D"),
                c(1, "Lockset", "T581 P6 LAT/LAT 626/626 G 23981152", None, "626/626"),
                c(1, "Flush Bolt", "FB31P-12-MD C32D", None, "C32D"),
                c(1, "Z Astragal", "Z Astragal Factory Applied By Door Manufacturer", None, None),
                c(2, "Surface Closer", "SC71A Rw/ PA 689", None, "689"),
                c(2, "Overhead Door Holder", "104H C26D", None, "C26D"),
                c(2, "Kick Plate", '8400 C32D 8" x 36 1/2"', None, "C32D"),
                c(2, "Weatherstripping", 'W-38S-CA x 38"', None, "CA"),
                c(1, "Weatherstripping", 'W-2050S-CA x 76"', None, "CA"),
                c(2, "Jamb Weatherstripping", 'W-50S-CAx84" Opening', None, "CA"),
                c(1, "Threshold", 'CT-65(Stock Size) x 76"', None, None),
            ],
        },
        {
            "source_path": "81-85 Bridgeport/08-70-00-Hardware-Schedule.pdf", "page": 22,
            "set_number": "38", "status": "active", "components": [
                c(3, "Standard Hinge", 'TA714 4 1/2" x 4" C26D', None, "C26D"),
                c(1, "Lockset", "W561 P6 LAT/LAT 626/626 G", None, "626/626"),
                c(1, "Surface Closer", "SC81A Rw/ PA 689", None, "689"),
                c(1, "Wall Door Stop", "S120 C26D", None, "C26D"),
                c(1, "Gasketing", "W-22AL 1/965 x 2/2134", None, None),
                c(1, "Kick Plate", '8400 C32D 8" x 36 1/2"', None, "C32D"),
            ],
        },
        {
            "source_path": "81-85 Bridgeport/08-70-00-Hardware-Schedule.pdf", "page": 22,
            "set_number": "39", "status": "active", "components": [
                c(3, "Standard Hinge", 'TA714 4 1/2" x 4" C26D', None, "C26D"),
                c(1, "Lockset", "W581 P6 LAT/LAT 626/626 G", None, "626/626"),
                c(1, "Surface Closer", "SC81A Rw/ PA 689", None, "689"),
                c(1, "Wall Door Stop", "S120 C26D", None, "C26D"),
                c(1, "Gasketing", "W-22AL 1/965 x 2/2134", None, None),
                c(1, "Kick Plate", '8400 C32D 8" x 36 1/2"', None, "C32D"),
            ],
        },
        {
            "source_path": "HFH DG - HOSPITAL/08 71 00 - DOOR HARDWARE.pdf", "pages": [180, 181],
            "set_number": "267", "status": "active", "components": [
                c(6, "HEAVYWEIGHT HINGE", "5BB1HW 4.5 X 4.5 - NRP AT OUTSWINGING LOCKING DOORS", "IVE", "652"),
                c(1, "CONST LATCHING BOLT", "FB51T/FB61T - AS REQUIRED", "IVE", "630"),
                c(1, "PASSAGE SET", "9K30N 15D", "BES", "626"),
                c(1, "SURFACE CLOSER", "4040XP REG TBSRT/ 4040XP EDA TBSRT - AS REQUIRED", "LCN", "689"),
                c(2, "KICK PLATE", '8400 10" HIGH LDW B-CS', "IVE", "630"),
                c(2, "WALL STOP", "WS401/402CCV", "IVE", "626"),
            ],
        },
        {
            "source_path": "HFH DG - HOSPITAL/08 71 00 - DOOR HARDWARE.pdf", "page": 181,
            "set_number": "268", "status": "active", "components": [
                c(6, "HEAVYWEIGHT HINGE", "5BB1HW 4.5 X 4.5 - NRP AT OUTSWINGING LOCKING DOORS", "IVE", "652"),
                c(2, "FIRE EXIT HARDWARE", "9827-EO-F-LBR/LBRAFL-499F-SNB", "VON", "626"),
                c(2, "DELAYED SURFACE CLOSER", "4041 DEL REG TBSRT/ 4041 DEL EDA TBSRT - AS REQUIRED", "LCN", "689"),
                c(2, "KICK PLATE", '8400 10" HIGH LDW B-CS', "IVE", "630"),
                c(2, "WALL STOP", "WS401/402CCV", "IVE", "626"),
            ],
        },
        {
            "source_path": "Morris Bank/030f2d1d-Morris_Bank_Macon_-Spec_Manual_Issued_for_Const._1-26-26_FULL_SPECS.pdf",
            "page": 251, "set_number": "203", "status": "active", "components": [
                c(4, "Hinges", "MPB79 4 1/2 x 4 1/2 NRP", "MC", "10BE"),
                c(1, "Lockset", '70 10XG05 LL 2 3/4" BS', "SA", "10BE"),
                c(1, "Construction Core", "7190224", "BE", None),
                c(1, "Wall Stop", "409", "RO", "10BE"),
                c(1, "SFIC", "33700006 N 26 DAKM", "MED1", None),
                c(3, "Door Silencer", "608-RKW", "RO", "BLK"),
            ],
        },
        {
            "source_path": "SAT TDP/2025.12.19 - SAT TDP - Project Manual.pdf", "page": 807,
            "set_number": "E210T", "status": "active", "components": [
                c(8, "HINGE", "5BB1 4.5 X 4.5 (PROVIDE NRP @ OUTSWING, LOCKABLE DOORS)", "IVE", "652"),
                c(1, "CONST LATCHING BOLT", "FB51P/FB61P AS REQ", "IVE", "630"),
                c(1, "DUST PROOF STRIKE", "DP2", "IVE", "626"),
                c(1, "MORTISE LOCK", "72-8204 FEJ 26D STOREROOM FUNCTION", "SAR", "626"),
                c(1, "XT INTELLIGENT KEY SYSTEM CORE", "MATCH FACILITY SYSTEM AS REQUIRED", "MED", "626"),
                c(1, "SURFACE CLOSER", "4040XP RW/PA TBWMS X MTG BRKT, SPCR & PLATE AS REQ", "LCN", "689"),
                c(2, "KICK PLATE", '8400 10" X 1" LDW B-CS', "IVE", "630"),
                c(2, "WALL STOP", "WS406/407CCV", "IVE", "630"),
                c(1, "GASKETING", "488S PSA H & J (USE SILENCERS @ NON-RATED DOORS)", "ZER", "BK"),
                c(1, "MEETING STILE", "8193AA (2 PCS - 1 SET) (OMIT @ NON-RATED DOORS)", "ZER", "AA"),
            ],
        },
        {
            "source_path": "SAT TDP/2025.12.19 - SAT TDP - Project Manual.pdf", "page": 807,
            "set_number": "E210TW", "status": "active", "components": [
                c(8, "HINGE", "5BB1HW 5 X 4.5 (PROVIDE NRP @ OUTSWING, LOCKABLE DOORS)", "IVE", "652"),
                c(1, "CONST LATCHING BOLT", "FB51P/FB61P AS REQ", "IVE", "630"),
                c(1, "DUST PROOF STRIKE", "DP2", "IVE", "626"),
                c(1, "MORTISE LOCK", "72-8204 FEJ 26D STOREROOM FUNCTION", "SAR", "626"),
                c(1, "XT INTELLIGENT KEY SYSTEM CORE", "MATCH FACILITY SYSTEM AS REQUIRED", "MED", "626"),
                c(1, "SURFACE CLOSER", "4040XP RW/PA TBWMS X MTG BRKT, SPCR & PLATE AS REQ", "LCN", "689"),
                c(2, "KICK PLATE", '8400 10" X 1" LDW B-CS', "IVE", "630"),
                c(2, "WALL STOP", "WS406/407CCV", "IVE", "630"),
                c(1, "GASKETING", "488S PSA H & J (USE SILENCERS @ NON-RATED DOORS)", "ZER", "BK"),
                c(1, "MEETING STILE", "8193AA (2 PCS - 1 SET) (OMIT @ NON-RATED DOORS)", "ZER", "AA"),
            ],
        },
        {
            "source_path": "SJC Well Behavioral/89671ede-20260218_SJC_BeWell_Bldg_B_85__DESIGN_UPDATE_-_SPECIFICATIONS.pdf",
            "page": 740, "set_number": "E11", "status": "active", "components": [
                c(None, "Hinge-HT", "4C51 HT NRP", "PBB", "630"),
                c(1, "Hinge-Power Transfer", "4C51EL HT", "PBB", "630"),
                c(1, "Fail Secure Cyl. Lock", "XCDC-86-S-RQE 24VDC", "TOW", "626"),
                c(1, "Cylinder", "Per project", "TBD", "626"),
                c(1, "OH Surface Closer", "4040XP/4040XP EDA", "LCN", "689"),
                c(1, "Door Stop", "Per Specification"),
                c(1, "Overhead Rain Drip", "16A (As Req)", "NGP", "628"),
                c(1, "Door Sweep", "600A", "NGP", "628"),
                c(1, "Weatherstrip", "700Nx700EN", "NGP", "719"),
                c(1, "Threshold", "To Suit Sill Condition", "PEM", "719"),
                c(1, "Card Reader", "By Division 28"),
                c(1, "Door Position Switch", "By Division 28"),
                c(1, "Lock Power Supply", "By Division 28"),
            ],
        },
        {
            "source_path": "StarHardware/9839d1a1-Division_8_Specs_-_Commons_Lane.pdf", "page": 101,
            "set_number": "31", "status": "active", "components": [
                c(None, "Hinges", "5BB1HW (size & quantity per 08 71 00)", "IV", "622"),
                c(1, "Fire Rated Rim Exit/Panic Device", mfr="VO", finish="622"),
                c(1, "I/C Cylinders (Rim or Mortise)", mfr="SC", finish="622"),
                c(1, "Permanent Core", "20-030", "SC", "622"),
                c(1, "Surface Closer", "4050A x REG (installed pull-side)", "LC", "693"),
                c(1, "Kick Plate", mfr="TR", finish="630"),
                c(1, "Floor Stop", "1214", "TR", "622"),
                c(1, "Seals"), c(1, "Door Bottom"), c(1, "Terrace Threshold"),
                c(1, "REX Device (security/alarm notification)"),
                c(1, "Door Position Switches (also known as Alarm/Door Contacts)"),
                c(1, "Power Supply"),
                c(1, "Coordination task for security and/or electrical design and additional non-Division 08 Section scope (including but not limited to wire / connectivity from ground or ceiling through frame to electrified hardware)"),
            ],
        },
        {
            "source_path": "The Door Company _Copy_/Vantage TX-22 Div 01, 08.pdf", "page": 418,
            "set_number": "D201", "status": "active", "components": [
                c(3, "HINGE", "5BB1HW 4.5 X 4.5", "IVE", "652"),
                c(1, "STOREROOM LOCK", "L9080T 17L", "SCH", "626"),
                c(1, "PERMANENT CORE", "COORDINATE WITH OWNER", "SCH", "626"),
                c(1, "SURFACE CLOSER", "4040XP", "LCN", "689"),
                c(1, "KICK PLATE", '8400 10" X 2" LDW B-CS', "IVE", "630"),
                c(1, "WALL STOP", "WS406/407CVX", "IVE", "630"),
                c(1, "GASKETING", "488SBK PSA", "ZER", "BK"),
                c(1, "DOOR POSITION SWITCH BY DIV 28", None, None, None),
            ],
        },
        {
            "source_path": "The Door Company _Copy_/Vantage TX-22 Div 01, 08.pdf", "pages": [418, 419],
            "set_number": "D204Z", "status": "active", "components": [
                c(2, "CONT. HINGE", "224XY", "IVE", "628"),
                c(1, "CONST LATCHING BOLT", "FB51P", "IVE", "630"),
                c(1, "DUST PROOF STRIKE", "DP2", "IVE", "626"),
                c(1, "STOREROOM LOCK", "L9080T 17L", "SCH", "626"),
                c(1, "PERMANENT CORE", "COORDINATE WITH OWNER", "SCH", "626"),
                c(1, "COORDINATOR", "COR X FL", "IVE", "628"),
                c(2, "MOUNTING BRACKET", "MB, TO SUIT HM FRAME (TO SUIT FRAME)", "IVE", "689"),
                c(2, "SURFACE CLOSER", "4040XP SCUSH", "LCN", "689"),
                c(2, "KICK PLATE", '8400 10" X 2" LDW B-CS', "IVE", "630"),
                c(1, "RAIN DRIP", "142AA", "ZER", "AA"),
                c(1, "GASKETING", "488SBK PSA", "ZER", "BK"),
                c(1, "ASTRAGAL", "43STST", "ZER", "STST"),
                c(2, "DOOR SWEEP", "8197AA", "ZER", "AA"),
                c(1, "THRESHOLD", "655A-MSLA-10", "ZER", "A"),
                c(2, "DOOR POSITION SWITCH BY DIV 28", None, None, None),
                c(1, "LOCAL ALARM BY DIV 28", None, None, None),
            ],
        },
        {
            "source_path": "Village of Oswego New Public Works Facility  _Copy_/SPECIFICATIONS VOLUME 1.pdf",
            "page": 437, "set_number": "44", "status": "active", "components": [
                c(3, "HINGE", "5BB1HW 4.5 X 4.5 NRP", "IVE", "630"),
                c(1, "STOREROOM LOCK", "L9080T.03.626.A.626.03.626.A.626", "SCH", "626"),
                c(1, "FSIC PRIMUS PERMANENT CORE", "20-740-XP CKC - MATCH EXISTING KEYWAY SYSTEM", "SCH", "626"),
                c(1, "SURFACE CLOSER", "4040XP SCUSH TBSRT", "LCN", "689"),
                c(1, "ARMOR PLATE", '8400 34" X AS REQ B-CS TKTX', "IVE", "630"),
                c(1, "GASKETING SET", "188SBK PSA", "ZER", "BK"),
                c(1, "DOOR SWEEP", "39A", "ZER", "A"),
                c(1, "HD THRESHOLD", "655A-V3-226", "ZER", "A"),
            ],
        },
        {
            "source_path": "Village of Oswego New Public Works Facility  _Copy_/SPECIFICATIONS VOLUME 1.pdf",
            "page": 437, "set_number": "45", "status": "active", "components": [
                c(3, "HINGE", "5BB1HW 4.5 X 4.5 NRP", "IVE", "630"),
                c(1, "PASSAGE SET", "L9010.03.626.A.626.03.626.A.626", "SCH", "626"),
                c(1, "SURFACE CLOSER", "4040XP SCUSH TBSRT", "LCN", "689"),
                c(1, "KICK PLATE", '8400 10" X AS REQ B-CS TKTX', "IVE", "630"),
                c(1, "GASKETING SET", "188SBK PSA", "ZER", "BK"),
                c(1, "DOOR SWEEP", "39A", "ZER", "A"),
                c(1, "HD THRESHOLD", "655A-V3-226", "ZER", "A"),
            ],
        },
    ]
    output = Path("tests/fixtures/heldout_gold.json")
    output.write_text(json.dumps(gold, indent=2), encoding="utf-8")
    print(f"{len(gold)} held-out sets, {sum(len(item['components']) for item in gold)} components")


if __name__ == "__main__":
    main()
