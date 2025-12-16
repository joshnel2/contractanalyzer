#!/bin/bash

# Test the Attorney Commission Calculator workflow

WEBHOOK_URL="${WEBHOOK_URL:-http://localhost:5678/webhook/calculate-commissions}"

# Read sample files
CASE_DATA=$(cat sample-data/case_data.csv)
RULES_SHEET=$(cat sample-data/rules_sheet.csv)

# Create JSON payload
JSON_PAYLOAD=$(jq -n \
  --arg case_data "$CASE_DATA" \
  --arg rules_sheet "$RULES_SHEET" \
  '{case_data_csv: $case_data, rules_sheet_csv: $rules_sheet}')

echo "=== Testing Attorney Commission Calculator ==="
echo ""
echo "Sending request to: $WEBHOOK_URL"
echo ""

# Make the request
RESPONSE=$(curl -s -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d "$JSON_PAYLOAD")

# Check if response is valid
if [ -z "$RESPONSE" ]; then
  echo "ERROR: No response received. Make sure:"
  echo "  1. n8n is running (docker-compose up -d)"
  echo "  2. The workflow is imported and ACTIVATED"
  exit 1
fi

echo "=== Response ==="
echo "$RESPONSE" | jq .

echo ""
echo "=== CSV Output ==="
echo "$RESPONSE" | jq -r '.csv_output'
