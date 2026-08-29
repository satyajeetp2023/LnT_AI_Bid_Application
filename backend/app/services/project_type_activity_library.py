from dataclasses import dataclass


@dataclass(frozen=True)
class ActivityTemplate:
    activity:str
    subactivities:tuple[str,...]=()
    keywords:tuple[str,...]=()
    confidence:float=.75


RAILWAY_COMMON=(
    ActivityTemplate("Project mobilization and site establishment",("Mobilization","Site offices and facilities","Survey control establishment"),("mobilization","site establishment","survey"),.78),
    ActivityTemplate("Design and engineering",("Design basis and criteria","Detailed design","Drawings and calculations","Design review and approvals"),("design","drawings","calculation","approval"),.82),
    ActivityTemplate("Procurement and supply",("Vendor approvals","Manufacturing","Factory inspection / testing","Delivery to site"),("procurement","vendor","manufacturing","delivery"),.80),
    ActivityTemplate("Interface and approvals",("Interface coordination","Statutory / employer approvals","Access and work-front release"),("interface","approval","access","work front"),.76),
    ActivityTemplate("Testing and commissioning",("Inspection and pre-commissioning","Integrated testing","Commissioning","Trial / acceptance"),("testing","commissioning","acceptance","trial"),.84),
    ActivityTemplate("Handover and closeout",("As-built documentation","Training","Handover","Defect / punch-list closure"),("as built","handover","training","defect"),.78),
)

OHE=(
    ActivityTemplate("OHE foundations",("Setting out","Excavation","Foundation installation / concreting","Curing and readiness"),("ohe","foundation","mast","excavation"),.90),
    ActivityTemplate("OHE mast and portal erection",("Mast erection","Portal / boom erection","Alignment and grouting"),("mast","portal","boom","erection"),.92),
    ActivityTemplate("OHE wiring",("Bracket assembly","Contact and catenary stringing","Droppers and registration","Sectioning / overlaps","Final adjustment"),("contact wire","catenary","dropper","registration","wiring"),.94),
    ActivityTemplate("OHE bonding and earthing",("Bonding","Earthing connections","Continuity checks"),("bonding","earthing","continuity"),.88),
    ActivityTemplate("OHE inspection and energization",("Geometry checks","Electrical checks","Section readiness","Energization"),("ohe","energization","geometry","inspection"),.90),
)

PSI=(
    ActivityTemplate("Traction substation / switching station civil works",("Survey and layout","Foundations","Building / equipment bases","Cable trenches"),("tss","ssp","sp","foundation","cable trench"),.88),
    ActivityTemplate("PSI equipment installation",("Transformers","Switchgear","Protection and control panels","Auxiliary systems"),("transformer","switchgear","protection","panel"),.92),
    ActivityTemplate("Traction power cabling",("Cable laying","Termination","Testing"),("power cable","termination","cable laying"),.90),
    ActivityTemplate("PSI testing and energization",("Equipment testing","Protection testing","Interlocks","Energization"),("protection","relay","interlock","energization"),.92),
)

SCADA=(
    ActivityTemplate("SCADA design and configuration",("Architecture","Point list / I/O mapping","Configuration","Factory acceptance testing"),("scada","io","point list","configuration","fat"),.92),
    ActivityTemplate("SCADA field installation",("RTU / PLC panels","Communication equipment","Field wiring","Network integration"),("rtu","plc","communication","network"),.90),
    ActivityTemplate("SCADA testing and integration",("Point-to-point testing","Communication testing","Integrated testing","SAT"),("scada","sat","point to point","integration"),.92),
)

TRACK=(
    ActivityTemplate("Track formation and earthwork",("Subgrade preparation","Blanketing","Formation finishing"),("earthwork","formation","subgrade","blanket"),.88),
    ActivityTemplate("Track materials and laying",("Sleeper / rail logistics","Track panel / long rail laying","Ballasting","Tamping and alignment"),("rail","sleeper","ballast","tamping","track laying"),.92),
    ActivityTemplate("Turnouts and special trackwork",("Turnout installation","Alignment","Testing"),("turnout","points","crossing"),.88),
)

SIGNALLING=(
    ActivityTemplate("Signalling design and approvals",("Signalling plan","Control tables","Application logic","Design approvals"),("signalling","control table","logic","plan"),.90),
    ActivityTemplate("Signalling equipment installation",("Indoor equipment","Outdoor equipment","Cables","Track circuits / axle counters"),("signal","axle counter","track circuit","relay","ei"),.92),
    ActivityTemplate("Signalling testing and commissioning",("Wire count / continuity","Functional testing","Integrated testing","Commissioning"),("signalling","testing","commissioning"),.92),
)

TELECOM=(
    ActivityTemplate("Telecom backbone and OFC",("Route survey","Duct / cable route preparation","OFC laying","Splicing and termination","OTDR / link testing"),("ofc","fiber","fibre","telecom","duct","splicing"),.90),
    ActivityTemplate("Telecom system installation",("Transmission equipment","IP / data network","PA / PIS / CCTV / clock systems","Power supply and racks"),("telecom","cctv","pis","pa system","network","ip"),.88),
    ActivityTemplate("Telecom integration and commissioning",("Equipment configuration","Subsystem testing","Integrated testing","Commissioning"),("telecom","integration","commissioning","testing"),.90),
)

CIVIL_STRUCTURES=(
    ActivityTemplate("Civil survey and enabling works",("Topographic survey","Utility identification / diversion","Access and temporary works"),("survey","utility","access","temporary works"),.80),
    ActivityTemplate("Earthwork and drainage",("Excavation / filling","Formation","Drainage works","Slope / erosion protection"),("earthwork","drainage","formation","excavation"),.86),
    ActivityTemplate("Bridges / culverts / structural works",("Foundations","Substructure","Superstructure","Waterproofing / finishing"),("bridge","culvert","structure","pier","abutment"),.86),
    ActivityTemplate("Station / building civil works",("Foundations","Structural frame","Architectural finishes","MEP interface readiness"),("station","building","platform","architectural"),.84),
)


def project_type_activity_library(project_type:str,scope_text:str="")->list[ActivityTemplate]:
    project=(project_type or "").lower()
    scope=(scope_text or "").lower()
    text=f"{project} {scope}"
    groups=[RAILWAY_COMMON]
    if any(x in text for x in ("ohe","overhead equipment","overhead electrification","catenary","contact wire","traction electrification")):groups.append(OHE)
    if any(x in text for x in ("psi","tss","ssp","traction substation","traction power","switching station","transformer")):groups.append(PSI)
    if any(x in text for x in ("scada","remote control","telecontrol","rtu","plc")):groups.append(SCADA)
    if any(x in text for x in ("track","formation","permanent way","rail laying","sleeper","ballast","turnout")):groups.append(TRACK)
    if any(x in text for x in ("signal","signalling","interlocking","axle counter","track circuit","control table")):groups.append(SIGNALLING)
    if any(x in text for x in ("telecom","ofc","fiber optic","fibre optic","cctv","pis","public address","ip network")):groups.append(TELECOM)
    if any(x in text for x in ("civil","earthwork","bridge","culvert","station building","platform","drainage","structure")):groups.append(CIVIL_STRUCTURES)
    result=[];seen=set()
    for group in groups:
        for item in group:
            key=item.activity.lower()
            if key in seen:continue
            seen.add(key);result.append(item)
    return result
