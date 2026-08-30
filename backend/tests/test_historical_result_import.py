import csv
import io

from openpyxl import Workbook

from app.services.historical_result_import import preview_historical_result


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
