from app.services.tender_qa import Evidence,_conflicts,_terms

def test_numeric_tender_conflict_is_surfaced():
    ranked=[
        Evidence("Retention shall be 5% of certified value.",1,"GCC.pdf","20","14.2",None,"Tender Document",.80),
        Evidence("Retention shall be 10% of certified value.",2,"SCC.pdf","5","14.2",None,"Tender Document",.75),
    ]
    conflicts=_conflicts("What is the retention percentage?",ranked)
    assert len(conflicts)==1
    values=sorted({x["value"] for x in conflicts[0]["values"]})
    assert values==[5.0,10.0]


def test_contract_shorthand_expands_for_retrieval():
    assert "liquidated" in _terms("What is the LD cap?")
    assert "warranty" in _terms("What is the DLP?")
    assert "performance" in _terms("What is the PBG requirement?")
