import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BidDocument,BidRequirement,TenderKnowledgeChunk
from app.services.requirement_extraction import RuleBasedRequirementExtractionProvider


STOP={
 "what","which","where","when","who","how","much","many","does","do","is","are","the","a","an","of","to","in","for","and",
 "this","that","with","from","our","bid","tender","contract","please","tell","me","show","give"
}

SYNONYM_EXPANSIONS={
 "ld":{"ld","liquidated","damages","delay"},
 "liquidated":{"ld","liquidated","damages","delay"},
 "retention":{"retention","withholding","withheld"},
 "dlp":{"dlp","defects","liability","warranty"},
 "defects":{"dlp","defects","liability","warranty"},
 "pbg":{"pbg","performance","security","guarantee"},
 "guarantee":{"pbg","performance","security","guarantee"},
 "mobilization":{"mobilization","mobilisation","advance"},
 "mobilisation":{"mobilization","mobilisation","advance"},
 "emd":{"emd","security","earnest"},
 "gst":{"gst","tax","taxes"},
 "indemnity":{"indemnity","indemnify"},
 "indemnify":{"indemnity","indemnify"},
 "termination":{"termination","terminate"},
}



def _terms(text:str):
 raw={x for x in re.findall(r"[a-z0-9%]+",str(text or "").lower()) if len(x)>1 and x not in STOP}
 expanded=set(raw)
 for token in list(raw):
  expanded.update(SYNONYM_EXPANSIONS.get(token,set()))
 return expanded


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


def _numeric_facts(text:str):
 facts=[]
 pattern=re.compile(r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>%|percent|days?|months?|years?|crore|cr\b|lakh|inr|rs\.?|₹)",re.I)
 for match in pattern.finditer(str(text or "")):
  unit=match.group("unit").lower().replace("percent","%")
  unit="crore" if unit=="cr" else unit
  facts.append({"value":float(match.group("value")),"unit":unit,"display":match.group(0).strip()})
 return facts


def _conflicts(question:str,ranked:list):
 if not _numeric_question(question):return []
 candidates=[]
 for evidence in ranked:
  if evidence.score<.30:continue
  for fact in _numeric_facts(evidence.text):
   candidates.append({
    **fact,"document_id":evidence.document_id,"document_name":evidence.document_name,
    "page":evidence.page,"clause":evidence.clause,"score":evidence.score,
   })
 groups={}
 for item in candidates:
  groups.setdefault(item["unit"],[]).append(item)
 conflicts=[]
 for unit,items in groups.items():
  values=sorted({round(x["value"],6) for x in items})
  if len(values)<=1:continue
  conflicts.append({"unit":unit,"values":items})
 return conflicts


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

 chunks=db.scalars(select(TenderKnowledgeChunk).where(
  TenderKnowledgeChunk.bid_project_id==bid_id,
  TenderKnowledgeChunk.is_active.is_(True),
 )).all()
 indexed_used=bool(chunks)
 indexed_documents={}
 if indexed_used:
  doc_ids={x.source_document_id for x in chunks}
  indexed_documents={x.id:x for x in db.scalars(select(BidDocument).where(BidDocument.id.in_(doc_ids))).all()}
  for chunk in chunks:
   score=_score(question,chunk.text,"Tender Knowledge Index")
   if score<.18:continue
   doc=indexed_documents.get(chunk.source_document_id)
   evidence.append(Evidence(
    text=_best_sentence(question,chunk.text),document_id=chunk.source_document_id,
    document_name=doc.original_filename if doc else None,
    page=chunk.source_page,clause=chunk.source_clause,section=chunk.source_section,
    source_kind="Tender Knowledge Index",score=score,
   ))
 else:
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
 conflicts=_conflicts(question,ranked)
 if conflicts:
  values=[]
  for conflict in conflicts:
   values.extend(x["display"] for x in conflict["values"])
  answer="Conflicting tender values were found: "+", ".join(dict.fromkeys(values))+". Review the cited sources before relying on one value."
  confidence="Conflict"
  grounded=True
  answer_mode="conflict"
 elif reliable:
  distinct=[]
  seen=set()
  for item in ranked:
   key=(item.document_id,item.page,item.clause)
   if item.score<.30 or key in seen:continue
   seen.add(key);distinct.append(_best_sentence(question,item.text))
   if len(distinct)>=2:break
  answer=" ".join(distinct) if distinct else _best_sentence(question,top.text)
  confidence="High" if top.score>=.70 else "Medium" if top.score>=.50 else "Low"
  grounded=True
  answer_mode="grounded_extract"
 else:
  answer="I could not find a sufficiently reliable answer in the currently indexed tender evidence."
  confidence="Not Found"
  grounded=False
  answer_mode="not_found"

 return {
  "question":question,
  "answer":answer,
  "confidence":confidence,
  "grounded":grounded,
  "answer_mode":answer_mode,
  "conflicts":conflicts,
  "knowledge_index_used":indexed_used,
  "indexed_chunk_count":len(chunks),
  "evidence":[{
   "document_id":x.document_id,"document_name":x.document_name,"page":x.page,"clause":x.clause,"section":x.section,
   "excerpt":x.text,"score":round(x.score,3),"source_kind":x.source_kind,
  } for x in ranked],
  "retrieval_version":"tender-qa-indexed-v4",
  "note":"The answer is limited to bid-scoped source evidence. The persistent tender index is used when available; weak evidence returns Not Found, and materially conflicting numeric values are surfaced rather than silently resolved.",
 }
