import {render,screen} from "@testing-library/react";
import {beforeEach,expect,test,vi} from "vitest";
import {Header} from "./Header";

const api=vi.fn();
vi.mock("@/services/api",()=>({request:(...args:unknown[])=>api(...args)}));

beforeEach(()=>api.mockReset());

test("GAP-004 shows the authenticated user identity",async()=>{
 api.mockResolvedValue({id:2,name:"Satyajeet Panda",roles:["Bid Manager"],permissions:["create_bid"]});
 render(<Header/>);
 expect(await screen.findByText("Satyajeet Panda")).toBeInTheDocument();
 expect(screen.getByText("Bid Manager")).toBeInTheDocument();
 expect(screen.getByLabelText("Satyajeet Panda")).toHaveTextContent("SP");
});
