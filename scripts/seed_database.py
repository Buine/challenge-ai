import json
import os
import sys

import requests

BASE_URL = "http://localhost:8000/api/v1"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data")

BATCH_SIZE = 50


def load_json(filename):
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        print("Run generate_test_data.py first to create the data files.")
        sys.exit(1)
    with open(filepath) as f:
        return json.load(f)


def post_in_batches(url, records, label):
    total_received = 0
    total_created = 0
    total_duplicates = 0

    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i:i + BATCH_SIZE]
        response = requests.post(url, json=batch, timeout=30)
        response.raise_for_status()
        result = response.json()
        total_received += result["received"]
        total_created += result["created"]
        total_duplicates += result["duplicates"]
        print(f"  {label} batch {i // BATCH_SIZE + 1}: "
              f"received={result['received']}, created={result['created']}, "
              f"duplicates={result['duplicates']}")

    return {
        "received": total_received,
        "created": total_created,
        "duplicates": total_duplicates,
    }


def check_health():
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        response.raise_for_status()
        data = response.json()
        print(f"API health: {data['status']}")
        return True
    except requests.exceptions.ConnectionError:
        print("Cannot connect to API at http://localhost:8000")
        print("Make sure the API server is running.")
        return False
    except Exception as e:
        print(f"Health check failed: {e}")
        return False


def main():
    print("=" * 60)
    print("Reconciliation Service - Database Seeder")
    print("=" * 60)

    if not check_health():
        sys.exit(1)

    print("\nLoading data files...")
    voucher_data = load_json("vouchers.json")
    payment_data = load_json("payments.json")
    settlement_data = load_json("settlements.json")
    print(f"  Loaded {len(voucher_data)} vouchers, {len(payment_data)} payments, "
          f"{len(settlement_data)} settlements")

    print("\nIngesting vouchers...")
    voucher_result = post_in_batches(f"{BASE_URL}/ingest/vouchers", voucher_data, "Vouchers")

    print("\nIngesting payments...")
    payment_result = post_in_batches(f"{BASE_URL}/ingest/payments", payment_data, "Payments")

    print("\nIngesting settlements...")
    settlement_result = post_in_batches(f"{BASE_URL}/ingest/settlements", settlement_data, "Settlements")

    print("\n" + "-" * 60)
    print("Ingestion Summary")
    print("-" * 60)
    for label, result in [("Vouchers", voucher_result), ("Payments", payment_result), ("Settlements", settlement_result)]:
        print(f"  {label:12s}: received={result['received']}, "
              f"created={result['created']}, duplicates={result['duplicates']}")

    print("\nRunning detection engine...")
    response = requests.post(f"{BASE_URL}/detection/run", timeout=60)
    response.raise_for_status()
    detection = response.json()

    print("\n" + "=" * 60)
    print("Detection Results")
    print("=" * 60)
    print(f"  Previous issues cleared: {detection['previous_issues_cleared']}")
    print(f"  New issues found:        {detection['new_issues_found']}")
    print("\n  Issues by type:")
    for issue_type, count in sorted(detection["issues_by_type"].items()):
        print(f"    {issue_type:30s}: {count}")

    print("\n" + "=" * 60)
    print("Seeding complete.")


if __name__ == "__main__":
    main()
