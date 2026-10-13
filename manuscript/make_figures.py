from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = json.loads(
    (ROOT / "controlled" / "controlled_summary.json").read_text(encoding="utf-8")
)
OUT = ROOT / "manuscript" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({"font.size": 9, "figure.dpi": 160})

metrics = SUMMARY["metric_analysis"]
labels = ["Node F1", "Edge F1", "Static score"]
keys = ["node_f1", "edge_f1", "pre_execution_score"]
rho = np.array([metrics[k]["spearman_with_execution"] for k in keys])
rho_ci = np.array([metrics[k]["spearman_95ci"] for k in keys])
auc = np.array([metrics[k]["auroc"] for k in keys])
auc_ci = np.array([metrics[k]["auroc_95ci"] for k in keys])

fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.7), constrained_layout=True)
x = np.arange(len(labels))
axes[0].bar(x, rho, color=["#8da0cb", "#66c2a5", "#fc8d62"])
axes[0].errorbar(
    x,
    rho,
    yerr=np.vstack((rho - rho_ci[:, 0], rho_ci[:, 1] - rho)),
    fmt="none",
    ecolor="black",
    capsize=3,
    linewidth=0.8,
)
axes[0].set_title("Rank agreement with execution")
axes[0].set_ylabel("Spearman correlation")
axes[0].set_ylim(0, 1.05)
axes[1].bar(x, auc, color=["#8da0cb", "#66c2a5", "#fc8d62"])
axes[1].errorbar(
    x,
    auc,
    yerr=np.vstack((auc - auc_ci[:, 0], auc_ci[:, 1] - auc)),
    fmt="none",
    ecolor="black",
    capsize=3,
    linewidth=0.8,
)
axes[1].axhline(0.5, color="gray", linestyle="--", linewidth=0.8)
axes[1].set_title("Valid/invalid discrimination")
axes[1].set_ylabel("AUROC")
axes[1].set_ylim(0.45, 1.05)
for ax in axes:
    ax.set_xticks(x, labels, rotation=25, ha="right")
    ax.spines[["top", "right"]].set_visible(False)
fig.savefig(OUT / "metric_comparison.pdf", bbox_inches="tight")
fig.savefig(OUT / "metric_comparison.png", bbox_inches="tight")
plt.close(fig)

variants = SUMMARY["by_variant"]
order = [
    "reference",
    "valid_serialization",
    "valid_equivalent_tool",
    "valid_redundant_audit",
    "invalid_missing_required",
    "invalid_reversed_dependency",
    "invalid_wrong_tool",
]
short = ["Ref.", "Serialize", "Equivalent", "Audit", "Missing", "Reversed", "Wrong tool"]
node = [variants[k]["mean_node_f1"] for k in order]
edge = [variants[k]["mean_edge_f1"] for k in order]
success = [variants[k]["success_rate"] for k in order]

fig, ax = plt.subplots(figsize=(7.0, 2.8), constrained_layout=True)
x = np.arange(len(order))
width = 0.25
ax.bar(x - width, node, width, label="Node F1", color="#8da0cb")
ax.bar(x, edge, width, label="Edge F1", color="#66c2a5")
ax.bar(x + width, success, width, label="Execution success", color="#fc8d62")
ax.axvline(3.5, color="gray", linestyle="--", linewidth=0.8)
ax.text(1.5, 1.035, "valid", ha="center")
ax.text(5.0, 1.035, "invalid", ha="center")
ax.set_ylim(0, 1.12)
ax.set_ylabel("Mean score")
ax.set_xticks(x, short, rotation=20, ha="right")
ax.legend(ncol=3, frameon=False, loc="lower left")
ax.spines[["top", "right"]].set_visible(False)
fig.savefig(OUT / "variant_analysis.pdf", bbox_inches="tight")
fig.savefig(OUT / "variant_analysis.png", bbox_inches="tight")
plt.close(fig)

print(f"Wrote figures to {OUT}")
