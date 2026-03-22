import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import time
import os

st.set_page_config(
    page_title="Traffic Management System",
    page_icon="🚦",
    layout="wide"
)

DB_PATH = "logs/traffic.db"

# ── Database helpers ──────────────────────────────────────
def get_traffic_log() -> pd.DataFrame:
    try:
        with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:  # ✅ context manager
            return pd.read_sql("SELECT * FROM traffic_log ORDER BY id DESC LIMIT 500", conn)
    except Exception as e:
        st.error(f"Database error (traffic_log): {e}")  # ✅ visible error
        return pd.DataFrame()

def get_challans() -> pd.DataFrame:
    try:
        with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
            return pd.read_sql("SELECT * FROM challans ORDER BY id DESC", conn)
    except Exception as e:
        st.error(f"Database error (challans): {e}")
        return pd.DataFrame()

def get_incidents() -> pd.DataFrame:
    try:
        with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
            return pd.read_sql("SELECT * FROM incidents ORDER BY id DESC LIMIT 50", conn)
    except Exception as e:
        st.error(f"Database error (incidents): {e}")
        return pd.DataFrame()

def get_summary() -> dict:
    try:
        with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*), SUM(total_fine) FROM challans")
            ch = c.fetchone()
            c.execute("SELECT COUNT(*) FROM incidents")
            inc = c.fetchone()
            c.execute("SELECT COUNT(*) FROM traffic_log")
            frames = c.fetchone()
        return {
            "total_challans":  ch[0] or 0,
            "total_fines":     ch[1] or 0,
            "total_incidents": inc[0] or 0,
            "total_frames":    frames[0] or 0
        }
    except Exception as e:
        st.error(f"Database error (summary): {e}")
        return {"total_challans": 0, "total_fines": 0,
                "total_incidents": 0, "total_frames": 0}

# ── Header ────────────────────────────────────────────────
st.title("🚦 Smart Traffic Management System")
st.markdown("Real-time traffic monitoring, signal control, and violation detection")
st.divider()

# ── Auto refresh toggle ───────────────────────────────────
col_r1, col_r2 = st.columns([3, 1])
with col_r2:
    auto_refresh = st.toggle("Auto Refresh", value=False)
    if auto_refresh:
        refresh_rate = st.slider("Refresh (sec)", 2, 30, 5)

# ── Top KPI Metrics ───────────────────────────────────────
summary = get_summary()
df_log  = get_traffic_log()

m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    avg_vehicles = int(df_log["vehicle_count"].mean()) if not df_log.empty else 0
    st.metric("🚗 Avg Vehicles/Frame", avg_vehicles)
with m2:
    st.metric("📋 Total Challans", summary["total_challans"])
with m3:
    st.metric("💰 Total Fines", f"Rs.{summary['total_fines']:,}")
with m4:
    st.metric("⚠️ Total Incidents", summary["total_incidents"])
with m5:
    st.metric("🎬 Frames Processed", f"{summary['total_frames']:,}")

st.divider()

# ── Row 1: Congestion + Vehicle Count Charts ──────────────
st.subheader("📊 Traffic Flow Analysis")
c1, c2 = st.columns(2)

with c1:
    if not df_log.empty:
        fig = px.line(
            df_log.iloc[::-1],
            x="frame_id", y="vehicle_count",
            title="Vehicle Count Over Time",
            color_discrete_sequence=["#00b4d8"]
        )
        fig.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                          font_color="white", height=300)
        st.plotly_chart(fig, width='stretch')  # ✅ fixed
    else:
        st.info("No traffic data yet — run main.py first")

with c2:
    if not df_log.empty and "congestion" in df_log.columns:
        level_counts = df_log["congestion"].value_counts().reset_index()
        level_counts.columns = ["level", "count"]
        colors = {"LOW": "#00c800", "MEDIUM": "#ffa500", "HIGH": "#ff3030"}
        fig = px.pie(
            level_counts, values="count", names="level",
            title="Congestion Level Distribution",
            color="level", color_discrete_map=colors
        )
        fig.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                          font_color="white", height=300)
        st.plotly_chart(fig, width='stretch')  # ✅ fixed
    else:
        st.info("No congestion data yet")

st.divider()

# ── Row 2: Density + Police Score ─────────────────────────
st.subheader("🔍 Detailed Metrics")
c3, c4 = st.columns(2)

with c3:
    if not df_log.empty and "density" in df_log.columns:
        fig = px.area(
            df_log.iloc[::-1], x="frame_id", y="density",
            title="Traffic Density Over Time",
            color_discrete_sequence=["#f77f00"]
        )
        fig.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                          font_color="white", height=300)
        st.plotly_chart(fig, width='stretch')  # ✅ fixed

with c4:
    if not df_log.empty and "police_score" in df_log.columns:
        fig = px.line(
            df_log.iloc[::-1], x="frame_id", y="police_score",
            title="Police Need Score Over Time",
            color_discrete_sequence=["#e63946"]
        )
        fig.add_hline(y=0.35, line_dash="dash", line_color="orange",
                      annotation_text="Alert Threshold")
        fig.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                          font_color="white", height=300)
        st.plotly_chart(fig, width='stretch')  # ✅ fixed

st.divider()

# ── Row 3: Signal Status ───────────────────────────────────
st.subheader("🚦 Signal Control Status")
required_signal_cols = {"green_dir", "green_dur", "congestion", "police_score"}
if not df_log.empty and required_signal_cols.issubset(df_log.columns):  # ✅ guard
    latest = df_log.iloc[0]
    s1, s2, s3 = st.columns(3)
    with s1:
        st.metric("Active Direction", latest["green_dir"])
    with s2:
        st.metric("Green Duration", f"{latest['green_dur']}s")
    with s3:
        congestion_color = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}
        level = latest["congestion"]
        st.metric("Current Congestion", f"{congestion_color.get(level,'⚪')} {level}")

    dir_counts = df_log["green_dir"].value_counts().reset_index()
    dir_counts.columns = ["direction", "count"]
    fig = px.bar(
        dir_counts, x="direction", y="count",
        title="Green Light Distribution by Direction",
        color="direction",
        color_discrete_sequence=["#2dc653","#f77f00","#00b4d8","#e63946"]
    )
    fig.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                      font_color="white", height=250)
    st.plotly_chart(fig, width='stretch')  # ✅ fixed
else:
    st.info("Signal data not available yet")

st.divider()

# ── Row 4: Challan Table ───────────────────────────────────
st.subheader("📋 Challan Records")
df_challans = get_challans()

if not df_challans.empty:
    ch1, ch2, ch3 = st.columns(3)
    with ch1:
        st.metric("Total Challans", len(df_challans))
    with ch2:
        st.metric("Total Amount", f"Rs.{df_challans['total_fine'].sum():,}")
    with ch3:
        pending = len(df_challans[df_challans["status"] == "PENDING"])
        st.metric("Pending", pending)

    search = st.text_input("🔍 Search by plate number")
    if search:
        df_challans = df_challans[
            df_challans["plate"].str.contains(search.upper(), na=False)
        ]

    st.dataframe(
        df_challans[["challan_id","plate","violations",
                     "total_fine","timestamp","status"]],
        width='stretch', height=300  # ✅ fixed
    )
else:
    st.info("No challans issued yet")

st.divider()

# ── Row 5: Incidents ───────────────────────────────────────
st.subheader("⚠️ Incident Log")
df_incidents = get_incidents()

if not df_incidents.empty:
    i1, i2 = st.columns(2)
    with i1:
        inc_counts = df_incidents["type"].value_counts().reset_index()
        inc_counts.columns = ["type", "count"]
        fig = px.bar(
            inc_counts, x="type", y="count",
            title="Incidents by Type", color="type",
            color_discrete_sequence=["#e63946","#f77f00","#00b4d8"]
        )
        fig.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
                          font_color="white", height=250)
        st.plotly_chart(fig, width='stretch')  # ✅ fixed
    with i2:
        st.dataframe(
            df_incidents[["type","severity","timestamp","resolved"]],
            width='stretch', height=250  # ✅ fixed
        )
else:
    st.info("No incidents recorded yet")

st.divider()

# ── Footer ─────────────────────────────────────────────────
st.markdown(
    "**Smart Traffic Management System** | "
    "Built with YOLOv8 + OpenCV + Streamlit"
)

# ── Auto refresh logic ─────────────────────────────────────
if auto_refresh:
    last = st.session_state.get("last_refresh", 0)
    if time.time() - last > refresh_rate:
        st.session_state["last_refresh"] = time.time()
        st.rerun()
    time.sleep(1)   # ✅ small sleep to avoid CPU spin, not blocking
    st.rerun()