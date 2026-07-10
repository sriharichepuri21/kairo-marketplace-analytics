"""
Quick sanity check: generate 5 customers and print them.

Run: python scripts/test_customer_generator.py
"""

from generator.entities.customer import generate_customers


def main() -> None:
    customers = generate_customers(n=5, seed=42)

    print(f"Generated {len(customers)} customers:\n")

    for i, customer in enumerate(customers, start=1):
        print(f"--- Customer {i} ---")
        print(f"  ID:        {customer.customer_external_id}")
        print(f"  Name:      {customer.first_name} {customer.last_name}")
        print(f"  Email:     {customer.email}")
        print(f"  Region:    {customer.region.value} ({customer.country_code})")
        print(f"  Segment:   {customer.segment.value}")
        print(f"  Signed up: {customer.signup_date}")
        print(f"  Channel:   {customer.signup_channel}")
        print()


if __name__ == "__main__":
    main()