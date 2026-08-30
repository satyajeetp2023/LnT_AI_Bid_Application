import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BidDocument,BidRequirement
from app.services.requirement_extraction import RuleBasedRequirementExtractionProvider


STOP={
 "what","which","where","when","who","how","much","many","does","do","is","are","the","a","an","of","to","in","for","and",
 "this","that","with","from","our","bid","tender","contract","please","tell","me","show","give"
}


def _terms(text:str):
 return {x for x in re.findall(r"[a-z0-9%]+",str(text or "").lower()) if len(x)>1 and x not in STOP}


def _sentences(text:str):
 parts=re.split(r"(?<=[.!?;])\s+|\n+",str(text or ""))
 return [re.sub(r"\s+"," ",x).strip() for x in parts if len(re.sub(r"\s+"," ",x).strip())>=20]


def _numeric_question(question:str):
 lower=question.lower()
 return any(x in lower for x in ("percentage","percent","%","amount","rate","days","months","years","period","retention","ld","liquidated damages","security","guarantee"))


@dataclass
class Evidence:
 text:str
 document_id:int|None
 document_name:str|None
 page:str|None
 clause:str|None
 section:str|None
 source_kind:str
 score:float


def _score(question:str,text:str,source_kind:str):
 q=_terms(question);t=_terms(text)
 if not q or not t:return 0.0
 overlap=len(q&t)/max(1,len(q))
 coverage=len(q&t)/max(1,min(len(q),8))
 phrase_bonus=.0
 lower_q=question.lower();lower_t=text.lower()
 important=[x for x in q if len(x)>=5]
 if important and all(x in lower_t for x in important[:3]):phrase_bonus=.12
 numeric_bonus=.10 if _numeric_question(question) and re.search(r"\b\d+(?:\.\d+)?\s*(?:%|percent|days?|months?|years?|crore|lakh|inr|rs\.?|₹)",lower_t,re.I) else 0
 source_bonus=.08 if source_kind=="Extracted Requirement" else 0
 return min(.99,.58*overlap+.22*coverage+phrase_bonus+numeric_bonus+source_bonus)


def _best_sentence(question:str,text:str):
 candidates=_sentences(text)
 if not candidates:return text[:1200]
 ranked=sorted(candidates,key=lambda x:_score(question,x,"Sentence"),reverse=True)
 best=ranked[0]
 # include adjacent support only when it is short enough to stay readable
 return best[:1600]


def tender_question_answer(
 db:Session,bid_id:int,question:str,storage,user_id:int|None=None,request_metadata:dict|None=None,top_k:int=6
):
 question=re.sub(r"\s+"," ",question).strip()
 if len(question)<3:raise ValueError("Question is too short")
 evidence=[]

 requirements=db.scalars(select(BidRequirement).where(
  BidRequirement.bid_project_id==bid_id,
  BidRequirement.requirement_status.notin_(["Closed","Not Applicable"]),
 )).all()
 for req in requirements:
  text=req.source_excerpt or req.requirement_text
  score=_score(question,text,"Extracted Requirement")
  if score<.12:continue
  evidence.append(Evidence(
   text=_best_sentence(question,text),
   document_id=req.source_document_id,
   document_name=req.source_original_filename,
   page=req.source_page,clause=req.source_clause,section=req.source_section,
   source_kind="Extracted Requirement",score=score,
  ))

 documents=db.scalars(select(BidDocument).where(
  BidDocument.bid_project_id==bid_id,
  BidDocument.is_latest_revision.is_(True),
  BidDocument.document_status!="Archived",
  BidDocument.duplicate_of_document_id.is_(None),
 )).all()
 provider=RuleBasedRequirementExtractionProvider()
 for doc in documents:
  if not doc.storage_path or doc.file_extension.lower() not in {"pdf","docx","txt"}:continue
  try:units=provider.source_units(doc.file_extension,storage.read(doc.storage_path))
  except Exception:continue
  for unit in units:
   for sentence in _sentences(unit.text):
    score=_score(question,sentence,"Tender Document")
    if score<.18:continue
    clause_match=re.match(r"\s*(?:(?:clause|section)\s+)?(\d+(?:\.\d+){1,6})\b",sentence,re.I)
    evidence.append(Evidence(
     text=sentence[:1800],document_id=doc.id,document_name=doc.original_filename,
     page=str(unit.page) if unit.page else None,clause=clause_match.group(1) if clause_match else None,
     section=unit.section,source_kind="Tender Document",score=score,
    ))

 # deduplicate same sentence/document/page
 unique={}
 for item in evidence:
  key=(item.document_id,item.page,re.sub(r"\W+","",item.text.lower())[:180])
  if key not in unique or item.score>unique[key].score:unique[key]=item
 ranked=sorted(unique.values(),key=lambda x:x.score,reverse=True)[:max(1,min(top_k,10))]
 top=ranked[0] if ranked else None
 reliable=bool(top and top.score>=.34)
 if reliable:
  answer=_best_sentence(question,top.text)
  confidence="High" if top.score>=.70 else "Medium" if top.score>=.50 else "Low"
 else:
  answer="I could not find a sufficiently reliable answer in the currently indexed tender evidence."
  confidence="Not Found"

 return {
  "question":question,
  "answer":answer,
  "confidence":confidence,
  "grounded":reliable,
  "evidence":[{
   "document_id":x.document_id,"document_name":x.document_name,"page":x.page,"clause":x.clause,"section":x.section,
   "excerpt":x.text,"score":round(x.score,3),"source_kind":x.source_kind,
  } for x in ranked],
  "retrieval_version":"tender-qa-extractive-v1",
  "note":"The answer is limited to bid-scoped source evidence. If evidence is weak or absent, the system returns Not Found rather than inferring an answer.",
 }
