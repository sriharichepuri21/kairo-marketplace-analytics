"""Customer Churn Risk dashboard for the compact deployment warehouse."""

from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "warehouse" / "kairo_dashboard.duckdb"

st.set_page_config(
    page_title="Customer Churn Risk",
    page_icon="🎯",
    layout="wide",
)


@st.cache_data
def load_churn_scores() -> pd.DataFrame:
    """Load governed customer churn scores."""
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Dashboard warehouse was not found at {DB_PATH}."
        )

    with duckdb.connect(str(DB_PATH), read_only=True) as conn:
        scores = conn.execute(
            """
            SELECT
                customer_id,
                score_date,
                signup_channel,
                region,
                segment,
                days_since_last_order,
                total_orders,
                orders_last_90d,
                lifetime_spend,
                return_order_rate,
                discount_order_rate,
                is_single_order_customer,
                churn_probability,
                predicted_churn_flag,
                risk_decile,
                risk_segment,
                recommended_action,
                lifetime_spend_missing_flag,
                probability_threshold,
                model_name,
                model_version,
                scored_at_utc
            FROM mart_customer_churn_scores
            """
        ).df()

    scores["risk_segment"] = (
        scores["risk_segment"]
        .astype("string")
        .str.strip()
        .str.lower()
        .str.replace("_", " ", regex=False)
        .replace({
            "high risk": "high",
            "medium risk": "medium",
            "low risk": "low",
        })
    )

    return scores


@st.cache_data
def load_model_metrics() -> dict:
    """Load deployment-safe production-model metrics."""
    if not DB_PATH.exists():
        return {}

    with duckdb.connect(str(DB_PATH), read_only=True) as conn:
        row = conn.execute(
            """
            SELECT
                model_name,
                roc_auc,
                pr_auc,
                recall,
                f1,
                top_10_pct_lift,
                probability_threshold,
                selection_reason
            FROM dashboard_model_metrics
            LIMIT 1
            """
        ).fetchone()

    if row is None:
        return {}

    columns = [
        "model_name",
        "roc_auc",
        "pr_auc",
        "recall",
        "f1",
        "top_10_pct_lift",
        "probability_threshold",
        "selection_reason",
    ]
    return dict(zip(columns, row))


def format_label(value: str) -> str:
    return str(value).replace("_", " ").title()


def apply_filters(
    scores: pd.DataFrame,
    risk_segments: list[str],
    regions: list[str],
    signup_channels: list[str],
    actions: list[str],
) -> pd.DataFrame:
    filtered = scores.copy()

    if risk_segments:
        filtered = filtered[
            filtered["risk_segment"].isin(risk_segments)
        ]

    if regions:
        filtered = filtered[filtered["region"].isin(regions)]

    if signup_channels:
        filtered = filtered[
            filtered["signup_channel"].isin(signup_channels)
        ]

    if actions:
        filtered = filtered[
            filtered["recommended_action"].isin(actions)
        ]

    return filtered


def show_model_performance(metrics: dict) -> None:
    st.subheader("Production Model Performance")

    if not metrics:
        st.info("Production-model metrics are unavailable.")
        return

    metric_columns = st.columns(5)
    metric_columns[0].metric(
        "Test ROC-AUC",
        f"{metrics['roc_auc']:.4f}",
    )
    metric_columns[1].metric(
        "Test PR-AUC",
        f"{metrics['pr_auc']:.4f}",
    )
    metric_columns[2].metric(
        "Test Recall",
        f"{metrics['recall']:.1%}",
    )
    metric_columns[3].metric(
        "Test F1",
        f"{metrics['f1']:.4f}",
    )
    metric_columns[4].metric(
        "Top-10% Lift",
        f"{metrics['top_10_pct_lift']:.2f}×",
    )

    st.caption(metrics["selection_reason"])


try:
    scores = load_churn_scores()
    model_metrics = load_model_metrics()
except Exception as error:
    st.error(str(error))
    st.stop()

st.title("🎯 Customer Churn Risk")

score_date = pd.to_datetime(scores["score_date"]).max()
st.caption(
    "Point-in-time customer churn predictions as of "
    f"{score_date:%B %d, %Y}. Operational segments use risk "
    "deciles, while the validation-selected probability threshold "
    "is tracked separately."
)

st.markdown("---")
st.subheader("Filters")

filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)

with filter_col1:
    selected_risk = st.multiselect(
        "Risk Segment",
        sorted(scores["risk_segment"].dropna().unique()),
        format_func=lambda value: f"{str(value).title()} Risk",
    )

with filter_col2:
    selected_regions = st.multiselect(
        "Region",
        sorted(scores["region"].dropna().unique()),
    )

with filter_col3:
    selected_channels = st.multiselect(
        "Signup Channel",
        sorted(scores["signup_channel"].dropna().unique()),
    )

with filter_col4:
    action_options = sorted(
        scores["recommended_action"].dropna().unique()
    )
    selected_actions = st.multiselect(
        "Recommended Action",
        action_options,
        format_func=format_label,
    )

filtered = apply_filters(
    scores,
    selected_risk,
    selected_regions,
    selected_channels,
    selected_actions,
)

st.markdown("---")

high_risk = filtered[filtered["risk_segment"] == "high"]
threshold_positive = filtered[
    filtered["predicted_churn_flag"] == 1
]

total_scored = len(filtered)
high_risk_count = len(high_risk)
threshold_positive_count = len(threshold_positive)
average_probability = (
    filtered["churn_probability"].mean()
    if total_scored
    else 0
)
high_risk_spend = high_risk["lifetime_spend"].sum(
    min_count=1
)
high_risk_spend = (
    float(high_risk_spend)
    if pd.notna(high_risk_spend)
    else 0.0
)

kpi_columns = st.columns(5)
kpi_columns[0].metric("Customers Scored", f"{total_scored:,}")
kpi_columns[1].metric(
    "High-Risk Customers",
    f"{high_risk_count:,}",
)
kpi_columns[2].metric(
    "Threshold Positive",
    f"{threshold_positive_count:,}",
)
kpi_columns[3].metric(
    "Average Churn Probability",
    f"{average_probability:.1%}",
)
kpi_columns[4].metric(
    "High-Risk Lifetime Spend",
    f"${high_risk_spend / 1_000_000:,.1f}M",
)

if filtered.empty:
    st.warning("No customers match the selected filters.")
    st.stop()

st.markdown("---")
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    risk_distribution = (
        filtered.groupby("risk_segment", as_index=False)
        .agg(customers=("customer_id", "count"))
    )

    risk_order = ["high", "medium", "low"]
    risk_distribution["risk_segment"] = pd.Categorical(
        risk_distribution["risk_segment"],
        categories=risk_order,
        ordered=True,
    )
    risk_distribution = risk_distribution.sort_values(
        "risk_segment"
    )
    risk_distribution["risk_label"] = (
        risk_distribution["risk_segment"]
        .astype("string")
        .str.title()
        + " Risk"
    )

    fig_risk = px.bar(
        risk_distribution,
        x="risk_label",
        y="customers",
        text="customers",
        title="Customers by Operational Risk Segment",
        labels={
            "risk_label": "Risk Segment",
            "customers": "Customers",
        },
    )
    fig_risk.update_traces(
        texttemplate="%{text:,}",
        textposition="outside",
    )
    fig_risk.update_layout(showlegend=False)
    st.plotly_chart(fig_risk, use_container_width=True)

with chart_col2:
    threshold = float(
        filtered["probability_threshold"].dropna().iloc[0]
    )

    fig_probability = px.histogram(
        filtered,
        x="churn_probability",
        nbins=40,
        title="Churn Probability Distribution",
        labels={
            "churn_probability": "Churn Probability",
            "count": "Customers",
        },
    )
    fig_probability.add_vline(
        x=threshold,
        line_dash="dash",
        annotation_text=f"Threshold {threshold:.0%}",
    )
    st.plotly_chart(
        fig_probability,
        use_container_width=True,
    )

st.subheader("Risk Deciles and Recommended Actions")
decile_col, action_col = st.columns(2)

with decile_col:
    decile_profile = (
        filtered.groupby("risk_decile", as_index=False)
        .agg(
            customers=("customer_id", "count"),
            avg_probability=("churn_probability", "mean"),
            lifetime_spend=("lifetime_spend", "sum"),
        )
        .sort_values("risk_decile")
    )

    fig_decile = px.bar(
        decile_profile,
        x="risk_decile",
        y="avg_probability",
        text="customers",
        title="Average Churn Probability by Risk Decile",
        labels={
            "risk_decile": "Risk Decile",
            "avg_probability": "Average Churn Probability",
        },
    )
    fig_decile.update_traces(
        texttemplate="%{text:,}",
        textposition="outside",
    )
    fig_decile.update_layout(
        xaxis=dict(
            autorange="reversed",
            dtick=1,
        ),
        yaxis_tickformat=".0%",
    )
    st.plotly_chart(fig_decile, use_container_width=True)

with action_col:
    action_summary = (
        filtered.groupby("recommended_action", as_index=False)
        .agg(customers=("customer_id", "count"))
        .sort_values("customers")
    )
    action_summary["action_label"] = action_summary[
        "recommended_action"
    ].map(format_label)

    fig_action = px.bar(
        action_summary,
        x="customers",
        y="action_label",
        orientation="h",
        text="customers",
        title="Recommended Customer Actions",
        labels={
            "customers": "Customers",
            "action_label": "",
        },
    )
    fig_action.update_traces(
        texttemplate="%{text:,}",
        textposition="outside",
        cliponaxis=False,
    )
    fig_action.update_layout(
        showlegend=False,
        margin=dict(r=100),
    )
    st.plotly_chart(fig_action, use_container_width=True)

st.subheader("High-Risk Customer Intervention Queue")

high_risk_queue = filtered[
    filtered["risk_segment"] == "high"
].sort_values(
    ["lifetime_spend", "churn_probability"],
    ascending=[False, False],
)

queue_display = high_risk_queue[
    [
        "customer_id",
        "churn_probability",
        "risk_decile",
        "lifetime_spend",
        "days_since_last_order",
        "total_orders",
        "orders_last_90d",
        "return_order_rate",
        "discount_order_rate",
        "signup_channel",
        "region",
        "recommended_action",
    ]
].copy()

queue_display["churn_probability"] *= 100.0
queue_display["return_order_rate"] *= 100.0
queue_display["discount_order_rate"] *= 100.0

queue_display = queue_display.rename(
    columns={
        "customer_id": "Customer ID",
        "churn_probability": "Churn Probability",
        "risk_decile": "Risk Decile",
        "lifetime_spend": "Lifetime Spend",
        "days_since_last_order": "Days Since Last Order",
        "total_orders": "Total Orders",
        "orders_last_90d": "Orders Last 90D",
        "return_order_rate": "Return Order Rate",
        "discount_order_rate": "Discount Order Rate",
        "signup_channel": "Signup Channel",
        "region": "Region",
        "recommended_action": "Recommended Action",
    }
)

st.dataframe(
    queue_display.head(100),
    use_container_width=True,
    hide_index=True,
    column_config={
        "Churn Probability": st.column_config.ProgressColumn(
            min_value=0.0,
            max_value=100.0,
            format="%.1f%%",
        ),
        "Lifetime Spend": st.column_config.NumberColumn(
            format="$%.2f",
        ),
        "Return Order Rate": st.column_config.NumberColumn(
            format="%.1f%%",
        ),
        "Discount Order Rate": st.column_config.NumberColumn(
            format="%.1f%%",
        ),
    },
)

csv_data = queue_display.to_csv(index=False).encode("utf-8")

st.download_button(
    "Download High-Risk Intervention Queue",
    data=csv_data,
    file_name="kairo_high_risk_customer_queue.csv",
    mime="text/csv",
)

st.markdown("---")
show_model_performance(model_metrics)

missing_spend_count = int(
    filtered["lifetime_spend_missing_flag"].sum()
)
st.caption(
    f"Missing lifetime-spend values explicitly tracked: "
    f"{missing_spend_count:,}. "
    f"Production model: "
    f"{model_metrics.get('model_name', 'behavioral_only')}."
)
