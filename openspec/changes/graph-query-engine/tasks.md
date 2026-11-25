# Tasks: graph-query-engine

> **Created by Claude, awaiting proofread.** Not reviewed by a human - do not submit or circulate as approved.

Every scenario below is a test in pdn-agent today. A task that moves code moves its test with it, and the test must fail with the mechanism removed.

## 1. Specification

- [x] 1.1 ADR-0019: pods and the assistant read pod data through a graph query engine
- [x] 1.2 Deltas: materialization interface, catch-up, ontology registry, queries
- [x] 1.3 Glossary: `architecture/language/pod-tool.md`
- [ ] 1.4 Settle Open Question 1, how mee-pdn carries a pod-tool's keyed records, before the materialization interface and catch-up move

## 2. Scenarios with no test yet (in pdn-agent, before the move)

- [ ] 2.1 A key whose newest record the materialization turns into nothing holds no claim (materialization interface)
- [ ] 2.2 A pod-tool with no registered materialization contributes nothing to the graph (materialization interface)
- [ ] 2.3 A bulk load that fails leaves no claims of its zones, which are then added one at a time (catch-up)
- [ ] 2.4 A handle made before its reader's removal (Open Question 4)
- [ ] 2.5 The engine with no materialization registered loads its registry and answers with no claims (materialization interface, D7)

## 3. The move into `crates/graph-query-engine`

Each item: compare the pdn-agent code with the capability's requirements, move what conforms with its tests, and open the two pull requests (mia-docs and mee-pdn) to be reviewed together. A test that uses chat or Info today uses a pod-tool of its own once it moves, so the engine's crate depends on no pod-tool (D7).

- [ ] 3.1 Ontology registry: `src/graph/ontology.rs`, the registry tables and their loading in `src/sdk/ladybug.rs`; tests `the_application_ontology_loads_on_top_of_mia_ontologies`, `a_registry_that_defines_a_type_twice_is_refused`, `a_message_is_read_as_text_by_a_reader_that_knows_only_text`, `shapes_types_and_subject_types_are_read_from_the_registry_in_the_database`
- [ ] 3.2 Queries: the handles and reads in `src/graph/mod.rs` and `src/sdk/ladybug.rs`, without `PodGraph::assert` and the inserts; tests `a_pod_reads_only_itself`, `infos_graph_handle_reads_infos_zone_alone`, `a_zone_the_reader_may_not_see_is_not_read`, `a_non_member_reads_none_of_the_pods_graph`, `pods_share_one_database_and_never_see_each_others_claims`, `filters_and_counts_run_in_the_database`, `a_long_list_is_read_a_page_at_a_time_newest_first`, `an_event_with_a_time_goes_in_and_comes_back`, `a_new_pod_bulk_loads_its_backlog_and_reads_back_exactly_what_was_written`
- [ ] 3.3 Materialization interface (after 1.4): `src/sdk/materialize.rs`, with an empty registry (D7). Chat's `pod_tool::chat::Materialize` and Info's `ladybug::Claims` stay in pdn-agent and register from there. The engine's tests use a pod-tool of their own in place of chat and Info, so the engine's crate depends on no pod-tool even for its tests: `telli_reads_a_pod_tool_it_was_not_written_for` (rewritten without the assistant), `each_pod_tool_says_what_its_zone_holds` (the part about which tool ontologies a reader is told), `an_edited_record_replaces_its_claim_and_a_deleted_one_removes_it`, `alices_graph_and_bobs_are_made_apart_and_read_the_same`, `a_graph_made_again_from_the_records_reads_the_same`
- [ ] 3.4 Catch-up (after 1.4): `GraphDb::catch_up_zone`, `GraphDb::catch_up_many` and the bulk load in `src/sdk/ladybug.rs`, without the version skip (Open Question 2); tests `after_the_first_load_each_new_claim_is_appended_and_nothing_is_applied_twice`, `a_claim_that_does_not_fit_its_type_is_left_out_and_the_rest_load`, `many_small_new_pods_bulk_load_together_into_the_same_graph`, `bulk_loaded_and_appended_claims_are_the_same_graph`, `each_user_has_one_database_for_all_of_their_pods`

## 4. Gates

- [ ] 4.1 `openspec validate graph-query-engine --strict` and `python3 -I scripts/check-docs.py`
- [ ] 4.2 pdn-agent reads the moved crate in place of its own code, and its tests still pass
