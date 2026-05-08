// FIND_PARTY_RISK
MATCH (p:Party {party_id: $party_id})-[r:REVIEWED_BY]->(c:Contract)
RETURN p.risk_score AS risk_score, count(c) AS contract_count

// FIND_PARTY_BY_NAME_HASH
MATCH (p:Party) WHERE p.name_hash = $name_hash RETURN p
