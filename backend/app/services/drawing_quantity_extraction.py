from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class DrawingQuantityCandidate:
    item_name:str
    quantity:float
    unit:str
    source_page:str|None=None
    drawing_reference:str|None=None
    item_category:str|None=None
    evidence_text:str|None=None
    evidence_region:dict|None=None
    confidence:float=.0


@dataclass(frozen=True)
class DrawingQuantityExtractionResult:
    candidates:list[DrawingQuantityCandidate]
    provider:str
    provider_version:str
    confidence_note:str
    limitations:list[str]


class DrawingQuantityExtractionProvider(Protocol):
    name:str
    version:str
    available:bool

    def extract(self,extension:str,content:bytes)->DrawingQuantityExtractionResult: ...


class UnconfiguredDrawingVisionProvider:
    name="Unconfigured Drawing Vision Provider"
    version="drawing-vision-provider-v1"
    available=False

    def extract(self,extension:str,content:bytes)->DrawingQuantityExtractionResult:
        return DrawingQuantityExtractionResult(
            candidates=[],
            provider=self.name,
            provider_version=self.version,
            confidence_note="No drawing vision provider is currently configured.",
            limitations=[
                "Drawing quantity extraction has not been run.",
                "The BOQ verification workflow is ready to consume observations once an approved vision provider is connected.",
            ],
        )


def get_drawing_quantity_provider()->DrawingQuantityExtractionProvider:
    # Provider selection remains intentionally decoupled from the BOQ comparison layer.
    # Replace this factory with an approved cloud/on-prem provider when deployment policy is decided.
    return UnconfiguredDrawingVisionProvider()


def drawing_vision_status():
    provider=get_drawing_quantity_provider()
    return {
        "available":provider.available,
        "provider":provider.name,
        "version":provider.version,
        "mode":"Provider Ready" if provider.available else "Provider Not Configured",
        "note":"Drawing-to-BOQ verification is provider-independent. No quantity is inferred until a configured provider returns traceable observations.",
    }
