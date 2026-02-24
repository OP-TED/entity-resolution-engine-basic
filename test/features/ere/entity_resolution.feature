Feature: Entity Mention Resolution
  As an ERE client
  I want to resolve entity mentions against known clusters
  So that I can identify and link entities across documents

  Scenario Outline: Resolving a known entity mention
    Given an ERE client is connected
    And the entity knowledge base is loaded
    When I submit a resolution request for entity "<entity_id>"
    Then I receive a resolution response
    And the response contains at least one cluster candidate

    Examples:
      | entity_id    |
      | entity-001   |
      | entity-002   |

  Scenario: Resolving an unknown entity mention
    Given an ERE client is connected
    And the entity knowledge base is loaded
    When I submit a resolution request for an unknown entity
    Then I receive a resolution response
    And the response contains a new singleton cluster

  Scenario: Malformed request returns an error response
    Given an ERE client is connected
    When I submit a malformed resolution request
    Then I receive an error response
