"use client";

import { useEffect, useState } from "react";
import { useChatStore } from "@/store/chatStore";
import type { ProjectFilter } from "@/store/chatStore";

function filterLabel(filter: ProjectFilter): string {
  if (filter === "all") return "All chats";
  if (filter === "default") return "default";
  return filter.name;
}

/** Brew 43 (docs/design/auth-projects-chat-management-design.md Section
 * 4.2) - replaces the Sidebar header's plain "default" text with a real
 * project selector: "All chats", "default", then every real project,
 * plus inline create/rename/delete. The first settings-shaped dropdown
 * in this app besides SessionMenu, so it reuses that component's
 * absolute-dropdown/stopPropagation pattern. */
export function ProjectSelector() {
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [renameValue, setRenameValue] = useState("");

  const projectFilter = useChatStore((s) => s.projectFilter);
  const projects = useChatStore((s) => s.projects);
  const loadProjects = useChatStore((s) => s.loadProjects);
  const setProjectFilter = useChatStore((s) => s.setProjectFilter);
  const createProject = useChatStore((s) => s.createProject);
  const renameProject = useChatStore((s) => s.renameProject);
  const deleteProject = useChatStore((s) => s.deleteProject);

  useEffect(() => {
    loadProjects().catch(() => {
      // Same "never block the shell" discipline as Sidebar's session load.
    });
  }, [loadProjects]);

  function handleCreate() {
    const name = newProjectName.trim();
    if (name.length === 0) return;
    createProject(name);
    setNewProjectName("");
    setCreating(false);
  }

  function handleRename(projectId: number) {
    const name = renameValue.trim();
    if (name.length > 0) renameProject(projectId, name);
    setRenamingId(null);
  }

  return (
    <div className="relative" data-testid="project-selector">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        data-testid="project-selector-button"
        className="rounded px-2 py-1 text-sm font-medium text-espresso transition hover:bg-cream"
      >
        {filterLabel(projectFilter)} &#9662;
      </button>

      {open && (
        <div
          className="absolute left-0 top-full z-10 mt-1 w-56 rounded border border-caramel bg-cream shadow-md"
          data-testid="project-selector-dropdown"
        >
          <button
            type="button"
            onClick={() => {
              setProjectFilter("all");
              setOpen(false);
            }}
            className="block w-full px-3 py-2 text-left text-xs text-espresso transition hover:bg-latte"
          >
            All chats
          </button>
          <button
            type="button"
            onClick={() => {
              setProjectFilter("default");
              setOpen(false);
            }}
            className="block w-full px-3 py-2 text-left text-xs text-espresso transition hover:bg-latte"
          >
            default
          </button>

          {projects.map((project) => (
            <div key={project.id} className="flex items-center justify-between px-1">
              {renamingId === project.id ? (
                <input
                  autoFocus
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  onBlur={() => handleRename(project.id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleRename(project.id);
                    if (e.key === "Escape") setRenamingId(null);
                  }}
                  className="my-1 flex-1 rounded border border-caramel bg-cream px-2 py-1 text-xs text-espresso outline-none"
                />
              ) : (
                <button
                  type="button"
                  onClick={() => {
                    setProjectFilter(project);
                    setOpen(false);
                  }}
                  data-testid="project-selector-item"
                  className="flex-1 truncate px-2 py-2 text-left text-xs text-espresso transition hover:bg-latte"
                >
                  {project.name}
                </button>
              )}
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setRenamingId(project.id);
                  setRenameValue(project.name);
                }}
                aria-label={`Rename ${project.name}`}
                className="px-1 text-xs text-medium-roast hover:text-espresso"
              >
                &#9998;
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  deleteProject(project.id);
                }}
                aria-label={`Delete ${project.name}`}
                className="px-1 text-xs text-medium-roast hover:text-crema-amber"
              >
                &times;
              </button>
            </div>
          ))}

          <div className="border-t border-caramel p-2">
            {creating ? (
              <div className="flex gap-1">
                <input
                  autoFocus
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleCreate();
                    if (e.key === "Escape") setCreating(false);
                  }}
                  placeholder="Project name"
                  className="flex-1 rounded border border-caramel bg-cream px-2 py-1 text-xs text-espresso outline-none"
                />
                <button
                  type="button"
                  onClick={handleCreate}
                  className="rounded bg-crema-amber px-2 py-1 text-xs text-cream hover:opacity-90"
                >
                  Create
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setCreating(true)}
                data-testid="new-project-button"
                className="w-full rounded border border-caramel px-2 py-1 text-left text-xs text-espresso transition hover:bg-latte"
              >
                + New project
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
