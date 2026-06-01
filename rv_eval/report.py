"""Report builder: HTML for humans, Markdown + JSON for LLMs, plus a run registry for progression.

Writes into the run directory:
  report.html    — self-contained (base64 PNGs), all §3/§5/§6 panels
  report.md      — compact LLM-readable tables + a Progression panel (signed Δ vs prior runs/benchmarks)
  metrics.json   — flat machine-readable headline metrics
and appends headline rows to execution/reports/registry.parquet.
"""

from __future__ import annotations

import base64
import io
import json
from datetime import date, datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import polars as pl  # noqa: E402

from rv_eval import config as C  # noqa: E402

_PROG_TOL = 0.005  # |Δ QLIKE| below this is "flat"


# --------------------------------------------------------------------------- table rendering
def _fmt(v) -> str:
    if isinstance(v, float):
        return f"{v:.4f}"
    if isinstance(v, bool):
        return "✓" if v else ""
    return "" if v is None else str(v)


def md_table(df: pl.DataFrame) -> str:
    cols = df.columns
    head = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    body = "\n".join("| " + " | ".join(_fmt(v) for v in row) + " |" for row in df.iter_rows())
    return "\n".join([head, sep, body])


def html_table(df: pl.DataFrame) -> str:
    th = "".join(f"<th>{c}</th>" for c in df.columns)
    trs = "".join("<tr>" + "".join(f"<td>{_fmt(v)}</td>" for v in row) + "</tr>"
                  for row in df.iter_rows())
    return f"<table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>"


def _png_b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


# --------------------------------------------------------------------------- figures
def _ann_vol(var_expr: pl.Expr, h: int) -> pl.Expr:
    return (var_expr * C.TRADING_DAYS_PER_YEAR / h).sqrt()


def fig_leaderboard(tier1_by_h: pl.DataFrame) -> str:
    h = C.PRIMARY_HORIZON
    d = tier1_by_h.filter(pl.col("horizon") == h).sort("qlike")
    fig, ax = plt.subplots(figsize=(6, 3.2))
    ax.bar(d["model"], d["qlike"], color="#3b6ea5")
    ax.set_title(f"QLIKE leaderboard (h={h}, pooled OOS) — lower is better")
    ax.set_ylabel("QLIKE")
    ax.grid(axis="y", alpha=0.3)
    return _png_b64(fig)


def fig_forecast_vs_realized(scored: pl.DataFrame, ticker: str) -> str | None:
    h = C.PRIMARY_HORIZON
    sub = scored.filter((pl.col("ticker") == ticker) & (pl.col("horizon") == h)).sort("date")
    if sub.is_empty():
        return None
    fig, ax = plt.subplots(figsize=(9, 3.4))
    realized = sub.unique("date", keep="first").sort("date")
    ax.plot(realized["date"], realized.select(_ann_vol(pl.col("target_var"), h)).to_series(),
            color="black", lw=1.3, label="realized")
    for model in sorted(sub["model"].unique().to_list()):
        m = sub.filter(pl.col("model") == model).sort("date")
        ax.plot(m["date"], m.select(_ann_vol(pl.col("rv_hat"), h)).to_series(), lw=0.9, alpha=0.8, label=model)
    for _lab, (s, e) in C.STRESS_REGIMES.items():
        ax.axvspan(date.fromisoformat(s), date.fromisoformat(e), color="red", alpha=0.07)
    ax.set_title(f"{ticker} h={h}: forecast vs realized (annualized vol); stress regimes shaded")
    ax.set_ylabel("annualized vol")
    ax.legend(fontsize=7, ncol=5)
    ax.grid(alpha=0.3)
    return _png_b64(fig)


def fig_coverage(scored: pl.DataFrame) -> str | None:
    if "in90" not in scored.columns:
        return None
    h = C.PRIMARY_HORIZON
    d = (scored.filter(pl.col("horizon") == h).group_by("model")
         .agg(cov50=pl.col("in50").mean(), cov90=pl.col("in90").mean()).sort("model"))
    fig, ax = plt.subplots(figsize=(6, 3.2))
    x = range(d.height)
    ax.scatter(x, d["cov50"], label="50% interval", color="#d08", zorder=3)
    ax.scatter(x, d["cov90"], label="90% interval", color="#08d", zorder=3)
    ax.axhline(0.5, color="#d08", ls="--", alpha=0.5)
    ax.axhline(0.9, color="#08d", ls="--", alpha=0.5)
    ax.set_xticks(list(x)); ax.set_xticklabels(d["model"].to_list())
    ax.set_title(f"Interval coverage vs nominal (h={h})"); ax.set_ylabel("empirical coverage")
    ax.legend(fontsize=7); ax.grid(alpha=0.3)
    return _png_b64(fig)


def fig_bias_by_ivbucket(cond_iv: pl.DataFrame) -> str | None:
    h = C.PRIMARY_HORIZON
    d = cond_iv.filter(pl.col("horizon") == h)
    if d.is_empty():
        return None
    fig, ax = plt.subplots(figsize=(6, 3.2))
    for model in sorted(d["model"].unique().to_list()):
        m = d.filter(pl.col("model") == model).sort("iv_pctile_bucket")
        ax.plot(m["iv_pctile_bucket"], m["log_bias"], marker="o", lw=1, label=model)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_title(f"Conditional log-bias by IV-percentile bucket (h={h}); 0 = unbiased")
    ax.set_xlabel("IV-percentile bucket (0=low .. 4=high)"); ax.set_ylabel("log bias")
    ax.legend(fontsize=7); ax.grid(alpha=0.3)
    return _png_b64(fig)


def fig_iv_slopes(iv_diag: pl.DataFrame) -> str:
    h = C.PRIMARY_HORIZON
    d = iv_diag.filter(pl.col("horizon") == h).sort("slope")
    fig, ax = plt.subplots(figsize=(6, 3.2))
    colors = ["#2a8" if v > 0 else "#c33" for v in d["slope"]]
    ax.bar(d["model"], d["slope"], color=colors)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_title(f"§5 incremental-skill slope (h={h}); >0 = adds info beyond IV")
    ax.set_ylabel("slope: realized spread ~ model spread")
    ax.grid(axis="y", alpha=0.3)
    return _png_b64(fig)


# --------------------------------------------------------------------------- registry / progression
def _git_commit() -> str:
    try:
        import subprocess
        return subprocess.check_output(["git", "-C", str(C.REPO_ROOT), "rev-parse", "--short", "HEAD"],
                                       text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "unknown"


def _read_registry() -> pl.DataFrame:
    """Return the prior registry (for Progression diffs); empty frame if none exists."""
    return pl.read_parquet(C.RUN_REGISTRY) if C.RUN_REGISTRY.exists() else pl.DataFrame()


def _append_registry(run_id: str, git: str, tier1_by_h: pl.DataFrame, iv_diag: pl.DataFrame,
                     status: pl.DataFrame, prior: pl.DataFrame) -> None:
    """Append this run's headline rows to the registry."""
    rows = (
        tier1_by_h.join(iv_diag.select("model", "horizon", "qlike_gain_vs_iv"),
                        on=["model", "horizon"], how="left")
        .join(status.select("model", "status"), on="model", how="left")
        .with_columns(run_id=pl.lit(run_id), git=pl.lit(git))
        .select("run_id", "git", "model", "horizon", "qlike", "log_rmse",
                "cov90", "qlike_gain_vs_iv", "status")
    )
    C.RUN_REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    combined = rows if prior.is_empty() else pl.concat([prior, rows], how="diagonal_relaxed")
    combined.write_parquet(C.RUN_REGISTRY)


def progression_table(tier1_by_h: pl.DataFrame, prior: pl.DataFrame) -> pl.DataFrame:
    """Signed Δ QLIKE at the primary horizon vs the most recent prior run of each model."""
    h = C.PRIMARY_HORIZON
    cur = tier1_by_h.filter(pl.col("horizon") == h).select("model", pl.col("qlike").alias("qlike_now"))
    if prior.is_empty():
        return cur.with_columns(qlike_prev=pl.lit(None, dtype=pl.Float64),
                                delta=pl.lit(None, dtype=pl.Float64), trend=pl.lit("baseline"))
    last_run = prior.sort("run_id").select("run_id").unique().tail(1).item()
    prev = (prior.filter((pl.col("run_id") == last_run) & (pl.col("horizon") == h))
            .select("model", pl.col("qlike").alias("qlike_prev")))
    out = cur.join(prev, on="model", how="left").with_columns(delta=pl.col("qlike_now") - pl.col("qlike_prev"))
    return out.with_columns(
        trend=pl.when(pl.col("delta").is_null()).then(pl.lit("new"))
        .when(pl.col("delta") < -_PROG_TOL).then(pl.lit("progressed"))
        .when(pl.col("delta") > _PROG_TOL).then(pl.lit("regressed"))
        .otherwise(pl.lit("flat"))
    ).sort("qlike_now")


# --------------------------------------------------------------------------- assembly
def build_report(scored: pl.DataFrame, tables: dict, out_dir: Path, tier: int,
                 write_registry: bool = True) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    git = _git_commit()
    h = C.PRIMARY_HORIZON
    first_ticker = sorted(scored["ticker"].unique().to_list())[0]
    ref_ticker = "SPY" if "SPY" in scored["ticker"].unique().to_list() else first_ticker

    figs = {
        "QLIKE leaderboard": fig_leaderboard(tables["tier1_by_h"]),
        f"{ref_ticker} forecast vs realized": fig_forecast_vs_realized(scored, ref_ticker),
        "Interval coverage": fig_coverage(scored),
        "Conditional bias by IV bucket": fig_bias_by_ivbucket(tables["cond_ivbucket"]),
        "§5 incremental-skill slope": fig_iv_slopes(tables["iv_diag"]),
    }

    prior = _read_registry()
    if write_registry:
        _append_registry(run_id, git, tables["tier1_by_h"], tables["iv_diag"], tables["status"], prior)
    prog = progression_table(tables["tier1_by_h"], prior)

    _write_md(out_dir, run_id, git, tier, tables, prog)
    _write_html(out_dir, run_id, git, tier, tables, prog, figs)
    _write_json(out_dir, run_id, git, tables, prog)
    return {"run_id": run_id, "git": git, "out": str(out_dir)}


def _write_md(out_dir, run_id, git, tier, t, prog):
    h = C.PRIMARY_HORIZON
    parts = [
        f"# RV Forecasting Evaluation — {run_id}",
        f"_git {git} · primary horizon h={h} · models judged on this doc alone (§9)_\n",
        "## Verdict (§9 status)", md_table(t["status"]), "",
        "## Progression vs previous run (primary horizon, QLIKE; lower=better)",
        md_table(prog), "",
        f"## Tier-1 pooled by horizon (§3)", md_table(t["tier1_by_h"]), "",
        "## IV comparison & incremental skill (§5)", md_table(t["iv_diag"]), "",
        "## Post-shock calibration trap (§6)", md_table(t["postshock_flags"]), "",
        f"## Tier-1 by ticker (h={h})",
        md_table(t["tier1_by_ticker"].filter(pl.col("horizon") == h)
                 .select("model", "ticker", "qlike", "log_bias", "cov90")), "",
    ]
    if tier >= 2 and "mcs" in t:
        parts += ["## Model Confidence Set (§4)", md_table(t["mcs"]), "",
                  "## Diebold-Mariano vs HAR (§4)",
                  md_table(t["dm"].filter(pl.col("model_a") == "HAR")), ""]
    (out_dir / "report.md").write_text("\n".join(parts))


def _write_html(out_dir, run_id, git, tier, t, prog, figs):
    h = C.PRIMARY_HORIZON
    img_html = "".join(
        f"<h3>{name}</h3><img src='data:image/png;base64,{b64}'/>"
        for name, b64 in figs.items() if b64)
    sections = [
        ("Verdict (§9 status)", t["status"]),
        ("Progression vs previous run", prog),
        ("Tier-1 pooled by horizon (§3)", t["tier1_by_h"]),
        ("IV comparison & incremental skill (§5)", t["iv_diag"]),
        ("Post-shock calibration trap (§6)", t["postshock_flags"]),
        ("Within-group rank correlation (§3)", t["rankcorr"]),
    ]
    if tier >= 2 and "mcs" in t:
        sections += [("Model Confidence Set (§4)", t["mcs"]),
                     ("Diebold-Mariano vs HAR (§4)", t["dm"].filter(pl.col("model_a") == "HAR"))]
    tbl_html = "".join(f"<h3>{title}</h3>{html_table(df)}" for title, df in sections)
    html = f"""<!doctype html><meta charset=utf-8><title>RV eval {run_id}</title>
<style>body{{font-family:-apple-system,Arial,sans-serif;margin:2em;max-width:1100px}}
table{{border-collapse:collapse;margin:.5em 0;font-size:13px}}
th,td{{border:1px solid #ccc;padding:3px 8px;text-align:right}}th{{background:#eef}}
img{{max-width:100%;border:1px solid #eee;margin:.3em 0}}h3{{margin-top:1.2em;color:#234}}</style>
<h1>RV Forecasting Evaluation</h1><p>run <b>{run_id}</b> · git {git} · primary h={h}</p>
<h2>Figures</h2>{img_html}<h2>Tables</h2>{tbl_html}"""
    (out_dir / "report.html").write_text(html)


def _write_json(out_dir, run_id, git, t, prog):
    payload = {
        "run_id": run_id, "git": git, "primary_horizon": C.PRIMARY_HORIZON,
        "status": t["status"].to_dicts(),
        "tier1_by_horizon": t["tier1_by_h"].to_dicts(),
        "iv_diagnostic": t["iv_diag"].to_dicts(),
        "progression": prog.to_dicts(),
    }
    (out_dir / "metrics.json").write_text(json.dumps(payload, indent=2, default=str))
