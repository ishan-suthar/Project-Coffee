import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { OrderBox } from "@/components/OrderBox";
import * as api from "@/lib/api";

vi.mock("@/lib/api");

function makeFile(name: string, type: string, content = "hello"): File {
  return new File([content], name, { type });
}

describe("OrderBox attachments", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listBeans).mockResolvedValue([]);
    vi.mocked(api.uploadFile).mockResolvedValue({
      attachment_id: "att-1",
      filename: "notes.txt",
      content_type: "text/plain",
      kind: "text",
      size_bytes: 5,
      extracted_text_chars: 5,
    });
    // jsdom does not implement the Blob URL API.
    global.URL.createObjectURL = vi.fn(() => "blob:mock-url");
    global.URL.revokeObjectURL = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("adds a chip when a file is selected via the hidden input", async () => {
    render(<OrderBox />);
    const input = screen.getByTestId("attachment-file-input") as HTMLInputElement;
    const file = makeFile("notes.txt", "text/plain");

    fireEvent.change(input, { target: { files: [file] } });

    expect(screen.getByTestId("attachment-chip-filename")).toHaveTextContent("notes.txt");
    await waitFor(() => {
      expect(screen.getByTestId("attachment-chip")).toHaveAttribute("data-status", "ready");
    });
    expect(api.uploadFile).toHaveBeenCalledWith(expect.any(String), file);
  });

  it("removes the chip when its remove button is clicked", async () => {
    render(<OrderBox />);
    const input = screen.getByTestId("attachment-file-input") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [makeFile("notes.txt", "text/plain")] } });

    await waitFor(() => {
      expect(screen.getByTestId("attachment-chip")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("attachment-chip-remove"));

    expect(screen.queryByTestId("attachment-chip")).not.toBeInTheDocument();
  });

  it("rejects a disallowed file extension client-side without uploading", async () => {
    render(<OrderBox />);
    const input = screen.getByTestId("attachment-file-input") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [makeFile("archive.zip", "application/zip")] } });

    expect(screen.getByTestId("attachment-chip")).toHaveAttribute("data-status", "error");
    expect(screen.getByTestId("attachment-chip-error")).toHaveTextContent(".zip");
    expect(api.uploadFile).not.toHaveBeenCalled();
  });

  it("shows a thumbnail for an image attachment", async () => {
    render(<OrderBox />);
    const input = screen.getByTestId("attachment-file-input") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [makeFile("screenshot.png", "image/png")] } });

    expect(screen.getByTestId("attachment-chip-thumbnail")).toBeInTheDocument();
  });
});
