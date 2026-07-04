# Recipes

Reusable workflows live here.

Recipes reduce token usage by replacing repeated task instructions with short
references to a shared local procedure. Future prompts can say "follow this
recipe" instead of restating the full workflow every time.

## Start Here

- Use `recipes/templates/recipe-template.md` when creating a new recipe.
- Keep each recipe scoped to one repeatable task shape.
- Link to existing project rules instead of copying them.
- Do not store secrets, credentials, API keys, or private data in recipes.

## Current Recipes

| Recipe | Use |
| --- | --- |
| `recipes/coding/small-feature-with-tests.md` | Small scoped implementation with tests and closeout. |
