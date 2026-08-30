from types import SimpleNamespace
from app.services.contract_clause_variation import _role

def doc(name,document_type=None,title=None):
    return SimpleNamespace(original_filename=name,document_type=document_type,document_title=title)

def test_contract_document_roles_are_detected():
    assert _role(doc("General Conditions of Contract.pdf","GCC"))=="GCC"
    assert _role(doc("Special Conditions.pdf","SCC"))=="SCC"
    assert _role(doc("Particular Conditions.pdf","PCC"))=="PCC"
    assert _role(doc("technical_specification.pdf",None)) is None
