import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { DiffView } from "@/components/Settings/DiffView";

describe("DiffView", () => {
  it("shows the default empty message when the diff is blank", () => {
    render(<DiffView diff="" />);
    expect(screen.getByText("No changes proposed.")).toBeInTheDocument();
  });

  it("shows a custom empty message when provided", () => {
    render(<DiffView diff="   " emptyMessage="Nothing to see here." />);
    expect(screen.getByText("Nothing to see here.")).toBeInTheDocument();
  });

  it("renders every line of a non-empty diff", () => {
    render(<DiffView diff={"--- a\n+++ b\n@@ -1 +1 @@\n-old\n+new\n"} />);
    const view = screen.getByTestId("diff-view");
    expect(view).toHaveTextContent("--- a");
    expect(view).toHaveTextContent("+++ b");
    expect(view).toHaveTextContent("-old");
    expect(view).toHaveTextContent("+new");
  });
});
