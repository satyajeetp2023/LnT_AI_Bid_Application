import pytest
from app.storage.base import LocalSecureStorage
from app.tests.conftest import TestingSession
from app.models import AuditEvent,ProjectMembership

def create(client,payload,headers=None): return client.post("/api/v1/bids",json=payload,headers=headers or {}).json()
def upload(client,bid,name,content=b"tender"): return client.post(f"/api/v1/bids/{bid}/documents",files=[("files",(name,content,"application/pdf"))])
def test_create_duplicate_draft_and_edit(client,bid_payload):
 bid=create(client,bid_payload);assert bid["bid_status"]=="Draft";assert client.post("/api/v1/bids",json=bid_payload).status_code==409;r=client.patch(f"/api/v1/bids/{bid['id']}",json={"client":"Updated Railways"});assert r.status_code==200 and r.json()["client"]=="Updated Railways"
def test_upload_duplicate_classify_notes_archive_and_filter(client,bid_payload):
 bid=create(client,bid_payload);first=upload(client,bid["id"],"spec.pdf");assert first.status_code==200;doc=first.json()[0];assert len(doc["checksum"])==64;dup=upload(client,bid["id"],"copy.pdf").json()[0];assert dup["document_status"]=="Duplicate" and dup["duplicate_of_document_id"]==doc["id"]
 classified=client.patch(f"/api/v1/documents/{doc['id']}/classification",json={"document_category":"Technical Specifications","document_subcategory":"OHE","information_tags":["Safety","OHE"]});assert classified.status_code==200 and classified.json()["information_tags"]==["Safety","OHE"]
 assert client.patch(f"/api/v1/documents/{doc['id']}/notes",json={"notes":"Reviewed"}).json()["notes"]=="Reviewed"
 found=client.get(f"/api/v1/bids/{bid['id']}/documents",params={"category":"Technical Specifications","search":"spec"}).json();assert found["total"]==1
 assert client.post(f"/api/v1/documents/{doc['id']}/archive").json()["document_status"]=="Archived"
def test_unsupported_revision_and_protected_download(client,bid_payload):
 bid=create(client,bid_payload);assert upload(client,bid["id"],"run.exe").status_code==415;one=upload(client,bid["id"],"base.pdf",b"one").json()[0];two=upload(client,bid["id"],"revised.pdf",b"two").json()[0];rev=client.post(f"/api/v1/documents/{two['id']}/revision",json={"revision_of_document_id":one["id"]});assert rev.json()["revision_no"]==2 and rev.json()["revision_of_document_id"]==one["id"];history=client.get(f"/api/v1/documents/{one['id']}/revisions").json();assert len(history)==2;download=client.get(f"/api/v1/documents/{one['id']}/download");assert download.status_code==200 and download.content==b"one"
def test_project_authorized_and_cross_project_denied(client,bid_payload):
 bid=create(client,bid_payload);doc=upload(client,bid["id"],"private.pdf").json()[0]
 assert client.get(f"/api/v1/bids/{bid['id']}/documents",headers={"X-User-ID":"2"}).status_code==403;assert client.get(f"/api/v1/documents/{doc['id']}/download",headers={"X-User-ID":"2"}).status_code==403
 with TestingSession() as db: db.add(ProjectMembership(bid_project_id=bid["id"],user_id=2,role="Read Only"));db.commit()
 assert client.get(f"/api/v1/bids/{bid['id']}/documents",headers={"X-User-ID":"2"}).status_code==200;assert client.get(f"/api/v1/documents/{doc['id']}/download",headers={"X-User-ID":"2"}).status_code==200
def test_audit_events_and_admin_only(client,bid_payload):
 bid=create(client,bid_payload);doc=upload(client,bid["id"],"audit.pdf").json()[0];client.patch(f"/api/v1/documents/{doc['id']}/classification",json={"document_category":"BOQ / Price Schedule","information_tags":[]});events=client.get("/api/v1/audit").json();names={x["event_type"] for x in events};assert {"bid.created","document.uploaded","document.reclassified"}<=names;assert client.get("/api/v1/audit",headers={"X-User-ID":"2"}).status_code==403
def test_storage_path_traversal(tmp_path):
 storage=LocalSecureStorage(tmp_path)
 with pytest.raises(ValueError): storage.read("../secret.txt")
def test_membership_change_is_audited(client,bid_payload):
 bid=create(client,bid_payload);response=client.post(f"/api/v1/bids/{bid['id']}/members",json={"user_id":2,"role":"Read Only"});assert response.status_code==200;events=client.get("/api/v1/audit").json();assert "project.membership_changed" in {e["event_type"] for e in events}
def test_document_metadata_defaults_and_manual_update(client,bid_payload):
 bid=create(client,bid_payload);uploaded=upload(client,bid["id"],"notice.pdf").json()[0]
 assert uploaded["classification_status"]=="needs_review" and uploaded["is_latest_version"] is True
 response=client.patch(f"/api/v1/documents/{uploaded['id']}/metadata",json={"document_category":"Notice / Invitation","document_type":"NIT","document_number":"NIT-01","document_title":"Notice Inviting Tender","revision":"R0","document_date":"2026-08-25","remarks":"Manually reviewed"})
 assert response.status_code==200;updated=response.json();assert updated["classification_status"]=="manually_classified" and updated["document_number"]=="NIT-01"
 persisted=client.get(f"/api/v1/bids/{bid['id']}/documents").json()["items"][0]
 assert persisted["document_title"]=="Notice Inviting Tender" and persisted["remarks"]=="Manually reviewed"
 assert client.get(f"/api/v1/documents/{uploaded['id']}/download").content==b"tender"
def test_manual_classification_protected_and_force_reclassification(client,bid_payload):
 bid=create(client,bid_payload);uploaded=client.post(f"/api/v1/bids/{bid['id']}/documents",files=[("files",("technical_specifications.txt",b"technical specification technical requirements specification","text/plain"))]).json()[0]
 manual=client.patch(f"/api/v1/documents/{uploaded['id']}/metadata",json={"document_category":"Reference Document"}).json();assert manual["classification_status"]=="manually_classified"
 assert client.post(f"/api/v1/documents/{uploaded['id']}/auto-classify",json={"force":False}).status_code==409
 forced=client.post(f"/api/v1/documents/{uploaded['id']}/auto-classify",json={"force":True});assert forced.status_code==200 and forced.json()["document_category"]=="Technical Specifications" and forced.json()["classification_status"]=="classified" and forced.json()["document_status"]=="Uploaded"
def test_unsupported_content_classification_is_safe(client,bid_payload):
 bid=create(client,bid_payload);response=client.post(f"/api/v1/bids/{bid['id']}/documents",files=[("files",("site_photo.png",b"not-real-image-content","image/png"))])
 assert response.status_code==200;document=response.json()[0];assert document["classification_status"]=="needs_review" and document["classification_confidence"] is None and document["document_status"]=="Needs Review"
 assert client.get(f"/api/v1/documents/{document['id']}/download").content==b"not-real-image-content"
def test_failed_forced_reclassification_clears_stale_manual_prediction(client,bid_payload,monkeypatch):
 bid=create(client,bid_payload);uploaded=client.post(f"/api/v1/bids/{bid['id']}/documents",files=[("files",("conditions.txt",b"general conditions of contract gcc","text/plain"))]).json()[0]
 manual=client.patch(f"/api/v1/documents/{uploaded['id']}/metadata",json={"document_category":"Conditions of Contract","document_type":"GCC"}).json();assert manual["classification_status"]=="manually_classified"
 def fail_classification(*args,**kwargs): raise RuntimeError("controlled test failure")
 monkeypatch.setattr("app.services.document_classification.RuleBasedDocumentIntelligenceProvider.classify",fail_classification)
 failed=client.post(f"/api/v1/documents/{uploaded['id']}/auto-classify",json={"force":True});assert failed.status_code==200
 result=failed.json();assert result["document_category"] is None and result["document_type"] is None and result["classification_confidence"] is None
 assert result["classification_status"]=="needs_review" and result["document_status"]=="Needs Review"
