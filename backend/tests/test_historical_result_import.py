import csv
import io

import pytest
from openpyxl import Workbook

from app.services import historical_result_import
from app.services.historical_result_import import _preview_pdf_text,preview_historical_result


def test_csv_historical_result_preview_detects_ranked_prices_and_our_bid():
    stream=io.StringIO()
    writer=csv.writer(stream)
    writer.writerow(["Rank","Bidder Name","Bid Value","Currency","Our Bid"])
    writer.writerow(["L1","Competitor A","1000","INR","No"])
    writer.writerow(["L2","Larsen & Toubro","1080","INR","Yes"])
    writer.writerow(["L3","Competitor C","1120","INR","No"])
    result=preview_historical_result("csv",stream.getvalue().encode(),"result.csv")
    assert result["detected"] is True
    assert result["requires_review"] is True
    assert result["outcome_candidate"]["result_status"]=="Lost"
    assert result["outcome_candidate"]["our_rank"]==2
    assert result["prices"][0]["rank"]==1
    assert result["prices"][1]["is_ours"] is True


def test_xlsx_historical_result_preview_is_review_first_and_handles_duplicates():
    wb=Workbook();ws=wb.active
    ws.append(["Position","Tenderer","Quoted Price"])
    ws.append([1,"A",100])
    ws.append([1,"B",110])
    out=io.BytesIO();wb.save(out)
    result=preview_historical_result("xlsx",out.getvalue(),"result.xlsx")
    assert result["detected"] is True
    assert len(result["prices"])==1
    assert any("Duplicate rank" in x for x in result["warnings"])
    assert "No bid outcome" in result["note"]


def test_pdf_text_result_preview_extracts_ranked_bidders_for_review():
    text="""
    Tender Result Notice
    Rank Bidder Bid Value
    1 Competitor A 1000 INR
    2 Larsen & Toubro 1080 INR
    3 Competitor C 1125 INR
    """
    result=_preview_pdf_text(text,"result.pdf")
    assert result["detected"] is True
    assert result["requires_review"] is True
    assert len(result["prices"])==3
    assert result["outcome_candidate"]["our_rank"]==2
    assert result["outcome_candidate"]["result_status"]=="Lost"


def test_pdf_text_result_preview_falls_back_when_text_is_insufficient():
    result=_preview_pdf_text("scan","scan.pdf")
    assert result["detected"] is False
    assert result["requires_review"] is True
    assert any("vision/OCR" in x for x in result["warnings"])


def test_csv_preview_rejects_excessive_row_count(monkeypatch):
    monkeypatch.setattr(historical_result_import,"MAX_PREVIEW_ROWS",2)
    content=b"Rank,Bidder Name,Bid Value\n1,A,100\n2,B,110\n"
    with pytest.raises(ValueError,match="at most 2 rows"):
        preview_historical_result("csv",content,"too-many.csv")


def test_xlsx_preview_rejects_excessive_uncompressed_archive(monkeypatch):
    wb=Workbook();ws=wb.active
    ws.append(["Rank","Bidder Name","Bid Value"]);ws.append([1,"A",100])
    out=io.BytesIO();wb.save(out)
    monkeypatch.setattr(historical_result_import,"MAX_XLSX_UNCOMPRESSED_BYTES",1)
    with pytest.raises(ValueError,match="uncompressed workbook content"):
        preview_historical_result("xlsx",out.getvalue(),"large.xlsx")
