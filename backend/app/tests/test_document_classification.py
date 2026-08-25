import pytest

from app.services.document_classification import classify_content

@pytest.mark.parametrize(("filename","text","category"),[
 ("technical_specifications.txt","technical specification technical requirements specification","Technical Specifications"),
 ("GCC_conditions_of_contract.txt","general conditions of contract gcc particular conditions of contract","Conditions of Contract"),
 ("BOQ_price_schedule.txt","bill of quantities boq schedule of prices","BOQ / Price Schedule"),
 ("addendum_01.txt","addendum amendment to tender corrigendum","Addendum / Corrigendum"),
])
def test_strong_rule_classifications(filename,text,category):
 result=classify_content(filename,text)
 assert result.category==category and result.status=="classified"
 assert result.confidence is not None and 0<=result.confidence<=1

def test_low_confidence_needs_review():
 result=classify_content("miscellaneous.txt","general tender information")
 assert result.category is None and result.status=="needs_review"
 assert result.confidence is None or 0<=result.confidence<.5

def test_filename_only_is_not_artificially_high_confidence():
 result=classify_content("boq.xlsx","")
 assert result.status=="needs_review"
 assert result.confidence is not None and 0<=result.confidence<.8
