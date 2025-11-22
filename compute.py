from typing import List, Dict, Tuple
from decimal import Decimal, ROUND_HALF_UP

def to_dec(x) -> Decimal:
    if isinstance(x, Decimal):
        return x
    return Decimal(str(x))

def round2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def compute_shares(total_amount: Decimal, left_rows: List[dict], group_member_ids: List[int]) -> Dict[int, Decimal]:
    """
    left_rows: list of {participant_id:int, owed_amount: Decimal or None}
    If left_rows is empty -> split equally across group_member_ids
    If left_rows provided and owed_amount present -> use owed_amount values (must sum to total)
    If left_rows provided but no owed_amounts -> split equally among those left participants
    Returns: dict participant_id -> owed_amount (Decimal)
    """
    total_amount = to_dec(total_amount)
    if left_rows and len(left_rows) > 0:
        # If explicit owed_amount present in any row -> prefer explicit amounts
        if any(r.get("owed_amount") is not None for r in left_rows):
            shares = {}
            ssum = Decimal("0")
            for r in left_rows:
                amt = r.get("owed_amount")
                if amt is None:
                    raise ValueError("Some left rows have no owed_amount while others do - inconsistent.")
                a = to_dec(amt)
                shares[int(r["participant_id"]) ] = round2(a)
                ssum += round2(a)
            if round2(ssum) != round2(total_amount):
                # small rounding differences allowed; but ensure close
                if abs(round2(ssum) - round2(total_amount)) > Decimal("0.05"):
                    raise ValueError(f"Sum of left owed amounts ({ssum}) != total ({total_amount}).")
            return shares
        else:
            # equal split among left_rows
            n = len(left_rows)
            per = round2(total_amount / n)
            shares = {int(r["participant_id"]): per for r in left_rows}
            # adjust last to match total (fix rounding)
            pid_last = int(left_rows[-1]["participant_id"])
            sum_shares = sum(shares.values())
            diff = round2(total_amount - sum_shares)
            shares[pid_last] = round2(shares[pid_last] + diff)
            return shares
    else:
        # Left is NULL -> split equally among all group members
        n = len(group_member_ids)
        if n == 0:
            raise ValueError("No group members to split among.")
        per = round2(total_amount / n)
        shares = {int(uid): per for uid in group_member_ids}
        pid_last = int(group_member_ids[-1])
        sum_shares = sum(shares.values())
        diff = round2(total_amount - sum_shares)
        shares[pid_last] = round2(shares[pid_last] + diff)
        return shares

def compute_group_balance(transactions: List[dict], group_member_ids: List[int]) -> Dict[int, Decimal]:
    """
    transactions: list of dicts:
      {
        "id": int,
        "total_amount": Decimal,
        "left_rows": [ {participant_id, owed_amount (opt)}... ] or [],
        "payments": [ {payer_id, amount} ... ]  # can include multiple payers
      }
    returns net: participant_id -> net (positive means they are owed money; negative means they owe)
    """
    net = {int(uid): Decimal("0.00") for uid in group_member_ids}
    for tx in transactions:
        total = to_dec(tx["total_amount"])
        left_rows = tx.get("left_rows") or []
        payments = tx.get("payments") or []
        shares = compute_shares(total, left_rows, group_member_ids)
        # each left participant owes their share
        for uid, owed in shares.items():
            net[uid] -= owed
        # apply payments
        if payments:
            for p in payments:
                pid = int(p["payer_id"])
                amt = to_dec(p["amount"])
                net[pid] += round2(amt)
        else:
            pid = tx.get("payer_id")
            if pid is not None:
                net[int(pid)] += total
            else:
                raise ValueError("Transaction has no payments and no payer_id.")
    # round nets
    for k in net:
        net[k] = round2(net[k])
    return net

def settle(net: Dict[int, Decimal]) -> List[Tuple[int, int, Decimal]]:
    """
    Given net map (user->net), produce a list of settlements (debtor_id, creditor_id, amount)
    using greedy algorithm.
    """
    creditors = []
    debtors = []
    for u, amt in net.items():
        if amt > 0:
            creditors.append([u, amt])  # mutable amt
        elif amt < 0:
            debtors.append([u, -amt])   # store positive owed amount

    # sort: largest creditors first, largest debtors first
    creditors.sort(key=lambda x: x[1], reverse=True)
    debtors.sort(key=lambda x: x[1], reverse=True)

    i = j = 0
    settlements = []
    while i < len(creditors) and j < len(debtors):
        c_uid, c_amt = creditors[i]
        d_uid, d_amt = debtors[j]
        transfer = min(c_amt, d_amt)
        transfer = round2(transfer)
        if transfer > Decimal("0"):
            settlements.append((d_uid, c_uid, transfer))  # debtor pays creditor
            creditors[i][1] = round2(c_amt - transfer)
            debtors[j][1] = round2(d_amt - transfer)
        if creditors[i][1] == 0:
            i += 1
        if debtors[j][1] == 0:
            j += 1
    return settlements
