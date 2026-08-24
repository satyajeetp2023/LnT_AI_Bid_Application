def test_create_bid_and_reject_duplicate(client,bid_payload):
 first=client.post("/api/v1/bids",json=bid_payload); assert first.status_code==201 and first.json()["bid_id"]=="BID-001"; assert client.post("/api/v1/bids",json=bid_payload).status_code==409
def test_upload_allowed_metadata_and_duplicate(client,bid_payload):
 bid=client.post("/api/v1/bids",json=bid_payload).json(); first=client.post(f"/api/v1/bids/{bid['id']}/documents",files=[("files",("spec.pdf",b"confidential tender","application/pdf"))]); assert first.status_code==200; data=first.json()[0]; assert data["original_filename"]=="spec.pdf" and len(data["checksum"])==64; second=client.post(f"/api/v1/bids/{bid['id']}/documents",files=[("files",("copy.pdf",b"confidential tender","application/pdf"))]); assert second.json()[0]["document_status"]=="Duplicate" and second.json()[0]["duplicate_of_document_id"]==data["id"]; assert len(client.get(f"/api/v1/bids/{bid['id']}/documents").json())==2
def test_reject_unsupported(client,bid_payload):
 bid=client.post("/api/v1/bids",json=bid_payload).json(); assert client.post(f"/api/v1/bids/{bid['id']}/documents",files=[("files",("run.exe",b"x","application/octet-stream"))]).status_code==415
def test_role_permissions(client,bid_payload):
 assert client.post("/api/v1/bids",json=bid_payload,headers={"X-User-ID":"2"}).status_code==403; assert client.get("/api/v1/audit",headers={"X-User-ID":"2"}).status_code==403
