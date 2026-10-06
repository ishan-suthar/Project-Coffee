# 002 Tiny Python Fix

## Purpose

Test small Python debugging and the ability to provide the smallest corrected
implementation plus one focused test.

## Order

You are Espresso Fast Coder. Use only Python standard library. Do not edit
files. Return the corrected function and one `unittest` test case.

Buggy function:

```python
def normalize_tags(tags):
    """Return lowercase unique tags in first-seen order."""
    normalized = []
    for tag in tags:
        tag = tag.strip().lower()
        if tag not in tags:
            normalized.append(tag)
    return sorted(normalized)
```

Required behavior:

- Strip surrounding whitespace.
- Lowercase tags.
- Skip empty tags after stripping.
- Preserve first-seen order.
- Remove duplicates after normalization.

Example:

```python
normalize_tags([" AI ", "coffee", "ai", "", " Coffee "])
```

Expected result:

```python
["ai", "coffee"]
```

Output:

1. One sentence explaining the bug.
2. One fenced Python block with the corrected function.
3. One fenced Python block with a focused `unittest` test.

## Success Criteria

- Fixes the membership check.
- Does not sort the result.
- Skips empty normalized tags.
- Uses only standard library.
- Includes one meaningful test.

## Scoring Notes

High scores should be minimal and correct. Lower scores should go to answers
that sort the output, keep duplicates, miss empty strings, or provide broad
unrequested refactors.

