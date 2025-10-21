# ALCOA++ Audit Trail - Ganglioside Analysis Algorithm Validation

## Purpose

This directory contains the complete audit trail for algorithm validation and development following **ALCOA++** principles:

- **A**ttributable - Who performed the action
- **L**egible - Data is readable and clear
- **C**ontemporaneous - Recorded at time of activity
- **O**riginal - First recording of data
- **A**ccurate - Data is correct and verified
- **+C**omplete - All data is present
- **+C**onsistent - Data matches across records
- **+E**nduring - Permanent, unalterable records
- **+A**vailable - Accessible for review/audit

---

## Directory Structure

```
trace/
├── README.md                           # This file
├── raw_data/                           # Original input data (immutable)
│   ├── testwork_user_20251021.csv     # Original dataset
│   └── data_checksums.txt             # SHA-256 hashes for integrity
│
├── validation_runs/                    # Each validation execution
│   ├── 20251021_143000_LOO/           # Leave-One-Out run
│   │   ├── input_snapshot.csv         # Copy of input data
│   │   ├── results.json               # Full results
│   │   ├── stdout.log                 # Console output
│   │   ├── metadata.json              # Timestamp, user, versions
│   │   └── signature.txt              # Digital signature
│   └── 20251021_143200_KFOLD/         # K-Fold run
│       └── ...
│
├── algorithm_versions/                 # Algorithm source code snapshots
│   ├── v1.0_baseline/                 # Original algorithm
│   │   ├── ganglioside_processor.py
│   │   ├── algorithm_validator.py
│   │   └── checksum.txt
│   ├── v1.1_tuned/                    # After auto-tuning
│   │   └── ...
│   └── changelog.md                   # Version history
│
├── audit_logs/                         # Timestamped activity log
│   ├── 2025-10-21.log                 # Daily log file
│   └── audit_trail.csv                # Structured audit trail
│
└── signatures/                         # Validation signatures
    ├── validation_approval.txt        # Final approval signature
    └── review_log.txt                 # Review history
```

---

## ALCOA++ Compliance Matrix

| Principle | Implementation | Location |
|-----------|----------------|----------|
| **Attributable** | User ID, timestamp in metadata.json | validation_runs/*/metadata.json |
| **Legible** | Human-readable JSON + CSV formats | All files |
| **Contemporaneous** | Auto-generated timestamps (ISO 8601) | metadata.json, audit_logs/ |
| **Original** | Immutable copies of input data | raw_data/ |
| **Accurate** | SHA-256 checksums, version control | checksums.txt |
| **+Complete** | Full stdout, stderr, inputs, outputs | validation_runs/*/ |
| **+Consistent** | Cross-references between runs | audit_trail.csv |
| **+Enduring** | Git version control, backups | .git/ |
| **+Available** | Clear structure, README documentation | This file |

---

## Validation Run Template

Each validation creates a timestamped directory with:

### 1. Input Snapshot (`input_snapshot.csv`)
Immutable copy of data used for this run.

### 2. Results (`results.json`)
```json
{
  "validation_id": "20251021_143000_LOO",
  "method": "Leave-One-Out",
  "timestamp": "2025-10-21T14:30:00Z",
  "metrics": {
    "r2": 0.8246,
    "rmse": 0.7448,
    ...
  },
  "predictions": [...],
  "summary": {...}
}
```

### 3. Metadata (`metadata.json`)
```json
{
  "run_id": "20251021_143000_LOO",
  "timestamp": "2025-10-21T14:30:00Z",
  "user": "seoljonghyeon",
  "hostname": "MacBook-Pro.local",
  "environment": {
    "python_version": "3.13.0",
    "pandas_version": "2.3.3",
    "scikit_learn_version": "1.7.2",
    "os": "macOS 15.0"
  },
  "input_file": "../data/samples/testwork_user.csv",
  "input_checksum": "sha256:abc123...",
  "algorithm_version": "v1.0_baseline",
  "command": "python validate_standalone.py --data ../data/samples/testwork_user.csv --method loo"
}
```

### 4. Console Output (`stdout.log`)
Complete terminal output for reproducibility.

### 5. Signature (`signature.txt`)
```
VALIDATION RUN SIGNATURE
========================
Run ID: 20251021_143000_LOO
Timestamp: 2025-10-21T14:30:00Z
Data Checksum: sha256:abc123...
Results Checksum: sha256:def456...
Reviewed by: [Name]
Approved: [Yes/No]
Date: [YYYY-MM-DD]
Signature: _________________
```

---

## Audit Trail Log Format

`audit_logs/audit_trail.csv`:

```csv
timestamp,user,action,target,status,checksum,notes
2025-10-21T14:00:00Z,seoljonghyeon,create_venv,.venv,success,n/a,Python 3.13 virtual environment
2025-10-21T14:10:00Z,seoljonghyeon,install_deps,requirements/validation.txt,success,sha256:abc,Installed pandas scikit-learn
2025-10-21T14:30:00Z,seoljonghyeon,run_validation,testwork_user.csv,complete,sha256:def,LOO R²=0.8246
2025-10-21T14:32:00Z,seoljonghyeon,run_validation,testwork_user.csv,complete,sha256:ghi,5-Fold R²=0.6619
```

---

## Usage Instructions

### Record New Validation Run

```bash
# Run validation with traceability
./validate_with_trace.sh --data ../data/samples/testwork_user.csv --method loo

# This automatically:
# 1. Creates timestamped directory
# 2. Copies input data
# 3. Runs validation
# 4. Saves all outputs
# 5. Generates checksums
# 6. Logs to audit trail
```

### Verify Data Integrity

```bash
# Check if data has been modified
cd trace/raw_data
sha256sum -c data_checksums.txt

# Check validation run integrity
cd trace/validation_runs/20251021_143000_LOO
sha256sum input_snapshot.csv results.json
```

### Review Audit Trail

```bash
# View all validation runs
ls -la trace/validation_runs/

# View audit log
cat trace/audit_logs/2025-10-21.log

# View structured audit trail
column -t -s, trace/audit_logs/audit_trail.csv
```

### Manual Validation Signature

```bash
# After reviewing results
cd trace/validation_runs/20251021_143000_LOO
nano signature.txt  # Add your signature and approval
```

---

## Data Retention Policy

- **Raw data**: Permanent retention
- **Validation runs**: Minimum 2 years
- **Audit logs**: Minimum 5 years
- **Algorithm versions**: Permanent retention

---

## Compliance Checklist

Before approving a validation run:

- [ ] Input data snapshot saved in validation_runs/
- [ ] Original data preserved in raw_data/
- [ ] SHA-256 checksums calculated and verified
- [ ] metadata.json contains complete environment info
- [ ] results.json contains all predictions and metrics
- [ ] stdout.log captured completely
- [ ] Audit trail updated in audit_logs/
- [ ] Algorithm version documented in algorithm_versions/
- [ ] Signature obtained from reviewer
- [ ] Results match expected format
- [ ] No data modifications detected

---

## Git Integration

This directory is tracked in Git for additional ALCOA++ compliance:

```bash
# Each validation should be committed
git add trace/
git commit -m "Validation run: LOO R²=0.8246 (2025-10-21)"

# Git provides:
# - Enduring: Permanent history
# - Attributable: Commit author
# - Contemporaneous: Commit timestamp
# - Available: Git log
```

---

## Contact

**Data Integrity Officer**: seoljonghyeon
**Project**: Ganglioside LC-MS/MS Analysis
**Repository**: Automated-LC-MS-MS-analaysis_ver2
**Last Updated**: 2025-10-21

---

**IMPORTANT**: Do not modify files in `raw_data/` or existing `validation_runs/`. Always create new timestamped directories for new validations.
