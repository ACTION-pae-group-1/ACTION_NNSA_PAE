"""Create and upload evaluation dataset to Phoenix.

No model is called here. The upload goes only to a loopback Phoenix server
(PHOENIX_ENDPOINT, default http://localhost:6006); any other host is refused.

Usage:
    python create_dataset.py --dataset-name pars-eval-1
    python create_dataset.py --list
    python create_dataset.py --dataset-name pars-eval-1 --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
import yaml

EVAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EVAL_DIR))

from tracing import is_loopback, phoenix_base_url  # noqa: E402


def load_dataset_config():
    """Load dataset configuration from datasets.yaml."""
    config_path = EVAL_DIR / "datasets.yaml"
    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config.get("datasets", {})


def _import_phoenix_client():
    from phoenix.client import Client

    return Client


def list_datasets():
    """List all available datasets."""
    datasets = load_dataset_config()
    print("\nAvailable datasets:")
    for name, config in datasets.items():
        print(f"  {name}: {config.get('description', 'No description')}")
        print(f"    CSV: {config.get('csv_path')}")
        print()


def validate_dataset(csv_path, config):
    """Validate that CSV has required columns."""
    try:
        df = pd.read_csv(csv_path)
        input_keys = config.get("input_keys", [])
        output_keys = config.get("output_keys", [])
        required_keys = set(input_keys + output_keys)
        missing = required_keys - set(df.columns)

        if missing:
            print(f"ERROR: Missing columns in {csv_path}: {missing}")
            return False

        print(f"CSV validation passed: {len(df)} rows, {len(df.columns)} columns")
        print(f"  Columns: {list(df.columns)}")
        return True
    except Exception as e:
        print(f"ERROR reading CSV: {e}")
        return False


def upload_dataset(
    dataset_name,
    csv_path,
    config=None,
    phoenix_name=None,
    dry_run=False,
    client_factory=None,
):
    """Upload dataset to a loopback Phoenix server. Returns True on success."""
    config = config or {}
    df = pd.read_csv(csv_path)
    if dry_run:
        print(f"\n[DRY RUN] Would upload dataset from {csv_path}")
        print(f"  Rows: {len(df)}")
        print(f"  Columns: {list(df.columns)}")
        return True

    endpoint = phoenix_base_url()
    if not is_loopback(endpoint):
        print(f"REFUSED: Phoenix endpoint {endpoint} is not a loopback address.")
        return False

    if client_factory is None:
        try:
            client_factory = _import_phoenix_client()
        except Exception as e:  # arize-phoenix can raise more than ImportError
            print(f"Phoenix client unavailable ({type(e).__name__}: {e}).")
            print("Use --dry-run to validate the CSV only.")
            return False

    try:
        client = client_factory(base_url=endpoint)
        dataset_name_phoenix = phoenix_name or dataset_name
        print(f"\nUploading dataset '{dataset_name_phoenix}' from {csv_path}...")
        dataset = client.datasets.create_dataset(
            name=dataset_name_phoenix,
            dataframe=df,
            input_keys=config.get("input_keys", []),
            output_keys=config.get("output_keys", []),
            dataset_description=config.get("description"),
        )
        print(f"Dataset created successfully: {getattr(dataset, 'id', dataset)}")
        return True
    except Exception as e:
        print(f"ERROR uploading dataset: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Create and upload evaluation datasets to Phoenix"
    )
    parser.add_argument("--list", action="store_true", help="List available datasets")
    parser.add_argument("--dataset-name", help="Dataset to upload (e.g., pars-eval-0)")
    parser.add_argument(
        "--phoenix-name", help="Name for dataset in Phoenix (defaults to dataset-name)"
    )
    parser.add_argument("--csv-path", help="Override CSV path")
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate CSV without uploading"
    )

    args = parser.parse_args()

    if args.list:
        list_datasets()
        return

    if not args.dataset_name:
        parser.print_help()
        return

    # Load dataset config
    datasets = load_dataset_config()
    if args.dataset_name not in datasets:
        print(f"ERROR: Unknown dataset '{args.dataset_name}'")
        list_datasets()
        return

    config = datasets[args.dataset_name]
    csv_path = args.csv_path or config.get("csv_path")

    if not csv_path:
        print("ERROR: No CSV path specified")
        return

    # Make path relative to script directory
    csv_path = Path(csv_path)
    if not csv_path.is_absolute():
        csv_path = EVAL_DIR / csv_path

    if not csv_path.exists():
        print(f"ERROR: CSV file not found: {csv_path}")
        return

    # Validate CSV
    if not validate_dataset(csv_path, config):
        return

    # Upload or dry-run
    upload_dataset(
        args.dataset_name,
        csv_path,
        config=config,
        phoenix_name=args.phoenix_name,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
