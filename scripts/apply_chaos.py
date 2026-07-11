"""
Apply the chaos engine to all generated data.

This script:
1. Backs up clean data to raw_data_clean/
2. Injects realistic production data quality issues
3. Logs every change to chaos_manifest/

Usage:
    python scripts/apply_chaos.py

To regenerate clean data and re-apply chaos:
    python scripts/generate_customers.py
    python scripts/generate_sellers.py
    python scripts/generate_products.py
    python scripts/generate_orders.py
    python scripts/generate_payments.py
    python scripts/generate_fulfillment.py
    python scripts/apply_chaos.py
"""

from generator.chaos.config import ChaosConfig
from generator.chaos.engine import run_chaos_engine


def main() -> None:
    # Use default config — all chaos types enabled
    # Tune rates here if you want more or less chaos
    config = ChaosConfig(
        seed=42,
        # Uncomment and modify to tune:
        # duplicates=DuplicateConfig(rate=0.05),    # more dupes
        # null_chaos=NullChaosConfig(rate=0.10),     # more nulls
        # type_drift=TypeDriftConfig(rate=0.08),     # more type mess
    )

    run_chaos_engine(config)


if __name__ == "__main__":
    main()