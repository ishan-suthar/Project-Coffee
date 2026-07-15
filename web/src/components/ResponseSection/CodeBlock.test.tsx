import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { CodeBlock } from "@/components/ResponseSection/CodeBlock";

describe("CodeBlock", () => {
  beforeEach(() => {
    Object.assign(navigator, { clipboard: { writeText: vi.fn().mockResolvedValue(undefined) } });
  });

  const sampleCode = 'print("hi")';

  it("shows the language label parsed from the className", async () => {
    render(<CodeBlock className="language-python">{sampleCode}</CodeBlock>);
    await waitFor(() => {
      expect(screen.getByTestId("code-block-language-label")).toHaveTextContent("python");
    });
  });

  it("falls back to 'text' when no language className is given", () => {
    render(<CodeBlock>plain text</CodeBlock>);
    expect(screen.getByTestId("code-block-language-label")).toHaveTextContent("text");
  });

  it("copies the code to the clipboard and flashes 'Copied'", async () => {
    render(<CodeBlock className="language-python">{sampleCode}</CodeBlock>);
    fireEvent.click(screen.getByTestId("code-block-copy-button"));

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(sampleCode);
      expect(screen.getByTestId("code-block-copy-button")).toHaveTextContent("Copied");
    });
  });

  it("renders the code content even before Shiki highlighting resolves", () => {
    render(<CodeBlock className="language-python">{sampleCode}</CodeBlock>);
    expect(screen.getByText(sampleCode)).toBeInTheDocument();
  });
});
