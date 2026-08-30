import {describe,expect,test} from "vitest";
import {bidToFormData} from "./page";
import type {Bid} from "@/types";

describe("GAP-001 bid edit value preservation",()=>{
 test("maps every existing optional bid value into the edit form",()=>{
  const bid={
   id:17,
   bid_id:"RLY-017",
   tender_reference_no:"DFCC/PKG/017",
   client:"DFCCIL",
   tender_name:"Railway Systems Package",
   contract_type:"EPC",
   project_type:"Integrated Railway Package",
   package_section:"Section A",
   location:"Ahmedabad",
   estimated_value:1234.56,
   currency:"INR",
   tender_due_date:"2026-10-15",
   pre_bid_meeting_date:"2026-09-12",
   bid_manager:"Bid Manager",
   co_bid_manager:"Co Manager",
   current_stage:"Bid Preparation",
   bid_status:"Active",
   description:"Existing bid description that must not be lost.",
   created_by:1,
   created_at:"2026-08-01T00:00:00Z",
   updated_at:"2026-08-20T00:00:00Z",
  } as Bid;

  expect(bidToFormData(bid)).toMatchObject({
   package_section:"Section A",
   location:"Ahmedabad",
   estimated_value:"1234.56",
   pre_bid_meeting_date:"2026-09-12",
   co_bid_manager:"Co Manager",
   description:"Existing bid description that must not be lost.",
  });
 });

 test("maps null optional values to editable empty fields without inventing data",()=>{
  const bid={
   id:18,
   bid_id:"RLY-018",
   tender_reference_no:"REF-18",
   client:"Client",
   tender_name:"Tender",
   contract_type:"EPC",
   project_type:"OHE",
   package_section:null,
   location:null,
   estimated_value:null,
   currency:"INR",
   tender_due_date:"2026-11-01",
   pre_bid_meeting_date:null,
   bid_manager:"Manager",
   co_bid_manager:null,
   current_stage:"Opportunity",
   bid_status:"Draft",
   description:null,
   created_by:1,
   created_at:"2026-08-01T00:00:00Z",
   updated_at:"2026-08-20T00:00:00Z",
  } as Bid;

  expect(bidToFormData(bid)).toMatchObject({
   package_section:"",
   location:"",
   estimated_value:"",
   pre_bid_meeting_date:"",
   co_bid_manager:"",
   description:"",
  });
 });
});
