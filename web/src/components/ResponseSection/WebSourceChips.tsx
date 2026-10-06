import type { WebSource } from "@/lib/events";

interface WebSourceChipsProps {
  sources: WebSource[] | null;
}

/** Citation chips for the web sources the router's `openrouter:web_search`
 * tool actually cited (web search citations Brew, contract v1.6
 * web_sources) - renders only from `sources`, which is only ever
 * non-null/non-empty when the router itself reported real citations, so
 * a chip can never claim a source the response didn't get (same rule
 * PantrySourceChips follows for Pantry sources). Unlike PantrySourceChips
 * (which opens an in-app FileViewerPanel for a local knowledge/ file),
 * each chip here is a real outbound link - the source lives on the open
 * web, not in this repo - and is styled with the crema-amber accent (the
 * same color used by the "Use Web" toggle) rather than Pantry chips'
 * caramel, so the two citation kinds stay visually distinct at a glance. */
export function WebSourceChips({ sources }: WebSourceChipsProps) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-2 flex flex-wrap gap-2" data-testid="web-source-chips">
      {sources.map((source) => (
        <a
          key={source.url}
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="rounded border border-crema-amber bg-latte px-2 py-1 text-xs text-crema-amber transition hover:bg-cream"
          data-testid="web-source-chip"
        >
          {source.title}
        </a>
      ))}
    </div>
  );
}
