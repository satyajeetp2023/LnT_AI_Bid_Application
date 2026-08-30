import io

from docx import Document
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


def test_iso_duration_is_parsed_as_hours_not_days():
    xml=b"""<?xml version="1.0"?>
<Project>
  <Activity>
    <Id>A100</Id><Name>Foundation</Name>
    <OriginalDuration>PT80H</OriginalDuration>
    <TotalFloat>PT16H</TotalFloat>
  </Activity>
</Project>"""
    ing=ingest_schedule("xml",xml)
    task=ing["tables"]["TASK"][0]
    assert task["target_drtn_hr_cnt"]==80
    assert task["total_float_hr_cnt"]==16


def test_word_schedule_table_is_extracted():
    document=Document()
    table=document.add_table(rows=1,cols=6)
    headers=["Activity ID","Activity Name","WBS","Start Date","Finish Date","Duration"]
    for i,value in enumerate(headers):
        table.rows[0].cells[i].text=value
    row=table.add_row().cells
    values=["A100","OHE Foundation","OHE","2026-01-01","2026-01-10","10 days"]
    for i,value in enumerate(values):
        row[i].text=value
    stream=io.BytesIO();document.save(stream)
    ing=ingest_schedule("docx",stream.getvalue())
    assert ing["detected"] is True
    assert ing["fidelity"]=="Report / Limited"
    assert ing["tables"]["TASK"][0]["task_code"]=="A100"
    assert ing["tables"]["TASK"][0]["target_drtn_hr_cnt"]==80


def test_mpp_is_recognized_as_native_binary_but_not_falsely_parsed():
    ing=ingest_schedule("mpp",b"not-a-real-mpp")
    assert ing["detected"] is False
    assert ing["source_kind"]=="Microsoft Project MPP"
    assert ing["fidelity"]=="Native Binary / Parser Required"
