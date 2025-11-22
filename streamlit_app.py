import streamlit as st
import requests
import pandas as pd

BASE_URL = st.secrets.get("backend_url", "http://localhost:8000")

st.title("Expense Reconciliation Dashboard")

# Participants
st.header("Participants")
name = st.text_input("New participant name")
if st.button("Add Participant"):
    r = requests.post(f"{BASE_URL}/participants", json={"name": name})
    st.success(f"Added: {r.json()['name']}" if r.status_code == 200 else f"Error: {r.text}")

participants = requests.get(f"{BASE_URL}/participants").json()
part_df = pd.DataFrame(participants)
st.dataframe(part_df)

# Categories
st.header("Categories")
label = st.text_input("New category label")
if st.button("Add Category"):
    r = requests.post(f"{BASE_URL}/categories", json={"label": label})
    st.success(f"Added: {r.json()['label']}" if r.status_code == 200 else f"Error: {r.text}")

categories = requests.get(f"{BASE_URL}/categories").json()
cat_df = pd.DataFrame(categories)
st.dataframe(cat_df)

# Add Transaction
st.header("Add Transaction")
if participants and categories:
    selected_category = st.selectbox("Category", options=categories, format_func=lambda c: c['label'])
    selected_payer = st.selectbox("Payer", options=participants, format_func=lambda p: p['name'])
    total_amount = st.number_input("Total Amount", min_value=0.0)

    left_participants = st.multiselect("Who should pay (Left side)", options=participants, format_func=lambda p: p['name'])
    left_shares = []
    for p in left_participants:
        amt = st.number_input(f"{p['name']}'s share", min_value=0.0, key=f"share_{p['id']}")
        left_shares.append({"participant_id": p['id'], "owed_amount": amt})

    if st.button("Submit Transaction"):
        tx_data = {
            "category_id": selected_category["id"],
            "description": f"{selected_category['label']} expense",
            "total_amount": total_amount,
            "payer_id": selected_payer["id"],
            "left": left_shares
        }
        r = requests.post(f"{BASE_URL}/transactions", json=tx_data)
        if r.status_code == 200:
            st.success("Transaction submitted")
        else:
            st.error(f"Error: {r.text}")

# View Settlement
st.header("Final Settlement")
if st.button("Compute Settlement"):
    r = requests.get(f"{BASE_URL}/settlement")
    if r.status_code == 200:
        data = r.json()
        st.subheader("Net Balances")
        st.json(data["net"])
        st.subheader("Settlements")
        st.json(data["settlements"])
    else:
        st.error(f"Error: {r.text}")
