# Install GEM Heatmap on your computer (beginner guide)

You do **not** need to know Python or VS Code. Follow these steps once.

## Do I connect to your PC?

| | |
|--|--|
| **This cloud chat** | I run scans here when you type `scan`. |
| **Your computer** | Separate. I do **not** see your PC unless you open this project in **Cursor** on your machine. |
| **This heatmap app** | Runs **on your PC** after you install once. Same signals, visual heatmap. |

## What you get

- **Heatmap** — each instrument is a row; colour = bullish (green) or bearish (red)
- **Table** — RSI, signal name, price
- **Scan now** button — refreshes live data
- Same **32 instruments** as your cloud watchlist

---

## Windows (easiest)

1. Install **Python 3.10+** from https://www.python.org/downloads/  
   - Check **“Add python to PATH”** during install.

2. Copy the **stock-screener** folder to your PC (from GitHub or Cursor).

3. **Double-click:** `START_HEATMAP.bat`  
   - First time: installs automatically (wait 5–10 minutes).  
   - Your browser opens the heatmap.

4. Click **Scan now** in the left sidebar.

**Stop the app:** close the black command window.

---

## Mac / Linux

```bash
chmod +x install.sh start_heatmap.sh
./install.sh
./start_heatmap.sh
```

Browser opens → click **Scan now**.

---

## VS Code?

Optional. You only need VS Code if you want to edit code.  
To **use** the heatmap: double-click `START_HEATMAP.bat` — no VS Code required.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| “Python not found” | Reinstall Python with **Add to PATH** |
| Browser empty | Wait for install to finish; run `START_HEATMAP.bat` again |
| Scan slow | Normal for 32 symbols (1–3 minutes) |

---

## Need help?

In **Cursor** on your PC, open this folder and ask the agent:  
*“Run START_HEATMAP.bat and fix any errors.”*
