// UPSERT_PARTY
MERGE (p:Party {party_id: $party_id, tenant_id: $tenant_id})
SET p.name = $name,
    p.normalized_name = $normalized_name

// LINK_PARTY_TO_CONTRACT
MATCH (c:Contract {contract_id: $contract_id})
MATCH (p:Party {party_id: $party_id, tenant_id: c.tenant_id})
MERGE (p)-[r:PARTY_TO]->(c)
SET r.role = $role
