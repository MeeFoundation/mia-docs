# What are ADRs?

See the Fowler's article: https://martinfowler.com/bliki/ArchitectureDecisionRecord.html

# Explore further

- https://github.com/adr

# Statuses

`rejected`, `deprecated` and `superseded by ADR-NNNN` keep their usual meaning. Two are read more tightly here: **`accepted`** is a decision taken and due to be implemented shortly, and **`proposed`** is a decision nothing implements, whose realization is far enough off that the tree must not read it as settled. One more is ours: **`obsolete`** — nothing in the record is worth keeping, either because the question it answered has gone away, or because the decision was never written down and something else has since answered it.

An obsolete ADR is erased down to a stub: frontmatter with the status and the date it was made obsolete, plus the title line. Nothing else stays in the file.

```markdown
---
status: obsolete
date: { YYYY-MM-DD when the decision was made obsolete }
---

# {title it carried}
```

The erased text is in git history — `git log --follow -p -- <path>` prints it — so a reader who needs the old reasoning gets it, and the tree stops carrying a record that reads as current.

The stub carries no reason line and nothing pointing at what replaced the decision: whatever explains it is written where the replacement lives. The stub stays a stub. Never refill it from history, never reuse its number for a new decision, and never read its emptiness as an ADR waiting to be written.

Making an ADR obsolete is finished by a sweep: grep the spec tree for its number, because specs cite ADRs by number and a citation left behind points a reader at a stub. Every hit either loses the citation or gains the decision that replaced it.

An ADR that was replaced is not obsolete: it is `superseded by ADR-NNNN` and keeps every word, because the reader has to see what changed.
