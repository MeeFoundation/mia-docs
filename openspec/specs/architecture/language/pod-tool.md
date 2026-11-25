# Pod-tool

> **Created by Claude, awaiting proofread.** Not reviewed by a human - do not submit or circulate as approved.

## Overview

A pod-tool is the part of the app that keeps one kind of a [pod](pod.md)'s content: chat keeps its messages, Info its claims, and notes, the calendar and attachments their own. Each pod-tool writes its content as records into the pod's record store, under keys of its own, and says what each of its records stands for in the graph its readers query.

A pod-tool's kind names it, and names its zone in every pod: the part of the graph built from its records. Readers reach a pod-tool's data through its zone and the types it declares for it, never through its records.
