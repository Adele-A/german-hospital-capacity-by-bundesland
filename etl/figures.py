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

    return out
