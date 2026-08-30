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
