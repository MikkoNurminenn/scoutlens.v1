import numpy as np
import plotly.graph_objects as go

def create_minutes_age_plot(df):
    if df.empty or df["Age"].isnull().all() or df["Minutes"].isnull().all():
        return go.Figure()

    df["FormattedName"] = df["Name"].apply(
        lambda name: name[0] + ". " + " ".join(name.split()[1:])
    )
    
    z = np.polyfit(df["Age"], df["Minutes"], 3)
    p = np.poly1d(z)
    x_range = np.linspace(df["Age"].min(), df["Age"].max(), 200)
    y_trend = p(x_range)

    fig = go.Figure()

    # Highlight peak age range (e.g. 24–29)
    fig.add_shape(
        type="rect",
        x0=24, x1=29,
        y0=0, y1=df["Minutes"].max() + 200,
        fillcolor="#F9C80E",
        opacity=0.15,
        line_width=0,
        layer="below"
    )

    # Player points with labels
    fig.add_trace(go.Scatter(
        x=df["Age"], y=df["Minutes"],
        mode="markers+text",
        marker=dict(size=12, color="#00B4D8"),
        text=df["FormattedName"],
        textposition="top center",
        textfont=dict(color="#FFFFFF", size=12),
        hovertext=df["FormattedName"],
        hoverinfo="text",
        name="Players"
    ))

    # Trendline
    fig.add_trace(go.Scatter(
        x=x_range, y=y_trend,
        mode="lines",
        line=dict(color="#06D6A0", dash="dash"),
        name="Trendline"
    ))

    # Layout settings
    fig.update_layout(
        title="Player Minutes by Age",
        xaxis_title="Age",
        yaxis_title="Minutes",
        template="plotly_dark",
        plot_bgcolor="#1E1E1E",
        paper_bgcolor="#1E1E1E",
        font=dict(size=14, color="#FFFFFF"),
        hoverlabel=dict(
            bgcolor="#333",
            font=dict(color="#FFFFFF")
        ),
        xaxis=dict(
            tickfont=dict(size=12, color="#FFFFFF"),
            title_font=dict(size=14, color="#FFFFFF"),
            linecolor="#444",
            showline=True,
            gridcolor="#444"
        ),
        yaxis=dict(
            tickfont=dict(size=12, color="#FFFFFF"),
            title_font=dict(size=14, color="#FFFFFF"),
            linecolor="#444",
            showline=True,
            gridcolor="#444"
        ),
        legend=dict(
            font=dict(color="#FFFFFF")
        ),
    )

    return fig
