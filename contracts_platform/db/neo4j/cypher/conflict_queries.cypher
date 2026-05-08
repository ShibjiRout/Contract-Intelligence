// FIND_CLAUSE_CONFLICTS
MATCH (c1:Clause {clause_id: $clause_id})-[:CONFLICTS_WITH]->(c2:Clause)
RETURN c2

// CHECK_CROSS_CONTRACT_CONFLICT
MATCH (p:Party {party_id: $party_id})-[:SIGNED]->(c:Contract)-[:CONTAINS]->(cl:Clause)
WHERE cl.type = $clause_type AND cl.risk_level = 'RED'
RETURN count(cl) AS conflict_count
