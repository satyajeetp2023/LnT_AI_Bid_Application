import io
import re
from dataclasses import asdict,dataclass

from openpyxl import load_workbook


YES_NO_SIGNALS={"yes","no","compliant","not compliant","compliance"}
FIELD_HINTS=("tenderer","document","name","date","reference","clause","comment","proposal","signature","stamp","designation")
TABLE_HINTS=("clause","yes","no","comments","proposal","description","item","response","compliance")


@dataclass
class TemplateCell:
    coordinate:str
    row:int
    column:int
    value:str|None
    merged_range:str|None
    role:str
    confidence:float


@dataclass
class TemplateTable:
    sheet:str
    header_row:int
    start_row:int
    end_row:int
    columns:list[dict]
    table_type:str
    confidence:float


def _norm(value)->str:
    return re.sub(r"\s+"," ",str(value or "")).strip()


def _merged_range(ws,coordinate:str)->str|None:
    for rng in ws.merged_cells.ranges:
        if coordinate in rng:return str(rng)
    return None


def _cell_role(value:str,has_border:bool,merged:bool)->tuple[str,float]:
    lower=value.lower()
    if any(x in lower for x in FIELD_HINTS) and (":" in value or len(value)<80):
        return "label",.86
    if lower in YES_NO_SIGNALS:
        return "choice_header",.96
    if has_border and not value:
        return "candidate_input",.74
    if merged and len(value)>6:
        return "heading",.78
    if value:
        return "text",.60
    return "blank",.20


def _table_type(headers:list[str])->tuple[str,float]:
    joined=" ".join(headers).lower()
    if "clause" in joined and "yes" in joined and "no" in joined:
        return "statement_of_compliance",.98
    if "clause" in joined and ("comment" in joined or "proposal" in joined):
        return "compliance_or_deviation_register",.92
    hits=sum(1 for x in TABLE_HINTS if x in joined)
    if hits>=3:return "structured_submission_table",min(.90,.55+hits*.07)
    return "generic_table",.55


def parse_xlsx_template(content:bytes)->dict:
    workbook=load_workbook(io.BytesIO(content),data_only=False)
    sheets=[]
    all_tables=[]
    for ws in workbook.worksheets:
        cells=[]
        nonempty=[]
        for row in ws.iter_rows():
            for cell in row:
                value=_norm(cell.value)
                merged_range=_merged_range(ws,cell.coordinate)
                has_border=any(getattr(side,"style",None) for side in (cell.border.left,cell.border.right,cell.border.top,cell.border.bottom))
                role,confidence=_cell_role(value,has_border,bool(merged_range))
                if value or has_border:
                    cells.append(asdict(TemplateCell(cell.coordinate,cell.row,cell.column,value or None,merged_range,role,confidence)))
                if value:nonempty.append(cell)

        tables=[]
        for row_index in range(1,ws.max_row+1):
            headers=[]
            columns=[]
            for col_index in range(1,ws.max_column+1):
                value=_norm(ws.cell(row_index,col_index).value)
                if value:
                    headers.append(value)
                    columns.append({"column":col_index,"coordinate":ws.cell(row_index,col_index).coordinate,"header":value})
            if len(headers)<2:continue
            lower=" ".join(headers).lower()
            hits=sum(1 for x in TABLE_HINTS if x in lower)
            if hits<2:continue
            table_type,confidence=_table_type(headers)
            end_row=row_index
            for scan in range(row_index+1,min(ws.max_row,row_index+50)+1):
                if any(_norm(ws.cell(scan,c["column"]).value) for c in columns) or any(
                    any(getattr(side,"style",None) for side in (ws.cell(scan,c["column"]).border.left,ws.cell(scan,c["column"]).border.right,ws.cell(scan,c["column"]).border.top,ws.cell(scan,c["column"]).border.bottom))
                    for c in columns
                ):
                    end_row=scan
                elif end_row>row_index:
                    break
            table=asdict(TemplateTable(ws.title,row_index,row_index+1,end_row,columns,table_type,confidence))
            tables.append(table);all_tables.append(table)

        sheets.append({
            "name":ws.title,
            "max_row":ws.max_row,
            "max_column":ws.max_column,
            "merged_ranges":[str(x) for x in ws.merged_cells.ranges],
            "cells":cells,
            "tables":tables,
        })

    return {
        "file_type":"xlsx",
        "sheet_count":len(workbook.worksheets),
        "sheets":sheets,
        "tables":all_tables,
        "summary":{
            "tables_detected":len(all_tables),
            "compliance_tables":sum(1 for x in all_tables if x["table_type"]=="statement_of_compliance"),
            "candidate_input_cells":sum(1 for s in sheets for c in s["cells"] if c["role"]=="candidate_input"),
        },
        "parser_version":"phase5-xlsx-template-parser-v1",
    }
