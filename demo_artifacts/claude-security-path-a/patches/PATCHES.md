# Suggested patches

Targeted patches for findings in `CLAUDE-SECURITY-20260904-161400`, each written against revision `78fea27f6900` and verified by a panel of agents before it was written. Nothing here is applied, committed, or opened as a pull request until you choose to do so.

## Patches written

- **F2** -- Multipart filename sanitized before HTML-unescape, allowing path separators to be reintroduced: `F2.patch`

## Applying a patch

From the repository root:

```
git apply CLAUDE-SECURITY-20260904-161400/patches/F<n>.patch
```

Each `F<n>.md` beside the patch explains the change and what was verified. The job that wrote these applied, committed, pushed, and opened nothing; if you want one applied, or turned into a pull request, ask Claude Security and it handles that as a separate request.
