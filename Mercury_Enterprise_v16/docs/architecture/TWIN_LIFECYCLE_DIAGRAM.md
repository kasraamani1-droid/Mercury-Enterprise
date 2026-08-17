# Twin — Lifecycle Diagram

```
Manufactured
    → Delivered
        → Installed
            → Operated
                → Removed ⇄ Inspected ⇄ Repaired ⇄ Modified
                → Transferred
                → Stored → Returned
                → Scrapped
                → Retired
                → Archived
```

Rules:

1. Transitions append an immutable `lifecycle` history entry
2. `retired` / `archived` / `scrapped` set `archived_at` but **do not delete** the twin or passport
3. Ownership changes are history entries — passport identity remains
