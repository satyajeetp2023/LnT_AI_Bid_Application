import io

from openpyxl import Workbook

from app.services.p6_xer import analyze_schedule_tables
from app.services.p6_schedule_optimizer import build_schedule_optimization_from_tables
from app.services.schedule_ingestion import ingest_schedule


def test_excel_schedule_normalizes_without_inventing_logic_or_float():
    wb=Workbook()
    ws=wb.active
    ws.title="Programme"
    ws.append(["Activity ID","Activity Name","WBS","Start","Finish","Duration"])
    ws.append(["A100","Foundation","Civil","2026-01-01","2026-01-10",10])
    ws.append(["A200","Mast Erection","OHE","2026-01-11","2026-01-20",10])
    stream=io.BytesIO();wb.save(stream)

    ing=ingest_schedule("xlsx",stream.getvalue())
    assert ing["detected"] is True
    assert ing["capabilities"]["activities"] is True
    assert ing["capabilities"]["logic"] is False
    assert ing["capabilities"]["float"] is False

    analysis=analyze_schedule_tables(ing["tables"],capabilities=ing["capabilities"])
    assert analysis["health"]["issue_counts"]["open_start"]==0
    assert analysis["health"]["issue_counts"]["open_finish"]==0
    assert analysis["health"]["issue_counts"]["negative_float"]==0
    assert analysis["criticality"]["critical_activities"]==[]

    advisor=build_schedule_optimization_from_tables(ing["tables"],capabilities=ing["capabilities"])
    assert all("open start" not in " ".join(x["issues"]).lower() for x in advisor["optimization"]["candidates"])
    assert all("negative total float" not in x["issues"] for x in advisor["optimization"]["candidates"])


def test_primavera_style_xml_normalizes_activity_and_relationship():
    xml=b"""<?xml version="1.0"?>
<Project>
  <Name>Railway Test</Name>
  <Activity>
    <ObjectId>1</ObjectId><Id>A100</Id><Name>Foundation</Name>
    <PlannedStartDate>2026-01-01</PlannedStartDate>
    <PlannedFinishDate>2026-01-10</PlannedFinishDate>
    <OriginalDuration>PT80H</OriginalDuration><TotalFloat>PT40H</TotalFloat>
  </Activity>
  <Activity>
    <ObjectId>2</ObjectId><Id>A200</Id><Name>Mast Erection</Name>
    <PlannedStartDate>2026-01-11</PlannedStartDate>
    <PlannedFinishDate>2026-01-20</PlannedFinishDate>
    <OriginalDuration>PT80H</OriginalDuration><TotalFloat>PT20H</TotalFloat>
  </Activity>
  <Relationship>
    <PredecessorActivityId>A100</PredecessorActivityId>
    <SuccessorActivityId>A200</SuccessorActivityId>
    <Type>Finish to Start</Type>
  </Relationship>
</Project>"""
    ing=ingest_schedule("xml",xml)
    assert ing["detected"] is True
    assert len(ing["tables"]["TASK"])==2
    assert len(ing["tables"]["TASKPRED"])==1
    assert ing["capabilities"]["logic"] is True
    assert ing["capabilities"]["float"] is True
