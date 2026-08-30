import {fireEvent,render,screen} from "@testing-library/react";
import {beforeEach,expect,test,vi} from "vitest";
import {Sidebar} from "./Sidebar";

const api=vi.fn();
let pathname="/";
vi.mock("next/navigation",()=>({usePathname:()=>pathname}));
vi.mock("@/services/api",()=>({request:(...args:unknown[])=>api(...args)}));

beforeEach(()=>{api.mockReset();pathname="/"});

test("GAP-005 hides Create New Bid without create permission",async()=>{
 api.mockResolvedValue({permissions:["view_document"],is_admin:false,bid_project_ids:[1]});
 render(<Sidebar/>);
 await screen.findByText("Overview");
 fireEvent.click(screen.getByText("Overview"));
 await screen.findByText("Dashboard");
 expect(screen.queryByText("Create New Bid")).not.toBeInTheDocument();
});

test("GAP-005 does not treat /bids/new as a bid workspace",async()=>{
 pathname="/bids/new";
 api.mockResolvedValue({permissions:["create_bid","view_document","requirement_view"],is_admin:false,bid_project_ids:[]});
 render(<Sidebar/>);
 const intelligence=await screen.findByText("Tender Intelligence");
 fireEvent.click(intelligence);
 await screen.findByText("Document Repository");
 expect(screen.getByText("Document Repository").closest("[aria-disabled='true']")).not.toBeNull();
});
