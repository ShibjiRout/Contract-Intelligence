// GET_PARTY_RISK_HISTORY
MATCH (p:Party {party_id: $party_id, tenant_id: $tenant_id})-[:PARTY_TO]->(c:Contract)-[:CONTAINS]->(cl:Clause)
WHERE cl.risk_level IN ["RED", "AMBER"]
RETURN c.contract_id AS contract_id,
       cl.clause_id AS clause_id,
       cl.type AS clause_type,
       cl.risk_level AS risk_level,
       cl.risk_score AS risk_score
ORDER BY cl.risk_score DESC
LIMIT 20
