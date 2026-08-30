from dataclasses import dataclass
from typing import Protocol,Sequence


@dataclass(frozen=True)
class SemanticCandidate:
    chunk_id:int
    text:str
    lexical_score:float
    metadata:dict


@dataclass(frozen=True)
class SemanticRerankResult:
    ordered_chunk_ids:list[int]
    scores:dict[int,float]
    provider:str
    provider_version:str
    note:str


@dataclass(frozen=True)
class SemanticAnswerResult:
    answer:str|None
    used_chunk_ids:list[int]
    provider:str
    provider_version:str
    confidence:float|None
    note:str


class TenderSemanticProvider(Protocol):
    name:str
    version:str
    available:bool

    def rerank(self,question:str,candidates:Sequence[SemanticCandidate])->SemanticRerankResult: ...
    def synthesize(self,question:str,candidates:Sequence[SemanticCandidate])->SemanticAnswerResult: ...


class UnconfiguredTenderSemanticProvider:
    name="Unconfigured Tender Semantic Provider"
    version="tender-semantic-provider-v1"
    available=False

    def rerank(self,question:str,candidates:Sequence[SemanticCandidate])->SemanticRerankResult:
        ordered=[x.chunk_id for x in sorted(candidates,key=lambda x:(-x.lexical_score,x.chunk_id))]
        return SemanticRerankResult(
            ordered_chunk_ids=ordered,
            scores={x.chunk_id:x.lexical_score for x in candidates},
            provider=self.name,
            provider_version=self.version,
            note="Semantic reranking is not configured; lexical/domain-aware ranking remains in effect.",
        )

    def synthesize(self,question:str,candidates:Sequence[SemanticCandidate])->SemanticAnswerResult:
        return SemanticAnswerResult(
            answer=None,
            used_chunk_ids=[],
            provider=self.name,
            provider_version=self.version,
            confidence=None,
            note="No semantic answer was generated. Grounded extractive Tender Q&A remains the active answer mode.",
        )


def get_tender_semantic_provider()->TenderSemanticProvider:
    # Deployment-specific provider selection belongs here.
    # This boundary can later host an approved OpenAI/Azure/on-prem embedding+LLM provider
    # without changing bid-scoped retrieval, citations, review gates or audit trails.
    return UnconfiguredTenderSemanticProvider()


def tender_semantic_status():
    provider=get_tender_semantic_provider()
    return {
        "available":provider.available,
        "provider":provider.name,
        "version":provider.version,
        "mode":"Semantic RAG Ready" if provider.available else "Provider Not Configured",
        "active_fallback":"Persistent lexical retrieval + railway/contracts synonym expansion + source-linked extractive answers",
        "note":"Semantic AI is an optional enhancement. It cannot weaken source grounding or bypass conflict/not-found safeguards.",
    }
