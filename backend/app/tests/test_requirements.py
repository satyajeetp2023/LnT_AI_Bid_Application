from app.tests.test_phase1 import create,upload

def payload(source_document_id=None,title="Submit OHE design plan",category="Technical Requirement"):
 return {"source_document_id":source_document_id,"requirement_category":category,"requirement_type":"Document Submission","requirement_title":title,"requirement_text":"The bidder shall submit the OHE design plan.","source_page":"118","source_clause":"7.4.2","source_section":"OHE Design Submission","source_excerpt":"The Bidder shall submit...","responsible_function":"Engineering","responsible_person":"Design Lead","due_date":"2026-10-01","priority":"Critical","requirement_status":"Open","is_mandatory":True,"compliance_status":"Not Assessed","review_status":"Not Reviewed","notes":"Track before submission"}
def test_create_list_filter_update_traceability_and_audit(client,bid_payload):
 bid=create(client,bid_payload);document=upload(client,bid["id"],"technical.pdf",b"technical specification").json()[0];created=client.post(f"/api/v1/bids/{bid['id']}/requirements",json=payload(document["id"]));assert created.status_code==201;item=created.json();assert item["extraction_method"]=="Manual" and item["extraction_confidence"] is None;assert item["source_clause"]=="7.4.2" and item["source_original_filename"]=="technical.pdf"
 listed=client.get(f"/api/v1/bids/{bid['id']}/requirements",params={"category":"Technical Requirement","priority":"Critical","search":"7.4.2"}).json();assert listed["total"]==1 and listed["summary"]["critical"]==1
 updated=client.patch(f"/api/v1/requirements/{item['id']}",json={"requirement_status":"Ready for Review","compliance_status":"Partially Compliant","source_page":"119"});assert updated.status_code==200 and updated.json()["source_page"]=="119"
 detail=client.get(f"/api/v1/requirements/{item['id']}").json();assert detail["source_section"]=="OHE Design Submission" and detail["source_excerpt"]=="The Bidder shall submit..."
 events=client.get("/api/v1/audit").json();names={x["event_type"] for x in events};assert {"requirement.created","requirement.updated"}<=names
def test_reject_invalid_category_and_cross_project_source(client,bid_payload):
 first=create(client,bid_payload);second_payload={**bid_payload,"bid_id":"BID-002"};second=create(client,second_payload);foreign=upload(client,second["id"],"foreign.pdf").json()[0]
 assert client.post(f"/api/v1/bids/{first['id']}/requirements",json=payload(category="Unknown")).status_code==422
 assert client.post(f"/api/v1/bids/{first['id']}/requirements",json=payload(foreign["id"])).status_code==422
def test_cross_project_access_denied_and_pagination(client,bid_payload):
 bid=create(client,bid_payload)
 for index in range(3):assert client.post(f"/api/v1/bids/{bid['id']}/requirements",json=payload(title=f"Requirement {index}")).status_code==201
 page=client.get(f"/api/v1/bids/{bid['id']}/requirements",params={"page":1,"page_size":2}).json();assert page["total"]==3 and len(page["items"])==2
 assert client.get(f"/api/v1/bids/{bid['id']}/requirements",headers={"X-User-ID":"2"}).status_code==403
 assert client.get(f"/api/v1/requirements/{page['items'][0]['id']}",headers={"X-User-ID":"2"}).status_code==403
