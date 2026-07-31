# data-layer: subset reconciliation

The tracked-contact surface changes shape with the runtime's contact derivation: the runtime sets the whole list per sweep instead of appending to it, because a list that only ever grows can never let a withdrawn device leave. The serving and refusal requirements are untouched.

## MODIFIED Requirements

### Requirement: A granted replica reconciles with siblings as well as the issuer

A granted replica's tracked contacts SHALL admit devices of the audience identities and of the issuer alike — supplied at import from the ticket, and thereafter set wholesale by the owning runtime as it re-derives the list from the device records. Setting SHALL replace the previous list, so a device absent from the new derivation stops being dialed by the periodic reconcile pass and the before-access nudge; both SHALL dial the tracked list as it stands at each pass. The engine's own record of peers that once served the replica is separate, unions into each dial, and ages out on its own.

#### Scenario: The reconcile pass dials a sibling contact

- **WHEN** a granted replica is tracked with a sibling device among its contacts and the issuer is unreachable
- **THEN** the next reconcile pass reaches the sibling and the replica converges without the issuer

#### Scenario: A replaced list drops the absent contact

- **WHEN** the tracked list is set anew without a device that was in it
- **THEN** the following passes and nudges dial the new list, and the dropped device is not in it
