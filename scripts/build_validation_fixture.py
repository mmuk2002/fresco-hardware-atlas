"""Source-transcribed development labels; never reads extractor predictions.

These pages were inspected while developing the parser. They are regression
evidence, not a held-out estimate of accuracy on unseen projects.
"""
import json
from pathlib import Path


def component(qty, description, catalog_number, mfr=None, finish=None):
    return dict(qty=qty, description=description, catalog_number=catalog_number,
                mfr=mfr, finish=finish, notes=None)


def main():
    c = component
    annotations = [
        dict(source_path='2353 Gerrard Street Shelter/Hdw Spec & Sch-IFT_5.pdf', page=19, set_number='AL 01', components=[
            c(1,'Continuous Hinge(s)','780-112HD x LAR EPT Prep','HA','CLR'),
            c(1,'Power Transfer(s)','2-679-0623','HA','ALM'),
            c(1,'Exit Device','40-CBK ER EX EC2','DE','630'),
            c(1,'Mortise Cylinder(s)','3902 x LAR','HA','US26D'),
            c(1,'Construction Core(s)','3982-BLU','HA','BLU'),
            c(1,'SFIC Core(s)','3969-C','HA','US26D'),
            c(1,'Offset Door Pull(s)','910P 36','HA','US10B'),
            c(1,'Overhead Stop(s)','7016 SRF','HA','US32D'),
            c(1,'Single Operator','8318 Push','HA','ALM'),
            c(1,'Thermally Broken Threshold','420S x LAR','HA','MIL'),
            c(1,'Weatherstrip','By Frame Mfr./Supplier'),
            c(1,'Sweep(s)','750S N x LAR','HA','CLR'),
            c(1,'Rain Drip','810S x LAR','HA','MIL'),
            c(1,'Door Position Switch(es)','2-679-0626','HA'),
            c(2,'Actuator(s)','8228-02H/00','HA','US32D'),
            c(1,'Reader/Keypad','By Security Provider'),
            c(1,'Intercom','By Security Provider'),
            c(1,'Remote Exit Button','By Security Provider'),
            c(1,'Power Supply','By Security Provider'),
            c(1,'Wiring Diagrams','Wiring Diagrams'),
        ]),
        dict(source_path='AMI _Copy_/c43c36d9-000_Full_Volume_ATC_Renovation_Bid_Specs_Volume_1__1_.pdf', page=397, set_number='01A', components=[
            c(6,'HINGE','5BB1 4.5 X 4.5 NRP','IVE','652'),
            c(1,'CONST LATCHING BOLT','FB51P','IVE','630'),
            c(1,'DUST PROOF STRIKE','DP2','IVE','626'),
            c(1,'PASSAGE SET','L9010 17A','SCH','626'),
            c(2,'OH STOP','100S','GLY','630'),
            c(2,'SURFACE CLOSER','4040XP','LCN','689'),
            c(2,'KICK PLATE','8400 8" X 1" LDW B-CS','IVE','630'),
            c(1,'GASKETING','488FSBK PSA','ZER','BK'),
            c(1,'WEATHERSTRIPPING','8217SBK PSA','ZER','BK'),
        ]),
        dict(source_path='JC Ryan 2/087100 - Door Hardware-6.pdf', page=28, set_number='1.0', components=[
            c(1,'Continuous Hinge','CFMxxHD1-M (Length Required)','Pemko'),
            c(1,'Storeroom/Closet Lock','8204 LNMI','Sargent'),
            c(1,'Door Closer','UNI7500','Norton'),
            c(1,'Jamb Gasketing','290_S (Finish to match door/frame color)','Pemko'),
            c(1,'Head Gasketing','2891_S (Finish to match door/frame color)','Pemko'),
            c(1,'Door Bottom','216AFG','Pemko'),
            c(1,'Threshold','To Suit Sill Condition'),
        ]),
        dict(source_path='JC Ryan 2/087100 - Door Hardware-6.pdf', page=28, set_number='2.0', components=[
            c(None,'Hinge, Full Mortise','T4A3786','McKinney'),
            c(1,'Electric Power Transfer','EL-CEPT','Securitron'),
            c(1,'Fail Safe Exit Device, RX','[12] 55 PE8875 ETMI','Sargent'),
            c(1,'Surface Closer (Mounted on stairwell side of door)','7500','Norton'),
            c(1,'Kick Plate','K1050 x 10" High x CSK x 4BE','Rockwood'),
            c(1,'Stop','RM860 / 446 / 9-ADJ Series Per Conditions','Rockwood'),
            c(1,'Gasketing','S44BL','Pemko'),
            c(1,'Door Sweep','315CN','Pemko'),
            c(1,'Threshold','151A','Pemko'),
            c(1,'Door/Frame Harness',None),
        ]),
        dict(source_path='Valor Acres Building E/087100-DOOR-HARDWARE_Rev_2.pdf', page=7, set_number='01', components=[
            c(3,'BB HINGE',None,None,'BLK'),
            c(1,'ENTRY SET (SCHLAGE LATITUDE LEVER STYLE)',None,None,'BLK'),
            c(1,'DEADBOLT W/ KEYFOB ACCESS',None,None,'BLK'),
            c(1,'OH STOP',None,None,'BLK'),
            c(1,'SURFACE CLOSER',None,None,'BLK'),
            c(1,'SEALS (SMOKE)',None,None,'BLK'),
            c(1,'DOOR VIEWER',None,None,'BLK'),
        ]),
        dict(source_path='Forest Park School/Project Manual (1).pdf', pages=[262,263], set_number='1', components=[
            c(3,'Hinge','FBB179 NRP 4.5X4.5','BES','26D'),
            c(1,'Mortise Lock-Storeroom','45H-0D-15H LESS CYLINDER','BES','626'),
            c(1,'Mortise Cylinder','CR1000-XXX-CAM-7 59D1 (TIE TO SYSTEM)','C-R','626'),
            c(1,'Surface Overhead Stop','4420 SERIES','ABH','US32D'),
            c(3,'Silencers','500','BRN','Gray'),
        ]),
    ]
    Path('tests/fixtures/validation_sets.json').write_text(json.dumps(annotations, indent=2), encoding='utf-8')
    initial = json.loads(Path('tests/fixtures/gold_sets.json').read_text(encoding='utf-8'))
    Path('tests/fixtures/development_gold.json').write_text(json.dumps(initial + annotations, indent=2), encoding='utf-8')
    print(f'{len(initial + annotations)} annotated sets, {sum(len(s["components"]) for s in initial + annotations)} components')


if __name__ == '__main__':
    main()
