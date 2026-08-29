import re
from openpyxl.utils import get_column_letter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BidRequirement
from app.services.template_structure_parser import parse_xlsx_template


def _norm_clause(value)->str:
    text=str(value or "").strip()
    if re.fullmatch(r"\d+\.0+",text):text=text.split(".")[0]
    return re.sub(r"\s+","",text).rstrip(".")


def _match_requirement(requirements:list[BidRequirement],clause:str):
    target=_norm_clause(clause)
    if not target:return None,.0
    exact=[r for r in requirements if _norm_clause(r.source_clause)==target]
    if len(exact)==1:return exact[0],.99
    if len(exact)>1:
        reviewed=[r for r in exact if r.review_status=="Reviewed"]
        if len(reviewed)==1:return reviewed[0],.97
        return None,.0
    prefixed=[]
    for r in requirements:
        text=f"{r.requirement_title} {r.requirement_text}".strip()
        if re.match(rf"^(?:clause\s+)?{re.escape(target)}(?:\b|\s|[-:])",text,re.I):
            prefixed.append(r)
    if len(prefixed)==1:return prefixed[0],.84
    return None,.0


def build_population_plan(db:Session,bid_id:int,template_content:bytes)->dict:
    structure=parse_xlsx_template(template_content)
    requirements=db.scalars(select(BidRequirement).where(BidRequirement.bid_project_id==bid_id)).all()
    rows=[]
    unresolved=[]
    matched=0

    for table in structure.get("tables",[]):
        if table.get("table_type")!="statement_of_compliance":continue
        sheet_name=table["sheet"]
        sheet=next((x for x in structure["sheets"] if x["name"]==sheet_name),None)
        if not sheet:continue
        clause_col=next((c for c in table["columns"] if c.get("semantic_field")=="clause_reference"),None)
        if not clause_col:continue
        start_row=table["start_row"]
        clause_cell=next((c for c in sheet["cells"] if c["row"]==start_row and c["column"]==clause_col["column"]),None)
        clause=clause_cell.get("value") if clause_cell else None
        requirement,match_confidence=_match_requirement(requirements,clause)
        if requirement:matched+=1

        fields=[]
        for column in table["columns"]:
            semantic=column.get("semantic_field")
            ownership=column.get("ownership")
            coordinate=f'{get_column_letter(column["column"])}{start_row}'
            action="preserve"
            proposed_value=None
            confidence=1.0
            reason=None

            if ownership=="employer_only":
                action="employer_only"
                reason="Reserved for Employer / evaluator input."
            elif semantic=="clause_reference":
                action="preserve"
                proposed_value=clause
                reason="Employer-prescribed clause reference is retained unchanged."
            elif not requirement:
                action="needs_review"
                confidence=.0
                reason="No unique tender requirement could be matched to this clause."
            elif semantic in {"compliant_yes","compliant_no"}:
                status=requirement.compliance_status
                reviewed=requirement.review_status=="Reviewed"
                if status=="Compliant" and reviewed:
                    action="propose_auto_fill"
                    proposed_value="Yes" if semantic=="compliant_yes" else ""
                    confidence=.98
                    reason="Reviewed requirement is marked Compliant."
                elif status=="Non-Compliant" and reviewed:
                    action="propose_auto_fill"
                    proposed_value="No" if semantic=="compliant_no" else ""
                    confidence=.98
                    reason="Reviewed requirement is marked Non-Compliant."
                elif status=="Partially Compliant":
                    action="needs_human_decision"
                    confidence=1.0
                    reason="Employer template is binary Yes/No but internal assessment is Partially Compliant."
                elif status=="Not Applicable":
                    action="needs_human_decision"
                    confidence=1.0
                    reason="Not Applicable cannot be safely converted to the employer's binary Yes/No choice."
                else:
                    action="needs_assessment"
                    confidence=1.0
                    reason="Compliance is not yet reviewed and assessed."
            elif semantic=="tenderer_comments":
                if not requirement:
                    action="needs_review"
                    confidence=.0
                    reason="No requirement match is available for comments."
                elif requirement.compliance_status=="Non-Compliant":
                    if requirement.notes and requirement.review_status=="Reviewed":
                        action="suggest_text"
                        proposed_value=requirement.notes
                        confidence=.70
                        reason="Reviewed requirement notes are available as a draft comment; bidder approval is still required."
                    else:
                        action="needs_input"
                        reason="Non-compliance requires Tenderer's Comments/Proposal."
                elif requirement.compliance_status=="Partially Compliant":
                    action="needs_input"
                    reason="Partial compliance requires an explicit bidder proposal/deviation statement."
                else:
                    action="leave_blank"
                    reason="Comments are normally unnecessary when compliant unless the bidder chooses to add them."
            else:
                action="needs_review"
                confidence=.50
                reason="Field semantics were detected but no safe population rule is available yet."

            fields.append({
                "coordinate":coordinate,
                "header":column.get("header"),
                "semantic_field":semantic,
                "ownership":ownership,
                "action":action,
                "proposed_value":proposed_value,
                "confidence":confidence,
                "reason":reason,
            })

        row={
            "sheet":sheet_name,
            "clause_reference":clause,
            "requirement_id":requirement.id if requirement else None,
            "requirement_title":requirement.requirement_title if requirement else None,
            "requirement_review_status":requirement.review_status if requirement else None,
            "compliance_status":requirement.compliance_status if requirement else None,
            "match_confidence":match_confidence,
            "fields":fields,
        }
        rows.append(row)
        if not requirement or any(f["action"] in {"needs_review","needs_human_decision","needs_assessment","needs_input"} for f in fields):
            unresolved.append(row)

    return {
        "template_type":"statement_of_compliance" if rows else "unknown",
        "rows":rows,
        "summary":{
            "template_rows":len(rows),
            "requirements_matched":matched,
            "unmatched_rows":sum(1 for x in rows if not x["requirement_id"]),
            "rows_requiring_action":len(unresolved),
            "safe_auto_fill_fields":sum(1 for x in rows for f in x["fields"] if f["action"]=="propose_auto_fill"),
            "suggested_text_fields":sum(1 for x in rows for f in x["fields"] if f["action"]=="suggest_text"),
            "employer_only_fields":sum(1 for x in rows for f in x["fields"] if f["action"]=="employer_only"),
        },
        "parser_version":structure.get("parser_version"),
        "plan_version":"phase5-template-population-plan-v1",
    }
