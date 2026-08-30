from app.tests.test_phase1 import create,upload
from app.tests.test_requirements import payload as requirement_payload

def gap(requirement_id=None,source_document_id=None,status="Open",required_by_date="2026-08-01"):
 return {"requirement_id":requirement_id,"source_document_id":source_document_id,"missing_input_title":"OEM data sheet required","missing_input_description":"Obtain the OEM technical data sheet before bid submission.","input_category":"Technical","input_type":"Document","responsible_function":"Engineering","responsible_person":"Design Lead","requested_from":"OEM","required_by_date":required_by_date,"priority":"Critical","status":status,"impact_if_missing":"Technical compliance cannot be completed.","resolution_notes":None,"source_page":"118","source_clause":"7.4.2","source_section":"OHE","source_excerpt":"The bidder shall submit the OEM data sheet."}

def test_create_filter_summary_and_audit(client,bid_payload):
 bid=create(client,bid_payload);doc=upload(client,bid["id"],"technical.pdf",b"technical").json()[0];req=client.post(f"/api/v1/bids/{bid['id']}/requirements",json=requirement_payload(doc["id"])).json();created=client.post(f"/api/v1/bids/{bid['id']}/missing-inputs",json=gap(req["id"],doc["id"]));assert created.status_code==201;item=created.json();assert item["requirement_title"]==req["requirement_title"] and item["source_original_filename"]=="technical.pdf"
 listed=client.get(f"/api/v1/bids/{bid['id']}/missing-inputs",params={"priority":"Critical","search":"OEM"}).json();assert listed["total"]==1;assert listed["summary"]["critical"]==1 and listed["summary"]["open"]==1 and listed["summary"]["overdue"]==1
 assert "missing_input.created" in {x["event_type"] for x in client.get("/api/v1/audit").json()}

def test_reject_cross_bid_requirement_and_document(client,bid_payload):
 first=create(client,bid_payload);second=create(client,{**bid_payload,"bid_id":"BID-MI-002"});foreign_doc=upload(client,second["id"],"foreign.pdf").json()[0];foreign_req=client.post(f"/api/v1/bids/{second['id']}/requirements",json=requirement_payload(foreign_doc["id"])).json()
 assert client.post(f"/api/v1/bids/{first['id']}/missing-inputs",json=gap(foreign_req["id"],None)).status_code==422
 assert client.post(f"/api/v1/bids/{first['id']}/missing-inputs",json=gap(None,foreign_doc["id"])).status_code==422

def test_resolve_and_reopen_metadata(client,bid_payload):
 bid=create(client,bid_payload);item=client.post(f"/api/v1/bids/{bid['id']}/missing-inputs",json=gap()).json();resolved=client.patch(f"/api/v1/missing-inputs/{item['id']}",json={"status":"Resolved","resolution_notes":"Received from OEM"});assert resolved.status_code==200;assert resolved.json()["resolved_by"]==1 and resolved.json()["resolved_at"] is not None
 reopened=client.patch(f"/api/v1/missing-inputs/{item['id']}",json={"status":"In Progress"});assert reopened.status_code==200;assert reopened.json()["resolved_by"] is None and reopened.json()["resolved_at"] is None
 names={x["event_type"] for x in client.get("/api/v1/audit").json()};assert "missing_input.resolved" in names and "missing_input.updated" in names

def test_permissions_and_filters(client,bid_payload):
 bid=create(client,bid_payload);assert client.post(f"/api/v1/bids/{bid['id']}/missing-inputs",json=gap(required_by_date="2026-10-01")).status_code==201
 assert client.get(f"/api/v1/bids/{bid['id']}/missing-inputs",params={"input_category":"Technical","status":"Open","required_by_from":"2026-09-01","required_by_to":"2026-12-31"}).json()["total"]==1
 assert client.get(f"/api/v1/bids/{bid['id']}/missing-inputs",headers={"X-User-ID":"2"}).status_code==403
