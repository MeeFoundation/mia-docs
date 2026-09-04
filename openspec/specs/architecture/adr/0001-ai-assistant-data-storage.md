---
status: accepted
date: 2026-05-12
---

# AI Assistant Data Storage

## Context and Problem Statement

The AI Assistant platform requires a reliable and scalable approach for storing user data as defined in the mia-ontology.

## Decision Drivers

- Scalability to support growing user data volume
- Low-latency access for real-time AI assistant interactions and retrieval operations
- Security, privacy, and compliance requirements for sensitive user data
- Support for future AI capabilities such as RAG, memory persistence, and semantic search
- Embeddable
- Rust-compatible

## Considered Options

- [LadybugDB](https://ladybugdb.com/)
- [Grafeo](https://grafeo.dev/)
- [fluree](https://flur.ee/)
- [IndraDB](https://github.com/indradb/indradb)
- [Oxigraph](https://github.com/oxigraph/oxigraph)
- [SurrealDB](https://surrealdb.com/)
- [SparrowDB](https://github.com/ryaker/SparrowDB)
- [petgraph](https://docs.rs/petgraph/latest/petgraph/)
- [FalkorDB](https://www.falkordb.com/)

## Decision Outcome

Chosen option: [LadybugDB](https://ladybugdb.com/), based on the benchmark results below (bulk insert, nested query, and Android emulator/device tests), which showed the best combination of ingest/query performance and memory footprint among the evaluated options, including on constrained mobile hardware.

### Consequences

- Good, because LadybugDB had the fastest bulk insert time (10,750 ms) and lowest nested query cold-start memory (276,780 KB) among all benchmarked options at the 100,000-claim dataset size, and was the only engine to complete the 500,000/1,000,000-record Android device tests without OOM or multi-minute ingest times.
- Bad, because LadybugDB is not implemented in Rust, so the platform takes on an FFI boundary rather than a native Rust dependency.
- Bad, because LadybugDB is a newer, more specialized project with a smaller ecosystem and fewer production references than more established graph or multi-model databases, so the team is taking on more first-mover risk.
- Neutral, because LadybugDB enforces a strict structured property graph model with mandatory schemas (`CREATE NODE TABLE` / `CREATE REL TABLE`) and Cypher queries, requiring upfront ontology and schema design discipline rather than schema-on-read flexibility. We circumvent this with extended-EAV data model.

## Pros and Cons of the Options

### [LadybugDB](https://ladybugdb.com/)

- Is in Rust?: No
- Embeddable?: Yes
- License: MIT

LPG. `CREATE NODE TABLE` / `CREATE REL TABLE` with typed columns — strong typing enforced at write time, primary key constraints.

- Good, because LadybugDB is specifically designed for AI memory workloads, combining graph traversal, vector search, typed schemas, and semantic querying in a single embedded database engine.
- Neutral, because LadybugDB uses a strict structured property graph model with mandatory schemas and Cypher queries, which improves consistency and type safety but requires upfront ontology and schema design discipline.
- Bad, because LadybugDB is a relatively new and specialized technology with a smaller ecosystem, fewer production references, and potentially limited community support compared to more mature graph or multi-model databases.

### [Grafeo](https://grafeo.dev/)

- Is in Rust?: Yes
- Embeddable?: Yes
- License: Apache2

LPG (GQL). Data validation: none — schema-free, no DDL.

- Good, because Grafeo supports both Labeled Property Graph (LPG) and RDF data models together with multiple query languages including GQL, Cypher, Gremlin, GraphQL, SPARQL, and SQL/PGQ. This provides strong flexibility for evolving AI memory and knowledge graph architectures.
- Good, because Grafeo is designed as a high-performance embedded Rust database with vector search, ACID transactions, MVCC isolation, and multi-language bindings, making it suitable for edge AI, semantic retrieval, and local-first AI assistants.
- Neutral, because Grafeo aims to unify RDF and LPG ecosystems, which increases interoperability and modeling flexibility but can also introduce additional architectural complexity and multiple querying paradigms for developers to manage.
- Bad, because Grafeo is still an early-stage project.

### [fluree](https://labs.flur.ee/)

- Is in Rust?: Yes
- Embeddable?: Yes
- License: BUSL

RDF triplestore. Fluree is an RDF/JSON-LD database: data is always inserted as JSON-LD values, and the fluree-db-api crate provides no derive macro.

SHACL is Fluree's own schema validation mechanism — it's the W3C standard for constraining RDF graphs, and it's what Fluree natively understands. SHACL (`sh:NodeShape`) validates class membership, cardinality, datatypes, node kinds.

- Good, because Fluree combines graph semantics, linked data, and blockchain-inspired immutability, providing strong auditability and trusted historical state management for AI memory and knowledge systems.
- Neutral, because Fluree's immutable ledger-style architecture improves traceability and temporal reasoning but introduces a more opinionated data model and operational paradigm than traditional property graph databases.
- Bad, because Fluree's RDF-first and semantic-web-oriented approach can increase modeling complexity, query learning curve (SPARQL/linked data concepts), and development overhead for teams primarily focused on application-centric AI memory workloads rather than semantic interoperability.

### [IndraDB](https://github.com/indradb/indradb)

- Is in Rust?: Yes
- Embeddable?: Yes

Out of consideration due to low maintainability.

- Good, because IndraDB is implemented in Rust with a lightweight architecture focused on high-performance graph storage and traversal, making it attractive for embedded or resource-constrained AI systems.
- Good, because IndraDB exposes a relatively simple graph model and API surface, which can reduce operational overhead and simplify integration for applications that primarily require graph relationships and traversal capabilities.
- Neutral, because IndraDB focuses mainly on core graph database functionality and intentionally keeps the feature set smaller and simpler compared to larger graph platforms, which can be beneficial for maintainability but limits advanced querying and AI-oriented features.
- Bad, because IndraDB lacks many modern AI-memory-oriented capabilities such as integrated vector search, semantic retrieval, advanced ontology tooling, and mature query ecosystems that are increasingly important for RAG and long-term AI memory systems. Not as actively maintained.

### [Oxigraph](https://github.com/oxigraph/oxigraph)

- Is in Rust?: Yes
- Embeddable?: Yes
- License: Apache 2 / MIT

RDF triplestore. No native SHACL support — schema-free in practice (could layer external SHACL validation, but the engine doesn't enforce it).

- Good, because Oxigraph is a lightweight and high-performance RDF and SPARQL graph database implemented in Rust, making it well suited for embedded semantic knowledge graph applications and local AI systems.
- Bad, because Oxigraph currently lacks native AI-oriented capabilities such as integrated vector embeddings, semantic similarity indexing, and hybrid graph-vector retrieval workflows that modern RAG and long-term AI memory systems often require.

### [SurrealDB](https://surrealdb.com/)

- Is in Rust?: Yes
- Embeddable?: Yes
- License: BUSL

Multi-model (document + graph + relational). `DEFINE TABLE SCHEMAFULL` + `DEFINE FIELD ... TYPE ...` — enforced at write time, per-field type constraints + `ASSERT` expressions.

- Good, because SurrealDB provides a multi-model architecture combining document, graph, key-value, and relational capabilities in a single database engine, which can simplify AI platform architectures and reduce infrastructure fragmentation.
- Good, because SurrealDB includes native graph relations, real-time synchronization, flexible schema options, and integrated querying capabilities, making it well suited for conversational AI systems with evolving data models and real-time workloads.
- Neutral, because SurrealDB emphasizes schema flexibility and developer ergonomics, which accelerates prototyping and iteration but may require additional governance and validation practices for large-scale ontology-driven AI memory systems.
- Bad, because SurrealDB's graph functionality is less specialized than dedicated graph or semantic databases.

### [SparrowDB](https://github.com/ryaker/SparrowDB)

- Is in Rust?: Yes
- Embeddable?: Yes
- License: MIT

LPG (Cypher). Data validation: none — schema-free, no DDL.

- Good, because SparrowDB is designed as a lightweight embedded graph database implemented in Rust, making it suitable for local-first applications, edge deployments, and low-overhead AI memory experimentation.
- Good, because SparrowDB focuses on simplicity and direct graph traversal operations, which can provide predictable performance and easier integration for applications that primarily need relationship-centric storage.
- Neutral, because SparrowDB appears intentionally minimalistic and focused on core graph capabilities rather than providing a large ecosystem of advanced tooling, query languages, or semantic standards support.
- Bad, because SparrowDB is an early-stage project with limited maturity, documentation, ecosystem adoption, and missing advanced AI-oriented features such as vector search, semantic retrieval, ontology enforcement, and production-grade operational tooling.

### [petgraph](https://docs.rs/petgraph/latest/petgraph/)

- Is in Rust?: Yes
- Embeddable?: Yes
- License: Apache 2 / MIT

* Good, because petgraph is a lightweight and highly flexible Rust graph library that integrates directly into application code without requiring a separate database process, making it suitable for embedded AI agents and in-memory graph workloads.
* Good, because petgraph provides efficient graph algorithms, traversal utilities, and customizable graph structures, allowing developers to build specialized memory and reasoning systems tailored to their AI architecture.
* Neutral, because petgraph is a graph data structure library rather than a full database system, which gives developers maximum implementation freedom but also shifts responsibility for persistence, indexing, querying, concurrency, and durability to the application layer.
* Bad, because petgraph lacks native database features such as persistent storage, ACID transactions, vector indexing, declarative query languages, replication, and semantic retrieval capabilities that are typically required for production-grade AI memory platforms.

### [FalkorDB](https://www.falkordb.com/)

- Is in Rust?: No
- Embeddable?: No?
- License: SSPL

* Good, because FalkorDB is purpose-built for graph workloads with efficient relationship traversal and Cypher query support, making it suitable for AI memory, knowledge graph, and agent reasoning systems.
* Good, because FalkorDB extends the Redis ecosystem and benefits from in-memory performance characteristics, enabling low-latency graph queries and real-time AI interaction patterns.
* Neutral, because FalkorDB is tightly coupled with Redis infrastructure and operational patterns, which simplifies adoption for Redis-based stacks but may constrain architectural flexibility for teams seeking fully standalone graph-native systems.
* Bad, because FalkorDB primarily focuses on graph traversal and querying rather than integrated AI-native features such as vector search, semantic retrieval orchestration, or ontology-centric memory modeling, which may require additional external components for advanced RAG systems.

## More Information

### [fluree](https://labs.flur.ee/)

Benchmark with SHACL:

```
ingest complete: graph_objects=157550, claims=100000, elapsed_ms=8906
```

The fluree-db-api crate doesn't provide Rust-level type safety through struct mapping either; data gets passed around as JSON-LD values using a builder pattern, with no derive macros for automatic schema binding. We could technically skip SHACL validation entirely and insert data without any constraints, but then we'd have no schema enforcement at the database level. There may also be a JSON-Schema option; not verified.

### [SurrealDB](https://surrealdb.com/)

Much longer compilation time compared to fluree.

Unlike Fluree, has questionable support for bulk JSON-LD data import. It can be technically implemented via `SCHEMALESS` tables, but from what I read, `SCHEMAFULL` tables are preferred. In the SurrealDB benchmark, we use `#[derive(SurrealValue)]` on Rust structs and `DEFINE TABLE SCHEMAFULL` DDL. The schema is enforced by SurrealDB's type system and the Rust structs map directly to SurrealDB records.

Benchmark with Rust structure mapping:

```
ingest complete: graph_objects=157550, claims=100000, elapsed_ms=14347
```

### [Grafeo](https://grafeo.dev/)

The benchmark does not terminate in a reasonable amount of time. After a rewrite into native Rust objects and 1 transaction for the whole bulk, the result is as follows:

```
ingest complete: graph_objects=157550, claims=100000, elapsed_ms=5169
```

Grafeo has Rust data shape validation only, no validation on the DB side.

### [LadybugDB](https://ladybugdb.com/)

LadyBug doesn't support SHACL (it's a property graph, not RDF), so its schema lives as Cypher DDL constants.

The benchmark does not terminate in a reasonable amount of time, therefore it was rewritten to make use of `COPY FROM`.

### [Oxigraph](https://github.com/oxigraph/oxigraph)

No SHACL support, raw JSON-LD ingestion:

```
ingest complete: graph_objects=157550, claims=100000, elapsed_ms=8779
```

### [SparrowDB](https://github.com/ryaker/SparrowDB)

The benchmark does not terminate in a reasonable amount of time.

| Database                                         | Bulk Insert Time | Peak Memory   | Nested Query Time | Nested Query RAM Cold Start |
| ------------------------------------------------ | ---------------- | ------------- | ----------------- | --------------------------- |
| [fluree](https://labs.flur.ee/)                  | Timeout          |               |                   |                             |
| [SurrealDB](https://surrealdb.com/)              | 155,594 ms       | 11,748,776 KB | 136 ms            | 185,300 KB                  |
| [Grafeo](https://grafeo.dev/)                    | 51,481 ms        | 3,891,744 KB  | 156 ms            | 3,588,864 KB                |
| [Oxigraph](https://github.com/oxigraph/oxigraph) | 126,152 ms       | 14,343,484 KB | 9 ms              | 9,232,032 KB                |
| [LadybugDB](https://ladybugdb.com/)              | 10,750 ms        | 3.2 GB        | 31 ms             | 276,780 KB                  |

---

## Tests on Android Emulator

The metrics are: (wall time: open + load, peak RAM RSS)

| Database                                         | Dataset 10,000                                      | Dataset 100,000                                         | Dataset 500,000                                          | Dataset 1,000,000                                      |
| ------------------------------------------------ | --------------------------------------------------- | ------------------------------------------------------- | -------------------------------------------------------- | ------------------------------------------------------ |
| [Grafeo](https://grafeo.dev/)                    | Ingest (520 ms, 236 MB); Query (243 ms, 226 MB)     | Ingest (4,080 ms, 727 MB); Query (1,858 ms, 544 MB)     | Ingest (24,661 ms, 2,755 MB); Query (9,115 ms, 2,234 MB) | Ingest (OOM on the 12 GB RAM device); Query ()         |
| [Oxigraph](https://github.com/oxigraph/oxigraph) | Ingest (1,564 ms, 288 MB); Query (1,569 ms, 199 MB) | Ingest (16,113 ms, 1,047 MB); Query (13,060 ms, 465 MB) | Ingest (OOM); Query ()                                   |                                                        |
| [LadybugDB](https://ladybugdb.com/)              | (INCOMPATIBLE WITH EMULATOR)                        |                                                         |                                                          |                                                        |
| [SurrealDB](https://surrealdb.com/)              | Ingest (2,046 ms, 269 MB); Query (601 ms, 271 MB)   | Ingest (19,602 ms, 388 MB); Query (2,472 ms, 305 MB)    | Ingest (102,579 ms, 1.6 GB); Query (1,505 ms, 264 MB)    | Ingest (212,166 ms, ~3.7 GB); Query (1,153 ms, 305 MB) |

---

## Tests on Android Device

- CPU: 8 cores (octa-core, aarch64), MediaTek MT6768 = Helio G85
- RAM: 8 GB
- Other: Android 15, kernel 6.6.82, 4 KB page size

The metrics are: (wall time: open + load, peak RAM RSS)

| Database                                         | Dataset 10,000                                    | Dataset 100,000                                      | Dataset 500,000                                            | Dataset 1,000,000                                          |
| ------------------------------------------------ | ------------------------------------------------- | ---------------------------------------------------- | ---------------------------------------------------------- | ---------------------------------------------------------- |
| [Grafeo](https://grafeo.dev/)                    | Ingest (1,244 ms, 244 MB); Query (584 ms, 235 MB) | Ingest (15,230 ms, 614 MB); Query (4,474 ms, 577 MB) | Ingest (190,000 ms, 2,534 MB); Query (25,000 ms, 2,416 MB) | Ingest (699,247 ms, 3,376 MB); Query (54,107 ms, 3,031 MB) |
| [Oxigraph](https://github.com/oxigraph/oxigraph) |                                                   |                                                      |                                                            |                                                            |
| [LadybugDB](https://ladybugdb.com/)              | Ingest (3,768 ms, 420 MB); Query (375 ms, 363 MB) | Ingest (10,591 ms, 732 MB); Query (385 ms, 356 MB)   | Ingest (36,817 ms, 1.74 GB); Query (547 ms, 344 MB)        | Ingest (65,892 ms, ~3.16 GB); Query (802 ms, 320 MB)       |
| [SurrealDB](https://surrealdb.com/)              | Ingest (7,417 ms, 301 MB); Query (970 ms, 299 MB) | Ingest (78,533 ms, 479 MB); Query (6,125 ms, 332 MB) | Ingest (428,794 ms, 1.7 GB); Query (3,112 ms, 294 MB)      | Ingest (987 s, ~3.26 GB); Query (2,478 ms, 291 MB)         |
