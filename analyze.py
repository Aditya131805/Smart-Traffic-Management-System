import os
import pandas as pd
import matplotlib.pyplot as plt

csv_path = "logs/session_log.csv"
if not os.path.exists(csv_path):
    print(f"❌ Log file not found: {csv_path}")
    exit(1)

df = pd.read_csv(csv_path)

required_cols = {"frame", "count", "density", "level"}
missing = required_cols - set(df.columns)
if missing:
    print(f"❌ Missing columns in CSV: {missing}")
    exit(1)

print(f"📊 Total frames logged: {len(df)}")
print(df["level"].value_counts())

fig, axes = plt.subplots(2, 2, figsize=(14, 8))
fig.suptitle("Week 1 — Traffic Analysis Report", fontsize=14)

# 1. Vehicle count over time
axes[0,0].plot(df["frame"], df["count"], color="steelblue")
axes[0,0].set_title("Vehicle Count Over Time")
axes[0,0].set_xlabel("Frame")
axes[0,0].set_ylabel("Count")

# 2. Density over time
axes[0,1].plot(df["frame"], df["density"], color="orange")
axes[0,1].set_title("Traffic Density Over Time")
axes[0,1].set_xlabel("Frame")        # ✅ added
axes[0,1].set_ylabel("Density")

# 3. Congestion level pie chart
level_counts = df["level"].value_counts()
colors = {"LOW": "#00c800", "MEDIUM": "#ffa500", "HIGH": "#ff3030"}
axes[1,0].pie(level_counts, labels=level_counts.index,
              colors=[colors.get(l, "#aaaaaa") for l in level_counts.index],  # ✅ safe
              autopct="%1.1f%%")
axes[1,0].set_title("Congestion Level Distribution")

# 4. Vehicle count histogram
axes[1,1].hist(df["count"], bins=15, color="mediumpurple", edgecolor="black")
axes[1,1].set_title("Vehicle Count Distribution")
axes[1,1].set_xlabel("Vehicles per frame")

plt.tight_layout(rect=[0, 0, 1, 0.95])  # ✅ prevent suptitle overlap
plt.savefig("outputs/week1_report.png", dpi=150)
plt.show()
print("✅ Report saved: outputs/week1_report.png")