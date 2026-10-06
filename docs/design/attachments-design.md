# File and Image Attachments Design

Status: Brew 38A draft - Decaf plan, no code written
Date: 2026-07-11

## 0. Reading done before this plan

Read in full: `router/EVENT_CONTRACT.md` (v1.1), `router/app/classifier.py`,
`router/app/routing.py`, `router/app/aliases.py`, `router/app/main.py`,
`router/app/openrouter_client.py`, `router/app/ledger.py`,
`router/config/beans.yaml`, `router/config/settings.yaml`,
`web/src/components/OrderBox/index.tsx`, `web/src/lib/{chat,api,sse,events}.ts`,
`web/src/store/chatStore.ts`. Checked installed packages directly rather
than assuming: `pypdf` 6.13.1, `pillow` 11.3.0, `charset_normalizer`, and
`python-multipart` 0.0.32 are all **already installed** - `python-multipart`
in particular is exactly what FastAPI needs for `UploadFile`, so this Brew
needs zero new Python dependencies. `pdfplumber` and `pymupdf` are not
installed.

## 1. What already exists - do not rebuild

- `router/app/classifier.py:Attachment` (filename, content_type) and
  `ClassificationResult.needs_vision` **already exist** and
  `needs_vision` is already computed correctly
  (`any(a.content_type.startswith("image/") for a in attachments)`).
  Nothing to add here - Requirement 4's `needs_vision` half is done.
- `router/app/main.py:run_order()` **already accepts** an `attachments`
  parameter and threads it into `classify()`. Nothing populates it today
  - `OrderRequest` (the HTTP body model) has no `attachments` field, and
    no upload endpoint exists yet. This plan wires the missing half, not
    a new classifier/run_order shape.
- `_classify_complexity()` already has `len(attachments) > 2 -> cold_brew`.
  Requirement 4 asks for attachments to "push complexity toward
  cold_brew" more generally - Section 6 below proposes a specific,
  approvable rule table rather than leaving "push toward" as a vague
  instruction implemented ad hoc.

## 2. Real gaps found - surfaced now, not worked around silently

1. **No Bean in `beans.yaml` has `vision: true`.** All four Beans
   (House Blend, Second Pour, Guest Bean, Reserve Blend) are
   `vision: false`. This is the same class of gap as the no-premium-Bean
   finding from Brew 36 (`docs/design/coffee-core-router-design.md`
   Section 3) - the routing constraint this plan builds (Requirement 4:
   "escalating to the vision-capable default") **has nothing to escalate
   to today.** See Section 7, Question 1 - this needs your decision
   before implementation, the same way the premium-Bean gap did.
2. **Browsers unreliably report MIME types for `.r` and `.sas` files.**
   `File.type` in a browser is typically empty string or
   `application/octet-stream` for these extensions - there is no widely
   registered MIME type for SAS scripts, and R script MIME reporting is
   inconsistent across browsers/OSes. Validating by `Content-Type` header
   alone would reject legitimate `.r`/`.sas` uploads unpredictably.
   **Resolution: validate by file extension first (an explicit allowlist),
   cross-check `Content-Type` only for the types that have a reliable one
   (images, PDF), and never reject solely because a text-like file's
   browser-reported MIME type looks wrong.**
3. **`ledger/router_requests.csv` already has committed rows** (from the
   Brew 36/37 live demos) using the current 12-column header. Adding
   `attachment_count`/`attachment_tokens_est` columns (Requirement 5)
   without migrating breaks column alignment for future appends - a
   `csv.writer.writerow()` call with more values than the existing header
   describes silently misaligns every column from that row onward. This
   needs an explicit one-time migration with a backup copy (Section 8).

## 3. Router: `POST /v1/upload`

### 3.1 Endpoint shape

`POST /v1/upload`, `multipart/form-data`, one file per call (the UI loops
over multiple selected/dropped/pasted files - Section 9). FastAPI's
`UploadFile` (needs `python-multipart`, already installed).

Response (HTTP 200):
```json
{
  "upload_id": "b7e1...",
  "filename": "invoice.pdf",
  "content_type": "application/pdf",
  "kind": "pdf",
  "size_bytes": 154201,
  "extracted_text_chars": 4213
}
```

Response (HTTP 422, validation or extraction failure):
```json
{"detail": "PDF has no extractable text (likely a scanned image). Extracted 3 characters from 8 pages."}
```

### 3.2 Validation

| Check | Rule |
| --- | --- |
| Extension allowlist (primary authority) | `.png`, `.jpg`, `.jpeg`, `.webp`, `.pdf`, `.md`, `.txt`, `.csv`, `.py`, `.r`, `.sas`, `.json` |
| Content-Type cross-check (images and PDF only - Section 2, Gap 2) | Must start with `image/` for image extensions, or be `application/pdf` for `.pdf`. Text-like extensions are not cross-checked against `Content-Type`. |
| Size cap | `settings.max_upload_size_bytes` (new setting, default `20_971_520` = 20 MB), checked against the actual bytes read, not a client-reported `Content-Length` (which can lie) |

Rejected files never get written to disk - validation happens on the
in-memory upload stream before any file write.

### 3.3 Storage and Spill Guard (same diff, per your instruction)

`router/uploads/<upload_id>/<original_filename>` - `upload_id` is a fresh
`uuid4()` generated per uploaded file at upload time, **not** the eventual
`/v1/order` `request_id`. Interpreting your "request scoped id" as "an id
scoped to this one upload, not shared/guessable across uploads" rather
than literally reusing `request_id` - a `request_id` does not exist yet
while the user is still composing a message and attaching files before
sending. Flagged as Question 2 (Section 7) in case you meant something
more specific.

Files added to `.gitignore`, `.cursorignore`, and `.cursorindexingignore`
in the same commit that introduces `router/uploads/` (matching the
`router/data/` precedent from Brew 37, and the hard lesson recorded in
`brew-log/mistakes.md` about checking all three ignore files together):

```
router/uploads/
```

### 3.4 Metadata and extracted-text storage

Extracted PDF text and text-file contents are held in an **in-memory**
dict on `RouterState` (`state.uploads: Dict[str, UploadRecord]`), not a
new SQLite table. Rationale: uploads are compose-time, ephemeral state
tied to one browser session's draft message - if the router restarts
mid-compose, re-uploading is a reasonable expectation, and a new DB table
adds real complexity (schema, migration, cleanup) for a use case Brew 37's
`SessionStore` doesn't need to solve. The raw files still persist to disk
under `router/uploads/`, so nothing is lost, only the extracted-text index
resets on restart. If you'd rather this survive a restart, say so - it
would mean either a small SQLite table or a JSON sidecar file per upload.

`UploadRecord`: `upload_id`, `filename`, `content_type`, `kind`
(`"image" | "pdf" | "text"`), `size_bytes`, `file_path`, and
`extracted_text: str | None` (populated for `pdf` and `text` kinds at
upload time; `None` for images, which are sent as image data, not text).

## 4. PDF extraction

**Library choice: `pypdf`, already installed.** `pdfplumber` generally
extracts more accurate text from complex multi-column layouts, but it is
not installed, and this repo's established discipline (Brew 36/37) is to
use what is already present before adding a dependency. `pypdf`'s
extraction is adequate for typical single/simple-layout text PDFs, which
covers the stated use case; a future Brew can revisit if `pypdf`'s
extraction quality proves insufficient in practice.

```python
from pypdf import PdfReader
reader = PdfReader(BytesIO(file_bytes))
text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
```

**Scanned-PDF detection:** if `len(text.strip()) < settings.pdf_min_extracted_chars`
(new setting, default `20`), treat as "no extractable text" and reject at
upload time with HTTP 422 (Section 3.1) - fail fast while the user is
still composing, rather than after they send the message. As defense in
depth, `_run_order_body` also re-checks this if an upload record is
somehow referenced with empty extracted text (Section 6.4) and emits the
SSE `error` event in that path, since that is the only mechanism available
once a stream is already open.

## 5. Images: multimodal OpenRouter format

`router/app/openrouter_client.py:stream_order()`'s payload currently
hardcodes `"content": prompt` (a plain string). OpenRouter (and the
underlying OpenAI-compatible chat completions format most providers
implement) expects a content **array** when images are present:

```json
{
  "role": "user",
  "content": [
    {"type": "text", "text": "What is shown in this diagram?"},
    {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KG..."}}
  ]
}
```

`stream_order()` gains an optional `image_data_urls: list[str] | None`
parameter (base64 `data:` URLs, built by the caller from
`UploadRecord.file_path` bytes at send time - not stored pre-encoded, to
avoid keeping a redundant ~33%-larger base64 copy on top of the raw
file). When present, content becomes the array form; when absent (today's
only path, and every non-image request), content stays the plain string -
**fully backward compatible, no change to any existing call site's
behavior.**

Extracted PDF/text-file content is **not** sent as a separate content
part - it is appended to the text part as clearly delimited plain text:

```
<user's prompt>

--- Attached file: invoice.pdf ---
<extracted text, truncated to settings.max_inline_text_chars if longer>
--- end of invoice.pdf ---
```

`settings.max_inline_text_chars` (new setting, default `50_000`) caps how
much attached text gets inlined into a single request, appending a
`...[truncated]` marker if cut. This protects against a huge CSV/PDF
blowing up the request context; matches the existing "cap something in
settings.yaml" pattern already used for `escalation_cost_cap_usd` etc.

## 6. Classifier and routing: vision constraint

### 6.1 Complexity rule (Requirement 4, made concrete)

Replacing the existing blanket `len(attachments) > 2` check with a
slightly richer, still data-driven table:

| Condition | Effect |
| --- | --- |
| Any attachment with `kind == "pdf"` | `cold_brew` |
| 2 or more attachments of any kind | `cold_brew` (unchanged from today) |
| Exactly 1 image or 1 text-like attachment, nothing else | No forced change - falls through to existing text-length/keyword rules |

Reasoning: a single image with a short question ("what's wrong with this
screenshot?") is not inherently a `cold_brew`-complexity task, but a PDF
implies enough extracted content that treating it as `cold_brew` by
default is safer than assuming otherwise. This is a judgment call -
Question 3 in Section 7 if you'd rather any attachment force `cold_brew`.

### 6.2 Vision-capable Bean selection

`BeanRegistry` gains `vision_capable_beans() -> List[Bean]` (available
Beans with `capabilities.vision: true`) and
`default_vision_bean() -> Optional[Bean]` (first available vision-capable
Bean, preferring one with `role: default` if multiple exist).

`RoutingPolicy.select_route()` and `.manual_route()` both gain a
`needs_vision: bool = False` parameter. When `True`:
- If the policy/manually-selected Bean already has `vision: true`, no
  change - proceeds normally.
- If it does not, and a vision-capable Bean exists, switch to
  `default_vision_bean()` and record why (Section 6.3).
- If it does not, and **no** vision-capable Bean exists anywhere (today's
  actual state - Section 2, Gap 1), `_run_order_body` emits an `error`
  event (`error_type: "no_vision_bean_available"`) instead of silently
  sending the request without the image or crashing.

### 6.3 Emitting the constraint reason - event contract v1.2

`route_selected` gains an additive optional field,
`constraint_reason: str | null` (`null` when routing was not constrained
by anything - the normal case today). When vision routing forces a Bean
switch: `constraint_reason: "needs_vision: escalated from House Blend to <vision Bean alias>"`.
This bumps `router/EVENT_CONTRACT.md` to **v1.2**, the same additive-field
mechanism v1.1 already established for `text_delta` - no field renamed or
removed. This is Question 4 in Section 7: confirming a new field is
preferred over overloading `policy_entry`'s existing free-form string
(which the manual-override path already uses for a similar purpose).

### 6.4 Files touched for this section

`router/app/aliases.py` (new methods), `router/app/routing.py`
(`needs_vision` parameter, constraint logic), `router/app/events.py`
(`constraint_reason` field), `router/app/main.py` (`_run_order_body` wires
`classification.needs_vision` into route selection and handles the
no-vision-Bean error path), `router/app/classifier.py` (complexity rule
table update), `router/EVENT_CONTRACT.md` (v1.2 changelog entry).

## 7. Decisions (resolved 2026-07-11, superseding the draft questions below)

1. **No vision-capable Bean exists today.** Ship inert, matching the
   premium-Bean precedent exactly: structurally correct routing logic,
   clear `no_vision_bean_available` error, no guessed model.
2. **Upload scoping id: use the real `request_id`, not a separate
   `upload_id`.** This changes Section 3.3: `request_id` (UUID4) is now
   generated **client-side** the first time a file is attached in a
   compose session (before the message is sent - `/v1/order` does not
   exist yet at that point). The same `request_id` is threaded through
   `/v1/upload` (directory scope) and then explicitly passed to
   `/v1/order` (`OrderRequest.request_id: Optional[str]`, new field) so
   the order actually runs under the id its attachments were stored
   under. Text-only messages with no attachments are unaffected - no
   client-generated id, server generates one as before (Principle 9:
   don't force new machinery onto the common case that does not need
   it). Storage becomes `router/uploads/<request_id>/<attachment_id>-<original_filename>`
   - `request_id` scopes the directory (shared across every file attached
     to one draft), `attachment_id` (still a fresh UUID4 per file) keeps
     individual files addressable and collision-free within that
     directory. `OrderRequest.attachment_ids` still lists individual
     `attachment_id`s, resolved against `state.uploads` at order time.
   - **Cleanup**: `router/uploads/<request_id>/` is deleted recursively
     in `run_order()`'s existing `finally` block (alongside the current
     `cancel_flags.pop()`), so it is removed the moment the request
     completes, errors, or is cancelled - success and failure paths
     alike.
   - **TTL for abandoned uploads** (attached, never sent): a
     `sweep_stale_uploads()` call at the top of the `/v1/upload` handler
     removes any `router/uploads/<dir>/` older than
     `settings.upload_ttl_seconds` (new setting, default `3600`). No
     background scheduler/new dependency - a cheap sweep-on-access,
     matching this repo's "no new infrastructure" discipline.
3. **Complexity rule: any attachment pushes toward `cold_brew`,
   unconditionally.** Simpler than Section 6.1's original PDF-or-2+
   proposal - replaces that table with a single rule:
   `if attachments: return "cold_brew"`. Refine later with real usage
   data if this proves too blunt.
4. **`constraint_reason` added as a new v1.2 event field** (Section
   6.3), not folded into `policy_entry`. Approved as drafted.
5. **Upload metadata stays in-memory only, never SQLite.** Approved as
   drafted (Section 3.4) - reinforced by the request_id-scoped cleanup
   in Decision 2: uploads are now explicitly per-request and ephemeral,
   not just "simpler to implement in-memory." If the router restarts
   mid-request, the in-flight request itself is already lost, so
   surviving restarts would not help.
6. **Settings defaults accepted as proposed**: `max_upload_size_bytes`
   20 MB, `pdf_min_extracted_chars` 20, `max_inline_text_chars` 50,000,
   plus new `upload_ttl_seconds` 3600 (Decision 2). All tunable later
   without a schema change.

### Superseded text

Section 3.3's "fresh `uuid4()` per upload, not the eventual `request_id`"
and Section 6.1's PDF-or-2+-attachments complexity table are superseded
by Decisions 2 and 3 above respectively - left in place above for the
historical record of what was originally proposed and why, per this
repo's convention of not silently rewriting reviewed design docs.

## 8. Ledger migration

`router/app/ledger.py:CSV_HEADER` gains `attachment_count` (int) and
`attachment_tokens_est` (int or `"unknown"` - Coffee Ledger discipline
never invents a number it cannot support; a rough estimate is
`len(extracted_text) // 4` per text/PDF attachment, `"unknown"` for
images since token cost for image inputs is provider/size-dependent and
not reliably computable client-side).

`RouterLedger.__init__` (or a new `_migrate_if_needed()` called before
the first `append()`) checks whether the existing file's header line
matches the current `CSV_HEADER`. If it does not:
1. Copy the existing file to `ledger/router_requests.csv.bak-<UTC ISO
   timestamp with colons replaced by dashes>` (Windows filenames cannot
   contain `:`).
2. Re-read all existing rows via `csv.DictReader` (old header).
3. Re-write the file with the new header via `csv.DictWriter`, letting
   `restval=""` (the default) fill `attachment_count`/`attachment_tokens_est`
   as empty for pre-migration rows - rendered as `unknown` when the UI or
   a future summarizer reads them, not `0` (a real, if small, distinction:
   empty/unknown is honest, `0` would claim to know those historical rows
   had no attachments, which is true here but the mechanism should not
   assume that in general for a future column addition).
4. Log the migration (print to stdout - the router has no other logging
   sink today) so it is visible in the terminal running `uvicorn`.

This is a one-time, automatic, backed-up migration - no manual step
required, matching the "migrate the file with a backup copy and document
it" instruction.

## 9. Frontend: Order Box attachments

### 9.1 New state and components

`web/src/lib/attachments.ts`: `validateFileClientSide(file)` (extension
allowlist check, size check - client-side pre-check for instant feedback,
the server-side check in Section 3.2 remains authoritative and is never
bypassed), `formatFileSize(bytes)` (human-readable, e.g. `"142 KB"`),
and an `uploadFile(file)` wrapper in `web/src/lib/api.ts` posting to
`/v1/upload`.

`web/src/components/OrderBox/AttachmentChip.tsx`: filename, formatted
size, a remove (`x`) button, and - for images - a thumbnail
(`URL.createObjectURL(file)` for the local preview, revoked on unmount/
removal to avoid leaking blob URLs). Chip states: `pending` (uploading),
`ready` (uploaded, has `upload_id`), `error` (validation or extraction
failure, shows the server's error message, still removable).

`OrderBox` gains:
- A paperclip button opening a native `<input type="file" multiple
  accept="...">` (accept list mirrors Section 3.2's extension allowlist).
- `onDragOver`/`onDrop` handlers on the Order Box container (files from
  `event.dataTransfer.files`).
- An `onPaste` handler checking `event.clipboardData.items` for
  `image/*` types (the standard "paste a screenshot" path).
- A chip row above the textarea rendering the current attachment list
  from a new `attachments: AttachmentChipState[]` piece of local
  component state (not global zustand state - attachments are
  compose-time-only until the message is actually sent, at which point
  their `upload_id`s are passed into `sendPrompt`, matching how `prompt`
  itself is local state until send).

### 9.2 Store and API wiring

`chatStore.ts:sendPrompt` gains an `uploadIds?: string[]` parameter,
threaded into `api.orderStream`'s body as `attachment_ids: string[]`.
`OrderRequest` (router side) gains `attachment_ids: List[str] = []`;
`_run_order_body` resolves each id against `state.uploads`, builds
`ClassifierAttachment` objects for `classify()`, and builds the
image/text content per Sections 4-5.

`ChatMessage` (`web/src/lib/chat.ts`) gains
`attachments: AttachmentSummary[]` (filename, size, kind, and - for
images - enough to re-render a thumbnail: either the original blob URL
if still in-memory from the same session, or a note that inline image
display for a reloaded-from-history session is out of scope for this
Brew - see Section 11).

## 10. Message rendering

`MessageBubble`/a new `AttachmentGallery` sub-component renders the
sending user message's attachment chips (read-only variant - no remove
button) above the message text. Images render inline via an `<img>` tag
at a constrained max size (`max-h-64`, matching the existing design
tokens' spacing scale), with `onClick` opening a simple controlled overlay
(`fixed inset-0` div, click-to-close) showing the image at a larger size -
no new library, matching the existing `CommandPalette` overlay pattern
already in the codebase.

## 11. Non-goals for this Brew

- No inline image re-rendering for attachments on a session reloaded from
  `GET /v1/sessions/{id}/messages` after a page refresh - the stored
  session message currently has no attachment persistence at all
  (Section 9.2's `AttachmentSummary` is in-memory for the live session
  only). Persisting attachment references into `SessionStore` for
  history replay is real future work, not silently done here.
- No image resizing/re-encoding before sending to OpenRouter (Pillow is
  available and could do this, but the 20 MB cap plus typical image sizes
  makes it unnecessary for this Brew; flagged as a future optimization if
  large images prove slow/expensive).
- No video, audio, or other file types beyond the ones listed in your
  request.
- No OCR fallback for scanned PDFs - they are rejected with a clear error
  (Requirement 2), not processed further.
- No change to `roastery/openrouter_client.py` (the synchronous Roastery
  client) - multimodal support is added only to the async router client.

## 12. Files touched (CREATE/MODIFY)

```
router/app/uploads.py             CREATE - validation, storage, PDF/text extraction, UploadRecord
router/app/main.py                MODIFY - POST /v1/upload, OrderRequest.attachment_ids,
                                            _run_order_body wiring, RouterState.uploads
router/app/classifier.py          MODIFY - complexity rule table (Section 6.1)
router/app/routing.py             MODIFY - needs_vision parameter, constraint logic
router/app/aliases.py             MODIFY - vision_capable_beans(), default_vision_bean()
router/app/events.py              MODIFY - RouteSelectedEvent.constraint_reason
router/app/openrouter_client.py   MODIFY - image_data_urls parameter, multimodal content array
router/app/ledger.py              MODIFY - new columns, migration logic
router/config/settings.yaml       MODIFY - max_upload_size_bytes, pdf_min_extracted_chars,
                                            max_inline_text_chars
router/EVENT_CONTRACT.md          MODIFY - v1.2 changelog + constraint_reason field
.gitignore / .cursorignore /
  .cursorindexingignore           MODIFY - router/uploads/ (same diff as uploads.py, per your instruction)
router/tests/test_uploads.py      CREATE - validation, PDF extraction happy/scanned-failure paths
router/tests/test_routing.py      MODIFY - vision constraint tests
router/tests/test_classifier.py   MODIFY - complexity rule tests
router/tests/test_ledger.py       MODIFY - migration tests
router/tests/test_main.py         MODIFY - end-to-end attachment flow tests (mocked)

web/src/lib/attachments.ts        CREATE - validateFileClientSide, formatFileSize
web/src/lib/api.ts                MODIFY - uploadFile()
web/src/lib/chat.ts               MODIFY - ChatMessage.attachments
web/src/lib/events.ts             MODIFY - constraint_reason type
web/src/store/chatStore.ts        MODIFY - sendPrompt(uploadIds)
web/src/components/OrderBox/
  AttachmentChip.tsx              CREATE
  index.tsx                       MODIFY - paperclip, drag-drop, paste, chip row
web/src/components/ResponseSection/
  AttachmentGallery.tsx           CREATE - read-only chip/image rendering for sent messages
  MessageBubble.tsx                MODIFY - render AttachmentGallery
web/src/components/OrderBox/AttachmentChip.test.tsx  CREATE - add/remove test
```

## 13. Tests (as requested)

- **Upload validation**: allowed/rejected extensions (including the
  `.r`/`.sas` MIME-unreliability case from Section 2), size cap
  enforcement, storage path shape.
- **PDF extraction**: a real small text-bearing PDF fixture (happy path,
  asserts extracted text and that it is inlined correctly), and a
  synthetic near-blank-page PDF fixture (scanned-failure path, asserts
  the HTTP 422 and its message).
- **Vision routing constraint**: policy Bean lacks vision + a vision Bean
  exists -> escalates and sets `constraint_reason`; policy Bean lacks
  vision + no vision Bean exists anywhere -> `error` event, not a crash
  or silent drop; policy Bean already has vision -> no change,
  `constraint_reason` stays `null`.
- **UI chip add/remove**: `AttachmentChip.test.tsx` - add via simulated
  file selection, remove via the chip's `x` button, verify the local
  attachment list updates. Real OS-level drag-and-drop is not simulated
  in jsdom (notoriously unreliable to test) - the drop handler itself
  reads `event.dataTransfer.files`, the same `FileList` shape as
  `<input type="file">`, so the same underlying add-attachment code path
  is exercised either way; only the DOM event trigger differs.

## 14. Workflow from here

1. You review this plan and answer Section 7's six questions.
2. On approval: router additions first, full router test suite green,
   before any frontend code.
3. Frontend implementation in small diffs, not committed automatically.
4. Vitest chip test, then a live demo: real router running, one real PDF
   question and one real image question through the actual UI.
5. `brew-log/active_context.md` and `brew-log/progress.md` updated;
   `roastery/tasting_notes.md` gets a Tasting Note for the live demo.
6. Summary: files changed, tests added/passing, risks, rollback path.
