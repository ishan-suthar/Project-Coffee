import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { WebSourceChips } from "@/components/ResponseSection/WebSourceChips";

describe("WebSourceChips", () => {
  it("renders nothing when sources is null", () => {
    const { container } = render(<WebSourceChips sources={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing when sources is an empty array", () => {
    const { container } = render(<WebSourceChips sources={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders one chip per source, linking out to the real URL", () => {
    render(
      <WebSourceChips
        sources={[
          { url: "https://example.com/a", title: "Example A" },
          { url: "https://example.com/b", title: "Example B" },
        ]}
      />
    );
    const chips = screen.getAllByTestId("web-source-chip");
    expect(chips).toHaveLength(2);
    expect(chips[0]).toHaveTextContent("Example A");
    expect(chips[0]).toHaveAttribute("href", "https://example.com/a");
    expect(chips[0]).toHaveAttribute("target", "_blank");
    expect(chips[1]).toHaveTextContent("Example B");
    expect(chips[1]).toHaveAttribute("href", "https://example.com/b");
  });

  it("renders the URL itself as the label when title equals the url (missing-title fallback)", () => {
    render(<WebSourceChips sources={[{ url: "https://example.com/a", title: "https://example.com/a" }]} />);
    expect(screen.getByTestId("web-source-chip")).toHaveTextContent("https://example.com/a");
  });
});
