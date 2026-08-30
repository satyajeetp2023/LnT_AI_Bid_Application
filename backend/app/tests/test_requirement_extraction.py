from app.services.requirement_extraction import RuleBasedRequirementExtractionProvider,SourceUnit
from app.tests.test_phase1 import create,upload
from app.tests.test_requirements import payload

def test_rule_scoring_extracts_obligation_and_ignores_narrative():
 provider=RuleBasedRequirementExtractionProvider()
 candidates,low=provider.candidates([SourceUnit("7.4.2 The Bidder shall submit the technical design report for approval.\nThe railway corridor serves the surrounding region.",page=118,section="7.4 OHE Design")])
 assert len(candidates)==1
 item=candidates[0]
 assert item.page==118 and item.clause=="7.4.2" and item.section=="7.4 OHE Design"
 assert item.category in {"Submission Requirement","Design Requirement","Documentation Requirement"}
 assert item.requirement_type in {"Document Submission","Approval","Report"}
 assert 0<=item.confidence<=1 and item.priority=="Medium" and item.is_mandatory is True
 assert "railway corridor" not in item.text.lower() and low==0

def test_low_confidence_obligation_is_skipped():
 candidates,low=RuleBasedRequirementExtractionProvider().candidates([SourceUnit("The system shall maintain operations during normal service.")])
 assert candidates==[] and low==1

def test_pdf_source_units_preserve_page_numbers(monkeypatch):
 class Page:
  def __init__(self,text):self.text=text
  def extract_text(self):return self.text
 class Reader:
  def __init__(self,stream):self.pages=[Page("First page"),Page("Second page")]
 monkeypatch.setattr("app.services.requirement_extraction.PdfReader",Reader)
 units=RuleBasedRequirementExtractionProvider().source_units("pdf",b"pdf")
 assert [(unit.page,unit.text) for unit in units]==[(1,"First page"),(2,"Second page")]

def test_txt_extraction_api_traceability_dedupe_and_review_safety(client,bid_payload):
 bid=create(client,bid_payload)
 text=b"7.4.2 The Bidder shall submit the technical design report for approval.\nThe corridor is located in India.\nThe system shall maintain operations during normal service."
 document=client.post(f"/api/v1/bids/{bid['id']}/documents",files=[("files",("requirements.txt",text,"text/plain"))]).json()[0]
 first=client.post(f"/api/v1/documents/{document['id']}/extract-requirements")
 assert first.status_code==200;summary=first.json();assert summary["created"]==1 and summary["low_confidence_skipped"]==1 and summary["no_text"] is False
 assert "requirement.extraction_completed" in {event["event_type"] for event in client.get("/api/v1/audit").json()}
 listed=client.get(f"/api/v1/bids/{bid['id']}/requirements").json();assert listed["total"]==1;item=listed["items"][0]
 assert item["source_document_id"]==document["id"] and item["source_clause"]=="7.4.2" and item["source_excerpt"]==item["requirement_text"]
 assert item["extraction_method"]=="Rule Based" and 0<=item["extraction_confidence"]<=1
 assert item["review_status"]=="Not Reviewed" and item["compliance_status"]=="Not Assessed" and item["priority"]=="Medium" and item["is_mandatory"] is True
 reviewed=client.patch(f"/api/v1/requirements/{item['id']}",json={"review_status":"Reviewed"}).json();assert reviewed["reviewed_at"] is not None
 rerun=client.post(f"/api/v1/documents/{document['id']}/extract-requirements").json();assert rerun["created"]==0 and rerun["skipped_duplicates"]==1
 persisted=client.get(f"/api/v1/requirements/{item['id']}").json();assert persisted["review_status"]=="Reviewed"
 manual=client.post(f"/api/v1/bids/{bid['id']}/requirements",json=payload(title="Manual protected requirement"));assert manual.status_code==201
 assert client.post(f"/api/v1/documents/{document['id']}/extract-requirements").json()["created"]==0
 assert client.get(f"/api/v1/bids/{bid['id']}/requirements").json()["total"]==2
 assert client.get(f"/api/v1/documents/{document['id']}/download").content==text

def test_no_text_duplicate_and_permission_handling(client,bid_payload):
 bid=create(client,bid_payload)
 empty=client.post(f"/api/v1/bids/{bid['id']}/documents",files=[("files",("empty.txt",b"","text/plain"))]).json()[0]
 result=client.post(f"/api/v1/documents/{empty['id']}/extract-requirements");assert result.status_code==200 and result.json()["no_text"] is True and result.json()["created"]==0
 original=upload(client,bid["id"],"original.pdf",b"same content").json()[0];duplicate=upload(client,bid["id"],"duplicate.pdf",b"same content").json()[0]
 assert duplicate["duplicate_of_document_id"]==original["id"]
 assert client.post(f"/api/v1/documents/{duplicate['id']}/extract-requirements").status_code==422
 assert client.post(f"/api/v1/documents/{original['id']}/extract-requirements",headers={"X-User-ID":"2"}).status_code==403

def test_pdf_extraction_persists_page_and_scanned_pdf_is_safe(client,bid_payload,monkeypatch):
 bid=create(client,bid_payload)
 document=upload(client,bid["id"],"clauses.pdf",b"fake-pdf").json()[0]
 monkeypatch.setattr("app.services.requirement_extraction.RuleBasedRequirementExtractionProvider.source_units",lambda self,extension,content:[SourceUnit("13.7 The Contractor shall provide the mandatory certificate.",page=9,section="Section 13 Submissions")])
 result=client.post(f"/api/v1/documents/{document['id']}/extract-requirements");assert result.status_code==200 and result.json()["created"]==1
 item=client.get(f"/api/v1/bids/{bid['id']}/requirements").json()["items"][0]
 assert item["source_page"]=="9" and item["source_clause"]=="13.7" and item["source_section"]=="Section 13 Submissions"
 scanned=upload(client,bid["id"],"scanned.pdf",b"different-fake-pdf").json()[0]
 monkeypatch.setattr("app.services.requirement_extraction.RuleBasedRequirementExtractionProvider.source_units",lambda self,extension,content:[])
 empty=client.post(f"/api/v1/documents/{scanned['id']}/extract-requirements");assert empty.status_code==200 and empty.json()["no_text"] is True and empty.json()["created"]==0
