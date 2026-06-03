"""LSTM on a multi-feature rolling window (MODEL_PLAN.md §4 model 10).

One LSTM network per ticker (multi-head over horizons): the network consumes a
trailing 60-day window of the eight "macro covariate" features and emits, from a
per-horizon linear head, a forecast of ``log(target_var)`` for every horizon in
``C.HORIZONS`` at once. Forecasts are exponentiated back to ``target_var`` units
(lognormal-mean corrected) and dressed with lognormal quantiles consistently with
the benchmarks (`_lognormal_quantiles`).

Window inputs (confirmed against rv_eval/features.py output; all eight columns are
present in build_features):

    log_rv_d, log_iv, vix, vix_slope, iv_slope, skew_25d, rs_minus_5d, rs_plus_5d

Architecture: LSTM(hidden, num_layers, dropout) -> last hidden state -> one linear
head per horizon -> log(target_var). Training: MSE on the log target, Adam,
batch_size=64, seeds fixed (torch.manual_seed(0), numpy.random.seed(0)). ``epochs``
is NOT gridded: early-stopping on a 10% time-ordered within-train tail (cap 80).
``sigma`` (per horizon) is the residual std of log(target_var) on that held-out tail.

Device (MODEL_PLAN §3): MPS if available else CPU; model AND tensors are moved to it.

Unlike the per-(ticker, horizon) base behaviour, this model fits ONE network per
ticker that is shared across horizons (multi-head). It therefore overrides ``fit``
and ``predict`` from ``_PerKeyModel`` while still using ``_lognormal_quantiles`` and
emitting the exact required output schema. State is keyed by ``(ticker, h)`` so the
base-class contract (predict iterates ``self.state[(tk, h)]``) is preserved; every
horizon for a ticker points at the same shared network with its own head index.

Hard-case note (IBIT/MSOS): these tickers are data-starved. The model runs them
anyway and degrades gracefully — if a ticker has too few windowed samples to fit it
is simply skipped (no state, no rows), and any non-finite forecast row is dropped by
the base ``_lognormal_quantiles`` filter. The card worker will note non-convergence.

=============================================================================
HYPERPARAMETER SELECTION — tune-once-then-freeze (MODEL_PLAN §4)
=============================================================================
Grid (24 points):
    hidden      in {32, 64, 128}
    num_layers  in {1, 2}
    dropout     in {0.1, 0.2}
    lr          in {5e-4, 1e-3}
Initial point (grid bold in the plan): hidden=64, num_layers=2, dropout=0.1,
    lr=1e-3.
Split (leakage-safe, pre-OOS only):
    search-train = rows with date <  HPTUNE_VAL_START (2016-01-01)
    validation   = rows in [HPTUNE_VAL_START, OOS_START) = 2016-2017
    (no date >= OOS_START / 2018 is read during tuning)
Subset (to bound compute, MODEL_PLAN §4): tune ONLY on HPTUNE_DL_SUBSET =
    (SPY, QQQ, TLT, XLE).
Procedure: for each grid point fit one network per subset-ticker on search-train
    (windows ending strictly before 2016-01-01), early-stopping on a within-
    search-train time-ordered 10% tail; predict h=22 over the validation block;
    pool QLIKE@h22 across the subset; keep the lowest.
Metric: pooled QLIKE @ h=22 (HPTUNE_METRIC_HORIZON),
    QLIKE = mean( rv/rv_hat - log(rv/rv_hat) - 1 ),
    rv_hat = exp(pred + 0.5*sigma^2) (lognormal-mean forecast).

CHOSEN (frozen below) — see _tune_lstm.py / tuning run 2026-06-01:
    hidden=64, num_layers=1, dropout=0.1, lr=5e-4  (pooled QLIKE@h22=0.210004 on
    2016-2017, vs initial point (64,2,0.1,1e-3)=0.412826; full 24-point grid
    searched on HPTUNE_DL_SUBSET). All 2-layer configs scored 0.36-0.87 while
    1-layer configs clustered ~0.21 — num_layers=1 clearly wins.
=============================================================================
"""

from __future__ import annotations

import numpy as np
import polars as pl
import torch
import torch.nn as nn

from rv_eval import config as C
from rv_eval.model_contract import _PerKeyModel, _lognormal_quantiles

# Window inputs — confirmed present in rv_eval/features.build_features output.
WINDOW_FEATURES: list[str] = [
    "log_rv_d", "log_iv", "vix", "vix_slope", "iv_slope",
    "skew_25d", "rs_minus_5d", "rs_plus_5d",
]

_SEED = 0
WINDOW = 60                  # rolling lookback length (fixed)
BATCH_SIZE = 64              # fixed
MAX_EPOCHS = 80              # cap; epochs chosen by early stopping (not gridded)
_PATIENCE = 8                # early-stop patience on the within-train tail
_VAL_TAIL_FRAC = 0.10        # time-ordered within-train tail for early stop + sigma

DEVICE = torch.device("mps" if torch.backends.mps.is_available() else "cpu")


def _seed_everything() -> None:
    torch.manual_seed(_SEED)
    np.random.seed(_SEED)


class _LSTMNet(nn.Module):
    """LSTM trunk + one linear head per horizon -> log(target_var)."""

    def __init__(self, n_features: int, hidden: int, num_layers: int,
                 dropout: float, n_heads: int):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=n_features,
            hidden_size=hidden,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0.0,
            batch_first=True,
        )
        self.drop = nn.Dropout(dropout)
        self.heads = nn.ModuleList([nn.Linear(hidden, 1) for _ in range(n_heads)])

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, window, n_features); use the last time-step hidden state.
        out, _ = self.lstm(x)
        h_last = self.drop(out[:, -1, :])
        return torch.cat([head(h_last) for head in self.heads], dim=1)  # (batch, n_heads)


def _build_windows(feat: np.ndarray, dates: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Stack trailing WINDOW-length windows. feat rows are date-sorted, no nulls.

    Returns (windows, end_idx) where windows[i] = feat[end_idx[i]-WINDOW+1 : end_idx[i]+1]
    and end_idx[i] is the index of the window's terminal (prediction) day.
    """
    n = feat.shape[0]
    if n < WINDOW:
        return np.empty((0, WINDOW, feat.shape[1]), np.float32), np.empty(0, np.int64)
    ends = np.arange(WINDOW - 1, n)
    wins = np.stack([feat[e - WINDOW + 1: e + 1] for e in ends]).astype(np.float32)
    return wins, ends.astype(np.int64)


class LSTMRV(_PerKeyModel):
    """LSTM over a 60-day multi-feature window; one shared multi-head net per ticker.

    Predicts log(target_var) for all horizons jointly; rv_hat is the lognormal-mean
    back-transform and sigma the held-out-tail residual std (per horizon).
    """

    name = "LSTMRV"
    needs = WINDOW_FEATURES
    min_obs = 120              # need a real window history + a usable tail to fit

    # --- frozen hyperparameters (tune-once-then-freeze; see module docstring) ---
    HIDDEN = 64
    NUM_LAYERS = 1
    DROPOUT = 0.1
    LR = 5e-4

    def __init__(self):
        self.horizon_index = {h: i for i, h in enumerate(self.horizons)}

    # ---- training ----------------------------------------------------------
    def _train_ticker(self, feat: np.ndarray, targets: dict[int, np.ndarray],
                      valid_end: dict[int, np.ndarray]):
        """Fit one multi-head network on a single ticker's date-sorted features.

        feat: (n_days, n_features) standardized inputs, date-sorted, no nulls.
        targets[h]: log(target_var) aligned to feat rows (NaN where target missing).
        valid_end[h]: bool mask over feat rows where horizon h's target is present.
        Returns (net, mu, sd, sigma_by_h) or None if unfittable.
        """
        wins, ends = _build_windows(feat, None)
        if wins.shape[0] < 20:
            return None

        n_heads = len(self.horizons)
        # Per-window target matrix + validity mask aligned to window terminal day.
        Y = np.full((wins.shape[0], n_heads), np.nan, np.float32)
        M = np.zeros((wins.shape[0], n_heads), np.bool_)
        for h, i in self.horizon_index.items():
            t = targets[h][ends]
            v = valid_end[h][ends]
            Y[:, i] = t
            M[:, i] = v

        # need at least some window with at least one valid head
        any_valid = M.any(axis=1)
        if any_valid.sum() < 20:
            return None
        wins, Y, M = wins[any_valid], Y[any_valid], M[any_valid]

        # time-ordered within-train tail for early stopping + sigma
        n = wins.shape[0]
        n_tail = max(5, int(round(n * _VAL_TAIL_FRAC)))
        if n - n_tail < 10:
            n_tail = max(1, n - 10)
        tr_w, tr_y, tr_m = wins[:-n_tail], Y[:-n_tail], M[:-n_tail]
        va_w, va_y, va_m = wins[-n_tail:], Y[-n_tail:], M[-n_tail:]
        if tr_w.shape[0] < 5 or va_w.shape[0] < 1:
            return None

        _seed_everything()
        net = _LSTMNet(feat.shape[1], self.HIDDEN, self.NUM_LAYERS,
                       self.DROPOUT, n_heads).to(DEVICE)
        opt = torch.optim.Adam(net.parameters(), lr=self.LR)

        tr_w_t = torch.from_numpy(tr_w).to(DEVICE)
        tr_y_t = torch.from_numpy(np.nan_to_num(tr_y)).to(DEVICE)
        tr_m_t = torch.from_numpy(tr_m.astype(np.float32)).to(DEVICE)
        va_w_t = torch.from_numpy(va_w).to(DEVICE)
        va_y_t = torch.from_numpy(np.nan_to_num(va_y)).to(DEVICE)
        va_m_t = torch.from_numpy(va_m.astype(np.float32)).to(DEVICE)

        n_tr = tr_w_t.shape[0]
        g = torch.Generator().manual_seed(_SEED)
        best_val = float("inf")
        best_state = None
        bad = 0
        for _ in range(MAX_EPOCHS):
            net.train()
            perm = torch.randperm(n_tr, generator=g)
            for s in range(0, n_tr, BATCH_SIZE):
                idx = perm[s: s + BATCH_SIZE]
                xb, yb, mb = tr_w_t[idx], tr_y_t[idx], tr_m_t[idx]
                opt.zero_grad()
                pred = net(xb)
                se = (pred - yb) ** 2 * mb
                denom = mb.sum()
                if denom.item() == 0:
                    continue
                loss = se.sum() / denom
                loss.backward()
                opt.step()
            # masked MSE on the held-out tail
            net.eval()
            with torch.no_grad():
                vp = net(va_w_t)
                vse = (vp - va_y_t) ** 2 * va_m_t
                vdenom = va_m_t.sum()
                vloss = (vse.sum() / vdenom).item() if vdenom.item() > 0 else float("inf")
            if vloss < best_val - 1e-6:
                best_val = vloss
                best_state = {k: v.detach().cpu().clone() for k, v in net.state_dict().items()}
                bad = 0
            else:
                bad += 1
                if bad >= _PATIENCE:
                    break
        if best_state is not None:
            net.load_state_dict(best_state)

        # per-horizon residual std (sigma in log space) on the held-out tail
        net.eval()
        with torch.no_grad():
            vp = net(va_w_t).cpu().numpy()
        sigma_by_h: dict[int, float] = {}
        for h, i in self.horizon_index.items():
            mask = va_m[:, i]
            if mask.sum() > 1:
                resid = va_y[mask, i] - vp[mask, i]
                sigma_by_h[h] = max(float(np.std(resid)), 1e-3)
            else:
                sigma_by_h[h] = 0.5
        return net, sigma_by_h

    def fit(self, X: pl.DataFrame, y: pl.DataFrame) -> None:
        self.state: dict[tuple[str, int], object] = {}
        # per-ticker shared net + standardization (computed on the fit slice only)
        self._nets: dict[str, object] = {}
        self._norm: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        # last (WINDOW-1) RAW feature rows per ticker, so predict() can prepend the
        # backward-only context the test slice lacks (walk-forward passes only the
        # ~21-row test month to predict — see _predict_one). Stored pre-standardization.
        self._ctx: dict[str, np.ndarray] = {}

        # wide target matrix: one column per horizon
        ywide = (y.select("ticker", "date", "horizon", "target_var")
                 .filter(pl.col("horizon").is_in(list(self.horizons)))
                 .pivot(values="target_var", index=["ticker", "date"],
                        on="horizon", aggregate_function="first"))
        xy = X.join(ywide, on=["ticker", "date"], how="left")

        for (tk,), sub in xy.partition_by("ticker", as_dict=True).items():
            sub = sub.sort("date").drop_nulls(self.needs)
            if sub.height < self.min_obs:
                continue
            feat = sub.select(self.needs).to_numpy().astype(np.float64)
            mu = feat.mean(axis=0)
            sd = feat.std(axis=0)
            sd = np.where(sd < 1e-8, 1.0, sd)
            feat_std = ((feat - mu) / sd).astype(np.float32)

            targets: dict[int, np.ndarray] = {}
            valid_end: dict[int, np.ndarray] = {}
            for h in self.horizons:
                col = str(h)
                if col in sub.columns:
                    tv = sub[col].to_numpy().astype(np.float64)
                else:
                    tv = np.full(sub.height, np.nan)
                valid = np.isfinite(tv) & (tv > 0)
                logt = np.where(valid, np.log(np.where(valid, tv, 1.0)), np.nan)
                targets[h] = logt.astype(np.float32)
                valid_end[h] = valid

            res = self._train_ticker(feat_std, targets, valid_end)
            if res is None:
                continue
            net, sigma_by_h = res
            self._nets[tk] = net
            self._norm[tk] = (mu, sd)
            # cache the backward-only context: the last WINDOW-1 RAW feature rows
            # (these are strictly before the upcoming test block, so no leakage).
            self._ctx[tk] = feat[-(WINDOW - 1):].copy()
            for h in self.horizons:
                self.state[(tk, h)] = (tk, h, sigma_by_h[h])

    # ---- prediction --------------------------------------------------------
    def _predict_one(self, state, sub: pl.DataFrame, h: int):
        tk, h_, s = state
        net = self._nets.get(tk)
        mu_sd = self._norm.get(tk)
        n = sub.height
        out = np.full(n, np.nan)
        if net is None or mu_sd is None:
            return out, np.full(n, s)
        mu, sd = mu_sd

        # raw test features (sub is this ticker's test slice, sorted by date)
        feat_test_raw = sub.select(self.needs).to_numpy().astype(np.float64)
        finite_row = np.isfinite(feat_test_raw).all(axis=1)  # per-test-row validity

        # Prepend the backward-only context cached in fit() so each test date has its
        # full 60-day window. The walk-forward passes only the ~21-row test month to
        # predict, so without this every fold would have n < WINDOW and emit nothing.
        ctx = getattr(self, "_ctx", {}).get(tk)
        n_ctx = 0 if ctx is None else ctx.shape[0]
        if ctx is None:
            feat_all_raw = feat_test_raw
        else:
            feat_all_raw = np.vstack([ctx, feat_test_raw])  # test rows occupy the LAST n

        # standardize the combined matrix with THIS ticker's (mu, sd); fill nulls with
        # mu for windowing only (never imputes a kept prediction — see finite_row below)
        feat_all_filled = np.where(np.isfinite(feat_all_raw), feat_all_raw, mu)
        feat_all_std = ((feat_all_filled - mu) / sd).astype(np.float32)

        # terminal position of each test row j in feat_all is (n_ctx + j); a window is
        # valid only if it has WINDOW preceding rows available (n_ctx + j >= WINDOW-1).
        head_i = self.horizon_index[h]
        starts = n_ctx + np.arange(n) - (WINDOW - 1)   # window start index per test row
        has_window = starts >= 0
        if not has_window.any():
            return out, np.full(n, s)

        valid_j = np.where(has_window)[0]
        wins = np.stack([
            feat_all_std[n_ctx + j - WINDOW + 1: n_ctx + j + 1] for j in valid_j
        ]).astype(np.float32)
        net.eval()
        with torch.no_grad():
            preds = net(torch.from_numpy(wins).to(DEVICE)).cpu().numpy()[:, head_i]
        mvals = np.exp(preds + 0.5 * s * s)  # lognormal mean -> target_var units
        # drop any test row whose OWN feature vector is non-finite (no imputed forecasts)
        mvals = np.where(finite_row[valid_j], mvals, np.nan)
        out[valid_j] = mvals
        return out, np.full(n, s)
