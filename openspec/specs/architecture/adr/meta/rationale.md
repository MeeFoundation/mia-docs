# What are ADRs?

See the Fowler's article: https://martinfowler.com/bliki/ArchitectureDecisionRecord.html

# Explore further
- https://github.com/adr

# Statuses

`proposed`, `rejected`, `accepted`, `deprecated` and `superseded by ADR-NNNN` keep their usual meaning. One more is ours: **`obsolete`** — the decision describes nothing any more, because the question it answered has gone away rather than been answered differently.

An obsolete ADR is erased down to a stub: frontmatter with the status and the date it was made obsolete, plus the title line. Nothing else stays in the file.

```markdown
---
status: obsolete
date: {YYYY-MM-DD when the decision was made obsolete}
---
# {title it carried}
```

The erased text is in git history — `git log --follow -p -- <path>` prints it — so a reader who needs the old reasoning gets it, and the tree stops carrying a record that reads as current.

The stub stays a stub. Never refill it from history, never reuse its number for a new decision, and never read its emptiness as an ADR waiting to be written.

Making an ADR obsolete is finished by a sweep: grep the spec tree for its number, because specs cite ADRs by number and a citation left behind points a reader at a stub. Every hit either loses the citation or gains the decision that replaced it.

An ADR that was replaced is not obsolete: it is `superseded by ADR-NNNN` and keeps every word, because the reader has to see what changed.

