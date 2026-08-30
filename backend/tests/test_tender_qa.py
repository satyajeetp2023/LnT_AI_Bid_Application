from app.services.tender_qa import Evidence,_conflicts

def test_numeric_tender_conflict_is_surfaced():
    ranked=[
        Evidence("Retention shall be 5% of certified value.",1,"GCC.pdf","20","14.2",None,"Tender Document",.80),
        Evidence("Retention shall be 10% of certified value.",2,"SCC.pdf","5","14.2",None,"Tender Document",.75),
    ]
    conflicts=_conflicts("What is the retention percentage?",ranked)
    assert len(conflicts)==1
    values=sorted({x["value"] for x in conflicts[0]["values"]})
    assert values==[5.0,10.0]
