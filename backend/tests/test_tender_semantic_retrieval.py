from app.services.tender_semantic_retrieval import SemanticCandidate,UnconfiguredTenderSemanticProvider


def test_unconfigured_semantic_provider_is_safe_noop():
    provider=UnconfiguredTenderSemanticProvider()
    candidates=[
        SemanticCandidate(chunk_id=2,text="Lower lexical match",lexical_score=.30,metadata={}),
        SemanticCandidate(chunk_id=1,text="Higher lexical match",lexical_score=.80,metadata={}),
    ]
    reranked=provider.rerank("What is the retention percentage?",candidates)
    assert provider.available is False
    assert reranked.ordered_chunk_ids==[1,2]
    assert reranked.scores[1]==.80

    answer=provider.synthesize("What is the retention percentage?",candidates)
    assert answer.answer is None
    assert answer.used_chunk_ids==[]
