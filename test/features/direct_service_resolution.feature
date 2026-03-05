Feature: Entity Mention Resolution — Direct Service Calls

  Tests: resolve_entity_mention(entity_mention: EntityMention) -> ClusterReference

  Fixed for all scenarios:
    source_id    = "ted-sws-pipeline"
    content_type = "text/turtle"

  Test data root: test/test_data/


  Background:
    Given a fresh resolution service is ready


  # ---------------------------------------------------------------------------
  # Known entity mention → resolves to an existing cluster
  # ---------------------------------------------------------------------------

  Scenario Outline: Resolving a known entity mention
    Given entity mention "<mention_id_seed>" of type "<entity_type>" was already resolved with content from "<rdf_file_seed>"
    When I resolve entity mention "<mention_id>" of type "<entity_type>" with content from "<rdf_file>"
    Then the result is a ClusterReference
    And the cluster_id matches the seed cluster

    Examples:
      | entity_type  | mention_id_seed                      | rdf_file_seed                        | mention_id                          | rdf_file                              |
      | ORGANISATION | http://ers.test/mention/org2-ks-seed | organizations/group2/663952-2023.ttl | http://ers.test/mention/org2-ks-new | organizations/group2/663952_-2023.ttl |


  # ---------------------------------------------------------------------------
  # Same-group entities → resolve to the same cluster
  # ---------------------------------------------------------------------------

  Scenario Outline: Same-group entity mentions resolve to the same cluster
    When I resolve the first entity mention "<mention_id_a>" of type "<entity_type>" with content from "<rdf_file_a>"
    And I resolve the second entity mention "<mention_id_b>" of type "<entity_type>" with content from "<rdf_file_b>"
    Then both results are ClusterReference instances
    And both cluster_ids are equal

    Examples:
      | group_id | entity_type  | mention_id_a                        | rdf_file_a                           | mention_id_b                        | rdf_file_b                           |
      | org-g1   | ORGANISATION | http://ers.test/mention/org1-001    | organizations/group1/661238-2023.ttl | http://ers.test/mention/org1-002    | organizations/group1/662860-2023.ttl |
      | org-g1   | ORGANISATION | http://ers.test/mention/org1-001    | organizations/group1/661238-2023.ttl | http://ers.test/mention/org1-003    | organizations/group1/663653-2023.ttl |


  # ---------------------------------------------------------------------------
  # Different-group entities → each produces its own new singleton cluster
  # ---------------------------------------------------------------------------

  Scenario Outline: Different-group entity mentions produce distinct clusters
    When I resolve the first entity mention "<mention_id_a>" of type "<entity_type>" with content from "<rdf_file_a>"
    And I resolve the second entity mention "<mention_id_b>" of type "<entity_type>" with content from "<rdf_file_b>"
    Then both results are ClusterReference instances
    And the cluster_ids are different

    Examples:
      | entity_type  | mention_id_a                        | rdf_file_a                           | mention_id_b                        | rdf_file_b                           |
      | ORGANISATION | http://ers.test/mention/org1-001    | organizations/group1/661238-2023.ttl | http://ers.test/mention/org2-001    | organizations/group2/661197-2023.ttl |
      | ORGANISATION | http://ers.test/mention/org1-001    | organizations/group1/661238-2023.ttl | http://ers.test/mention/org2-002    | organizations/group2/663952-2023.ttl |


  # ---------------------------------------------------------------------------
  # Idempotency — same mention + same content → identical ClusterReference
  # ---------------------------------------------------------------------------

  Scenario Outline: Resolving the same entity mention twice returns identical ClusterReference
    When I resolve entity mention "<mention_id>" of type "<entity_type>" with content from "<rdf_file>"
    And I resolve entity mention "<mention_id>" of type "<entity_type>" with content from "<rdf_file>" again
    Then both ClusterReference results are identical

    Examples:
      | entity_type  | mention_id                          | rdf_file                             |
      | ORGANISATION | http://ers.test/mention/org1-idem   | organizations/group1/661238-2023.ttl |


  # ---------------------------------------------------------------------------
  # Idempotency conflict — same mention_id, different content → exception
  # ---------------------------------------------------------------------------

  Scenario Outline: Resolving the same mention_id with different content raises an exception
    Given entity mention "<mention_id>" of type "<entity_type>" was already resolved with content from "<rdf_file_first>"
    When I try to resolve entity mention "<mention_id>" of type "<entity_type>" with content from "<rdf_file_conflict>"
    Then an exception is raised

    Examples:
      | entity_type  | mention_id                           | rdf_file_first                       | rdf_file_conflict                    |
      | ORGANISATION | http://ers.test/mention/org1-conf    | organizations/group1/661238-2023.ttl | organizations/group2/661197-2023.ttl |


  # ---------------------------------------------------------------------------
  # Unsupported entity type → exception
  # ---------------------------------------------------------------------------

  Scenario Outline: Unsupported entity type raises an exception
    When I try to resolve entity mention "<mention_id>" of type "<entity_type>" with content from "<rdf_file>"
    Then an unsupported entity type exception is raised

    Examples:
      | entity_type | mention_id                        | rdf_file                             |
      | CONTRACT    | http://ers.test/mention/unsup-001 | organizations/group1/661238-2023.ttl |


  # ---------------------------------------------------------------------------
  # Malformed input → exception
  # ---------------------------------------------------------------------------

  Scenario Outline: Malformed entity mention content raises an exception
    When I try to resolve entity mention "<mention_id>" of type "<entity_type>" with invalid content "<bad_content>"
    Then an exception is raised

    Examples:
      | entity_type  | mention_id                       | bad_content   |
      | ORGANISATION | http://ers.test/mention/err-001  | not valid rdf |
      | ORGANISATION | http://ers.test/mention/err-002  |               |
