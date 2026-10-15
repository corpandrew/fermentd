"""Draws docs/images/wiring.svg and wiring.png.  Run: python docs/images/wiring.py (needs matplotlib)."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).resolve().parent
RED, BLK, YEL, BLU, GRN, ORG, GRY = "#d62728", "#222222", "#e0b000", "#1f77b4", "#2ca02c", "#ff7f0e", "#888888"

fig, ax = plt.subplots(figsize=(13, 8.2))
ax.set_xlim(0, 130)
ax.set_ylim(0, 82)
ax.axis("off")


def box(x, y, w, h, title, sub="", color="#f4f4f4", edge="#333", dashed=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.2", fc=color, ec=edge,
                                lw=1.6, ls="--" if dashed else "-"))
    ax.text(x + w / 2, y + h - 2.2, title, ha="center", va="top", fontsize=11, weight="bold")
    if sub:
        ax.text(x + w / 2, y + h - 5.6, sub, ha="center", va="top", fontsize=8.5, color="#444")


def wire(points, color, label=None, dashed=False, lx=None, ly=None):
    xs, ys = zip(*points)
    ax.plot(xs, ys, color=color, lw=2.6, ls=(0, (5, 3)) if dashed else "-", solid_capstyle="round")
    if label:
        ax.text(lx, ly, label, fontsize=8.5, color=color, weight="bold", ha="center",
                bbox=dict(fc="white", ec="none", pad=0.6))


ax.text(65, 80, "fermentd wiring (Raspberry Pi 3 Model B)", ha="center", fontsize=15, weight="bold")
ax.text(65, 76.6, "solid = wired today    dashed = planned (HX711 scale is owned but not wired yet)",
        ha="center", fontsize=9.5, color="#555")

# Raspberry Pi header
box(2, 14, 30, 58, "Raspberry Pi 3B", "40-pin header (physical pin numbers)", color="#e8f3e8", edge=GRN)
pins = [  # (y, pin, name, color)
    (60, 1, "3.3V", RED), (55, 6, "GND", BLK), (50, 7, "GPIO4 (1-Wire)", YEL),
    (38, 17, "3.3V", RED), (33, 9, "GND", BLK), (28, 29, "GPIO5 (HX711 DT)", BLU), (23, 31, "GPIO6 (HX711 SCK)", ORG),
]
for y, pin, name, c in pins:
    ax.add_patch(plt.Circle((29, y), 1.1, color=c))
    ax.text(26.5, y, f"pin {pin:>2}  {name}", ha="right", va="center", fontsize=9, family="monospace")
ax.text(17, 44, "via breadboard + GPIO breakout", ha="center", fontsize=8, color="#555", style="italic")
ax.text(17, 17.5, "Wi-Fi (built in)", ha="center", fontsize=9, color="#555")

# DS18B20 adapter
box(52, 47, 28, 21, "DS18B20 adapter board", "screw terminals, built-in pull-up", color="#fff7e0", edge=YEL)
for y, lab, c in [(60, "VCC", RED), (55, "GND", BLK), (50, "DAT", YEL)]:
    ax.add_patch(plt.Circle((52, y), 1.0, color=c))
    ax.text(54.5, y, lab, va="center", fontsize=9, family="monospace")
wire([(30, 60), (52, 60)], RED, "VCC -> pin 1", lx=41, ly=61.2)
wire([(30, 55), (52, 55)], BLK, "GND -> pin 6", lx=41, ly=56.2)
wire([(30, 50), (52, 50)], YEL, "DAT -> pin 7", lx=41, ly=51.2)
box(96, 51, 30, 12, "DS18B20 probe", "waterproof, on/among the vessels", color="#fff7e0", edge=YEL)
wire([(80, 56), (96, 56)], GRY, "3-wire cable", lx=88, ly=57.3)

# HX711 (planned)
box(52, 18, 28, 26, "HX711 board", "24-bit load-cell ADC (planned)", color="#e8f0fb", edge=BLU, dashed=True)
for y, lab, c in [(36, "VCC", RED), (31, "GND", BLK), (26, "DT", BLU), (21.5, "SCK", ORG)]:
    ax.add_patch(plt.Circle((52, y), 1.0, color=c))
    ax.text(54.5, y, lab, va="center", fontsize=9, family="monospace")
wire([(30, 38), (40, 38), (40, 36), (52, 36)], RED, "VCC -> 3.3V", dashed=True, lx=46, ly=37.2)
wire([(30, 33), (40, 33), (40, 31), (52, 31)], BLK, "GND", dashed=True, lx=46, ly=32.2)
wire([(30, 28), (40, 28), (40, 26), (52, 26)], BLU, "DT -> pin 29", dashed=True, lx=46, ly=27.2)
wire([(30, 23), (40, 23), (40, 21.5), (52, 21.5)], ORG, "SCK -> pin 31", dashed=True, lx=46, ly=22.6)
box(96, 22, 30, 16, "10 kg load cell", "E+ E- A+ A- to HX711\n(vessel sits on it)", color="#e8f0fb", edge=BLU,
    dashed=True)
wire([(80, 30), (96, 30)], GRY, "4-wire bridge", dashed=True, lx=88, ly=31.3)

# Heat path
box(40, 1, 26, 12, "Teckin SP10 plug", "Tuya, local LAN control\nswitch DP1, countdown DP11", color="#fdecec",
    edge=RED)
box(74, 1, 22, 12, "Seedling heat mat", "plugged into the Teckin", color="#fdecec", edge=RED)
box(102, 1, 25, 12, "Cooler = chamber", "mat + bottles + probe inside", color="#eeeeee", edge=GRY)
wire([(17, 14), (17, 7), (40, 7)], GRN, "Wi-Fi (LAN)", dashed=False, lx=28, ly=8.3)
wire([(66, 7), (74, 7)], RED)
wire([(96, 7), (102, 7)], GRY)
ax.text(28, 4.2, "no wires: tinytuya over Wi-Fi", ha="center", fontsize=8, color="#555", style="italic")

fig.tight_layout()
fig.savefig(OUT / "wiring.svg")
fig.savefig(OUT / "wiring.png", dpi=130)
print("wrote", OUT / "wiring.svg", OUT / "wiring.png")
