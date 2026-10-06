import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { PantrySourceChips } from "@/components/ResponseSection/PantrySourceChips";
import * as api from "@/lib/api";

vi.mock("@/lib/api");

describe("PantrySourceChips", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders nothing when sources is null", () => {
    const { container } = render(<PantrySourceChips sources={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing when sources is an empty array", () => {
    const { container } = render(<PantrySourceChips sources={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders one chip per source", () => {
    render(<PantrySourceChips sources={["knowledge/00_index.md", "knowledge/README.md"]} />);
    const chips = screen.getAllByTestId("pantry-source-chip");
    expect(chips).toHaveLength(2);
    expect(chips[0]).toHaveTextContent("knowledge/00_index.md");
    expect(chips[1]).toHaveTextContent("knowledge/README.md");
  });

  it("clicking a chip fetches and displays that file's content", async () => {
    vi.mocked(api.getPantryFile).mockResolvedValue({
      path: "knowledge/00_index.md",
      content: "# Knowledge Index\n\nSome content.",
    });

    render(<PantrySourceChips sources={["knowledge/00_index.md"]} />);
    fireEvent.click(screen.getByTestId("pantry-source-chip"));

    expect(api.getPantryFile).toHaveBeenCalledWith("knowledge/00_index.md");
    await waitFor(() => {
      expect(screen.getByText(/Some content\./)).toBeInTheDocument();
    });
  });

  it("shows an error message when the file fetch fails", async () => {
    vi.mocked(api.getPantryFile).mockRejectedValue(new Error("Failed to load Pantry file: 404"));

    render(<PantrySourceChips sources={["knowledge/missing.md"]} />);
    fireEvent.click(screen.getByTestId("pantry-source-chip"));

    await waitFor(() => {
      expect(screen.getByTestId("file-viewer-error")).toHaveTextContent(
        "Failed to load Pantry file: 404"
      );
    });
  });

  it("closes the viewer when Close is clicked", async () => {
    vi.mocked(api.getPantryFile).mockResolvedValue({
      path: "knowledge/00_index.md",
      content: "content",
    });

    render(<PantrySourceChips sources={["knowledge/00_index.md"]} />);
    fireEvent.click(screen.getByTestId("pantry-source-chip"));
    await waitFor(() => screen.getByTestId("file-viewer-overlay"));

    fireEvent.click(screen.getByLabelText("Close file viewer"));
    expect(screen.queryByTestId("file-viewer-overlay")).not.toBeInTheDocument();
  });
});
