#!/bin/bash
# Validation Script with ALCOA++ Traceability
# Automatically creates audit trail for each validation run

set -e  # Exit on error

# ===== Configuration =====
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
USER=$(whoami)
HOSTNAME=$(hostname)

# ===== Parse Arguments =====
DATA_FILE=""
METHOD="loo"
FOLDS=5

while [[ $# -gt 0 ]]; do
  case $1 in
    --data)
      DATA_FILE="$2"
      shift 2
      ;;
    --method)
      METHOD="$2"
      shift 2
      ;;
    --folds)
      FOLDS="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

if [ -z "$DATA_FILE" ]; then
  echo "Error: --data argument is required"
  echo "Usage: $0 --data <file.csv> --method <loo|kfold> [--folds <n>]"
  exit 1
fi

# ===== Create Run Directory =====
METHOD_UPPER=$(echo "$METHOD" | tr '[:lower:]' '[:upper:]')
RUN_ID="${TIMESTAMP}_${METHOD_UPPER}"
RUN_DIR="trace/validation_runs/${RUN_ID}"

echo "=========================================="
echo "ALCOA++ Validation Run"
echo "=========================================="
echo "Run ID: $RUN_ID"
echo "User: $USER"
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Method: $METHOD"
echo "Data: $DATA_FILE"
echo ""

mkdir -p "$RUN_DIR"

# ===== Copy Input Data (Original) =====
echo "[1/7] Copying input data snapshot..."
cp "$DATA_FILE" "$RUN_DIR/input_snapshot.csv"
INPUT_CHECKSUM=$(shasum -a 256 "$RUN_DIR/input_snapshot.csv" | awk '{print $1}')
echo "  ✓ Input checksum: $INPUT_CHECKSUM"

# ===== Create Metadata =====
echo "[2/7] Creating metadata..."
cat > "$RUN_DIR/metadata.json" <<EOF
{
  "run_id": "$RUN_ID",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "user": "$USER",
  "hostname": "$HOSTNAME",
  "environment": {
    "python_version": "$(python --version 2>&1 | awk '{print $2}')",
    "pandas_version": "$(python -c 'import pandas; print(pandas.__version__)' 2>/dev/null || echo 'unknown')",
    "scikit_learn_version": "$(python -c 'import sklearn; print(sklearn.__version__)' 2>/dev/null || echo 'unknown')",
    "numpy_version": "$(python -c 'import numpy; print(numpy.__version__)' 2>/dev/null || echo 'unknown')",
    "os": "$(uname -s) $(uname -r)"
  },
  "input_file": "$DATA_FILE",
  "input_checksum": "sha256:$INPUT_CHECKSUM",
  "algorithm_version": "v1.0_baseline",
  "validation_method": "$METHOD",
  "parameters": {
    "method": "$METHOD",
    "folds": $FOLDS
  }
}
EOF
echo "  ✓ Metadata created"

# ===== Run Validation =====
echo "[3/7] Running validation..."
CMD="python validate_standalone.py --data $RUN_DIR/input_snapshot.csv --method $METHOD"
if [ "$METHOD" = "kfold" ]; then
  CMD="$CMD --folds $FOLDS"
fi

# Save command
echo "$CMD" > "$RUN_DIR/command.txt"

# Run and capture output
$CMD --output "$RUN_DIR/results.json" 2>&1 | tee "$RUN_DIR/stdout.log"

echo "  ✓ Validation complete"

# ===== Generate Checksums =====
echo "[4/7] Generating checksums..."
cd "$RUN_DIR"
shasum -a 256 input_snapshot.csv > checksums.txt
shasum -a 256 results.json >> checksums.txt
shasum -a 256 stdout.log >> checksums.txt
cd - > /dev/null
echo "  ✓ Checksums generated"

# ===== Create Signature Template =====
echo "[5/7] Creating signature template..."
RESULTS_CHECKSUM=$(shasum -a 256 "$RUN_DIR/results.json" | awk '{print $1}')

cat > "$RUN_DIR/signature.txt" <<EOF
VALIDATION RUN SIGNATURE
========================
Run ID: $RUN_ID
Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
Data Checksum: sha256:$INPUT_CHECKSUM
Results Checksum: sha256:$RESULTS_CHECKSUM

METRICS (from results.json):
$(python -c "import json; data=json.load(open('$RUN_DIR/results.json')); metrics=data.get('metrics', data.get('aggregated_metrics', {})); print('\n'.join([f'{k}: {v}' for k,v in metrics.items() if k in ['r2', 'mean_r2_test', 'rmse', 'mean_rmse_test', 'mae', 'mean_mae_test']]))" 2>/dev/null || echo "See results.json")

APPROVAL:
---------
Reviewed by: _________________
Date: ____________________
Approved: [ ] Yes  [ ] No  [ ] Conditional

Reviewer Notes:
_______________________________________________________________________________
_______________________________________________________________________________
_______________________________________________________________________________

Signature: _________________

EOF
echo "  ✓ Signature template created"

# ===== Update Audit Log =====
echo "[6/7] Updating audit trail..."
AUDIT_LOG="trace/audit_logs/$(date +%Y-%m-%d).log"
AUDIT_CSV="trace/audit_logs/audit_trail.csv"

mkdir -p trace/audit_logs

# Create CSV header if doesn't exist
if [ ! -f "$AUDIT_CSV" ]; then
  echo "timestamp,user,action,target,status,checksum,notes" > "$AUDIT_CSV"
fi

# Append to CSV
R2_VALUE=$(python -c "import json; data=json.load(open('$RUN_DIR/results.json')); print(data.get('metrics', {}).get('r2', data.get('aggregated_metrics', {}).get('mean_r2_test', 'N/A')))" 2>/dev/null || echo "N/A")

echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ"),$USER,run_validation,$DATA_FILE,complete,sha256:$RESULTS_CHECKSUM,$METHOD R²=$R2_VALUE" >> "$AUDIT_CSV"

# Append to daily log
cat >> "$AUDIT_LOG" <<EOF
[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] VALIDATION RUN
  Run ID: $RUN_ID
  User: $USER
  Method: $METHOD
  Data: $DATA_FILE (checksum: $INPUT_CHECKSUM)
  Results: $RESULTS_CHECKSUM
  R²: $R2_VALUE
  Status: COMPLETE
  Location: $RUN_DIR/

EOF

echo "  ✓ Audit trail updated"

# ===== Summary =====
echo "[7/7] Generating summary..."
echo ""
echo "=========================================="
echo "VALIDATION RUN COMPLETE"
echo "=========================================="
echo "Run ID: $RUN_ID"
echo "Location: $RUN_DIR/"
echo ""
echo "Files created:"
echo "  - input_snapshot.csv    (Original data)"
echo "  - results.json          (Full results)"
echo "  - stdout.log            (Console output)"
echo "  - metadata.json         (Environment info)"
echo "  - signature.txt         (For manual approval)"
echo "  - checksums.txt         (SHA-256 hashes)"
echo ""
echo "Next steps:"
echo "  1. Review results: cat $RUN_DIR/results.json"
echo "  2. Sign validation: nano $RUN_DIR/signature.txt"
echo "  3. Commit to Git: git add trace/ && git commit -m 'Validation: $RUN_ID'"
echo ""
echo "Audit trail: $AUDIT_CSV"
echo "=========================================="
