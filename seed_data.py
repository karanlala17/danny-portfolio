"""One-time seed script to populate the database from CSV and config."""

import csv
import os

from config import INDICES
from db import init_db, upsert_index, add_to_watchlist, add_transaction, is_seeded


def seed_indices():
    """Seed the indices table from config."""
    for idx in INDICES:
        upsert_index(idx["ticker"], idx["display_name"], idx["sort_order"])
    print(f"Seeded {len(INDICES)} indices.")


def seed_transactions_from_csv(csv_path: str = "seed_transactions.csv"):
    """Seed transactions and watchlist from the CSV file."""
    if not os.path.exists(csv_path):
        print(f"CSV not found: {csv_path}")
        return

    count = 0
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            add_transaction(
                ticker=row["ticker"],
                display_name=row["display_name"],
                action=row["action"],
                txn_date=row["date"],
                quantity=float(row["quantity"]),
                price_per_share=float(row["price_per_share"]),
                currency=row["currency"],
                broker=row["broker"],
                exchange_rate_to_gbp=float(row["exchange_rate_to_gbp"]),
                notes="",
            )
            count += 1

    print(f"Seeded {count} transactions.")


def seed_all():
    """Initialize DB and seed all data."""
    init_db()
    if is_seeded():
        print("Database already seeded. Skipping.")
        return
    seed_indices()
    seed_transactions_from_csv()
    print("Seeding complete.")


if __name__ == "__main__":
    seed_all()
