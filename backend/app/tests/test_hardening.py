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
