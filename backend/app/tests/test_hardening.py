import pytest
import io
import zipfile
from fastapi.testclient import TestClient
from app.main import app

def test_security_headers_are_present(client):
    response=client.get("/api/v1/health")
    assert response.status_code==200
    assert response.headers["x-content-type-options"]=="nosniff"
    assert response.headers["x-frame-options"]=="DENY"
    assert response.headers["referrer-policy"]=="no-referrer"


def test_disguised_executable_upload_is_rejected(client,bid_payload):
    bid=client.post("/api/v1/bids",json=bid_payload).json()
    response=client.post(
        f"/api/v1/bids/{bid['id']}/documents",
        files=[("files",("fake.pdf",b"MZ"+b"not really a pdf","application/pdf"))],
    )
    assert response.status_code==415
    assert "Executable content" in response.text


def test_read_only_member_cannot_preview_or_save_bid_result(client,bid_payload):
    bid=client.post("/api/v1/bids",json=bid_payload).json()
    add=client.post(f"/api/v1/bids/{bid['id']}/members",json={"user_id":2,"role":"Read Only"})
    assert add.status_code==200

    preview=client.post(
        f"/api/v1/bids/{bid['id']}/outcome/import-preview",
        files={"file":("result.csv",b"Rank,Bidder,Bid Value\n1,A,100\n","text/csv")},
        headers={"X-User-ID":"2"},
    )
    assert preview.status_code==403

    save=client.put(
        f"/api/v1/bids/{bid['id']}/outcome",
        json={"result_status":"Lost","prices":[]},
        headers={"X-User-ID":"2"},
    )
    assert save.status_code==403


def test_sensitive_api_requires_explicit_identity_header():
    anonymous=TestClient(app)
    response=anonymous.get("/api/v1/auth/me")
    assert response.status_code==422
    assert "X-User-ID" in response.text


def test_known_file_signature_mismatch_is_rejected(client,bid_payload):
    bid=client.post("/api/v1/bids",json=bid_payload).json()
    response=client.post(
        f"/api/v1/bids/{bid['id']}/documents",
        files=[("files",("misnamed.png",b"%PDF-1.7 fake pdf body","image/png"))],
    )
    assert response.status_code==415
    assert "does not match" in response.text


def test_invalid_office_zip_package_is_rejected(client,bid_payload):
    bid=client.post("/api/v1/bids",json=bid_payload).json()
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,"w") as archive:
        archive.writestr("random.txt","not an xlsx workbook")
    response=client.post(
        f"/api/v1/bids/{bid['id']}/documents",
        files=[("files",("fake.xlsx",buffer.getvalue(),"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))],
    )
    assert response.status_code==415
    assert "XLSX package structure is invalid" in response.text


def test_historical_comparison_uses_completed_visible_bid(client,bid_payload):
    current_payload={**bid_payload,"bid_id":"BID-CURRENT","tender_reference_no":"T-CURRENT","location":"Gujarat"}
    prior_payload={**bid_payload,"bid_id":"BID-PRIOR","tender_reference_no":"T-PRIOR","location":"Gujarat"}
    current=client.post("/api/v1/bids",json=current_payload).json()
    prior=client.post("/api/v1/bids",json=prior_payload).json()
    saved=client.put(
        f"/api/v1/bids/{prior['id']}/outcome",
        json={
            "result_status":"Lost",
            "our_rank":2,
            "our_bid_value":108,
            "prices":[
                {"bidder_name":"Competitor A","rank":1,"bid_value":100,"currency":"INR","is_ours":False},
                {"bidder_name":"L&T","rank":2,"bid_value":108,"currency":"INR","is_ours":True},
            ],
        },
    )
    assert saved.status_code==200
    response=client.get(f"/api/v1/bids/{current['id']}/historical-comparison")
    assert response.status_code==200
    body=response.json()
    assert body["summary"]["comparable_bids"]==1
    assert body["matches"][0]["bid_project_id"]==prior["id"]
    assert body["matches"][0]["similarity_score"]==100
    assert set(body["matches"][0]["matched_fields"])=={"project_type","client","contract_type","location"}
    assert "no win prediction" in body["methodology"].lower()
    intelligence=client.get("/api/v1/historical-bids/intelligence")
    assert intelligence.status_code==200
    competitor=next(x for x in intelligence.json()["competitors"] if x["name"]=="Competitor A")
    assert competitor["appearances"]==1
    assert competitor["l1_wins"]==1
    assert competitor["l1_rate_percent"]==100.0
    assert competitor["average_rank"]==1.0


def test_result_import_preview_is_audited_without_saving_outcome(client,bid_payload):
    bid=client.post("/api/v1/bids",json={**bid_payload,"bid_id":"BID-AUDIT","tender_reference_no":"T-AUDIT"}).json()
    payload=b"Rank,Bidder Name,Bid Value,Currency,Our Bid\n1,Competitor A,100,INR,No\n2,Larsen & Toubro,108,INR,Yes\n"
    preview=client.post(
        f"/api/v1/bids/{bid['id']}/outcome/import-preview",
        files={"file":("result.csv",payload,"text/csv")},
    )
    assert preview.status_code==200
    assert preview.json()["requires_review"] is True
    assert client.get(f"/api/v1/bids/{bid['id']}/outcome").json()["outcome"] is None
    events=client.get("/api/v1/audit").json()
    event=next(x for x in events if x["event_type"]=="historical_bid.import_previewed")
    assert event["details"]["filename"]=="result.csv"
    assert len(event["details"]["sha256"])==64
    assert event["details"]["price_rows"]==2


def test_batch_preflight_prevents_partial_persistence(client,bid_payload):
    bid=client.post("/api/v1/bids",json={**bid_payload,"bid_id":"BID-BATCH","tender_reference_no":"T-BATCH"}).json()
    response=client.post(
        f"/api/v1/bids/{bid['id']}/documents",
        files=[
            ("files",("good.txt",b"valid tender text","text/plain")),
            ("files",("bad.png",b"%PDF-1.7 mismatched content","image/png")),
        ],
    )
    assert response.status_code==415
    docs=client.get(f"/api/v1/bids/{bid['id']}/documents").json()
    assert docs["total"]==0


def test_historical_intelligence_filters_are_server_side(client,bid_payload):
    a=client.post("/api/v1/bids",json={**bid_payload,"bid_id":"HIST-A","tender_reference_no":"H-A","client":"DFCCIL","project_type":"OHE"}).json()
    b=client.post("/api/v1/bids",json={**bid_payload,"bid_id":"HIST-B","tender_reference_no":"H-B","client":"DMRC","project_type":"Civil"}).json()
    for bid,competitor in [(a,"Rail Competitor"),(b,"Metro Competitor")]:
        response=client.put(
            f"/api/v1/bids/{bid['id']}/outcome",
            json={
                "result_status":"Lost","our_rank":2,"our_bid_value":110,"source_reference":"Official Result Notice",
                "prices":[
                    {"bidder_name":competitor,"rank":1,"bid_value":100,"currency":"INR","is_ours":False,"source_reference":"Official Result Notice"},
                    {"bidder_name":"L&T","rank":2,"bid_value":110,"currency":"INR","is_ours":True,"source_reference":"Official Result Notice"},
                ],
            },
        )
        assert response.status_code==200
    filtered=client.get("/api/v1/historical-bids/intelligence",params={"client":"DFCCIL"})
    assert filtered.status_code==200
    body=filtered.json()
    assert body["summary"]["completed"]==1
    assert body["applied_filters"]["client"]=="DFCCIL"
    names={x["name"] for x in body["competitors"]}
    assert "Rail Competitor" in names
    assert "Metro Competitor" not in names
    assert body["data_quality"]["outcome_source_coverage_percent"]==100.0
    assert body["data_quality"]["price_source_coverage_percent"]==100.0
    competitor=next(x for x in body["competitors"] if x["name"]=="Rail Competitor")
    assert competitor["top_client"]=="DFCCIL"
    assert competitor["top_project_type"]=="OHE"
    assert competitor["head_to_head"]==1
    assert competitor["competitor_ahead"]==1
    assert competitor["our_ahead"]==0
    assert len(body["records"])==1
    record=body["records"][0]
    assert record["bid_id"]=="HIST-A"
    assert record["evidence_status"]=="Complete"
    assert record["source_reference"]=="Official Result Notice"


def test_failed_historical_result_save_rolls_back_previous_state(client,bid_payload,monkeypatch):
    bid=client.post("/api/v1/bids",json={**bid_payload,"bid_id":"ROLLBACK-HIST","tender_reference_no":"ROLLBACK-HIST"}).json()
    original={
        "result_status":"Lost","our_rank":2,"our_bid_value":108,
        "prices":[
            {"bidder_name":"Competitor A","rank":1,"bid_value":100,"currency":"INR","is_ours":False},
            {"bidder_name":"L&T","rank":2,"bid_value":108,"currency":"INR","is_ours":True},
        ],
    }
    assert client.put(f"/api/v1/bids/{bid['id']}/outcome",json=original).status_code==200

    class BrokenAuditEvent:
        def __init__(self,*args,**kwargs):
            raise RuntimeError("controlled persistence failure")

    monkeypatch.setattr("app.services.historical_bid_intelligence.AuditEvent",BrokenAuditEvent)
    with pytest.raises(RuntimeError,match="controlled persistence failure"):
        client.put(
            f"/api/v1/bids/{bid['id']}/outcome",
            json={
                "result_status":"Won","our_rank":1,"our_bid_value":95,
                "prices":[{"bidder_name":"L&T","rank":1,"bid_value":95,"currency":"INR","is_ours":True}],
            },
        )

    persisted=client.get(f"/api/v1/bids/{bid['id']}/outcome").json()
    assert persisted["outcome"]["result_status"]=="Lost"
    assert persisted["outcome"]["our_rank"]==2
    assert len(persisted["prices"])==2


def test_unchanged_historical_result_save_is_idempotent(client,bid_payload):
    bid=client.post("/api/v1/bids",json={**bid_payload,"bid_id":"IDEMP-HIST","tender_reference_no":"IDEMP-HIST"}).json()
    payload={
        "result_status":"Lost","our_rank":2,"our_bid_value":108,"source_reference":"Official Result",
        "prices":[
            {"bidder_name":"Competitor A","rank":1,"bid_value":100,"currency":"INR","is_ours":False,"source_reference":"Official Result"},
            {"bidder_name":"L&T","rank":2,"bid_value":108,"currency":"INR","is_ours":True,"source_reference":"Official Result"},
        ],
    }
    first=client.put(f"/api/v1/bids/{bid['id']}/outcome",json=payload)
    assert first.status_code==200
    first_body=first.json()
    first_ids=[x["id"] for x in first_body["prices"]]
    saved_events_before=[x for x in client.get("/api/v1/audit").json() if x["event_type"]=="historical_bid.outcome_saved" and x["bid_project_id"]==bid["id"]]

    second=client.put(f"/api/v1/bids/{bid['id']}/outcome",json=payload)
    assert second.status_code==200
    second_body=second.json()
    assert [x["id"] for x in second_body["prices"]]==first_ids
    saved_events_after=[x for x in client.get("/api/v1/audit").json() if x["event_type"]=="historical_bid.outcome_saved" and x["bid_project_id"]==bid["id"]]
    assert len(saved_events_after)==len(saved_events_before)


def test_historical_result_period_filter_and_invalid_range(client,bid_payload):
    old=client.post("/api/v1/bids",json={**bid_payload,"bid_id":"HIST-OLD","tender_reference_no":"H-OLD"}).json()
    new=client.post("/api/v1/bids",json={**bid_payload,"bid_id":"HIST-NEW","tender_reference_no":"H-NEW"}).json()
    for bid,result_date in [(old,"2025-01-15"),(new,"2026-08-15")]:
        response=client.put(
            f"/api/v1/bids/{bid['id']}/outcome",
            json={
                "result_status":"Lost","result_date":result_date,"our_rank":2,"our_bid_value":110,
                "prices":[
                    {"bidder_name":"Competitor "+bid["bid_id"],"rank":1,"bid_value":100,"currency":"INR","is_ours":False},
                    {"bidder_name":"L&T","rank":2,"bid_value":110,"currency":"INR","is_ours":True},
                ],
            },
        )
        assert response.status_code==200
    filtered=client.get("/api/v1/historical-bids/intelligence",params={"result_from":"2026-01-01","result_to":"2026-12-31"})
    assert filtered.status_code==200
    assert filtered.json()["summary"]["completed"]==1
    assert filtered.json()["applied_filters"]["result_from"]=="2026-01-01"
    invalid=client.get("/api/v1/historical-bids/intelligence",params={"result_from":"2026-12-31","result_to":"2026-01-01"})
    assert invalid.status_code==422
