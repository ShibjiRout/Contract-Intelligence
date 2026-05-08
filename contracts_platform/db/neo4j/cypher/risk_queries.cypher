// GET_PARTY_RISK_HISTORY
MATCH (p:Party {party_id: $party_id})-[r:REVIEWED_BY]->(c:Contract)
RETURN r.outcome AS outcome, c.contract_id AS contract_id, r.timestamp AS timestamp
ORDER BY r.timestamp DESC LIMIT 10
