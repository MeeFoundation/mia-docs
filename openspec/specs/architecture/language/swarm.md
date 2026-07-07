# Swarm

## Overview

A swarm is the set of peers currently participating in the synchronization of one replica — the devices (and, later, other authorized parties) that hold the replica and are reachable to each other. Every replica has its own swarm: the gossip topic is the replica's namespace id, so a device is a member of as many swarms as it holds replicas, and the swarms of different replicas are independent even when the same devices sit in all of them.

Joining is implicit: creating or importing a replica joins its swarm. Membership is maintained by iroh-gossip (a partial-view membership protocol, HyParView-based), and the swarm serves both replication paths: meeting a new swarm neighbor triggers a set-reconciliation session (catch-up), and fresh writes are broadcast to swarm neighbors over gossip (live updates).

The term is inherited from the iroh vocabulary and the wider peer-to-peer tradition (BitTorrent, libp2p). In these specs it always means one replica's swarm, never the network as a whole.
