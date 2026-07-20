# Swarm

## Overview

A swarm is the set of peers currently participating in the synchronization of one replica — the devices that hold the replica and are reachable to each other. Every replica has its own swarm: the gossip topic is the replica's namespace id, so a device is a member of as many swarms as it holds replicas, and the swarms of different replicas are independent even when the same devices sit in all of them.

Joining follows the replica's role: creating a replica joins its swarm, and so does importing it as a device of its identity (for a connection metadata store, the counterparty's devices join too). A grant import — scoped or whole-store — deliberately stays outside (subset-rbsr D5): reconciliation is a grantee's only data path. Membership is maintained by iroh-gossip (a partial-view membership protocol, HyParView-based), and the swarm serves both replication paths: meeting a new swarm neighbor triggers a set-reconciliation session (catch-up), and a fresh write announces a content-free author-head digest to swarm neighbors, each of whom pulls the entry over a reconciliation and re-announces to its own neighbors (live updates — the topic carries the announcement, never the entry, subset-rbsr's content-free swarm).

The term is inherited from the iroh vocabulary and the wider peer-to-peer tradition (BitTorrent, libp2p). In these specs it always means one replica's swarm, never the network as a whole.
