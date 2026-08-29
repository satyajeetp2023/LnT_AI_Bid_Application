from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BidDocument,BidMissingInput,BidPreBidQuery,BidRequirement


STOP_WORDS={
    "about","after","again","against","also","and","any","are","bid","bidder","clarification","confirm","contractor",
    "could","document","employer","for","from","has","have","information","into","its","may","must","not","of","on",
    "or","our","please","provide","regarding","required","requirement","shall","should","that","the","their","there",
    "these","this","tender","to","was","we","were","what","when","where","which","will","with","would"
}
AUTHORITATIVE_ANSWER_CATEGORIES={"Pre-Bid Clarification","Addendum / Corrigendum"}

REFERENCE_RE=re.compile(r"\b(?:drawing(?:\s+no\.?)?|drg\.?\s*no\.?|annexure|annex|appendix)\s*[:#-]?\s*([A-Z0-9][A-Z0-9./_-]{2,})",re.I)
NUMBER_RE=re.compile(r"\b\d+(?:\.\d+)?\s*(?:days?|months?|years?|km|m|mm|kv|mw|mva|%|nos?\.?|units?)?\b",re.I)

def _compact(text:str)->str:
    return re.sub(r"[^a-z0-9]+","",text.lower())

def _missing_references(db:Session,bid_id:int,requirements:list[BidRequirement],blocked:set[int])->list[SuggestedPreBidQuery]:
    documents=db.scalars(select(BidDocument).where(BidDocument.bid_project_id==bid_id)).all()
    haystacks=[_compact(f"{d.original_filename} {d.document_title or ''} {d.document_number or ''}") for d in documents]
    out=[]
    seen=set()
    for req in requirements:
        if req.id in blocked:continue
        for match in REFERENCE_RE.finditer(req.requirement_text or ""):
            ref=match.group(1).strip(" .,:;")
            if not any(ch.isdigit() for ch in ref):continue
            key=(req.id,ref.lower())
            if key in seen:continue
            seen.add(key)
            token=_compact(ref)
            if len(token)<3 or any(token in h for h in haystacks):continue
            check=KnowledgeCheck("unresolved",.0,0)
            source=req.source_document.document_title or req.source_document.original_filename if req.source_document else None
            query_text=f"The tender requirement refers to {match.group(0)}; however, the referenced document/drawing could not be identified in the uploaded tender package. Kindly provide the referenced document/drawing or confirm the applicable reference."
            out.append(SuggestedPreBidQuery(
                source_kind="Missing Reference",source_id=req.id,
                query_title=f"Missing referenced document: {ref}",query_text=query_text,
                query_category=_category(req.requirement_category),priority="High" if req.priority in {"Critical","High"} else "Medium",
                responsible_function=req.responsible_function,requirement_id=req.id,missing_input_id=None,
                source_document_id=req.source_document_id,source_page=req.source_page,source_clause=req.source_clause,
                source_section=req.source_section,source_excerpt=req.source_excerpt or req.requirement_text,
                impact_if_unresolved="Referenced tender information is unavailable for complete technical/commercial assessment.",
                rationale=f"The extracted requirement explicitly references {ref}, but no uploaded tender document title, number or filename matches that reference.",
                confidence=.88,knowledge_check=check,
            ))
            blocked.add(req.id)
            break
    return out

def _conflicting_requirements(requirements:list[BidRequirement],blocked:set[int])->list[SuggestedPreBidQuery]:
    out=[]
    for i,left in enumerate(requirements):
        if left.id in blocked or not left.source_document_id:continue
        left_terms=_terms(f"{left.requirement_title} {left.requirement_text}")
        left_numbers=set(x.lower().strip() for x in NUMBER_RE.findall(left.requirement_text or ""))
        if len(left_terms)<5 or not left_numbers:continue
        for right in requirements[i+1:]:
            if right.id in blocked or not right.source_document_id or right.source_document_id==left.source_document_id:continue
            if right.requirement_category!=left.requirement_category:continue
            right_terms=_terms(f"{right.requirement_title} {right.requirement_text}")
            common=left_terms&right_terms
            similarity=len(common)/max(1,min(len(left_terms),len(right_terms)))
            if len(common)<5 or similarity<.58:continue
            right_numbers=set(x.lower().strip() for x in NUMBER_RE.findall(right.requirement_text or ""))
            if not right_numbers or left_numbers==right_numbers or left_numbers&right_numbers:continue
            right_source=right.source_document.document_title or right.source_document.original_filename if right.source_document else None
            check=KnowledgeCheck(
                "related_evidence_found",round(min(.95,similarity),2),1,
                (right.source_excerpt or right.requirement_text or "")[:1200],right_source,right.source_page,right.source_clause
            )
            left_source=left.source_document.document_title or left.source_document.original_filename if left.source_document else "one tender document"
            query_text=f"Two tender requirements appear to address the same subject but contain different numeric particulars. {left_source} states: '{left.requirement_text[:500]}'. {right_source or 'Another tender document'} states: '{right.requirement_text[:500]}'. Kindly clarify which requirement/particular shall govern for bid preparation."
            out.append(SuggestedPreBidQuery(
                source_kind="Cross-Document Conflict",source_id=left.id,
                query_title=f"Conflicting tender particulars: {left.requirement_title[:180]}",query_text=query_text,
                query_category=_category(left.requirement_category),priority="High",
                responsible_function=left.responsible_function,requirement_id=left.id,missing_input_id=None,
                source_document_id=left.source_document_id,source_page=left.source_page,source_clause=left.source_clause,
                source_section=left.source_section,source_excerpt=left.source_excerpt or left.requirement_text,
                impact_if_unresolved="Conflicting tender particulars may affect pricing, design, planning, compliance or contractual interpretation.",
                rationale="Two independently extracted requirements from different tender documents are highly similar in subject but contain incompatible numeric particulars.",
                confidence=round(min(.90,.62+similarity*.25),2),knowledge_check=check,
            ))
            blocked.add(left.id);blocked.add(right.id)
            break
    return out


def _terms(text:str)->set[str]:
    return {x for x in re.findall(r"[a-z0-9]+",text.lower()) if len(x)>2 and x not in STOP_WORDS}


@dataclass(frozen=True)
class KnowledgeCheck:
    status:str
    confidence:float
    evidence_count:int
    answer_excerpt:str|None=None
    source_document:str|None=None
    source_page:str|None=None
    source_clause:str|None=None

    def as_dict(self):
        return {
            "status":self.status,
            "confidence":self.confidence,
            "evidence_count":self.evidence_count,
            "answer_excerpt":self.answer_excerpt,
            "source_document":self.source_document,
            "source_page":self.source_page,
            "source_clause":self.source_clause,
        }


class TenderKnowledgeProvider(Protocol):
    def check(self,db:Session,bid_id:int,question:str,exclude_requirement_id:int|None=None)->KnowledgeCheck:...


class ExtractedTenderKnowledgeProvider:
    version="phase2-extracted-knowledge-v1"

    def check(self,db:Session,bid_id:int,question:str,exclude_requirement_id:int|None=None)->KnowledgeCheck:
        qterms=_terms(question)
        if len(qterms)<2:return KnowledgeCheck("unresolved",0.0,0)
        rows=db.scalars(select(BidRequirement).where(BidRequirement.bid_project_id==bid_id)).all()
        ranked=[]
        for row in rows:
            if exclude_requirement_id and row.id==exclude_requirement_id:continue
            candidate=f"{row.requirement_title} {row.requirement_text} {row.source_excerpt or ''}"
            cterms=_terms(candidate)
            overlap=qterms&cterms
            if len(overlap)<2:continue
            score=len(overlap)/max(1,len(qterms))
            category=row.source_document.document_category if row.source_document else None
            authoritative=category in AUTHORITATIVE_ANSWER_CATEGORIES
            ranked.append((score,len(overlap),authoritative,row))
        ranked.sort(key=lambda x:(x[2],x[0],x[1]),reverse=True)
        if not ranked:return KnowledgeCheck("unresolved",0.0,0)
        score,overlap_count,authoritative,row=ranked[0]
        excerpt=(row.source_excerpt or row.requirement_text or "")[:1200]
        source=row.source_document.document_title or row.source_document.original_filename if row.source_document else None
        if authoritative and score>=.72 and overlap_count>=4:
            return KnowledgeCheck("answered_in_tender",round(min(.98,score),2),len(ranked),excerpt,source,row.source_page,row.source_clause)
        if score>=.35:
            return KnowledgeCheck("related_evidence_found",round(min(.90,score),2),len(ranked),excerpt,source,row.source_page,row.source_clause)
        return KnowledgeCheck("unresolved",round(score,2),len(ranked))


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
    knowledge_check:KnowledgeCheck

    def as_dict(self):
        return {
            "source_kind":self.source_kind,
            "source_id":self.source_id,
            "rationale":self.rationale,
            "confidence":self.confidence,
            "knowledge_check":self.knowledge_check.as_dict(),
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
    def suggest(self,db:Session,bid_id:int)->tuple[list[SuggestedPreBidQuery],list[dict]]:...


def _category(value:str|None)->str:
    allowed={"Technical","Commercial","Contractual","Qualification","Financial","Planning / Scheduling","Design","Procurement / Vendor","Construction","Testing & Commissioning","Safety","Quality","Environmental / Social","Interface","Statutory / Approval","Security / Guarantee","Insurance","Documentation","Management Decision","Other"}
    if value in allowed:return value
    mapping={
        "Technical Requirement":"Technical","Commercial Requirement":"Commercial","Contractual Requirement":"Contractual",
        "Qualification Requirement":"Qualification","Financial Requirement":"Financial","Planning / Scheduling Requirement":"Planning / Scheduling",
        "Design Requirement":"Design","Procurement Requirement":"Procurement / Vendor","Construction Requirement":"Construction",
        "Testing & Commissioning Requirement":"Testing & Commissioning","Safety Requirement":"Safety","Quality Requirement":"Quality",
        "Interface Requirement":"Interface","Documentation Requirement":"Documentation",
    }
    return mapping.get(value,"Other")


class RuleBasedPreBidQuerySuggestionProvider:
    version="phase2-query-suggestion-rule-v3"

    def __init__(self,knowledge:TenderKnowledgeProvider|None=None):
        self.knowledge=knowledge or ExtractedTenderKnowledgeProvider()

    def suggest(self,db:Session,bid_id:int)->tuple[list[SuggestedPreBidQuery],list[dict]]:
        existing_missing=set(db.scalars(select(BidPreBidQuery.missing_input_id).where(BidPreBidQuery.bid_project_id==bid_id,BidPreBidQuery.missing_input_id.is_not(None))).all())
        existing_requirements=set(db.scalars(select(BidPreBidQuery.requirement_id).where(BidPreBidQuery.bid_project_id==bid_id,BidPreBidQuery.requirement_id.is_not(None))).all())
        suggestions:list[SuggestedPreBidQuery]=[]
        answered:list[dict]=[]

        gaps=db.scalars(select(BidMissingInput).where(BidMissingInput.bid_project_id==bid_id,BidMissingInput.status.notin_(["Resolved","Not Applicable"]))).all()
        for gap in gaps:
            if gap.id in existing_missing:continue
            question=f"{gap.missing_input_title}. {gap.missing_input_description}"
            check=self.knowledge.check(db,bid_id,question,gap.requirement_id)
            if check.status=="answered_in_tender":
                answered.append({"source_kind":"Missing Input","source_id":gap.id,"title":gap.missing_input_title,"knowledge_check":check.as_dict()})
                continue
            context="With reference to the tender requirement"
            if gap.source_clause:context+=f" at Clause {gap.source_clause}"
            if gap.source_page:context+=f" (Page {gap.source_page})"
            query_text=f"{context}, clarification is requested regarding {gap.missing_input_title}. {gap.missing_input_description.strip()} Kindly provide the required information / confirmation to enable complete and unambiguous bid preparation."
            rationale="The issue remains unresolved after checking the extracted tender knowledge base."
            if check.status=="related_evidence_found":rationale+=" Related tender evidence was found but is not authoritative enough to treat the issue as answered."
            suggestions.append(SuggestedPreBidQuery(
                source_kind="Missing Input",source_id=gap.id,query_title=f"Clarification required: {gap.missing_input_title}",
                query_text=query_text,query_category=_category(gap.input_category),priority=gap.priority,responsible_function=gap.responsible_function,
                requirement_id=gap.requirement_id,missing_input_id=gap.id,source_document_id=gap.source_document_id,source_page=gap.source_page,
                source_clause=gap.source_clause,source_section=gap.source_section,source_excerpt=gap.source_excerpt,
                impact_if_unresolved=gap.impact_if_missing,rationale=rationale,confidence=.90,knowledge_check=check,
            ))

        requirements=db.scalars(select(BidRequirement).where(
            BidRequirement.bid_project_id==bid_id,BidRequirement.requirement_status!="Closed",BidRequirement.review_status=="Needs Clarification",
        )).all()
        for req in requirements:
            if req.id in existing_requirements:continue
            check=self.knowledge.check(db,bid_id,f"{req.requirement_title}. {req.requirement_text}",req.id)
            if check.status=="answered_in_tender":
                answered.append({"source_kind":"Requirement","source_id":req.id,"title":req.requirement_title,"knowledge_check":check.as_dict()})
                continue
            query_text=f"Please clarify the requirement titled '{req.requirement_title}'. {req.requirement_text.strip()} Kindly confirm the Employer's intended requirement and provide any missing particulars necessary for compliant bid preparation."
            rationale="The requirement is marked as needing clarification and remains unresolved after checking the extracted tender knowledge base."
            if check.status=="related_evidence_found":rationale+=" Related evidence exists and should be reviewed with the draft."
            suggestions.append(SuggestedPreBidQuery(
                source_kind="Requirement",source_id=req.id,query_title=f"Clarification of requirement: {req.requirement_title}",
                query_text=query_text,query_category=_category(req.requirement_category),priority=req.priority,responsible_function=req.responsible_function,
                requirement_id=req.id,missing_input_id=None,source_document_id=req.source_document_id,source_page=req.source_page,
                source_clause=req.source_clause,source_section=req.source_section,source_excerpt=req.source_excerpt,
                impact_if_unresolved=None,rationale=rationale,confidence=.82,knowledge_check=check,
            ))

        all_requirements=db.scalars(select(BidRequirement).where(BidRequirement.bid_project_id==bid_id,BidRequirement.requirement_status!="Closed")).all()
        blocked=set(existing_requirements)|{s.requirement_id for s in suggestions if s.requirement_id is not None}
        suggestions.extend(_missing_references(db,bid_id,all_requirements,blocked))
        suggestions.extend(_conflicting_requirements(all_requirements,blocked))

        suggestions.sort(key=lambda x:({"Critical":0,"High":1,"Medium":2,"Low":3}.get(x.priority,4),-x.confidence,x.query_title.lower()))
        return suggestions,answered


def suggest_pre_bid_queries(db:Session,bid_id:int):
    provider=RuleBasedPreBidQuerySuggestionProvider()
    items,answered=provider.suggest(db,bid_id)
    return {
        "provider":provider.version,
        "knowledge_provider":getattr(provider.knowledge,"version","unknown"),
        "items":[x.as_dict() for x in items],
        "answered":answered,
        "summary":{"suggested":len(items),"answered_in_tender":len(answered),"automatic_discoveries":sum(1 for x in items if x.source_kind in {"Missing Reference","Cross-Document Conflict"})},
    }
