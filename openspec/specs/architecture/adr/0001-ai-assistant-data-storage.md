# ---

status: {proposed | rejected | accepted | deprecated | … | superseded by ADR-0005 <0005-example.md>}
date: 2026-05-12
deciders: {list everyone involved in the decision}
consulted: {list everyone whose opinions are sought (typically subject-matter experts); and with whom there is a two-way communication}
informed: {list everyone who is kept up-to-date on progress; and with whom there is a one-way communication}

---

# AI Assistant Data Storage

## Context and Problem Statement

The AI Assistant platform requires a reliable and scalable approach for storing user data as defined in the mia-ontology. 


## Decision Drivers

* Scalability to support growing user data volume
* Low-latency access for real-time AI assistant interactions and retrieval operations
* Security, privacy, and compliance requirements for sensitive user data
* Support for future AI capabilities such as RAG, memory persistence, and semantic search
* Embeddable
* Rust-compatible

## Considered Options

* [LadybugDB](https://ladybugdb.com/)
* [Grafeo](https://grafeo.dev/)
* [fluree](https://flur.ee/)
* [IndraDB](https://github.com/indradb/indradb)
* [Oxigraph](https://github.com/oxigraph/oxigraph)
* [SurrealDB](https://surrealdb.com/)
* [SparrowDB](https://github.com/ryaker/SparrowDB)
* [petgraph](https://docs.rs/petgraph/latest/petgraph/)
* [FalkorDB](https://www.falkordb.com/)

## Decision Outcome

WIP - no decision made so far

### Consequences

* Good, because {positive consequence, e.g., improvement of one or more desired qualities, …}
* Bad, because {negative consequence, e.g., compromising one or more desired qualities, …}

## Pros and Cons of the Options

### [LadybugDB](https://ladybugdb.com/)

Is in Rust?: No
Embeddable?: Yes
License: MIT

LPG. `CREATE NODE TABLE` / `CREATE REL TABLE` with typed columns — strong typing enforced at write time, primary key constraints

* Good, because LadybugDB is specifically designed for AI memory workloads, combining graph traversal, vector search, typed schemas, and semantic querying in a single embedded database engine.  

* Neutral, because LadybugDB uses a strict structured property graph model with mandatory schemas and Cypher queries, which improves consistency and type safety but requires upfront ontology and schema design discipline. 

* Bad, because LadybugDB is a relatively new and specialized technology with a smaller ecosystem, fewer production references, and potentially limited community support compared to more mature graph or multi-model databases.


### [Grafeo](https://grafeo.dev/)

Is in Rust?: Yes
Embeddable?: Yes
License: Apache2

LPG (GQL). Data Validation - None — schema-free, no DDL.

* Good, because Grafeo supports both Labeled Property Graph (LPG) and RDF data models together with multiple query languages including GQL, Cypher, Gremlin, GraphQL, SPARQL, and SQL/PGQ. This provides strong flexibility for evolving AI memory and knowledge graph architectures. 

* Good, because Grafeo is designed as a high-performance embedded Rust database with vector search, ACID transactions, MVCC isolation, and multi-language bindings, making it suitable for edge AI, semantic retrieval, and local-first AI assistants. 

* Neutral, because Grafeo aims to unify RDF and LPG ecosystems, which increases interoperability and modeling flexibility but can also introduce additional architectural complexity and multiple querying paradigms for developers to manage. 

* Bad, because Grafeo is still an early-stage project.


### [fluree](https://labs.flur.ee/)

Is in Rust?: Yes
Embeddable?: Yes
License: BUSL

RDF triplestore. Fluree is an RDF/JSON-LD database. Data is always inserted as JSON-LD values, and the fluree-db-api crate provides no derive macro.
SHACL is Fluree's own schema validation mechanism — it's the W3C standard for constraining RDF graphs, and it's what Fluree natively understands. SHACL (sh:NodeShape) validates class membership, cardinality, datatypes, node kinds

* Good, because Fluree combines graph semantics, linked data, and blockchain-inspired immutability, providing strong auditability and trusted historical state management for AI memory and knowledge systems.

* Neutral, because Fluree’s immutable ledger-style architecture improves traceability and temporal reasoning but introduces a more opinionated data model and operational paradigm than traditional property graph databases.

* Bad, because Fluree’s RDF-first and semantic-web-oriented approach can increase modeling complexity, query learning curve (SPARQL/linked data concepts), and development overhead for teams primarily focused on application-centric AI memory workloads rather than semantic interoperability.

  
### [IndraDB](https://github.com/indradb/indradb)

Is in Rust?: Yes
Embeddable?: Yes

Out of consideration due to low maintainability

* Good, because IndraDB is implemented in Rust with a lightweight architecture focused on high-performance graph storage and traversal, making it attractive for embedded or resource-constrained AI systems.

* Good, because IndraDB exposes a relatively simple graph model and API surface, which can reduce operational overhead and simplify integration for applications that primarily require graph relationships and traversal capabilities.

* Neutral, because IndraDB focuses mainly on core graph database functionality and intentionally keeps the feature set smaller and simpler compared to larger graph platforms, which can be beneficial for maintainability but limits advanced querying and AI-oriented features.

* Bad, because IndraDB lacks many modern AI-memory-oriented capabilities such as integrated vector search, semantic retrieval, advanced ontology tooling, and mature query ecosystems that are increasingly important for RAG and long-term AI memory systems. Not as actively maintained.

  
### [Oxigraph](https://github.com/oxigraph/oxigraph)

Is in Rust?: Yes
Embeddable?: Yes
License: Apache 2 / MIT

RDF triplestore. No native SHACL support — schema-free in practice (could layer external SHACL validation, but the engine doesn't enforce it).

* Good, because Oxigraph is a lightweight and high-performance RDF and SPARQL graph database implemented in Rust, making it well suited for embedded semantic knowledge graph applications and local AI systems.

* Bad, because Oxigraph currently lacks native AI-oriented capabilities such as integrated vector embeddings, semantic similarity indexing, and hybrid graph-vector retrieval workflows that modern RAG and long-term AI memory systems often require.

  
### [SurrealDB](https://surrealdb.com/)

Is in Rust?: Yes
Embeddable?: Yes
License: BUSL

Multi-model (document + graph + relational). `DEFINE TABLE SCHEMAFULL` + `DEFINE FIELD ... TYPE ...` — enforced at write time, per-field type constraints + ASSERT expressions. 

* Good, because SurrealDB provides a multi-model architecture combining document, graph, key-value, and relational capabilities in a single database engine, which can simplify AI platform architectures and reduce infrastructure fragmentation.

* Good, because SurrealDB includes native graph relations, real-time synchronization, flexible schema options, and integrated querying capabilities, making it well suited for conversational AI systems with evolving data models and real-time workloads.

* Neutral, because SurrealDB emphasizes schema flexibility and developer ergonomics, which accelerates prototyping and iteration but may require additional governance and validation practices for large-scale ontology-driven AI memory systems.

* Bad, because SurrealDB’s graph functionality is less specialized than dedicated graph or semantic databases.

  
### [SparrowDB](https://github.com/ryaker/SparrowDB)

Is in Rust?: Yes
Embeddable?: Yes
License: MIT

LPG (Cypher). None — schema-free, no DDL.

* Good, because SparrowDB is designed as a lightweight embedded graph database implemented in Rust, making it suitable for local-first applications, edge deployments, and low-overhead AI memory experimentation.

* Good, because SparrowDB focuses on simplicity and direct graph traversal operations, which can provide predictable performance and easier integration for applications that primarily need relationship-centric storage.

* Neutral, because SparrowDB appears intentionally minimalistic and focused on core graph capabilities rather than providing a large ecosystem of advanced tooling, query languages, or semantic standards support.

* Bad, because SparrowDB is an early-stage project with limited maturity, documentation, ecosystem adoption, and missing advanced AI-oriented features such as vector search, semantic retrieval, ontology enforcement, and production-grade operational tooling.

  
### [petgraph](https://docs.rs/petgraph/latest/petgraph/)

Is in Rust?: Yes
Embeddable?: Yes
License: Apache 2 / MIT

{example | description | pointer to more information | …}

* Good, because petgraph is a lightweight and highly flexible Rust graph library that integrates directly into application code without requiring a separate database process, making it suitable for embedded AI agents and in-memory graph workloads.

* Good, because petgraph provides efficient graph algorithms, traversal utilities, and customizable graph structures, allowing developers to build specialized memory and reasoning systems tailored to their AI architecture.

* Neutral, because petgraph is a graph data structure library rather than a full database system, which gives developers maximum implementation freedom but also shifts responsibility for persistence, indexing, querying, concurrency, and durability to the application layer.

* Bad, because petgraph lacks native database features such as persistent storage, ACID transactions, vector indexing, declarative query languages, replication, and semantic retrieval capabilities that are typically required for production-grade AI memory platforms.


### [FalkorDB](https://www.falkordb.com/)

Is in Rust?: No
Embeddable?: No?
License: SSPL

{example | description | pointer to more information | …}

* Good, because FalkorDB is purpose-built for graph workloads with efficient relationship traversal and Cypher query support, making it suitable for AI memory, knowledge graph, and agent reasoning systems.
* Good, because FalkorDB extends the Redis ecosystem and benefits from in-memory performance characteristics, enabling low-latency graph queries and real-time AI interaction patterns.
* Neutral, because FalkorDB is tightly coupled with Redis infrastructure and operational patterns, which simplifies adoption for Redis-based stacks but may constrain architectural flexibility for teams seeking fully standalone graph-native systems.
* Bad, because FalkorDB primarily focuses on graph traversal and querying rather than integrated AI-native features such as vector search, semantic retrieval orchestration, or ontology-centric memory modeling, which may require additional external components for advanced RAG systems.


## More Information

### [fluree](https://labs.flur.ee/)

Benchmark with SHACL:
ingest complete: graph_objects=157550, claims=100000, elapsed_ms=8906

The fluree-db-api crate doesn't provide Rust-level type safety through struct mapping either; data gets passed around as JSON-LD values using a builder pattern, with no derive macros for automatic schema binding. We could technically skip SHACL validation entirely and insert data without any constraints, but then we'd have no schema enforcement at the database level. Still, there's JSON-SCHEMA option, right?


### [SurrealDB](https://surrealdb.com/)

Much longer compilation time compared to fluree.
Unlike Fluree, has questionable support for bulk jsonld data import. It can be technically implemented via SCHEMALESS tables, but from what I read, SCHEMAFULL tables are preferred. 
In the SurrealDB benchmark, we use #[derive(SurrealValue)] on Rust structs and DEFINE TABLE SCHEMAFULL DDL. The schema is enforced by SurrealDB's type system and the Rust structs map directly to SurrealDB records.
Metrics

Benchmark with Rust Structure Mapping:
ingest complete: graph_objects=157550, claims=100000, elapsed_ms=14347


### [Grafeo](https://grafeo.dev/)

The benchmark does not terminate in a reasonable amount of time. 
After rewrite into native Rust objects + 1 transaction for the whole bulk, the result is as follows:
ingest complete: graph_objects=157550, claims=100000, elapsed_ms=5169
Once again, it has Rust data shape validation only, no validation on the DB side.


### [LadybugDB](https://ladybugdb.com/)

LadyBug doesn't support SHACL (it's a property graph, not RDF), so its schema lives as Cypher DDL constants.
The benchmark does not terminate in a reasonable amount of time, therefore it was rewritten to make use of COPY FROM.


### [Oxigraph](https://github.com/oxigraph/oxigraph)

No ShaCL support, raw JSONLD ingestion
ingest complete: graph_objects=157550, claims=100000, elapsed_ms=8779


### [SparrowDB](https://github.com/ryaker/SparrowDB)

The benchmark does not terminate in a reasonable amount of time. 

| Database | Bulk Insert Time | Peak Memory | Nested Query Time | Nested Query RAM Cold Start|
| ---      | ---              | ---         | ---               | ---                        |
|[fluree](https://labs.flur.ee/)| Timeout | | | |
|[SurrealDB](https://surrealdb.com/)|155,594 ms|11,748,776 KB|136ms| 185,300 KB|
|[Grafeo](https://grafeo.dev/)|51,481 ms|3,891,744 KB|156 ms|3,588,864 KB |
|[Oxigraph](https://github.com/oxigraph/oxigraph)|126,152 ms|14,343,484 KB|9 ms|9,232,032 KB |
|[LadybugDB](https://ladybugdb.com/)|10,750ms|3.2GB|31 ms|276,780 KB |


----

## Tests on Android Emulator

The metrics are: (wall time: open + load, peak RAM RSS)

| Database | Dataset 10k | Dataset 100k | Dataset 500k | Dataset 1kk |
| ---------|-------------|--------------|--------------|-------------|
|[Grafeo](https://grafeo.dev/)|Ingest (520ms, 236mb); Query (243ms, 226mb)|Ingest (4080ms, 727mb); Query (1858ms, 544mb)|Ingest (24661ms, 2755mb); Query (9115ms, 2234mb)|Ingest (OOM 12GB RAM device); Query ()|
|[Oxigraph](https://github.com/oxigraph/oxigraph)|Ingest (1564ms, 288mb); Query (1569ms, 199mb)|Ingest (16113ms, 1047mb); Query (13060ms, 465mb)|Ingest (OOM); Query ()||
|[LadybugDB](https://ladybugdb.com/)|(INCOMPATIBLE WITH EMULATOR)||||
|[SurrealDB](https://surrealdb.com/)|Ingest (2046ms, 269mb); Query (601ms, 271mb)|Ingest (19602ms, 388mb); Query (2472ms, 305mb)|Ingest (102579ms, 1.6gb); Query (1505ms, 264mb)|Ingest (212,166 ms, ~3.7 GB); Query (1153ms, 305mb)|
