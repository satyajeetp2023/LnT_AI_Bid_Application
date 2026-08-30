import io

from openpyxl import Workbook

from app.services.tender_knowledge_index import _chunks,_spreadsheet_units


def test_tender_chunking_preserves_readable_overlap():
    text="Clause one requires a performance guarantee. Clause two states the guarantee is ten percent. Clause three states the validity period is 180 days."
    chunks=_chunks(text,target_chars=85,overlap_sentences=1)
    assert len(chunks)>=2
    assert any("ten percent" in x.lower() for x in chunks)


def test_xlsx_tender_rows_become_searchable_units():
    wb=Workbook()
    ws=wb.active
    ws.title="BOQ"
    ws.append(["Item No","Description","Unit","Quantity"])
    ws.append(["1","OHE Mast","Nos",250])
    stream=io.BytesIO();wb.save(stream)

    units=_spreadsheet_units("xlsx",stream.getvalue())
    assert any("OHE Mast" in x.text and "250" in x.text for x in units)
    assert any(x.section=="BOQ" for x in units)
