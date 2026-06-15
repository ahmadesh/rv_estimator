#!/bin/zsh
# Build the WIDE-universe pipeline cache (30 names) for the cross-sectional breadth experiment.
# Writes to strategy_backtest/data_wide/ (the original 10-name cache in data/ is untouched).
# Idempotent: each stage overwrites its own outputs; walkforward upserts per ticker. Re-run on
# interruption — completed model parquets are refreshed, not corrupted.
set -e
cd "$(dirname "$0")/../.."          # repo root

export SB_EXTRA_TICKERS="XLI,XLU,XLP,XLV,XLY,XLB,DIA,EFA,FXI,EWZ,GDX,SLV,USO,XOP,SMH,XBI,IBB,KRE,XRT,IYR"
export SB_DATA_ROOT="strategy_backtest/data_wide"

echo "=== [1/3] prepare_panel (inputs + targets, 30 tickers) ==="
.venv/bin/python -m strategy_backtest.pipeline.setup.prepare_panel

echo "=== [2/3] features ==="
.venv/bin/python -m strategy_backtest.pipeline.features

echo "=== [3/3] walk-forward: 4 HAR components then the ensemble ==="
for m in candidate_models.harq:HARQ candidate_models.har_rs:HARRS \
         candidate_models.har_cj:HARCJ candidate_models.har_rs_iv_q:HARRSIVQ \
         candidate_models.ensemble_top:EnsembleTopK ; do
  echo "--- $m ---"
  .venv/bin/python -m strategy_backtest.pipeline.walkforward \
      --model strategy_backtest.pipeline.$m --universe all
done
echo "DONE wide cache -> strategy_backtest/data_wide/"
