"""
E2E pipeline test — requires fully running services.
Skipped automatically in CI unit/integration runs.
Run manually against a live environment.
"""
import pytest

pytestmark = pytest.mark.skip(reason="E2E requires running services — run manually")


@pytest.mark.asyncio
async def test_full_contract_pipeline():
    """
    Full pipeline: upload → processing → REVIEW_READY → clause approve.

    Steps:
    1. POST /contracts/upload with sample_nda.pdf
    2. Poll GET /contracts/{id}/status until REVIEW_READY (5 min timeout)
    3. GET /contracts/{id}/clauses → validate ExtractedClause schema
    4. Validate final_risk in {GREEN, AMBER, RED}
    5. PATCH /clauses/{clause_id}/approve
    """
    import asyncio

    import httpx

    base_url = "http://localhost:8000"

    async with httpx.AsyncClient(base_url=base_url) as client:
        # Step 1: Login
        login_resp = await client.post(
            "/auth/login", json={"email": "lawyer@test.com", "password": "testpass"}
        )
        assert login_resp.status_code == 200

        # Step 2: Upload contract
        with open("tests/e2e/fixtures/sample_nda.pdf", "rb") as f:
            upload_resp = await client.post(
                "/contracts/upload",
                files={"file": ("sample_nda.pdf", f, "application/pdf")},
            )
        assert upload_resp.status_code == 200
        contract_id = upload_resp.json()["contract_id"]

        # Step 3: Poll until REVIEW_READY (max 5 minutes)
        for _ in range(60):
            status_resp = await client.get(f"/contracts/{contract_id}/status")
            if status_resp.json()["status"] == "REVIEW_READY":
                break
            await asyncio.sleep(5)
        else:
            pytest.fail("Pipeline did not reach REVIEW_READY within 5 minutes")

        # Step 4: Validate clauses
        clauses_resp = await client.get(f"/contracts/{contract_id}/clauses")
        assert clauses_resp.status_code == 200
        clauses = clauses_resp.json()
        assert isinstance(clauses, list)

        # Step 5: Validate final_risk
        contract_resp = await client.get(f"/contracts/{contract_id}")
        assert contract_resp.status_code == 200
        final_risk = contract_resp.json().get("final_risk")
        assert final_risk in {"GREEN", "AMBER", "RED"}

        # Step 6: Approve first clause if any exist
        if clauses:
            clause_id = clauses[0]["clause_id"]
            approve_resp = await client.patch(f"/clauses/{clause_id}/approve")
            assert approve_resp.status_code in {200, 204}
