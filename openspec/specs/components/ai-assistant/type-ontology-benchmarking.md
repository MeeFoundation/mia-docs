# Benchmarking the Type Ontology ingestion in LadybugDB


These results are for Type Ontology ingestion and querying. It means that the ontology is temporarily limited
to a subset that contains type-related data and value-data, omitting metainformation types like Relations and capability-related entities.

| Dataset size | Ingestion Speed | Ingestion Memory | Query Speed | Query Memory |
| ---          | ---             | ---              | ---         | ---          |
| 10K          | 61,673 ms       | 328.6 MB RSS     | 159ms       |  284.6 MB    |
| 100K         | 590,533 ms      | 703.0 MB RSS     | 764 ms      | 576.9 MB RSS |
| 500K         | 2,942,934 ms    | 1965.8 MB RSS    | 918 ms      | 1361.6 MB RSS|
