import streamlit as st
import requests
import pandas as pd
import time

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Agri-Flow Dashboard", page_icon="🌱", layout="wide")

# Static Header (Always visible)
st.title("🌱 Agri-Flow Live Warehouse Agent")
st.markdown("### Real-time WhatsApp Inventory Management")

# --- 2. SIDEBAR ---
st.sidebar.header("Settings")
refresh_rate = st.sidebar.slider("Refresh Rate (seconds)", 2, 30, 5)
if st.sidebar.button("Force Refresh Now"):
    st.rerun()


# --- 3. DATA FETCHING FUNCTION ---
def fetch_data():
    try:
        inv_res = requests.get("http://localhost:8000/inventory", timeout=2)
        log_res = requests.get("http://localhost:8000/logs?limit=5", timeout=2)
        if inv_res.status_code == 200 and log_res.status_code == 200:
            return inv_res.json(), log_res.json()
    except Exception as e:
        st.error(f"Connection Error: {e}")
    return None, None


# --- 4. DISPLAY LOGIC ---
# Create empty slots so we can update them inside the loop
metric_slot = st.empty()
st.divider()
col_left, col_right = st.columns([2, 1])
table_slot = col_left.empty()
log_slot = col_right.empty()

# --- 5. THE LIVE LOOP ---
# This loop now lives at the end of the script
while True:
    inventory, logs = fetch_data()

    if inventory is not None:
        # Update Metric Cards
        with metric_slot.container():
            if inventory:
                cols = st.columns(len(inventory))
                for i, item in enumerate(inventory):
                    with cols[i]:
                        st.metric(
                            label=item['name'].upper(),
                            value=f"{item['quantity']} {item['unit']}"
                        )
            else:
                st.info("Inventory is empty. Send a WhatsApp message!")

        # Update Table
        with table_slot.container():
            st.subheader("📦 Inventory Levels")
            if inventory:
                df = pd.DataFrame(inventory)[['name', 'quantity', 'unit']]
                st.table(df)

        # Update Logs
        with log_slot.container():
            st.subheader("🕒 Recent Activity")
            if logs:
                for log in logs:
                    st.write(f"**{log['timestamp'][11:16]}**: {log['original_transcript']}")
                    st.caption(f"From: {log['from_number']}")
                    st.divider()

    # Wait before next update
    time.sleep(refresh_rate)