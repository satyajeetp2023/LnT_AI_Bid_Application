from abc import ABC, abstractmethod
class DocumentIntelligenceProvider(ABC):
    """Provider-neutral boundary for replaceable document classification."""
    @abstractmethod
    def classify(self, filename: str, extension: str, content: bytes): ...
