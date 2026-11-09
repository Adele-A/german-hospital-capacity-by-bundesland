"""Stage 5 — static figures for the README (reports/figures/*.png).

Matplotlib/geopandas are imported lazily (optional geo extra), so importing this module is cheap.
"""

from __future__ import annotations

import duckdb

from etl.paths import DASHBOARD_GEO_DIR, FIGURES_DIR

ACCENT = "#2a6f97"
HIGHLIGHT = {"11": "#e63946", "12": "#f4a261"}  # Berlin, Brandenburg


def _wide(con: duckdb.DuckDBPyConnection, year: int):
    return (
        con.cursor()
        .execute(
            "SELECT w.*, d.name_en FROM fact_indicators_wide w "
            "JOIN dim_bundesland d USING (ags_code) WHERE w.year = ? AND w.ags_code <> 'DG' "
            "ORDER BY w.beds_per_100k DESC",
            [year],
        )
        .df()
    )


def build_figures(con: duckdb.DuckDBPyConnection, year: int = 2024) -> list[str]:
    import geopandas as gpd
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"figure.dpi": 130, "font.size": 10, "savefig.bbox": "tight"})
    df = _wide(con, year)
    out: list[str] = []

    # 1) Choropleth map — beds per 100k
    gdf = gpd.read_file(DASHBOARD_GEO_DIR / "bundeslaender.geojson").merge(
        df[["ags_code", "beds_per_100k", "name_en"]], on="ags_code", how="left"
    )
    fig, ax = plt.subplots(figsize=(6, 7))
    gdf.plot(
        column="beds_per_100k",
        cmap="YlGnBu",
        edgecolor="white",
        linewidth=0.5,
        legend=True,
        legend_kwds={"label": f"Beds per 100k ({year})", "shrink": 0.6},
        ax=ax,
    )
    ax.set_title(f"Hospital beds per 100,000 inhabitants by Bundesland, {year}")
    ax.axis("off")
    p = FIGURES_DIR / "map_beds_per_100k.png"
    fig.savefig(p)
    plt.close(fig)
    out.append(str(p))

    # 2) Ranking bar — beds per 100k
    fig, ax = plt.subplots(figsize=(7, 5))
    colors = [HIGHLIGHT.get(a, ACCENT) for a in df["ags_code"]]
    ax.barh(df["name_en"], df["beds_per_100k"], color=colors)
    ax.invert_yaxis()
    ax.set_xlabel("Beds per 100,000 inhabitants")
    ax.set_title(f"Hospital beds per 100k by Bundesland, {year}")
    for y_, v in enumerate(df["beds_per_100k"]):
        ax.text(v + 3, y_, f"{v:.0f}", va="center", fontsize=8)
    p = FIGURES_DIR / "ranking_beds_per_100k.png"
    fig.savefig(p)
    plt.close(fig)
    out.append(str(p))

    # 3) Trends — beds per 100k over the available years (states faint, DE + BE/BB highlighted)
    ts = (
        con.cursor()
        .execute(
            "SELECT ags_code, year, beds_per_100k FROM fact_indicators_wide ORDER BY ags_code, year"
        )
        .df()
    )
    fig, ax = plt.subplots(figsize=(7, 5))
    for a, g in ts.groupby("ags_code"):
        if a in HIGHLIGHT:
            ax.plot(
                g["year"],
                g["beds_per_100k"],
                color=HIGHLIGHT[a],
                lw=2.2,
                marker="o",
                label={"11": "Berlin", "12": "Brandenburg"}[a],
            )
        elif a == "DG":
            ax.plot(g["year"], g["beds_per_100k"], color="black", lw=2, ls="--", label="Germany")
        else:
            ax.plot(g["year"], g["beds_per_100k"], color="#b9c6d0", lw=1)
    ax.set_xlabel("Year")
    ax.set_ylabel("Beds per 100,000 inhabitants")
    ax.set_title("Beds per 100k over time (grey = other states)")
    ax.set_xticks(sorted(ts["year"].unique()))
    ax.legend(frameon=False, fontsize=9)
    p = FIGURES_DIR / "trends_beds_per_100k.png"
    fig.savefig(p)
    plt.close(fig)
    out.append(str(p))

    # 4) National pandemic context — Deutschland cases & beds, 2000-2024 (pre-COVID baseline)
    nat = (
        con.cursor().execute("SELECT year, cases, beds FROM fact_germany_series ORDER BY year").df()
    )
    fig, ax1 = plt.subplots(figsize=(7, 5))
    ax1.plot(nat["year"], nat["cases"] / 1e6, color=ACCENT, lw=2, marker="o", label="Cases (M)")
    ax1.set_xlabel("Year")
    ax1.set_ylabel("Inpatient cases (millions)", color=ACCENT)
    ax1.axvspan(2019.5, 2021.5, color="#f4a26133", label="COVID-19")
    ax1.axvline(2019, color="#888", ls=":", lw=1)
    ax1.annotate(
        "2019 pre-COVID",
        (2019, nat.loc[nat.year == 2019, "cases"].iloc[0] / 1e6),
        textcoords="offset points",
        xytext=(-6, 8),
        ha="right",
        fontsize=8,
    )
    ax2 = ax1.twinx()
    ax2.plot(nat["year"], nat["beds"] / 1e3, color="#b5651d", lw=1.8, ls="--", label="Beds (k)")
    ax2.set_ylabel("Available beds (thousands)", color="#b5651d")
    ax1.set_title("Germany: inpatient cases & beds, 2000–2024")
    p = FIGURES_DIR / "national_trend.png"
    fig.savefig(p)
    plt.close(fig)
    out.append(str(p))

    return out
