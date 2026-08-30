from collections import defaultdict
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BidClauseRiskFinding,BidDocument,TenderKnowledgeChunk


def _role(document:BidDocument):
 dtype=(document.document_type or "").upper()
 name=(document.original_filename or "").lower()
 title=(document.document_title or "").lower()
 hay=f"{name} {title}"
 if dtype=="GCC" or "general conditions" in hay or "general condition" in hay:return "GCC"
 if dtype in {"SCC","PCC"} or any(x in hay for x in ("special conditions","particular conditions","special condition","particular condition")):
  return dtype if dtype in {"SCC","PCC"} else "SCC/PCC"
 return None


def _clean(text:str):
 return " ".join(str(text or "").split())


def contract_clause_variations(db:Session,bid_id:int):
 docs=db.scalars(select(BidDocument).where(
  BidDocument.bid_project_id==bid_id,
  BidDocument.is_latest_revision.is_(True),
  BidDocument.document_status!="Archived",
  BidDocument.duplicate_of_document_id.is_(None),
 )).all()
 roles={x.id:_role(x) for x in docs}
 contract_doc_ids={doc_id for doc_id,role in roles.items() if role}
 if not contract_doc_ids:
  return {"items":[],"summary":{"gcc_documents":0,"special_documents":0,"modified":0,"special_only":0,"risk_linked":0},"version":"contract-clause-variation-v1","note":"No indexed GCC/SCC/PCC document pair is currently available."}

 chunks=db.scalars(select(TenderKnowledgeChunk).where(
  TenderKnowledgeChunk.bid_project_id==bid_id,
  TenderKnowledgeChunk.source_document_id.in_(contract_doc_ids),
  TenderKnowledgeChunk.is_active.is_(True),
  TenderKnowledgeChunk.source_clause.is_not(None),
 ).order_by(TenderKnowledgeChunk.source_document_id,TenderKnowledgeChunk.chunk_index)).all()
 by_doc_clause=defaultdict(list)
 for chunk in chunks:
  by_doc_clause[(chunk.source_document_id,chunk.source_clause)].append(chunk)

 doc_map={x.id:x for x in docs}
 gcc=defaultdict(list);special=defaultdict(list)
 for (doc_id,clause),rows in by_doc_clause.items():
  entry={
   "document_id":doc_id,
   "document_name":doc_map[doc_id].original_filename,
   "role":roles[doc_id],
   "clause":clause,
   "page":next((x.source_page for x in rows if x.source_page),None),
   "text":_clean(" ".join(x.text for x in rows)),
  }
  if roles[doc_id]=="GCC":gcc[clause].append(entry)
  else:special[clause].append(entry)

 risk_findings=db.scalars(select(BidClauseRiskFinding).where(
  BidClauseRiskFinding.bid_project_id==bid_id
 )).all()
 risks_by_doc_clause=defaultdict(list)
 for risk in risk_findings:
  if risk.source_clause:
   risks_by_doc_clause[(risk.source_document_id,risk.source_clause)].append(risk)

 items=[]
 for clause,special_entries in special.items():
  gcc_entries=gcc.get(clause,[])
  for spec in special_entries:
   if gcc_entries:
    comparisons=[]
    for general in gcc_entries:
     similarity=SequenceMatcher(None,general["text"].lower(),spec["text"].lower()).ratio()
     comparisons.append((similarity,general))
    similarity,general=max(comparisons,key=lambda x:x[0])
    if similarity>=.985:continue
    status="Modified Clause"
   else:
    similarity=0.0;general=None;status="Special-Clause Only"
   linked=risks_by_doc_clause.get((spec["document_id"],clause),[])
   items.append({
    "clause":clause,"status":status,"similarity":round(similarity,3),
    "special_document_id":spec["document_id"],"special_document_name":spec["document_name"],
    "special_role":spec["role"],"special_page":spec["page"],"special_text":spec["text"][:3500],
    "gcc_document_id":general["document_id"] if general else None,
    "gcc_document_name":general["document_name"] if general else None,
    "gcc_page":general["page"] if general else None,
    "gcc_text":general["text"][:3500] if general else None,
    "risk_flags":[{
     "id":x.id,"title":x.risk_title,"severity":x.severity,
     "review_status":x.review_status,"reviewer_disposition":x.reviewer_disposition,
    } for x in linked],
    "review_priority":"High" if any(x.severity in {"Critical","High"} and x.review_status!="Closed" for x in linked) else "Medium",
   })
 items.sort(key=lambda x:(0 if x["review_priority"]=="High" else 1,0 if x["status"]=="Modified Clause" else 1,x["clause"]))
 return {
  "items":items,
  "summary":{
   "gcc_documents":sum(1 for x in roles.values() if x=="GCC"),
   "special_documents":sum(1 for x in roles.values() if x and x!="GCC"),
   "modified":sum(1 for x in items if x["status"]=="Modified Clause"),
   "special_only":sum(1 for x in items if x["status"]=="Special-Clause Only"),
   "risk_linked":sum(1 for x in items if x["risk_flags"]),
  },
  "version":"contract-clause-variation-v1",
  "note":"This is a source-linked change map, not a legal interpretation. Similarity identifies text changes; Contracts must determine legal effect and governing precedence.",
 }
