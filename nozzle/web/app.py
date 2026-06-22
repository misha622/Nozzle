"""Nozzle Dashboard — Streamlit web interface."""

import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timedelta

st.set_page_config(
    page_title="Nozzle Dashboard",
    page_icon="🔇",
    layout="wide",
)

API_URL = "http://localhost:8000/api/v1"

st.title("🔇 Nozzle Dashboard")
st.caption("ML-powered alert deduplication for SIEM systems")

# Sidebar
st.sidebar.header("⚙️ Actions")

if st.sidebar.button("🔄 Run Clustering", use_container_width=True):
    with st.spinner("Running clustering..."):
        try:
            resp = requests.post(f"{API_URL}/clusters/run")
            data = resp.json()
            st.sidebar.success(f"Created {data['clusters_created']} clusters, {data['alerts_clustered']} alerts clustered")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Failed: {e}")

st.sidebar.divider()

# Refresh
if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
    st.rerun()

# Tabs
tab1, tab2, tab3 = st.tabs(["📊 Clusters", "🚨 Alerts", "📈 Stats"])

# ============================================
# Tab 1: Clusters
# ============================================
with tab1:
    st.header("Alert Clusters")

    try:
        resp = requests.get(f"{API_URL}/clusters/")
        clusters = resp.json()

        if not clusters:
            st.info("No clusters yet. Run clustering to group alerts.")
        else:
            # Metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Clusters", len(clusters))
            with col2:
                total_clustered = sum(c["alert_count"] for c in clusters)
                st.metric("Alerts Clustered", total_clustered)
            with col3:
                avg_size = total_clustered // len(clusters) if clusters else 0
                st.metric("Avg Cluster Size", avg_size)

            # Bar chart
            df = pd.DataFrame(clusters)
            fig = px.bar(
                df.nlargest(15, "alert_count"),
                x="name",
                y="alert_count",
                color="strategy",
                title="Top Clusters by Alert Count",
                labels={"name": "Cluster", "alert_count": "Alerts"},
            )
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)

            # Cluster table
            st.subheader("All Clusters")
            for c in clusters:
                with st.expander(f"🔹 {c['name']} ({c['alert_count']} alerts, {c['confidence']:.0%} confidence)"):
                    st.write(f"**Strategy:** {c['strategy']}")
                    st.write(f"**Description:** {c['description']}")
                    st.write(f"**Status:** {c['status']}")
                    st.write(f"**Created:** {c['created_at']}")
                    if st.button(f"View Alerts in Cluster", key=f"view_{c['id']}"):
                        try:
                            detail_resp = requests.get(f"{API_URL}/clusters/{c['id']}")
                            detail = detail_resp.json()
                            alerts_df = pd.DataFrame(detail["alerts"])
                            st.dataframe(alerts_df[["rule_id", "rule_name", "severity", "agent_name", "description", "received_at"]], use_container_width=True)
                        except Exception as e:
                            st.error(f"Failed to load cluster details: {e}")

    except Exception as e:
        st.error(f"Failed to load clusters: {e}")

# ============================================
# Tab 2: Alerts
# ============================================
with tab2:
    st.header("Recent Alerts")

    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox("Status", ["All", "NEW", "CLUSTERED", "DISMISSED", "ESCALATED"])
    with col2:
        hours_filter = st.slider("Hours back", 1, 168, 24)
    with col3:
        limit_filter = st.slider("Max alerts", 10, 200, 50)

    params = {"hours": hours_filter, "page_size": limit_filter}
    if status_filter != "All":
        params["status"] = status_filter

    try:
        resp = requests.get(f"{API_URL}/alerts/", params=params)
        data = resp.json()
        alerts = data.get("items", [])

        if not alerts:
            st.info("No alerts found.")
        else:
            st.metric("Total Alerts (filtered)", data["total"])

            df = pd.DataFrame(alerts)
            if "received_at" in df.columns:
                df["received_at"] = pd.to_datetime(df["received_at"])
                df["hour"] = df["received_at"].dt.floor("h")
                time_df = df.groupby("hour").size().reset_index(name="count")
                fig = px.line(time_df, x="hour", y="count", title="Alerts Over Time")
                st.plotly_chart(fig, use_container_width=True)

            st.dataframe(
                df[["rule_id", "rule_name", "severity", "agent_name", "status", "cluster_id", "received_at"]].head(50),
                use_container_width=True,
            )

    except Exception as e:
        st.error(f"Failed to load alerts: {e}")

# ============================================
# Tab 3: Stats
# ============================================
with tab3:
    st.header("System Overview")

    try:
        # Alerts stats
        alerts_resp = requests.get(f"{API_URL}/alerts/", params={"hours": 24, "page_size": 1})
        total_alerts_24h = alerts_resp.json().get("total", 0)

        # Clusters stats
        clusters_resp = requests.get(f"{API_URL}/clusters/")
        clusters_data = clusters_resp.json()
        total_clusters = len(clusters_data)
        total_clustered = sum(c["alert_count"] for c in clusters_data)

        # Health
        health_resp = requests.get(f"{API_URL}/health/ready")
        health = health_resp.json()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Alerts (24h)", total_alerts_24h)
        with col2:
            st.metric("Clusters", total_clusters)
        with col3:
            st.metric("Alerts in Clusters", total_clustered)
        with col4:
            noise_reduction = (total_clustered / total_alerts_24h * 100) if total_alerts_24h > 0 else 0
            st.metric("Noise Reduction", f"{noise_reduction:.0f}%")

        st.divider()
        st.subheader("System Health")
        st.json(health)

    except Exception as e:
        st.error(f"Failed to load stats: {e}")
