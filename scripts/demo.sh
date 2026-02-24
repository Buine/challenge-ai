#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
API="$BASE_URL/api/v1"

echo "=== OXXO Reconciliation Service - End-to-End Demo ==="
echo ""

echo "1. Health Check"
curl -s "$BASE_URL/health" | python3 -m json.tool
echo ""

echo "2. Generating test data..."
python3 scripts/generate_test_data.py
echo ""

echo "3. Ingesting vouchers..."
curl -s -X POST "$API/ingest/vouchers" \
  -H "Content-Type: application/json" \
  -d @data/vouchers.json | python3 -m json.tool
echo ""

echo "4. Ingesting payments..."
curl -s -X POST "$API/ingest/payments" \
  -H "Content-Type: application/json" \
  -d @data/payments.json | python3 -m json.tool
echo ""

echo "5. Ingesting settlements..."
curl -s -X POST "$API/ingest/settlements" \
  -H "Content-Type: application/json" \
  -d @data/settlements.json | python3 -m json.tool
echo ""

echo "6. Running detection engine..."
curl -s -X POST "$API/detection/run" | python3 -m json.tool
echo ""

echo "7. Querying all issues (first 10)..."
curl -s "$API/issues?limit=10" | python3 -m json.tool
echo ""

echo "8. Filtering issues by type (ORPHANED_PAYMENT)..."
curl -s "$API/issues?issue_type=ORPHANED_PAYMENT" | python3 -m json.tool
echo ""

echo "9. Filtering issues by severity (HIGH)..."
curl -s "$API/issues?severity=HIGH" | python3 -m json.tool
echo ""

echo "10. Filtering issues by payment method (OXXO)..."
curl -s "$API/issues?payment_method=OXXO" | python3 -m json.tool
echo ""

echo "11. Summary statistics..."
curl -s "$API/issues/summary" | python3 -m json.tool
echo ""

echo "12. Transaction lookup (TXN-OXXO-001)..."
curl -s "$API/transactions/TXN-OXXO-001" | python3 -m json.tool
echo ""

echo "13. Transaction lookup (orphaned payment - TXN-OXXO-166)..."
curl -s "$API/transactions/TXN-OXXO-166" | python3 -m json.tool
echo ""

echo "=== Demo Complete ==="
