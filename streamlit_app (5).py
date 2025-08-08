import streamlit as st
import pandas as pd
import altair as alt


# -------------------------------
# Page Config
# -------------------------------
st.set_page_config(layout="wide")
st.title("COMPAS Risk Assessment Dashboard")


# -------------------------------
# Load Data
# -------------------------------
@st.cache_data
def load_data():
   df = pd.read_csv("compas-scores-two-years (1).csv")
   df["recidivism_status"] = df["two_year_recid"].map({0: "No Recidivism", 1: "Recidivism"})
   df["priors_bin"] = pd.cut(df["priors_count"], bins=[-1, 0, 2, 5, 10, 20, 100],
                             labels=["0", "1-2", "3-5", "6-10", "11-20", "21+"])
   return df


df = load_data()


# -------------------------------
# Sidebar Filters
# -------------------------------
st.sidebar.header("Filters")


race_options = sorted(df["race"].dropna().unique().tolist())
selected_races = st.sidebar.multiselect("Select Race(s)", race_options, default=race_options)


age_group_options = sorted(df["age_cat"].dropna().unique().tolist())
selected_age_group = st.sidebar.selectbox("Select Age Group", ["All"] + age_group_options)


# Apply filters
filtered_df = df[df["race"].isin(selected_races)]
if selected_age_group != "All":
   filtered_df = filtered_df[filtered_df["age_cat"] == selected_age_group]


# -------------------------------
# Chart 1 – COMPAS vs Recidivism Line Chart
# -------------------------------
grouped = filtered_df.groupby("priors_bin").agg({
   "decile_score": "mean",
   "two_year_recid": "mean"
}).reset_index()


grouped["decile_score_norm"] = grouped["decile_score"] / 10
grouped["recidivism_rate_norm"] = grouped["two_year_recid"]


line_data = pd.DataFrame({
   "Prior Convictions": grouped["priors_bin"].astype(str).tolist() * 2,
   "Score": grouped["decile_score_norm"].tolist() + grouped["recidivism_rate_norm"].tolist(),
   "Metric": ["Average COMPAS Score"] * len(grouped) + ["Average Recidivism Rate"] * len(grouped)
})


metric_selection = alt.selection_point(fields=["Metric"], bind="legend")


line_chart = alt.Chart(line_data).mark_line(point=True).encode(
   x=alt.X("Prior Convictions:N", sort=["0", "1-2", "3-5", "6-10", "11-20", "21+"]),
   y=alt.Y("Score:Q", scale=alt.Scale(domain=[0, 1])),
   color="Metric:N",
   tooltip=["Prior Convictions", "Score", "Metric"],
   opacity=alt.condition(metric_selection, alt.value(1), alt.value(0.1))
).add_params(
   metric_selection
).properties(
   title="COMPAS Score vs. Recidivism Rate by Prior Convictions",
   width=600,
   height=300
)


# -------------------------------
# Chart 2 – Faceted Scatter Plot
# -------------------------------
recidivism_selection = alt.selection_point(fields=["recidivism_status"], bind="legend")


base_scatter = alt.Chart(
   filtered_df.dropna(subset=["age", "decile_score"])
).mark_circle(size=30).encode(
   x=alt.X("age:Q", title="Age", scale=alt.Scale(zero=False)),
   y=alt.Y("decile_score:Q", title="COMPAS Risk Score", scale=alt.Scale(zero=False)),
   color=alt.Color("recidivism_status:N", title="Recidivism"),
   tooltip=[
       alt.Tooltip("name:N", title="Name"),
       alt.Tooltip("c_charge_desc:N", title="Charge"),
       alt.Tooltip("state:N", title="State"),
       alt.Tooltip("age:Q", title="Age"),
       alt.Tooltip("sex:N", title="Sex"),
       alt.Tooltip("race:N", title="Race"),
       alt.Tooltip("decile_score:Q", title="COMPAS Score"),
       alt.Tooltip("recidivism_status:N", title="Recidivism")
   ],
   opacity=alt.condition(recidivism_selection, alt.value(1), alt.value(0.05))
).add_params(
   recidivism_selection
).properties(
   width=150,
   height=150
)


faceted_scatter = base_scatter.facet(
   column=alt.Column("race:N", title="Race"),
   row=alt.Row("sex:N", title="Sex"),
   title="COMPAS Risk Score vs. Age by Race and Gender"
).interactive()


# -------------------------------
# Chart 3 – Bar Chart (Error Rates)
# -------------------------------
error_data = pd.DataFrame({
   "Race": ["African-American", "Asian", "Caucasian", "Hispanic", "Native American", "Other"],
   "False Positive Rate": [7.5, 4.0, 3.9, 4.1, 4.2, 1.5],
   "False Negative Rate": [31.5, 19.0, 31.0, 30.8, 32.0, 30.5]
}).melt(id_vars="Race", var_name="Error Type", value_name="Rate")


error_type_selection = alt.selection_point(fields=["Error Type"], bind="legend")


bar_chart = alt.Chart(error_data).mark_bar().encode(
   x=alt.X("Race:N", sort="-y"),
   y=alt.Y("Rate:Q"),
   color="Error Type:N",
   tooltip=["Race", "Rate", "Error Type"],
   opacity=alt.condition(error_type_selection, alt.value(1), alt.value(0.05))
).add_params(
   error_type_selection
).properties(
   width=600,
   height=300,
   title="False Positive and Negative Rates by Race"
)


# -------------------------------
# Display Charts with Explanations
# -------------------------------
col1, col2 = st.columns(2)


with col1:
   st.markdown("""
   ### COMPAS Score vs. Recidivism


   **What this shows:** 
   This line chart compares two metrics such as average COMPAS risk scores and average recidivism rates for individuals with different numbers of prior convictions. 
   - **COMPAS Score** is an algorithmic prediction of how likely someone is to reoffend.
   - **Recidivism Rate** is the actual percentage of people who reoffended within two years.


   **How to use it:** 
   - Use the legend to toggle lines on or off.
   - Hover over data points to see exact values.
   """)
   st.altair_chart(line_chart, use_container_width=True)


with col2:
   st.markdown("""
   ### Error Rates by Race


   **What this shows:** 
   This bar chart presents the rates of false positives and false negatives made by the COMPAS algorithm across different racial groups. 
   - A **false positive** means the system predicted someone would reoffend, but they did not. 
   - A **false negative** means the system predicted someone would not reoffend, but they did.


   **How to use it:** 
   - Click the legend to isolate either error type.
   - Hover to view detailed rate values.
   """)
   st.altair_chart(bar_chart, use_container_width=True)


st.markdown("""
### COMPAS Score vs. Age by Race and Gender


**What this shows:** 
This scatter plot breaks down COMPAS risk scores by age, with separate panels (facets) for each race and sex combination. 
Each point represents one individual. Color indicates whether or not the individual reoffended within two years.


**How to use it:** 
- Hover over points to view the person’s name, charge, and state.
- Also see their age, race, sex, COMPAS score, and recidivism status.
- Use the legend to highlight or filter by recidivism status.
""")
st.altair_chart(faceted_scatter, use_container_width=True)