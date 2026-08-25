export type Bid={id:number;bid_id:string;tender_reference_no:string;tender_name:string;client:string;location?:string|null;contract_type:string;project_type:string;tender_due_date:string;current_stage:string;bid_status:string;bid_manager:string;updated_at:string};
export type Document={
  id:number;bid_project_id:number;original_filename:string;file_extension:string;mime_type:string;file_size:number;checksum:string;
  uploaded_by:number;uploader_name:string|null;uploaded_at:string;document_status:string;document_category:string|null;
  document_type:string|null;document_number:string|null;document_title:string|null;revision:string|null;document_date:string|null;
  classification_status:"pending"|"classified"|"needs_review"|"manually_classified"|null;
  classification_confidence:number|null;is_latest_version:boolean|null;remarks:string|null;
  document_subcategory:string|null;information_tags:string[];revision_no:number;is_latest_revision:boolean;
  revision_of_document_id:number|null;duplicate_of_document_id:number|null;notes:string|null;
};
export type Page<T>={items:T[];total:number;page:number;page_size:number};
export type Requirement={id:number;bid_project_id:number;source_document_id:number|null;requirement_category:string;requirement_type:string|null;requirement_title:string;requirement_text:string;source_page:string|null;source_clause:string|null;source_section:string|null;source_excerpt:string|null;responsible_function:string|null;responsible_person:string|null;due_date:string|null;priority:string;requirement_status:string;is_mandatory:boolean;compliance_status:string;review_status:string;reviewed_by:number|null;reviewed_at:string|null;extraction_method:string;extraction_confidence:number|null;created_by:number;created_at:string;updated_at:string;notes:string|null;source_original_filename:string|null;source_document_title:string|null;source_document_category:string|null};
export type RequirementPage=Page<Requirement>&{summary:{total:number;critical:number;open:number;needs_review:number;non_compliant:number}};
export type RequirementExtractionSummary={document_id:number;created:number;skipped_duplicates:number;low_confidence_skipped:number;no_text:boolean;extractor_version:string};
export type MissingInput={id:number;bid_project_id:number;requirement_id:number|null;source_document_id:number|null;missing_input_title:string;missing_input_description:string;input_category:string;input_type:string;responsible_function:string|null;responsible_person:string|null;requested_from:string|null;required_by_date:string|null;priority:string;status:string;impact_if_missing:string|null;resolution_notes:string|null;source_page:string|null;source_clause:string|null;source_section:string|null;source_excerpt:string|null;created_by:number;created_at:string;updated_at:string;resolved_by:number|null;resolved_at:string|null;requirement_title:string|null;requirement_category:string|null;requirement_status:string|null;source_original_filename:string|null;source_document_title:string|null};
export type MissingInputPage=Page<MissingInput>&{summary:{total:number;critical:number;open:number;overdue:number;requested:number;resolved:number}};
