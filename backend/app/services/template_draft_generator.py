import io

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
):
    if choice_mark not in ALLOWED_CHOICE_MARKS:
        raise ValueError("Unsupported choice mark")
    plan=build_population_plan(db,bid_id,template_content)
    workbook=load_workbook(io.BytesIO(template_content),data_only=False)
    written=[]
    skipped=[]

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
        "plan_version":plan.get("plan_version"),
        "generator_version":"phase5-controlled-xlsx-generator-v1",
    }
