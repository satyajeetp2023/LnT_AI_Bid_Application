import io
import re

from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.services.template_population_plan import build_population_plan


ALLOWED_CHOICE_MARKS={"X","✓","Yes"}


def generate_controlled_xlsx_draft(
    db:Session,
    bid_id:int,
    template_content:bytes,
    choice_mark:str="X",
    include_suggested_text:bool=False,
    header_values:dict|None=None,
):
    if choice_mark not in ALLOWED_CHOICE_MARKS:
        raise ValueError("Unsupported choice mark")
    plan=build_population_plan(db,bid_id,template_content)
    workbook=load_workbook(io.BytesIO(template_content),data_only=False)
    written=[]
    skipped=[]
    header_values=header_values or {}

    structure=plan.get("_structure") if isinstance(plan.get("_structure"),dict) else None
    if structure is None:
        from app.services.template_structure_parser import parse_xlsx_template
        structure=parse_xlsx_template(template_content)
    for placeholder in structure.get("workbook_placeholders",[]):
        value=str(header_values.get(placeholder["semantic_field"],"") or "").strip()
        if not value:continue
        label=placeholder["label"]
        pattern=re.compile(rf"\b({re.escape(label)})\s*[-_]{{5,}}",re.I)
        for occurrence in placeholder.get("occurrences",[]):
            ws=workbook[occurrence["sheet"]]
            cell=ws[occurrence["coordinate"]]
            original=str(cell.value or "")
            updated=pattern.sub(lambda m:f"{m.group(1)}: {value}",original)
            if updated!=original:
                cell.value=updated
                written.append({"sheet":occurrence["sheet"],"coordinate":occurrence["coordinate"],"semantic_field":placeholder["semantic_field"],"value":value})

    for row in plan["rows"]:
        ws=workbook[row["sheet"]]
        for field in row["fields"]:
            coordinate=field.get("coordinate")
            if not coordinate:continue
            action=field.get("action")
            semantic=field.get("semantic_field")
            proposed=field.get("proposed_value")

            if action=="propose_auto_fill":
                if semantic in {"compliant_yes","compliant_no"}:
                    if proposed:
                        ws[coordinate]=choice_mark
                        written.append({"sheet":row["sheet"],"coordinate":coordinate,"semantic_field":semantic,"value":choice_mark})
                elif proposed not in (None,""):
                    ws[coordinate]=proposed
                    written.append({"sheet":row["sheet"],"coordinate":coordinate,"semantic_field":semantic,"value":proposed})
            elif action=="suggest_text" and include_suggested_text and proposed:
                ws[coordinate]=proposed
                written.append({"sheet":row["sheet"],"coordinate":coordinate,"semantic_field":semantic,"value":proposed})
            elif action in {"needs_review","needs_human_decision","needs_assessment","needs_input"}:
                skipped.append({"sheet":row["sheet"],"coordinate":coordinate,"semantic_field":semantic,"reason":field.get("reason")})

    output=io.BytesIO()
    workbook.save(output)
    return output.getvalue(),{
        "written_fields":len(written),
        "unresolved_fields":len(skipped),
        "written":written,
        "unresolved":skipped,
        "choice_mark":choice_mark,
        "suggested_text_included":include_suggested_text,
        "header_values_applied":sorted(k for k,v in header_values.items() if str(v or "").strip()),
        "plan_version":plan.get("plan_version"),
        "generator_version":"phase5-controlled-xlsx-generator-v2",
    }
