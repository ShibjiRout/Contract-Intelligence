// CHECK_PARTY_RISKY_CLAUSE_HISTORY
MATCH (current:Contract {contract_id: $contract_id, tenant_id: $tenant_id})<-[:PARTY_TO]-(p:Party)
MATCH (p)-[:PARTY_TO]->(old:Contract {tenant_id: $tenant_id})-[:CONTAINS]->(cl:Clause)
WHERE old.contract_id <> $contract_id
  AND cl.type = $clause_type
  AND cl.risk_level IN ["RED", "AMBER"]
RETURN p.name AS party_name,
       p.party_id AS party_id,
       count(cl) AS risky_history,
       collect(DISTINCT old.contract_id)[0..5] AS contract_ids
ORDER BY risky_history DESC
