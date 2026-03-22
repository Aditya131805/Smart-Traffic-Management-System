import ast
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from datetime import datetime
import os

def parse_violations(val):                  # ✅ robust parser
    try:
        items = ast.literal_eval(val)
        return items if isinstance(items, list) else [str(val)]
    except:
        return ["UNKNOWN"]

def generate_report():
    print("📊 Generating project report...\n")

    os.makedirs("outputs", exist_ok=True)   # ✅ ensure output dir exists

    try:
        with sqlite3.connect("logs/traffic.db") as conn:   # ✅ context manager
            df_log = pd.read_sql(
            "SELECT * FROM traffic_log WHERE frame_id < 100000 ORDER BY frame_id", 
            conn
            )
            df_challans  = pd.read_sql("SELECT * FROM challans", conn)
            df_incidents = pd.read_sql("SELECT * FROM incidents", conn)
    except Exception as e:
        print(f"❌ Database error: {e}")
        return

    if df_log.empty:
        print("❌ No data found! Run main.py first.")
        return

    fig = plt.figure(figsize=(18, 12))
    fig.patch.set_facecolor('#0e1117')
    gs  = gridspec.GridSpec(3, 3, figure=fig)

    fig.suptitle(
        "Smart Traffic Management System — Project Report",
        fontsize=16, color="white", y=0.98
    )

    text_color = "white"
    grid_color = "#333333"

    # 1. Vehicle count over time
    ax1 = fig.add_subplot(gs[0, :2])
    ax1.set_facecolor('#1a1a2e')
    ax1.plot(df_log["frame_id"], df_log["vehicle_count"],
             color="#00b4d8", linewidth=0.8)
    ax1.set_title("Vehicle Count Over Time", color=text_color)
    ax1.set_xlabel("Frame", color=text_color)
    ax1.set_ylabel("Vehicles", color=text_color)
    ax1.tick_params(colors=text_color)
    ax1.grid(color=grid_color, alpha=0.3)

    # 2. Congestion pie
    ax2 = fig.add_subplot(gs[0, 2])
    ax2.set_facecolor('#1a1a2e')
    level_counts = df_log["congestion"].value_counts()
    colors_pie   = {"LOW": "#00c800", "MEDIUM": "#ffa500", "HIGH": "#ff3030"}
    ax2.pie(
        level_counts,
        labels=level_counts.index,
        colors=[colors_pie.get(l, "gray") for l in level_counts.index],
        autopct="%1.1f%%",
        textprops={"color": text_color}
    )
    ax2.set_title("Congestion Distribution", color=text_color)

    # 3. Density over time
    ax3 = fig.add_subplot(gs[1, :2])
    ax3.set_facecolor('#1a1a2e')
    ax3.fill_between(df_log["frame_id"], df_log["density"],
                     color="#f77f00", alpha=0.6)
    ax3.set_title("Traffic Density Over Time", color=text_color)
    ax3.set_xlabel("Frame", color=text_color)
    ax3.set_ylabel("Density", color=text_color)
    ax3.tick_params(colors=text_color)
    ax3.grid(color=grid_color, alpha=0.3)

    # 4. Police score
    ax4 = fig.add_subplot(gs[1, 2])
    ax4.set_facecolor('#1a1a2e')
    ax4.plot(df_log["frame_id"], df_log["police_score"],
             color="#e63946", linewidth=0.8)
    ax4.axhline(y=0.35, color="orange", linestyle="--",
                label="Alert threshold")
    ax4.set_title("Police Need Score", color=text_color)
    ax4.tick_params(colors=text_color)
    ax4.legend(facecolor="#1a1a2e", labelcolor=text_color)
    ax4.grid(color=grid_color, alpha=0.3)

    # 5. Violations by type
    ax5 = fig.add_subplot(gs[2, 0])
    ax5.set_facecolor('#1a1a2e')
    if not df_challans.empty:
        viol_counts = (
            df_challans["violations"]
            .apply(parse_violations)    # ✅ robust parsing
            .explode()                  # ✅ one row per violation type
            .value_counts()
        )
        bar_colors = ["#e63946","#f77f00","#2dc653","#00b4d8","#9b5de5"]
        ax5.bar(viol_counts.index, viol_counts.values,
                color=bar_colors[:len(viol_counts)])    # ✅ safe color indexing
        ax5.set_title("Violations by Type", color=text_color)
        ax5.tick_params(colors=text_color)
    else:
        ax5.text(0.5, 0.5, "No challans", ha="center",
                 color=text_color, transform=ax5.transAxes)

    # 6. Signal distribution
    ax6 = fig.add_subplot(gs[2, 1])
    ax6.set_facecolor('#1a1a2e')
    dir_counts = df_log["green_dir"].value_counts()
    ax6.bar(dir_counts.index, dir_counts.values,
            color=["#2dc653","#f77f00","#00b4d8","#e63946"])
    ax6.set_title("Signal Green Distribution", color=text_color)
    ax6.tick_params(colors=text_color)

    # 7. Summary stats
    ax7 = fig.add_subplot(gs[2, 2])
    ax7.set_facecolor('#1a1a2e')
    ax7.axis("off")
    total_fines = df_challans["total_fine"].sum() if not df_challans.empty else 0
    stats = [
        f"Total Frames   : {len(df_log):,}",
        f"Avg Vehicles   : {df_log['vehicle_count'].mean():.1f}",
        f"Max Vehicles   : {df_log['vehicle_count'].max()}",
        f"Avg Density    : {df_log['density'].mean():.3f}",
        f"Total Challans : {len(df_challans)}",
        f"Total Fines    : Rs.{total_fines:,}",   # ✅ cleaner, no inline condition
        f"Total Incidents: {len(df_incidents)}",
        f"Report Date    : {datetime.now().strftime('%Y-%m-%d')}",
    ]
    for i, stat in enumerate(stats):
        ax7.text(0.05, 0.9 - i*0.11, stat,
                 color=text_color, fontsize=9,
                 transform=ax7.transAxes,
                 fontfamily="monospace")
    ax7.set_title("Summary Statistics", color=text_color)

    plt.tight_layout(rect=[0, 0, 1, 0.96])     # ✅ prevent suptitle clipping
    report_path = "outputs/project_report.png"
    plt.savefig(report_path, dpi=150,
                bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.show()
    print(f"✅ Report saved: {report_path}")

if __name__ == "__main__":
    generate_report()