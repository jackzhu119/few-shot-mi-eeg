"""Start/resume the fixed four-arm external replication using the existing CPU env."""
import os
from pathlib import Path
import sys

for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[name] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiments.external_validation_20261027.runner import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
