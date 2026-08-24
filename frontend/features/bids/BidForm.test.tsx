import {render,screen,fireEvent} from "@testing-library/react";import {vi,test,expect} from "vitest";import {BidForm} from "./BidForm";
vi.mock("next/navigation",()=>({useRouter:()=>({push:vi.fn(),back:vi.fn()})}));
test("shows required-field validation",async()=>{render(<BidForm/>);fireEvent.click(screen.getByText("Save & Continue"));expect(await screen.findAllByText("Required")).not.toHaveLength(0);expect(screen.getByText("Due date is required")).toBeInTheDocument()});
