# ---

status: {proposed | rejected | accepted | deprecated | … | superseded by ADR-0005 <0005-example.md>}
date: 2026-05-12
deciders: {list everyone involved in the decision}
consulted: {list everyone whose opinions are sought (typically subject-matter experts); and with whom there is a two-way communication}
informed: {list everyone who is kept up-to-date on progress; and with whom there is a one-way communication}

---

# AI Assistant Data Storage

## Context and Problem Statement

The AI Assistant platform requires a reliable and scalable approach for storing conversation history, user preferences, embeddings, and operational metadata. 

The key question is how to design a storage strategy that balances performance, security, cost, and maintainability while supporting future AI capabilities such as long-term memory, analytics, and retrieval-augmented generation (RAG).

## Decision Drivers

* Scalability to support growing conversation volume, embeddings, and analytics workloads
* Low-latency access for real-time AI assistant interactions and retrieval operations
* Data consistency and reliability across user sessions and distributed services
* Security, privacy, and compliance requirements for sensitive user data
* Cost efficiency for long-term storage and high-throughput operations
* Support for future AI capabilities such as RAG, memory persistence, and semantic search
* Operational simplicity, maintainability, and observability for platform teams
* Embeddable
* Rust-first

## Considered Options

* [LadybugDB](https://ladybugdb.com/)
* [Grafeo](https://grafeo.dev/)
* [fluree](https://flur.ee/)
* [IndraDB](https://github.com/indradb/indradb)
* [Oxigraph](https://github.com/oxigraph/oxigraph)
* [SurrealDB](https://surrealdb.com/)
* [SparrowDB](https://github.com/ryaker/SparrowDB)
* [petgraph](https://docs.rs/petgraph/latest/petgraph/)


## Decision Outcome

WIP - no decision made so far

### Consequences

* Good, because {positive consequence, e.g., improvement of one or more desired qualities, …}
* Bad, because {negative consequence, e.g., compromising one or more desired qualities, …}

## Pros and Cons of the Options

### [LadybugDB](https://ladybugdb.com/)

Is in Rust?: No
Embeddable?: Yes

{example | description | pointer to more information | …}

* Good, because LadybugDB is specifically designed for AI memory workloads, combining graph traversal, vector search, typed schemas, and semantic querying in a single embedded database engine. This aligns closely with the platform’s long-term memory and RAG requirements. 

* Good, because the embedded architecture eliminates network overhead and deployment complexity while supporting ACID transactions, low-latency queries, and portable local-first AI applications. 

* Neutral, because LadybugDB uses a strict structured property graph model with mandatory schemas and Cypher queries, which improves consistency and type safety but requires upfront ontology and schema design discipline. 

* Bad, because LadybugDB is a relatively new and specialized technology with a smaller ecosystem, fewer production references, and potentially limited community support compared to more mature graph or multi-model databases.


### [Grafeo](https://grafeo.dev/)

Is in Rust?: Yes
Embeddable?: Yes

{example | description | pointer to more information | …}

* Good, because Grafeo supports both Labeled Property Graph (LPG) and RDF data models together with multiple query languages including GQL, Cypher, Gremlin, GraphQL, SPARQL, and SQL/PGQ. This provides strong flexibility for evolving AI memory and knowledge graph architectures. 

* Good, because Grafeo is designed as a high-performance embedded Rust database with vector search, ACID transactions, MVCC isolation, and multi-language bindings, making it suitable for edge AI, semantic retrieval, and local-first AI assistants. 

* Neutral, because Grafeo aims to unify RDF and LPG ecosystems, which increases interoperability and modeling flexibility but can also introduce additional architectural complexity and multiple querying paradigms for developers to manage. 

* Bad, because Grafeo is still an early-stage project with a relatively small ecosystem, limited production adoption, and evolving tooling compared to mature graph databases such as Neo4j or RDF-focused platforms.


### [fluree](https://labs.flur.ee/)

Is in Rust?: Yes
Embeddable?: 

{example | description | pointer to more information | …}

* Good, because Fluree combines graph semantics, linked data, and blockchain-inspired immutability, providing strong auditability and trusted historical state management for AI memory and knowledge systems.
* 
* Good, because Fluree supports semantic web standards such as RDF and JSON-LD, enabling interoperable ontologies, linked knowledge graphs, and integration with external semantic ecosystems.

* Neutral, because Fluree’s immutable ledger-style architecture improves traceability and temporal reasoning but introduces a more opinionated data model and operational paradigm than traditional property graph databases.

* Bad, because Fluree’s RDF-first and semantic-web-oriented approach can increase modeling complexity, query learning curve (SPARQL/linked data concepts), and development overhead for teams primarily focused on application-centric AI memory workloads rather than semantic interoperability.

  
### [IndraDB](https://github.com/indradb/indradb)

Is in Rust?: Yes
Embeddable?: Yes

{example | description | pointer to more information | …}

* Good, because IndraDB is implemented in Rust with a lightweight architecture focused on high-performance graph storage and traversal, making it attractive for embedded or resource-constrained AI systems.

* Good, because IndraDB exposes a relatively simple graph model and API surface, which can reduce operational overhead and simplify integration for applications that primarily require graph relationships and traversal capabilities.

* Neutral, because IndraDB focuses mainly on core graph database functionality and intentionally keeps the feature set smaller and simpler compared to larger graph platforms, which can be beneficial for maintainability but limits advanced querying and AI-oriented features.

* Bad, because IndraDB lacks many modern AI-memory-oriented capabilities such as integrated vector search, semantic retrieval, advanced ontology tooling, and mature query ecosystems that are increasingly important for RAG and long-term AI memory systems. Not as actively maintained.

  
### [Oxigraph](https://github.com/oxigraph/oxigraph)

Is in Rust?: Yes
Embeddable?: Yes

{example | description | pointer to more information | …}

* Good, because Oxigraph is a lightweight and high-performance RDF and SPARQL graph database implemented in Rust, making it well suited for embedded semantic knowledge graph applications and local AI systems.

* Good, because Oxigraph fully embraces semantic web standards such as RDF, SPARQL, and RDF-star, enabling interoperability, linked data modeling, and standards-based ontologies for structured AI memory systems.

* Neutral, because Oxigraph focuses strongly on RDF and semantic graph capabilities rather than broader multi-model database features, which is beneficial for standards compliance but may require complementary systems for vector search or operational application data.

* Bad, because Oxigraph currently lacks native AI-oriented capabilities such as integrated vector embeddings, semantic similarity indexing, and hybrid graph-vector retrieval workflows that modern RAG and long-term AI memory systems often require.

  
### [SurrealDB](https://surrealdb.com/)

Is in Rust?: Yes
Embeddable?:

{example | description | pointer to more information | …}

* Good, because SurrealDB provides a multi-model architecture combining document, graph, key-value, and relational capabilities in a single database engine, which can simplify AI platform architectures and reduce infrastructure fragmentation.

* Good, because SurrealDB includes native graph relations, real-time synchronization, flexible schema options, and integrated querying capabilities, making it well suited for conversational AI systems with evolving data models and real-time workloads.

* Neutral, because SurrealDB emphasizes schema flexibility and developer ergonomics, which accelerates prototyping and iteration but may require additional governance and validation practices for large-scale ontology-driven AI memory systems.

* Bad, because SurrealDB’s graph functionality is less specialized than dedicated graph or semantic databases, and its ecosystem and operational maturity are still developing compared to long-established database platforms.

  
### [SparrowDB](https://github.com/ryaker/SparrowDB)

Is in Rust?: Yes
Embeddable?: Yes

{example | description | pointer to more information | …}

* Good, because SparrowDB is designed as a lightweight embedded graph database implemented in Rust, making it suitable for local-first applications, edge deployments, and low-overhead AI memory experimentation.

* Good, because SparrowDB focuses on simplicity and direct graph traversal operations, which can provide predictable performance and easier integration for applications that primarily need relationship-centric storage.

* Neutral, because SparrowDB appears intentionally minimalistic and focused on core graph capabilities rather than providing a large ecosystem of advanced tooling, query languages, or semantic standards support.

* Bad, because SparrowDB is an early-stage project with limited maturity, documentation, ecosystem adoption, and missing advanced AI-oriented features such as vector search, semantic retrieval, ontology enforcement, and production-grade operational tooling.

  
### [petgraph](https://docs.rs/petgraph/latest/petgraph/)

Is in Rust?: Yes
Embeddable?: Yes

{example | description | pointer to more information | …}

* Good, because petgraph is a lightweight and highly flexible Rust graph library that integrates directly into application code without requiring a separate database process, making it suitable for embedded AI agents and in-memory graph workloads.

* Good, because petgraph provides efficient graph algorithms, traversal utilities, and customizable graph structures, allowing developers to build specialized memory and reasoning systems tailored to their AI architecture.

* Neutral, because petgraph is a graph data structure library rather than a full database system, which gives developers maximum implementation freedom but also shifts responsibility for persistence, indexing, querying, concurrency, and durability to the application layer.

* Bad, because petgraph lacks native database features such as persistent storage, ACID transactions, vector indexing, declarative query languages, replication, and semantic retrieval capabilities that are typically required for production-grade AI memory platforms.


**## More Information**


{You might want to provide additional evidence/confidence for the decision outcome here and/or

 document the team agreement on the decision and/or

 define when and how this decision should be realized and if/when it should be re-visited and/or

 how the decision is validated.

 Links to other decisions and resources might appear here as well.}

 
