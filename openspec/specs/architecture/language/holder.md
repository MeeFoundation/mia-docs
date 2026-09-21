# Holder

## Overview

The party a replica is held for, and the party a session's caller acts for, as pdn-store names it: 32 opaque bytes it compares and never interprets. Above pdn-store the platform fills a holder with the `PdnId` of a hosted identity, so the store stays free of the platform's identity vocabulary.

## Details

A sync session names two holders — the one whose replica is addressed and the one the caller acts for — and the serving node admits the caller's holder only when the records it holds of that identity list the caller's node id among its devices ([identity-scoped replicas](../../components/mee-pdn/data-layer/identity-scoped-replicas/spec.md)). The session's rights, its egress filter and its write admission follow those two alone, so a node hosting several identities receives, in each session, what the identity named there was granted and nothing of what a co-located one was granted. ADR-0013 states the level of isolation this carries.
