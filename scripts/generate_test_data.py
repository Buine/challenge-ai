import json
import os
import random
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

BASE_DATE = datetime(2026, 2, 20, 10, 0, 0)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data")

FIRST_NAMES = [
    "Carlos", "Maria", "Juan", "Ana", "Pedro", "Luisa", "Diego", "Valentina",
    "Andres", "Camila", "Jorge", "Sofia", "Miguel", "Isabella", "Luis",
    "Gabriela", "Fernando", "Daniela", "Ricardo", "Natalia", "Alejandro",
    "Laura", "Sebastian", "Paula", "Javier", "Angela", "Oscar", "Carolina",
    "Manuel", "Mariana", "Roberto", "Adriana", "Eduardo", "Monica", "Raul",
    "Elena", "Francisco", "Paola", "Gustavo", "Andrea",
]
LAST_NAMES = [
    "Garcia", "Rodriguez", "Martinez", "Lopez", "Hernandez", "Gonzalez",
    "Perez", "Sanchez", "Ramirez", "Torres", "Flores", "Rivera", "Gomez",
    "Diaz", "Reyes", "Morales", "Cruz", "Ortiz", "Gutierrez", "Chavez",
    "Romero", "Vargas", "Castillo", "Mendoza", "Ruiz", "Alvarez", "Jimenez",
    "Moreno", "Rojas", "Silva",
]

random.seed(42)

oxxo_counter = 0
efy_counter = 0


def next_oxxo_id():
    global oxxo_counter
    oxxo_counter += 1
    return f"TXN-OXXO-{oxxo_counter:03d}"


def next_efy_id():
    global efy_counter
    efy_counter += 1
    return f"TXN-EFY-{efy_counter:03d}"


def random_customer_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def random_oxxo_amount():
    return Decimal(str(random.randint(50, 5000)))


def random_efecty_amount():
    return Decimal(str(random.randint(100, 5000) * 100))


def random_oxxo_store():
    return f"OXXO-STORE-{random.randint(1, 50):03d}"


def random_efecty_store():
    return f"EFECTY-STORE-{random.randint(1, 30):03d}"


def pick_method():
    return "OXXO" if random.random() < 0.60 else "EFECTY"


def gen_amount(method):
    return random_oxxo_amount() if method == "OXXO" else random_efecty_amount()


def gen_currency(method):
    return "MXN" if method == "OXXO" else "COP"


def gen_store(method):
    return random_oxxo_store() if method == "OXXO" else random_efecty_store()


def gen_txn_id(method):
    return next_oxxo_id() if method == "OXXO" else next_efy_id()


def expiry_hours(method):
    return 48 if method == "OXXO" else 72


def dt_str(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def decimal_str(d):
    return str(d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


vouchers = []
payments = []
settlements = []


def make_voucher(txn_id, amount, currency, method, status, created_at, expires_at, store_id):
    return {
        "transaction_id": txn_id,
        "amount": decimal_str(amount),
        "currency": currency,
        "payment_method": method,
        "status": status,
        "source_system": "voucher_system",
        "created_at": dt_str(created_at),
        "expires_at": dt_str(expires_at),
        "customer_name": random_customer_name(),
        "store_id": store_id,
    }


def make_payment(txn_id, amount, currency, method, status, paid_at, store_id):
    return {
        "transaction_id": txn_id,
        "amount": decimal_str(amount),
        "currency": currency,
        "payment_method": method,
        "status": status,
        "source_system": "payment_processor",
        "paid_at": dt_str(paid_at),
        "store_id": store_id,
    }


def make_settlement(txn_id, amount, currency, status, settled_at):
    return {
        "transaction_id": txn_id,
        "amount": decimal_str(amount),
        "currency": currency,
        "status": status,
        "source_system": "bank_settlement",
        "settled_at": dt_str(settled_at),
    }


def generate_full_lifecycle(count):
    for i in range(count):
        method = pick_method()
        txn_id = gen_txn_id(method)
        amount = gen_amount(method)
        currency = gen_currency(method)
        store_id = gen_store(method)

        created_offset_hours = random.uniform(0, 72)
        created_at = BASE_DATE - timedelta(hours=created_offset_hours)
        exp_at = created_at + timedelta(hours=expiry_hours(method))

        payment_delay_hours = random.uniform(1, 24)
        paid_at = created_at + timedelta(hours=payment_delay_hours)

        settlement_delay_days = random.uniform(1, 3)
        settled_at = paid_at + timedelta(days=settlement_delay_days)

        is_weekend_case = i < 5
        if is_weekend_case:
            friday = datetime(2026, 2, 13, 14, 0, 0) + timedelta(hours=random.uniform(0, 4))
            created_at = friday
            exp_at = created_at + timedelta(hours=expiry_hours(method))
            monday_paid = datetime(2026, 2, 16, 9, 0, 0) + timedelta(hours=random.uniform(0, 8))
            if monday_paid >= exp_at:
                paid_at = exp_at - timedelta(hours=random.uniform(1, 4))
            else:
                paid_at = monday_paid
            settled_at = paid_at + timedelta(days=random.uniform(1, 3))

        vouchers.append(make_voucher(txn_id, amount, currency, method, "PAID", created_at, exp_at, store_id))
        payments.append(make_payment(txn_id, amount, currency, method, "CONFIRMED", paid_at, store_id))
        settlements.append(make_settlement(txn_id, amount, currency, "COMPLETED", settled_at))


def generate_expired(count):
    for _ in range(count):
        method = pick_method()
        txn_id = gen_txn_id(method)
        amount = gen_amount(method)
        currency = gen_currency(method)
        store_id = gen_store(method)

        created_at = BASE_DATE - timedelta(hours=random.uniform(96, 240))
        exp_at = created_at + timedelta(hours=expiry_hours(method))

        vouchers.append(make_voucher(txn_id, amount, currency, method, "EXPIRED", created_at, exp_at, store_id))


def generate_cancelled(count):
    for _ in range(count):
        method = pick_method()
        txn_id = gen_txn_id(method)
        amount = gen_amount(method)
        currency = gen_currency(method)
        store_id = gen_store(method)

        created_at = BASE_DATE - timedelta(hours=random.uniform(24, 120))
        exp_at = created_at + timedelta(hours=expiry_hours(method))

        vouchers.append(make_voucher(txn_id, amount, currency, method, "CANCELLED", created_at, exp_at, store_id))


def generate_in_progress(count):
    for _ in range(count):
        method = pick_method()
        txn_id = gen_txn_id(method)
        amount = gen_amount(method)
        currency = gen_currency(method)
        store_id = gen_store(method)

        created_at = BASE_DATE - timedelta(hours=random.uniform(1, 24))
        exp_at = created_at + timedelta(hours=expiry_hours(method))

        vouchers.append(make_voucher(txn_id, amount, currency, method, "PENDING", created_at, exp_at, store_id))


def generate_orphaned(count):
    for _ in range(count):
        method = pick_method()
        txn_id = gen_txn_id(method)
        amount = gen_amount(method)
        currency = gen_currency(method)
        store_id = gen_store(method)

        paid_at = BASE_DATE - timedelta(hours=random.uniform(1, 48))

        payments.append(make_payment(txn_id, amount, currency, method, "CONFIRMED", paid_at, store_id))


def generate_stuck_pending(count):
    medium_count = count // 2
    high_count = count - medium_count

    for _ in range(medium_count):
        method = pick_method()
        txn_id = gen_txn_id(method)
        amount = gen_amount(method)
        currency = gen_currency(method)
        store_id = gen_store(method)

        age_hours = random.uniform(73, 120)
        created_at = BASE_DATE - timedelta(hours=age_hours)
        exp_at = created_at + timedelta(hours=expiry_hours(method))

        vouchers.append(make_voucher(txn_id, amount, currency, method, "PENDING", created_at, exp_at, store_id))

    near_boundary_done = False
    for _ in range(high_count):
        method = pick_method()
        txn_id = gen_txn_id(method)
        amount = gen_amount(method)
        currency = gen_currency(method)
        store_id = gen_store(method)

        if not near_boundary_done:
            age_hours = 72 + (1 / 3600)
            near_boundary_done = True
        else:
            age_hours = random.uniform(121, 200)

        created_at = BASE_DATE - timedelta(hours=age_hours)
        exp_at = created_at + timedelta(hours=expiry_hours(method))

        vouchers.append(make_voucher(txn_id, amount, currency, method, "PENDING", created_at, exp_at, store_id))


def generate_amount_mismatch(count):
    mismatch_specs = [
        {"pct": Decimal("0.02"), "label": "2%"},
        {"pct": Decimal("0.02"), "label": "2%"},
        {"pct": Decimal("0.07"), "label": "7%"},
        {"pct": Decimal("0.07"), "label": "7%"},
        {"pct": Decimal("0.07"), "label": "7%"},
        {"pct": Decimal("0.15"), "label": "15%"},
        {"pct": Decimal("0.15"), "label": "15%"},
        {"pct": Decimal("0.0101"), "label": "1.01%"},
        {"pct": Decimal("0.0101"), "label": "1.01%"},
        {"pct": None, "label": "currency_mismatch"},
    ]

    for spec in mismatch_specs[:count]:
        method = pick_method()
        txn_id = gen_txn_id(method)
        amount = gen_amount(method)
        currency = gen_currency(method)
        store_id = gen_store(method)

        created_at = BASE_DATE - timedelta(hours=random.uniform(24, 72))
        exp_at = created_at + timedelta(hours=expiry_hours(method))
        paid_at = created_at + timedelta(hours=random.uniform(1, 24))

        if spec["pct"] is None:
            voucher_currency = "MXN"
            payment_currency = "COP"
            method = "OXXO"
            txn_id_override = txn_id
            payment_amount = amount
        else:
            voucher_currency = currency
            payment_currency = currency
            direction = random.choice([1, -1])
            diff = (amount * spec["pct"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            payment_amount = amount + (diff * direction)
            txn_id_override = txn_id

        vouchers.append(make_voucher(txn_id_override, amount, voucher_currency, method, "PAID", created_at, exp_at, store_id))
        payments.append(make_payment(txn_id_override, payment_amount, payment_currency, method, "CONFIRMED", paid_at, store_id))


def generate_zombie(count):
    for _ in range(count):
        method = pick_method()
        txn_id = gen_txn_id(method)
        amount = gen_amount(method)
        currency = gen_currency(method)
        store_id = gen_store(method)

        created_at = BASE_DATE - timedelta(hours=random.uniform(48, 120))
        exp_at = created_at + timedelta(hours=expiry_hours(method))
        settled_at = created_at + timedelta(days=random.uniform(2, 5))

        vouchers.append(make_voucher(txn_id, amount, currency, method, "PAID", created_at, exp_at, store_id))
        settlements.append(make_settlement(txn_id, amount, currency, "COMPLETED", settled_at))


def generate_post_expiration(count):
    delay_specs = [
        timedelta(minutes=1),
        timedelta(minutes=1),
        timedelta(hours=1),
        timedelta(hours=1),
        timedelta(days=1),
        timedelta(days=1),
    ]

    for delay in delay_specs[:count]:
        method = pick_method()
        txn_id = gen_txn_id(method)
        amount = gen_amount(method)
        currency = gen_currency(method)
        store_id = gen_store(method)

        created_at = BASE_DATE - timedelta(hours=random.uniform(72, 120))
        exp_at = created_at + timedelta(hours=expiry_hours(method))
        paid_at = exp_at + delay

        vouchers.append(make_voucher(txn_id, amount, currency, method, "PAID", created_at, exp_at, store_id))
        payments.append(make_payment(txn_id, amount, currency, method, "CONFIRMED", paid_at, store_id))


def generate_same_day_settlements(count):
    for _ in range(count):
        method = pick_method()
        txn_id = gen_txn_id(method)
        amount = gen_amount(method)
        currency = gen_currency(method)
        store_id = gen_store(method)

        created_at = BASE_DATE - timedelta(hours=random.uniform(24, 48))
        exp_at = created_at + timedelta(hours=expiry_hours(method))
        paid_at = created_at + timedelta(hours=random.uniform(1, 6))
        settled_at = paid_at + timedelta(hours=random.uniform(2, 10))

        vouchers.append(make_voucher(txn_id, amount, currency, method, "PAID", created_at, exp_at, store_id))
        payments.append(make_payment(txn_id, amount, currency, method, "CONFIRMED", paid_at, store_id))
        settlements.append(make_settlement(txn_id, amount, currency, "COMPLETED", settled_at))


def main():
    generate_full_lifecycle(175)
    generate_same_day_settlements(5)
    generate_expired(40)
    generate_cancelled(30)
    generate_in_progress(20)

    generate_orphaned(8)
    generate_stuck_pending(10)
    generate_amount_mismatch(10)
    generate_zombie(6)
    generate_post_expiration(6)

    os.makedirs(DATA_DIR, exist_ok=True)

    with open(os.path.join(DATA_DIR, "vouchers.json"), "w") as f:
        json.dump(vouchers, f, indent=2)

    with open(os.path.join(DATA_DIR, "payments.json"), "w") as f:
        json.dump(payments, f, indent=2)

    with open(os.path.join(DATA_DIR, "settlements.json"), "w") as f:
        json.dump(settlements, f, indent=2)

    total_txn_ids = set()
    for v in vouchers:
        total_txn_ids.add(v["transaction_id"])
    for p in payments:
        total_txn_ids.add(p["transaction_id"])
    for s in settlements:
        total_txn_ids.add(s["transaction_id"])

    print(f"Generated {len(total_txn_ids)} unique transactions")
    print(f"  Vouchers:    {len(vouchers)}")
    print(f"  Payments:    {len(payments)}")
    print(f"  Settlements: {len(settlements)}")

    oxxo_count = sum(1 for v in vouchers if v["payment_method"] == "OXXO")
    efecty_count = sum(1 for v in vouchers if v["payment_method"] == "EFECTY")
    total_vouchers = len(vouchers)
    print(f"\n  OXXO:   {oxxo_count} ({100 * oxxo_count / total_vouchers:.1f}%)")
    print(f"  Efecty: {efecty_count} ({100 * efecty_count / total_vouchers:.1f}%)")

    print(f"\nFiles written to {DATA_DIR}/")
    print("  - vouchers.json")
    print("  - payments.json")
    print("  - settlements.json")


if __name__ == "__main__":
    main()
