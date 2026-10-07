# Connection

## Overview

A connection is a relationship between two [Mee Identities](mee-identity.md) that have met and agreed to share with each other. It is owned by neither side; it exists as mutual state.

Being connected grants no access to data by itself. What a counterparty may read is granted per [claim](claim.md) through [capabilities](capability.md).

A connection is one way to share: it carries what one identity grants the other from its own data. A space that several identities write into is a [pod](pod.md), which needs no connection between its members and creates none.

Connections are produced by the connection establishment procedure. A [Relying Party](relying-party.md) is the identity on the other side of a connection, seen from the [User](user.md)'s side.
