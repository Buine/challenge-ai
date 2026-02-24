import time

from app.services.batch import _jobs


class TestBatchSubmit:
    def test_submit_batch_returns_job_id_and_queued_status(self, client):
        response = client.post("/api/v1/batch/reconcile", json={
            "vouchers": [],
            "payments": [],
            "settlements": [],
        })

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        assert data["job_id"].startswith("batch-")

    def test_submit_batch_with_data_returns_job_id(self, client):
        response = client.post("/api/v1/batch/reconcile", json={
            "vouchers": [{
                "transaction_id": "TXN-BATCH-001",
                "amount": "150.00",
                "currency": "MXN",
                "payment_method": "OXXO",
                "status": "PENDING",
                "source_system": "voucher_system",
                "created_at": "2026-02-20T10:00:00",
            }],
            "payments": [],
            "settlements": [],
        })

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"].startswith("batch-")

    def test_get_nonexistent_job_returns_404(self, client):
        response = client.get("/api/v1/batch/nonexistent-job-id")

        assert response.status_code == 404
        assert response.json()["detail"] == "Job not found"

    def test_get_job_returns_status_fields(self, client):
        submit = client.post("/api/v1/batch/reconcile", json={
            "vouchers": [],
            "payments": [],
            "settlements": [],
        })
        job_id = submit.json()["job_id"]

        time.sleep(0.5)

        response = client.get(f"/api/v1/batch/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert "status" in data
        assert "created_at" in data
        assert "progress" in data
        assert "total" in data

    def test_batch_job_completes_with_empty_data(self, client):
        submit = client.post("/api/v1/batch/reconcile", json={
            "vouchers": [],
            "payments": [],
            "settlements": [],
        })
        job_id = submit.json()["job_id"]

        for _ in range(20):
            time.sleep(0.2)
            response = client.get(f"/api/v1/batch/{job_id}")
            if response.json()["status"] in ("completed", "failed"):
                break

        data = response.json()
        assert data["status"] == "completed"
        assert data["summary"] is not None
        assert data["summary"]["detection"]["issues_found"] >= 0

    def test_batch_invalid_data_returns_422(self, client):
        response = client.post("/api/v1/batch/reconcile", json={
            "vouchers": [{"invalid": "data"}],
        })

        assert response.status_code == 422
