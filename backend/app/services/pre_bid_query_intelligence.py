from dataclasses import dataclass
from typing import Protocol
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BidMissingInput,BidPreBidQuery,BidRequirement


@dataclass(frozen=True)
class SuggestedPreBidQuery:
    source_kind:str
    source_id:int
    query_title:str
    query_text:str
    query_category:str
    priority:str
    responsible_function:str|None
    requirement_id:int|None
    missing_input_id:int|None
    source_document_id:int|None
    source_page:str|None
    source_clause:str|None
    source_section:str|None
    source_excerpt:str|None
    impact_if_unresolved:str|None
    rationale:str
    confidence:float

    def as_dict(self):
        return {
            "source_kind":self.source_kind,
            "source_id":self.source_id,
            "rationale":self.rationale,
            "confidence":self.confidence,
            "query":{
                "query_title":self.query_title,
                "query_text":self.query_text,
                "query_category":self.query_category,
                "priority":self.priority,
                "responsible_function":self.responsible_function,
                "requirement_id":self.requirement_id,
                "missing_input_id":self.missing_input_id,
                "source_document_id":self.source_document_id,
                "source_page":self.source_page,
                "source_clause":self.source_clause,
                "source_section":self.source_section,
                "source_excerpt":self.source_excerpt,
                "impact_if_unresolved":self.impact_if_unresolved,
                "status":"Draft",
            },
        }


class PreBidQuerySuggestionProvider(Protocol):
    def suggest(self,db:Session,bid_id:int)->list[SuggestedPreBidQuery]:...


def _category(value:str|None)->str:
    allowed={"Technical","Commercial","Contractual","Qualification","Financial","Planning / Scheduling","Design","Procurement / Vendor","Construction","Testing & Commissioning","Safety","Quality","Environmental / Social","Interface","Statutory / Approval","Security / Guarantee","Insurance","Documentation","Management Decision","Other"}
    if value in allowed:return value
    if value in {"Technical Requirement"}:return "Technical"
    if value in {"Commercial Requirement"}:return "Commercial"
    if value in {"Contractual Requirement"}:return "Contractual"
    if value in {"Qualification Requirement"}:return "Qualification"
    if value in {"Financial Requirement"}:return "Financial"
    if value in {"Planning / Scheduling Requirement"}:return "Planning / Scheduling"
    if value in {"Design Requirement"}:return "Design"
    if value in {"Procurement Requirement"}:return "Procurement / Vendor"
    if value in {"Construction Requirement"}:return "Construction"
    if value in {"Testing & Commissioning Requirement"}:return "Testing & Commissioning"
    if value in {"Safety Requirement"}:return "Safety"
    if value in {"Quality Requirement"}:return "Quality"
    if value in {"Interface Requirement"}:return "Interface"
    if value in {"Documentation Requirement"}:return "Documentation"
    return "Other"


class RuleBasedPreBidQuerySuggestionProvider:
    version="phase2-query-suggestion-rule-v1"

    def suggest(self,db:Session,bid_id:int)->list[SuggestedPreBidQuery]:
        existing_missing=set(db.scalars(select(BidPreBidQuery.missing_input_id).where(BidPreBidQuery.bid_project_id==bid_id,BidPreBidQuery.missing_input_id.is_not(None))).all())
        existing_requirements=set(db.scalars(select(BidPreBidQuery.requirement_id).where(BidPreBidQuery.bid_project_id==bid_id,BidPreBidQuery.requirement_id.is_not(None))).all())
        suggestions:list[SuggestedPreBidQuery]=[]

        gaps=db.scalars(select(BidMissingInput).where(BidMissingInput.bid_project_id==bid_id,BidMissingInput.status.notin_(["Resolved","Not Applicable"]))).all()
        for gap in gaps:
            if gap.id in existing_missing:continue
            context=f"With reference to the tender requirement"
            if gap.source_clause:context+=f" at Clause {gap.source_clause}"
            if gap.source_page:context+=f" (Page {gap.source_page})"
            query_text=f"{context}, clarification is requested regarding {gap.missing_input_title}. {gap.missing_input_description.strip()} Kindly provide the required information / confirmation to enable complete and unambiguous bid preparation."
            suggestions.append(SuggestedPreBidQuery(
                source_kind="Missing Input",source_id=gap.id,
                query_title=f"Clarification required: {gap.missing_input_title}",
                query_text=query_text,
                query_category=_category(gap.input_category),
                priority=gap.priority,
                responsible_function=gap.responsible_function,
                requirement_id=gap.requirement_id,
                missing_input_id=gap.id,
                source_document_id=gap.source_document_id,
                source_page=gap.source_page,
                source_clause=gap.source_clause,
                source_section=gap.source_section,
                source_excerpt=gap.source_excerpt,
                impact_if_unresolved=gap.impact_if_missing,
                rationale="The bid contains an unresolved missing input that may prevent complete pricing, planning, compliance or submission.",
                confidence=0.90,
            ))

        requirements=db.scalars(select(BidRequirement).where(
            BidRequirement.bid_project_id==bid_id,
            BidRequirement.requirement_status!="Closed",
            BidRequirement.review_status=="Needs Clarification",
        )).all()
        for req in requirements:
            if req.id in existing_requirements:continue
            query_text=f"Please clarify the requirement titled '{req.requirement_title}'. {req.requirement_text.strip()} Kindly confirm the Employer's intended requirement and provide any missing particulars necessary for compliant bid preparation."
            suggestions.append(SuggestedPreBidQuery(
                source_kind="Requirement",source_id=req.id,
                query_title=f"Clarification of requirement: {req.requirement_title}",
                query_text=query_text,
                query_category=_category(req.requirement_category),
                priority=req.priority,
                responsible_function=req.responsible_function,
                requirement_id=req.id,
                missing_input_id=None,
                source_document_id=req.source_document_id,
                source_page=req.source_page,
                source_clause=req.source_clause,
                source_section=req.source_section,
                source_excerpt=req.source_excerpt,
                impact_if_unresolved=None,
                rationale="The extracted requirement has been marked as needing clarification and no linked pre-bid query exists.",
                confidence=0.82,
            ))

        return sorted(suggestions,key=lambda x:({"Critical":0,"High":1,"Medium":2,"Low":3}.get(x.priority,4),-x.confidence,x.query_title.lower()))


def suggest_pre_bid_queries(db:Session,bid_id:int):
    provider=RuleBasedPreBidQuerySuggestionProvider()
    return {"provider":provider.version,"items":[x.as_dict() for x in provider.suggest(db,bid_id)]}
