import {act,render,screen} from "@testing-library/react";
import {expect,test,vi} from "vitest";
import BidDocuments from "./page";

vi.mock("@/features/documents/UploadZone",()=>({UploadZone:()=> <div>Upload control</div>}));
vi.mock("@/services/api",()=>({
 API:"http://test/api/v1",
 request:vi.fn((path:string)=>Promise.resolve(
  path==="/bids/1"
   ?{id:1,bid_id:"RLY-01",tender_name:"Railway Package",client:"DFCCIL",location:"Gujarat",tender_due_date:"2026-10-15",bid_status:"Active"}
   :{items:[{id:4,bid_project_id:1,original_filename:"technical.txt",file_extension:"txt",mime_type:"text/plain",file_size:100,checksum:"x",uploaded_by:1,uploader_name:"Admin",uploaded_at:"2026-08-25T00:00:00Z",document_status:"Uploaded",document_category:"Technical Specifications",document_type:null,document_number:null,document_title:null,revision:null,document_date:null,classification_status:"classified",classification_confidence:.91,is_latest_version:true,remarks:null,document_subcategory:null,information_tags:[],revision_no:1,is_latest_revision:true,revision_of_document_id:null,duplicate_of_document_id:null,notes:null}],total:1,page:1,page_size:20}
 ))
}));

test("renders automatically classified repository document",async()=>{
 await act(async()=>{render(<BidDocuments params={Promise.resolve({id:"1"})}/>)});
 expect((await screen.findAllByText("technical.txt")).length).toBeGreaterThan(0);
 expect(screen.getAllByText("Auto Classified").length).toBeGreaterThan(0);
 expect(screen.queryByText("Extract Requirements")).not.toBeInTheDocument();
 expect(screen.getByText(/extracts bid requirements/i)).toBeInTheDocument();
});
