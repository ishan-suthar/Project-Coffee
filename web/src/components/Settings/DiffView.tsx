/** Renders a unified diff string as colored +/- lines (stdlib
 * difflib.unified_diff output from the router - approved Question 2 of
 * docs/design/memory-and-pantry-design.md: no new dependency, no
 * side-by-side view). Shared by MemoryProposalPanel (Brew 41) and
 * SettingsPanel's policy-rebuild diff (Brew 42) - extracted here rather
 * than duplicated (docs/design/learning-loop-and-release-design.md
 * Section 3.2). */
interface DiffViewProps {
  diff: string;
  emptyMessage?: string;
}

export function DiffView({ diff, emptyMessage = "No changes proposed." }: DiffViewProps) {
  if (!diff.trim()) {
    return <p className="text-xs italic text-medium-roast">{emptyMessage}</p>;
  }
  return (
    <pre className="overflow-x-auto rounded bg-espresso/5 p-2 font-mono text-xs" data-testid="diff-view">
      {diff.split("\n").map((line, index) => {
        let className = "text-espresso";
        if (line.startsWith("+++") || line.startsWith("---")) {
          className = "text-medium-roast";
        } else if (line.startsWith("+")) {
          className = "text-green-700";
        } else if (line.startsWith("-")) {
          className = "text-red-700";
        } else if (line.startsWith("@@")) {
          className = "text-medium-roast";
        }
        return (
          <div key={index} className={className}>
            {line || " "}
          </div>
        );
      })}
    </pre>
  );
}
