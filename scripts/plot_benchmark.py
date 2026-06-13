import os
import matplotlib.pyplot as plt
import numpy as np

# Ensure target directory exists
os.makedirs("docs/paper", exist_ok=True)

# Set up clean styling rules for premium/academic looks
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
plt.rcParams['axes.edgecolor'] = '#CCCCCC'
plt.rcParams['axes.linewidth'] = 0.8
plt.rcParams['xtick.color'] = '#333333'
plt.rcParams['ytick.color'] = '#333333'
plt.rcParams['grid.color'] = '#EEEEEE'
plt.rcParams['grid.linewidth'] = 0.5

# -------------------------------------------------------------
# Chart 1: Benchmark F1-score Comparison
# -------------------------------------------------------------
models = [
    "CogAlpha",
    "AlphaSharpe",
    "EDINET-Bench\n(Sugiura et al. 2026)",
    "AlphaPROBE",
    "EBISU\n(Peng et al. 2026)",
    "FactorMiner",
    "AAARTS (Ours)"
]
f1_scores = [0.55, 0.58, 0.59, 0.60, 0.61, 0.64, 0.67]

# Colors: Steel/slate gray for baselines, bright active indigo/coral for AAARTS
colors = ['#8892B0'] * 6 + ['#3B82F6']  # Indigo blue for AAARTS to stand out

fig, ax = plt.subplots(figsize=(9, 5.5), dpi=300)
bars = ax.barh(models, f1_scores, color=colors, height=0.6, edgecolor='none')

# Add values on the bars
for bar in bars:
    width = bar.get_width()
    label_color = '#FFFFFF' if bar.get_facecolor() == (59/255, 130/255, 246/255, 1.0) else '#333333'
    # Adjust position slightly for readability
    if width > 0.1:
        ax.text(width - 0.05, bar.get_y() + bar.get_height()/2, f"{width:.2f}",
                va='center', ha='right', color=label_color, fontweight='bold', fontsize=10)
    else:
        ax.text(width + 0.01, bar.get_y() + bar.get_height()/2, f"{width:.2f}",
                va='center', ha='left', color='#333333', fontsize=10)

# Styling
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('#CCCCCC')
ax.spines['bottom'].set_color('#CCCCCC')
ax.xaxis.grid(True, linestyle='--', alpha=0.7)
ax.set_axisbelow(True)

ax.set_title("Earnings Forecast F1-Score Comparison", fontsize=14, fontweight='bold', pad=15, color='#1E293B')
ax.set_xlabel("F1-Score (Higher is Better)", fontsize=11, labelpad=10, color='#475569')
ax.set_xlim(0, 0.75)

plt.tight_layout()
plt.savefig("docs/paper/benchmark_comparison_chart.png", bbox_inches='tight', transparent=True)
plt.close()
print("Saved docs/paper/benchmark_comparison_chart.png")

# -------------------------------------------------------------
# Chart 2: Ablation Study Comparison (Accuracy vs F1-score)
# -------------------------------------------------------------
categories = ['Financials Only', 'Texts Only', 'Combined\n(AAARTS)']
accuracy = [52.00, 56.00, 58.00]  # in %
f1_val = [0.59, 0.68, 0.67]        # in decimal

x = np.arange(len(categories))
width = 0.35  # width of the bars

fig, ax1 = plt.subplots(figsize=(8, 5.5), dpi=300)

# Plot Accuracy
color_acc = '#10B981'  # Teal/Green
rects1 = ax1.bar(x - width/2, accuracy, width, label='Accuracy (%)', color=color_acc, alpha=0.85)
ax1.set_ylabel('Accuracy (%)', color='#0F766E', fontweight='bold', fontsize=11)
ax1.tick_params(axis='y', labelcolor='#0F766E')
ax1.set_ylim(0, 70)

# Instantiate a second axes that shares the same x-axis
ax2 = ax1.twinx()
color_f1 = '#6366F1'  # Indigo
rects2 = ax2.bar(x + width/2, f1_val, width, label='F1-Score', color=color_f1, alpha=0.85)
ax2.set_ylabel('F1-Score', color='#4338CA', fontweight='bold', fontsize=11)
ax2.tick_params(axis='y', labelcolor='#4338CA')
ax2.set_ylim(0, 0.8)

# Add value labels on top of the bars
def autolabel_acc(rects, ax):
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f"{height:.1f}%",
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=9, fontweight='bold', color='#115E59')

def autolabel_f1(rects, ax):
    for rect in rects:
        height = rect.get_height()
        ax.annotate(f"{height:.2f}",
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=9, fontweight='bold', color='#3730A3')

autolabel_acc(rects1, ax1)
autolabel_f1(rects2, ax2)

# Styling and labels
ax1.set_xticks(x)
ax1.set_xticklabels(categories, fontsize=10, fontweight='bold', color='#333333')
ax1.spines['top'].set_visible(False)
ax2.spines['top'].set_visible(False)
ax1.spines['left'].set_color(color_acc)
ax1.spines['right'].set_visible(False)
ax2.spines['right'].set_color(color_f1)
ax2.spines['left'].set_visible(False)

# Title
plt.title("Ablation Study: Textual vs. Numerical Modalities", fontsize=14, fontweight='bold', pad=20, color='#1E293B')

# Legends
lines = [rects1, rects2]
labels = [l.get_label() for l in lines]
ax1.legend(lines, labels, loc='upper left')

plt.tight_layout()
plt.savefig("docs/paper/ablation_study_chart.png", bbox_inches='tight', transparent=True)
plt.close()
print("Saved docs/paper/ablation_study_chart.png")
