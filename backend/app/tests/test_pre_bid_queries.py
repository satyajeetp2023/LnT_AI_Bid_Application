from app.tests.test_phase1 import create,upload
from app.tests.test_requirements import payload as requirement_payload
from app.tests.test_missing_inputs import gap

def query(requirement_id=None,missing_input_id=None,source_document_id=None,status="Draft",target_response_date="2026-09-01"):
 return {"requirement_id":requirement_id,"missing_input_id":missing_input_id,"source_document_id":source_document_id,"query_number":"PBQ-001","query_title":"Clarify OEM data requirement","query_text":"Please clarify whether the OEM data sheet is required at bid stage.","query_category":"Technical","responsible_function":"Engineering","responsible_person":"Design Lead","priority":"Critical","status":status,"target_response_date":target_response_date,"submitted_date":"2026-08-25" if status=="Submitted" else None,"employer_response":None,"response_date":None,"response_reference":None,"impact_if_unresolved":"Technical compliance position remains uncertain.","source_page":"118","source_clause":"7.4.2","source_section":"OHE","source_excerpt":"The bidder shall submit the OEM data sheet."}

def setup_links(client,bid_payload):
 bid=create(client,bid_payload);doc=upload(client,bid["id"],"technical.pdf",b"technical").json()[0];req=client.post(f"/api/v1/bids/{bid['id']}/requirements",json=requirement_payload(doc["id"])).json();missing=client.post(f"/api/v1/bids/{bid['id']}/missing-inputs",json=gap(req["id"],doc["id"])).json();return bid,doc,req,missing

def test_create_filter_summary_and_traceability(client,bid_payload):
 bid,doc,req,missing=setup_links(client,bid_payload);created=client.post(f"/api/v1/bids/{bid['id']}/pre-bid-queries",json=query(req["id"],missing["id"],doc["id"],"Submitted","2026-08-01"));assert created.status_code==201;item=created.json();assert item["requirement_title"]==req["requirement_title"] and item["missing_input_title"]==missing["missing_input_title"]
 listed=client.get(f"/api/v1/bids/{bid['id']}/pre-bid-queries",params={"search":"OEM","priority":"Critical","status":"Submitted"}).json();assert listed["total"]==1 and listed["summary"]["submitted"]==1 and listed["summary"]["overdue"]==1
 assert "pre_bid_query.created" in {x["event_type"] for x in client.get("/api/v1/audit").json()}

def test_reject_cross_bid_links(client,bid_payload):
 first=create(client,bid_payload);second=create(client,{**bid_payload,"bid_id":"BID-PBQ-002"});doc=upload(client,second["id"],"foreign.pdf").json()[0];req=client.post(f"/api/v1/bids/{second['id']}/requirements",json=requirement_payload(doc["id"])).json();missing=client.post(f"/api/v1/bids/{second['id']}/missing-inputs",json=gap(req["id"],doc["id"])).json()
 assert client.post(f"/api/v1/bids/{first['id']}/pre-bid-queries",json=query(req["id"],None,None)).status_code==422
 assert client.post(f"/api/v1/bids/{first['id']}/pre-bid-queries",json=query(None,missing["id"],None)).status_code==422
 assert client.post(f"/api/v1/bids/{first['id']}/pre-bid-queries",json=query(None,None,doc["id"])).status_code==422

def test_response_close_reopen_and_permissions(client,bid_payload):
 bid,doc,req,missing=setup_links(client,bid_payload);item=client.post(f"/api/v1/bids/{bid['id']}/pre-bid-queries",json=query(req["id"],missing["id"],doc["id"],"Submitted")).json();responded=client.patch(f"/api/v1/pre-bid-queries/{item['id']}",json={"status":"Responded","employer_response":"Confirmed at bid stage.","response_date":"2026-08-28","response_reference":"COR-01"});assert responded.status_code==200 and responded.json()["employer_response"]
 closed=client.patch(f"/api/v1/pre-bid-queries/{item['id']}",json={"status":"Closed"});assert closed.json()["closed_by"]==1 and closed.json()["closed_at"] is not None
 reopened=client.patch(f"/api/v1/pre-bid-queries/{item['id']}",json={"status":"Ready for Review"});assert reopened.json()["closed_by"] is None and reopened.json()["closed_at"] is None
 assert client.get(f"/api/v1/bids/{bid['id']}/pre-bid-queries",headers={"X-User-ID":"2"}).status_code==403
