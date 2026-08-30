from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database.session import SessionLocal
from app.main import app
from app.models import User


client=TestClient(app)


def _user_ids():
    with SessionLocal() as db:
        admin=db.scalar(select(User).where(User.email=="admin@railbid.local"))
        viewer=db.scalar(select(User).where(User.email=="viewer@railbid.local"))
        assert admin and viewer
        return admin.id,viewer.id


def test_phase_1_to_9_acceptance_journey():
    admin_id,viewer_id=_user_ids()
    admin={"X-User-ID":str(admin_id)}
    viewer={"X-User-ID":str(viewer_id)}

    # Environment + identity
    health=client.get("/api/v1/health")
    assert health.status_code==200
    assert health.json()=={"status":"ok","database":"connected"}
    assert client.get("/api/v1/auth/me",headers=admin).status_code==200
    assert client.get("/api/v1/auth/me").status_code==401

    # RBAC: read-only user cannot create a bid.
    bid_payload={
        "bid_id":"UAT-RLY-001",
        "tender_reference_no":"UAT/DFCC/001",
        "client":"DFCCIL",
        "tender_name":"UAT Railway Package",
        "contract_type":"EPC",
        "project_type":"OHE",
        "package_section":"Section A",
        "location":"Gujarat",
        "estimated_value":1000,
        "currency":"INR",
        "tender_due_date":"2026-12-15",
        "bid_manager":"UAT Bid Manager",
        "current_stage":"Opportunity",
        "bid_status":"Active",
        "description":"Internal acceptance test bid"
    }
    assert client.post("/api/v1/bids",json=bid_payload,headers=viewer).status_code==403

    created=client.post("/api/v1/bids",json=bid_payload,headers=admin)
    assert created.status_code==201,created.text
    bid=created.json()
    bid_id=bid["id"]

    # Bid visibility and project membership control.
    assert client.get(f"/api/v1/bids/{bid_id}",headers=viewer).status_code==403
    member=client.post(
        f"/api/v1/bids/{bid_id}/members",
        json={"user_id":viewer_id,"role":"Reviewer"},
        headers=admin,
    )
    assert member.status_code==200,member.text
    assert client.get(f"/api/v1/bids/{bid_id}",headers=viewer).status_code==200

    # Phase 1: document repository and automated intake.
    tender_text=(
        b"The contractor shall submit a detailed baseline programme and resource plan. "
        b"The programme shall identify milestones, testing and commissioning activities."
    )
    upload=client.post(
        f"/api/v1/bids/{bid_id}/documents",
        files={"files":("uat_tender.txt",tender_text,"text/plain")},
        headers=admin,
    )
    assert upload.status_code==200,upload.text
    uploaded=upload.json()
    assert len(uploaded)==1
    doc_id=uploaded[0]["id"]

    docs=client.get(f"/api/v1/bids/{bid_id}/documents",headers=admin)
    assert docs.status_code==200
    assert docs.json()["total"]==1

    classified=client.post(f"/api/v1/documents/{doc_id}/auto-classify",json={},headers=admin)
    assert classified.status_code==200,classified.text

    extracted=client.post(f"/api/v1/documents/{doc_id}/extract-requirements",headers=admin)
    assert extracted.status_code==200,extracted.text

    # Phase 2: controlled requirement register.
    requirement=client.post(
        f"/api/v1/bids/{bid_id}/requirements",
        json={
            "requirement_category":"Planning / Scheduling Requirement",
            "requirement_type":"Schedule",
            "requirement_title":"Detailed baseline programme",
            "requirement_text":"Submit a detailed baseline programme identifying milestones and resource deployment.",
            "responsible_function":"Planning",
            "priority":"High",
            "is_mandatory":True,
        },
        headers=admin,
    )
    assert requirement.status_code==201,requirement.text
    req_id=requirement.json()["id"]

    req_list=client.get(f"/api/v1/bids/{bid_id}/requirements",headers=viewer)
    assert req_list.status_code==200
    assert req_list.json()["summary"]["total"]>=1

    # Phase 3: missing-input / readiness workflow.
    missing=client.post(
        f"/api/v1/bids/{bid_id}/missing-inputs",
        json={
            "requirement_id":req_id,
            "missing_input_title":"Construction productivity basis",
            "missing_input_description":"Planning requires bidder productivity basis before freezing resource deployment.",
            "input_category":"Planning / Scheduling",
            "input_type":"Data",
            "responsible_function":"Planning",
            "priority":"High",
        },
        headers=admin,
    )
    assert missing.status_code==201,missing.text
    missing_id=missing.json()["id"]

    readiness=client.get(f"/api/v1/bids/{bid_id}/estimation-readiness",headers=admin)
    assert readiness.status_code==200,readiness.text
    assert "overall_score" in readiness.json()

    # Phase 4: department workflow.
    queue=client.get(f"/api/v1/bids/{bid_id}/department-work-queue",headers=admin)
    assert queue.status_code==200,queue.text
    queue_body=queue.json()
    assert isinstance(queue_body.get("items"),list)
    assert queue_body["summary"]["total"]>=1

    # Phase 5: pre-bid query workflow and submission readiness.
    query=client.post(
        f"/api/v1/bids/{bid_id}/pre-bid-queries",
        json={
            "requirement_id":req_id,
            "missing_input_id":missing_id,
            "query_title":"Clarify productivity / resource basis",
            "query_text":"Please clarify whether any prescribed productivity or minimum resource deployment basis applies.",
            "query_category":"Planning / Scheduling",
            "responsible_function":"Planning",
            "priority":"High",
        },
        headers=admin,
    )
    assert query.status_code==201,query.text

    pbq=client.get(f"/api/v1/bids/{bid_id}/pre-bid-queries",headers=viewer)
    assert pbq.status_code==200
    assert pbq.json()["summary"]["total"]>=1

    submission=client.get(f"/api/v1/bids/{bid_id}/submission-readiness",headers=admin)
    assert submission.status_code==200,submission.text

    # Phase 6: schedule skeleton + planning readiness without inventing missing evidence.
    skeleton=client.get(f"/api/v1/bids/{bid_id}/schedule-skeleton?sync_scope=true",headers=admin)
    assert skeleton.status_code==200,skeleton.text
    assert "activities" in skeleton.json() or "items" in skeleton.json()

    planning_resources=client.get(f"/api/v1/bids/{bid_id}/planning-resources",headers=admin)
    assert planning_resources.status_code==200,planning_resources.text

    # Phase 7: capture final outcome, L1-L4 and verify descriptive intelligence.
    preview=client.post(
        f"/api/v1/bids/{bid_id}/outcome/import-preview",
        files={"file":("uat_result.csv",b"Rank,Bidder Name,Bid Value,Currency,Our Bid\n1,Competitor A,1000,INR,No\n2,Larsen & Toubro,1080,INR,Yes\n3,Competitor C,1120,INR,No\n4,Competitor D,1180,INR,No\n","text/csv")},
        headers=admin,
    )
    assert preview.status_code==200,preview.text
    preview_body=preview.json()
    assert preview_body["requires_review"] is True
    assert preview_body["outcome_candidate"]["our_rank"]==2
    assert len(preview_body["prices"])==4

    outcome_payload={
        "result_status":"Lost",
        "result_date":"2026-12-20",
        "our_rank":2,
        "our_bid_value":1080,
        "our_margin_percent":7.5,
        "awarded_bidder":"Competitor A",
        "loss_reason":"Commercial gap to L1",
        "source_reference":"UAT Result Notice",
        "notes":"Acceptance test result",
        "prices":[
            {"bidder_name":"Competitor A","rank":1,"bid_value":1000,"currency":"INR","is_ours":False},
            {"bidder_name":"L&T","rank":2,"bid_value":1080,"currency":"INR","is_ours":True},
            {"bidder_name":"Competitor C","rank":3,"bid_value":1120,"currency":"INR","is_ours":False},
            {"bidder_name":"Competitor D","rank":4,"bid_value":1180,"currency":"INR","is_ours":False},
        ],
    }
    saved=client.put(f"/api/v1/bids/{bid_id}/outcome",json=outcome_payload,headers=admin)
    assert saved.status_code==200,saved.text
    body=saved.json()
    assert body["price_summary"]["our_gap_to_l1_percent"]==8.0
    assert body["warnings"]==[]

    # Viewer may read outcome but may not edit it.
    assert client.get(f"/api/v1/bids/{bid_id}/outcome",headers=viewer).status_code==200
    assert client.put(f"/api/v1/bids/{bid_id}/outcome",json=outcome_payload,headers=viewer).status_code==403

    history=client.get("/api/v1/historical-bids/intelligence",headers=admin)
    assert history.status_code==200,history.text
    summary=history.json()["summary"]
    assert summary["recorded"]>=1
    assert summary["lost"]>=1

    comparison=client.get(f"/api/v1/bids/{bid_id}/historical-comparison",headers=admin)
    assert comparison.status_code==200,comparison.text
    comparison_body=comparison.json()
    assert comparison_body["current_bid_id"]==bid_id
    assert "methodology" in comparison_body

    dashboard=client.get("/api/v1/dashboard/summary",headers=admin)
    assert dashboard.status_code==200
    assert dashboard.json()["documents_uploaded"]>=1


    # Phase 8: reviewed bid-versus-actual execution learning for a won bid.
    won_payload={**bid_payload,"bid_id":"UAT-RLY-WON","tender_reference_no":"UAT/DFCC/WON","tender_name":"UAT Won Railway Package"}
    won_bid=client.post("/api/v1/bids",json=won_payload,headers=admin)
    assert won_bid.status_code==201,won_bid.text
    won_id=won_bid.json()["id"]
    won_outcome=client.put(
        f"/api/v1/bids/{won_id}/outcome",
        json={
            "result_status":"Won","result_date":"2026-12-21","our_rank":1,"our_bid_value":1000,"our_margin_percent":8.0,
            "awarded_bidder":"L&T","source_reference":"UAT Award Notice",
            "prices":[{"bidder_name":"L&T","rank":1,"bid_value":1000,"currency":"INR","is_ours":True,"source_reference":"UAT Award Notice"}],
        },
        headers=admin,
    )
    assert won_outcome.status_code==200,won_outcome.text

    actuals=client.put(
        f"/api/v1/bids/{won_id}/execution-outcome",
        json={
            "execution_status":"Completed","data_date":"2027-02-01",
            "actual_start_date":"2026-01-01","actual_completion_date":"2027-01-15",
            "final_contract_value":1150,"actual_cost":1035,"final_margin_percent":10.0,
            "approved_variations":100,"claims_recovered":25,"eot_days":45,
            "source_reference":"UAT Certified Final Account",
        },
        headers=admin,
    )
    assert actuals.status_code==200,actuals.text
    reviewed=client.post(f"/api/v1/bids/{won_id}/execution-outcome/review",headers=admin)
    assert reviewed.status_code==200,reviewed.text
    assert reviewed.json()["learning_eligible"] is True
    assert reviewed.json()["comparison"]["revenue_change_vs_bid_percent"]==15.0

    factor=client.post(
        f"/api/v1/bids/{won_id}/execution-learning-factors",
        json={
            "factor_category":"Planning","impact_area":"Time","direction":"Adverse",
            "title":"Late work-front access","description":"Execution access was later than the original bid assumption.",
            "quantified_impact":45,"impact_unit":"days","source_reference":"UAT Approved EOT",
            "source_excerpt":"Forty-five days of access delay were recognized.",
            "lesson_for_future_bids":"Model access-release milestones explicitly and preserve float against delayed handover.",
        },
        headers=admin,
    )
    assert factor.status_code==201,factor.text
    factor_review=client.post(f"/api/v1/execution-learning-factors/{factor.json()['id']}/review",headers=admin)
    assert factor_review.status_code==200,factor_review.text
    assert factor_review.json()["review_status"]=="Reviewed"

    portfolio=client.get("/api/v1/execution-learning/intelligence",headers=admin)
    assert portfolio.status_code==200,portfolio.text
    assert portfolio.json()["summary"]["reviewed_projects"]>=1
    assert portfolio.json()["summary"]["reviewed_factors"]>=1

    # Phase 9: deterministic management decision analytics and immutable decision snapshot.
    analytics=client.get(f"/api/v1/bids/{won_id}/decision-analytics",headers=admin)
    assert analytics.status_code==200,analytics.text
    analytics_body=analytics.json()
    assert analytics_body["methodology"]["type"].startswith("Deterministic")
    assert "decision_posture" in analytics_body
    assert "readiness_score" in analytics_body
    assert "historical_context" in analytics_body

    snapshot=client.post(f"/api/v1/bids/{won_id}/decision-snapshots",headers=admin)
    assert snapshot.status_code==201,snapshot.text
    snap=snapshot.json()
    assert len(snap["checksum"])==64
    same_snapshot=client.post(f"/api/v1/bids/{won_id}/decision-snapshots",headers=admin)
    assert same_snapshot.status_code==201,same_snapshot.text
    assert same_snapshot.json()["id"]==snap["id"]

    snapshots=client.get(f"/api/v1/bids/{won_id}/decision-snapshots",headers=admin)
    assert snapshots.status_code==200
    assert snapshots.json()["total"]==1
