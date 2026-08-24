from abc import ABC, abstractmethod
class DocumentIntelligenceProvider(ABC):
    """Provider-neutral boundary reserved for a future, approved Phase 2 service."""
    @abstractmethod
    async def classify(self, document_id:int): ...
