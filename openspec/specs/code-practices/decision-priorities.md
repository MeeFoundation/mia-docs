# Decision priorities: what outweighs what when choosing between options

## Constraints

An option that breaks any of these is excluded, whatever the priorities below say for it.

- Data reaches only a party entitled to it.
- A confirmed defect is never lost: it is fixed, or recorded where the next reader finds it.
- A fix that contradicts a recorded decision comes with an explicit change to that decision.
- An option with worse than linear complexity says so, and in what.
- Tests are deterministic.

## High value priorities

Ordered from the highest to the lowest; each outweighs every low value priority.

1. Data eventually reaches every party entitled to it.
2. A node is as hard to stall or exhaust as it can be made.
3. The fact that data exists, or existed, reaches only a party entitled to it.
4. A failure is visible and ends within a bound.
5. A defect is closed at its cause rather than compensated after it happens.

## Low value priorities

Ordered from the highest to the lowest.

1. Tests cover the whole behaviour.
2. An invariant holds by construction rather than by discipline.
3. Nothing goes stale silently.
4. Least astonishment for whoever knows the rest of the system.
5. Wire format and compatibility with deployed builds stay as they are.
6. A change stays within its scope.
7. The edit is as small as the defect allows.
8. Our code stays close to the upstream it was taken from.
