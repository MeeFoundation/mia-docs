# Pod-tool

> **Created by Claude, awaiting proofread.** Not reviewed by a human - do not submit or circulate as approved.

## Overview

A pod-tool is an application unit that keeps one kind of a [pod](pod.md)'s content. Each pod-tool writes its content as records into the pod's record store, under keys of its own, and reflects its internal state, as far as it chooses, as graph representations that conform to the ontology, through the graph query engine's interface.

A pod-tool's kind names it, and names its zone in every pod: the part of the graph built from its records. Readers reach a pod-tool's data through its zone and the types it declares for it, never through its records or its internal state.
