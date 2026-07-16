"""
Customer Churn Risk Dashboard

Displays customer-level churn probabilities, operational risk
segments, intervention recommendations, and model performance from
the governed mart_customer_churn_scores dbt model.
"""

import json
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st


PAGE_PATH = Path(__file__).resolve()
PROJECT_ROOT = PAGE_PATH.parents[3]

DB_PATH = PROJECT_ROOT / "warehouse" / "kairo.duckdb"

PRODUCTION_DECISION_PATH = (
    PROJECT_ROOT
    / "analytics"
    / "churn_model"
    / "model_artifacts"
    / "production_model_decision.json"
)


st.set_page_config(
    page_title="Customer Churn Risk",
    page_icon="🎯",
    layout="wide",
)


@st.cache_data
def load_churn_scores() -> pd.DataFrame:
    """Load the governed customer churn scoring mart."""

    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"DuckDB warehouse was not found at {DB_PATH}"
        )

    conn = duckdb.connect(
        str(DB_PATH),
        read_only=True,
    )

    try:
        table_exists = conn.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'main'
              AND table_name = 'mart_customer_churn_scores'
        """).fetchone()[0]

        if table_exists == 0:
            raise RuntimeError(
                "mart_customer_churn_scores does not exist. "
                "Run dbt build --select mart_customer_churn_scores."
            )

        scores = conn.execute("""
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
            FROM main.mart_customer_churn_scores
        """).df()

    finally:
        conn.close()

    return scores


@st.cache_data
def load_model_decision() -> dict:
    """Load the documented production-model decision."""

    if not PRODUCTION_DECISION_PATH.exists():
        return {}

    with PRODUCTION_DECISION_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def format_label(value: str) -> str:
    """Convert snake_case labels to display labels."""

    return str(value).replace("_", " ").title()


def apply_filters(
    scores: pd.DataFrame,
    risk_segments: list[str],
    regions: list[str],
    signup_channels: list[str],
    actions: list[str],
) -> pd.DataFrame:
    """Apply dashboard filters."""

    filtered = scores.copy()

    if risk_segments:
        filtered = filtered[
            filtered["risk_segment"].isin(risk_segments)
        ]

    if regions:
        filtered = filtered[
            filtered["region"].isin(regions)
        ]

    if signup_channels:
        filtered = filtered[
            filtered["signup_channel"].isin(signup_channels)
        ]

    if actions:
        filtered = filtered[
            filtered["recommended_action"].isin(actions)
        ]

    return filtered


def show_model_performance(
    decision: dict,
) -> None:
    """Display production-model evaluation metrics."""

    behavioral_metrics = decision.get(
        "behavioral_test_metrics",
        {},
    )

    if not behavioral_metrics:
        st.info(
            "Production-model evaluation metrics are not available."
        )
        return

    st.subheader("Production Model Performance")

    metric_columns = st.columns(5)

    metric_columns[0].metric(
        "Test ROC-AUC",
        f"{behavioral_metrics.get('roc_auc', 0):.4f}",
    )

    metric_columns[1].metric(
        "Test PR-AUC",
        f"{behavioral_metrics.get('pr_auc', 0):.4f}",
    )

    metric_columns[2].metric(
        "Test Recall",
        f"{behavioral_metrics.get('recall', 0):.1%}",
    )

    metric_columns[3].metric(
        "Test F1",
        f"{behavioral_metrics.get('f1', 0):.4f}",
    )

    metric_columns[4].metric(
        "Top-10% Lift",
        f"{behavioral_metrics.get('top_10_pct_lift', 0):.2f}×",
    )

    st.caption(
        "The behavioral-only model was promoted because adding "
        "signup channel produced negligible out-of-time improvement."
    )


try:
    scores = load_churn_scores()
    model_decision = load_model_decision()

except Exception as error:
    st.error(str(error))
    st.stop()


st.title("🎯 Customer Churn Risk")

score_date = pd.to_datetime(
    scores["score_date"]
).max()

st.caption(
    "Point-in-time customer churn predictions as of "
    f"{score_date:%B %d, %Y}. "
    "The model predicts whether an existing customer will place "
    "an eligible order during the following 90 days."
)


with st.sidebar:
    st.header("Filters")

    available_risk_segments = [
        value
        for value in [
            "high_risk",
            "medium_risk",
            "low_risk",
        ]
        if value in scores["risk_segment"].unique()
    ]

    selected_risk_segments = st.multiselect(
        "Risk Segment",
        options=available_risk_segments,
        default=available_risk_segments,
        format_func=format_label,
    )

    available_regions = sorted(
        scores["region"]
        .dropna()
        .unique()
        .tolist()
    )

    selected_regions = st.multiselect(
        "Region",
        options=available_regions,
        default=available_regions,
    )

    available_channels = sorted(
        scores["signup_channel"]
        .dropna()
        .unique()
        .tolist()
    )

    selected_channels = st.multiselect(
        "Signup Channel",
        options=available_channels,
        default=available_channels,
        format_func=format_label,
    )

    available_actions = sorted(
        scores["recommended_action"]
        .dropna()
        .unique()
        .tolist()
    )

    selected_actions = st.multiselect(
        "Recommended Action",
        options=available_actions,
        default=available_actions,
        format_func=format_label,
    )


filtered_scores = apply_filters(
    scores=scores,
    risk_segments=selected_risk_segments,
    regions=selected_regions,
    signup_channels=selected_channels,
    actions=selected_actions,
)


if filtered_scores.empty:
    st.warning(
        "No customers match the selected filters."
    )
    st.stop()


customers_scored = len(filtered_scores)

high_risk_customers = int(
    (
        filtered_scores["risk_segment"]
        == "high_risk"
    ).sum()
)

threshold_positive = int(
    filtered_scores[
        "predicted_churn_flag"
    ].sum()
)

average_probability = (
    filtered_scores[
        "churn_probability"
    ].mean()
)

high_risk_spend = filtered_scores.loc[
    filtered_scores["risk_segment"]
    == "high_risk",
    "lifetime_spend",
].sum()


metric_columns = st.columns(5)

metric_columns[0].metric(
    "Customers Scored",
    f"{customers_scored:,}",
)

metric_columns[1].metric(
    "High-Risk Customers",
    f"{high_risk_customers:,}",
    f"{high_risk_customers / customers_scored:.1%}",
)

metric_columns[2].metric(
    "Threshold-Positive",
    f"{threshold_positive:,}",
    f"{threshold_positive / customers_scored:.1%}",
)

metric_columns[3].metric(
    "Average Churn Probability",
    f"{average_probability:.1%}",
)

metric_columns[4].metric(
    "High-Risk Lifetime Spend",
    f"${high_risk_spend / 1_000_000:,.1f}M",
)


st.divider()


risk_summary = (
    filtered_scores
    .groupby(
        "risk_segment",
        as_index=False,
    )
    .agg(
        customers=(
            "customer_id",
            "count",
        ),
        average_probability=(
            "churn_probability",
            "mean",
        ),
        average_lifetime_spend=(
            "lifetime_spend",
            "mean",
        ),
    )
)

risk_order = [
    "high_risk",
    "medium_risk",
    "low_risk",
]

risk_summary["risk_segment"] = pd.Categorical(
    risk_summary["risk_segment"],
    categories=risk_order,
    ordered=True,
)

risk_summary = risk_summary.sort_values(
    "risk_segment"
)

risk_summary["Risk Segment"] = (
    risk_summary["risk_segment"]
    .astype(str)
    .map(format_label)
)


left_chart, right_chart = st.columns(2)

with left_chart:
    st.subheader("Customer Risk Distribution")

    risk_chart = px.bar(
        risk_summary,
        x="Risk Segment",
        y="customers",
        text="customers",
        labels={
            "customers": "Customers",
        },
    )

    risk_chart.update_traces(
        texttemplate="%{text:,}",
        textposition="outside",
    )

    risk_chart.update_layout(
        showlegend=False,
        yaxis_title="Customers",
        xaxis_title=None,
    )

    st.plotly_chart(
        risk_chart,
        use_container_width=True,
    )


with right_chart:
    st.subheader("Churn Probability Distribution")

    probability_chart = px.histogram(
        filtered_scores,
        x="churn_probability",
        nbins=40,
        labels={
            "churn_probability": (
                "Predicted Churn Probability"
            ),
        },
    )

    probability_chart.add_vline(
        x=float(
            filtered_scores[
                "probability_threshold"
            ].iloc[0]
        ),
        line_dash="dash",
        annotation_text="Validation threshold",
    )

    probability_chart.update_layout(
        showlegend=False,
        xaxis_tickformat=".0%",
        yaxis_title="Customers",
    )

    st.plotly_chart(
        probability_chart,
        use_container_width=True,
    )


st.divider()


decile_summary = (
    filtered_scores
    .groupby(
        "risk_decile",
        as_index=False,
    )
    .agg(
        customers=(
            "customer_id",
            "count",
        ),
        average_probability=(
            "churn_probability",
            "mean",
        ),
        average_lifetime_spend=(
            "lifetime_spend",
            "mean",
        ),
        average_recency_days=(
            "days_since_last_order",
            "mean",
        ),
    )
    .sort_values(
        "risk_decile"
    )
)


left_decile, right_action = st.columns(2)

with left_decile:
    st.subheader("Risk Decile Profile")

    decile_chart = px.bar(
        decile_summary,
        x="risk_decile",
        y="average_probability",
        text="customers",
        labels={
            "risk_decile": "Risk Decile",
            "average_probability": (
                "Average Churn Probability"
            ),
            "customers": "Customers",
        },
    )

    decile_chart.update_traces(
        texttemplate="%{text:,}",
        textposition="outside",
    )

    decile_chart.update_layout(
        xaxis=dict(
            dtick=1,
            autorange="reversed",
        ),
        yaxis_tickformat=".0%",
        showlegend=False,
    )

    st.plotly_chart(
        decile_chart,
        use_container_width=True,
    )

    st.caption(
        "Decile 1 contains the highest-risk customers; "
        "decile 10 contains the lowest-risk customers."
    )


with right_action:
    st.subheader("Recommended Intervention Actions")

    action_summary = (
        filtered_scores[
            "recommended_action"
        ]
        .value_counts()
        .rename_axis(
            "recommended_action"
        )
        .reset_index(
            name="customers"
        )
    )

    action_summary["Action"] = (
        action_summary[
            "recommended_action"
        ].map(format_label)
    )

    action_chart = px.bar(
        action_summary.sort_values(
            "customers",
            ascending=True,
        ),
        x="customers",
        y="Action",
        orientation="h",
        text="customers",
        labels={
            "customers": "Customers",
        },
    )

    action_chart.update_traces(
        texttemplate="%{text:,}",
        textposition="outside",
        cliponaxis=False,
    )

    action_chart.update_layout(
        showlegend=False,
        xaxis_title="Customers",
        yaxis_title=None,
        margin=dict(r=100),
    )

    st.plotly_chart(
        action_chart,
        use_container_width=True,
    )


st.divider()


st.subheader("High-Risk Customer Intervention Queue")

high_risk_queue = (
    filtered_scores[
        filtered_scores[
            "risk_segment"
        ] == "high_risk"
    ]
    .sort_values(
        [
            "churn_probability",
            "lifetime_spend",
        ],
        ascending=[
            False,
            False,
        ],
    )
    .copy()
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

queue_display["churn_probability"] = (
    queue_display["churn_probability"] * 100.0
)

queue_display["return_order_rate"] = (
    queue_display["return_order_rate"] * 100.0
)

queue_display["discount_order_rate"] = (
    queue_display["discount_order_rate"] * 100.0
)

queue_display = queue_display.rename(
    columns={
        "customer_id": "Customer ID",
        "churn_probability": "Churn Probability",
        "risk_decile": "Risk Decile",
        "lifetime_spend": "Lifetime Spend",
        "days_since_last_order": (
            "Days Since Last Order"
        ),
        "total_orders": "Lifetime Orders",
        "orders_last_90d": "Orders Last 90 Days",
        "return_order_rate": "Return Order Rate",
        "discount_order_rate": "Discount Order Rate",
        "signup_channel": "Signup Channel",
        "region": "Region",
        "recommended_action": (
            "Recommended Action"
        ),
    }
)


st.dataframe(
    queue_display,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Churn Probability": (
            st.column_config.ProgressColumn(
                "Churn Probability",
                min_value=0.0,
                max_value=100.0,
                format="%.1f%%",
            )
        ),
        "Lifetime Spend": (
            st.column_config.NumberColumn(
                "Lifetime Spend",
                format="$%.2f",
            )
        ),
        "Return Order Rate": (
            st.column_config.NumberColumn(
                "Return Order Rate",
                format="%.1f%%",
            )
        ),
        "Discount Order Rate": (
            st.column_config.NumberColumn(
                "Discount Order Rate",
                format="%.1f%%",
            )
        ),
    },
)


download_data = queue_display.to_csv(
    index=False
).encode("utf-8")

st.download_button(
    label="Download High-Risk Intervention Queue",
    data=download_data,
    file_name=(
        "kairo_high_risk_customer_queue.csv"
    ),
    mime="text/csv",
)


st.divider()


show_model_performance(
    model_decision
)


st.info(
    "Risk segments are capacity-based: the top 20% of scores are "
    "High Risk, the next 30% are Medium Risk, and the remaining "
    "50% are Low Risk. The 0.30 validation threshold is reported "
    "separately and should not be interpreted as outreach capacity."
)
