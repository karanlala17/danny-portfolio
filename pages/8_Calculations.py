"""Calculations — explains every formula, method, and conversion used in the dashboard."""

import streamlit as st
st.set_page_config(page_title="Calculations", page_icon="📐", layout="wide")

st.title("How Calculations Work")
st.markdown(
    "This page explains the methodology behind every metric on the dashboard, "
    "with formulas and worked examples."
)

# ── 1. Lot Matching Method ──────────────────────────────────────────────────
st.header("1. Lot Matching — FIFO (First In, First Out)")
st.markdown("""
When you sell shares, the system needs to decide **which buy lot** the sale is matched against.
We use **FIFO**: the **oldest** (first) buy is consumed first.

**Example — Microsoft (MSFT), JB Broker:**

| # | Date | Action | Qty | Price (USD) |
|---|------|--------|-----|-------------|
| 1 | 11-Jul-2023 | BUY | 70 | 360.37 |
| 2 | 15-Feb-2024 | BUY | 60 | 406.44 |
| 3 | 14-Jun-2024 | SELL | 16 | 439.55 |

**FIFO matching for the SELL of 16 shares:**
- The oldest buy is Lot 1 (70 shares @ 360.37).
- 16 shares are taken from Lot 1. Lot 1 now has 70 - 16 = **54 shares** remaining.
- Lot 2 (60 shares @ 406.44) is untouched.

**Remaining holdings:** 54 @ 360.37 + 60 @ 406.44 = **114 shares**.

> **Note:** In certain cases, specific buy/sell transactions are matched directly
> against each other (overriding FIFO) when the client has indicated a
> particular trade pair.
""")

# ── 2. Average Cost ─────────────────────────────────────────────────────────
st.header("2. Average Cost per Share")
st.markdown("""
After FIFO matching removes sold shares, the **average cost** of the remaining
lots is calculated as:

```
Average Cost = Total Cost of Remaining Lots / Total Remaining Shares
```

**Continuing the MSFT example above:**

| Lot | Remaining Qty | Price | Cost |
|-----|---------------|-------|------|
| 1 | 54 | 360.37 | 19,459.98 |
| 2 | 60 | 406.44 | 24,386.40 |
| **Total** | **114** | | **43,846.38** |

```
Average Cost = 43,846.38 / 114 = $384.62 per share
```
""")

# ── 3. Market Value ─────────────────────────────────────────────────────────
st.header("3. Market Value")
st.markdown("""
```
Market Value = Quantity Held x Current Market Price
```

Prices are fetched live from Yahoo Finance. If the market is closed, the
**last available closing price** is used.

**Example — holding 114 MSFT shares, current price $430.00:**
```
Market Value = 114 x 430.00 = $49,020.00 (USD)
```
""")

# ── 4. Unrealised P&L ──────────────────────────────────────────────────────
st.header("4. Unrealised P&L (Profit & Loss)")
st.markdown("""
Profit or loss on shares you **still hold** — not yet "realised" by selling.

```
Unrealised P&L = Market Value - Total Cost
Unrealised P&L % = (Unrealised P&L / Total Cost) x 100
```

**Example — MSFT (114 shares):**
```
Market Value  = $49,020.00
Total Cost    = $43,846.38
Unrealised P&L = $49,020.00 - $43,846.38 = $5,173.62
Unrealised %   = (5,173.62 / 43,846.38) x 100 = 11.80%
```
""")

# ── 5. Realised P&L ────────────────────────────────────────────────────────
st.header("5. Realised P&L")
st.markdown("""
Profit or loss on shares that have been **sold**, calculated per matched lot.

```
Realised P&L = Sale Proceeds - Cost of Matched Lot
Realised P&L % = (Realised P&L / Cost) x 100
```

**Example — MSFT SELL 16 shares @ 439.55 (matched against Lot 1 @ 360.37):**
```
Cost     = 16 x 360.37 = $5,765.92
Proceeds = 16 x 439.55 = $7,032.80
Realised P&L = $7,032.80 - $5,765.92 = $1,266.88
Realised %   = (1,266.88 / 5,765.92) x 100 = 21.97%
```
""")

# ── 6. Total P&L ───────────────────────────────────────────────────────────
st.header("6. Total P&L")
st.markdown("""
```
Total P&L = Unrealised P&L + Realised P&L
Total P&L % = (Total P&L / (Total Cost of Open + Realised Cost)) x 100
```

This captures both the gain on shares you still hold and the gain on shares
you have already sold.
""")

# ── 7. USD to GBP Conversion ───────────────────────────────────────────────
st.header("7. Currency Conversion (USD to GBP)")
st.markdown("""
The dashboard uses the **GBP/USD exchange rate** (how many USD = 1 GBP).

```
Amount in GBP = Amount in USD / GBP-USD Rate
```

**Two different rates are used depending on the context:**

| Context | Which Rate? | Why? |
|---------|-------------|------|
| **Cost of a BUY** | FX rate on the **transaction date** | Locks in historical cost |
| **Proceeds of a SELL** | FX rate on the **transaction date** | Locks in actual proceeds |
| **Current Market Value** | **Live** GBP/USD rate | Reflects today's FX exposure |
| **Unrealised P&L (GBP)** | **Live** GBP/USD rate | Shows current GBP equivalent |
| **Realised P&L (GBP)** | Transaction-date rates for both buy and sell | Reflects actual rates at time of trade |

---

**Example — BUY 70 MSFT @ $360.37 on 11-Jul-2023, GBP/USD = 1.2934:**
```
Cost (USD) = 70 x 360.37 = $25,225.90
Cost (GBP) = 25,225.90 / 1.2934 = £19,504.57
```

**Current valuation — price $430.00, live GBP/USD = 1.2700:**
```
Market Value (USD) = 70 x 430.00 = $30,100.00
Market Value (GBP) = 30,100.00 / 1.2700 = £23,700.79
```

> **Key point:** The GBP cost uses the **historical** rate (1.2934) while the
> market value uses the **current** rate (1.2700). This means GBP P&L
> includes both the stock price movement *and* the FX movement.
""")

# ── 8. Pence vs Pounds (LSE Stocks) ────────────────────────────────────────
st.header("8. Pence vs Pounds (London Stock Exchange)")
st.markdown("""
Some LSE-listed stocks are quoted in **pence (GBp)** rather than pounds (GBP).
The dashboard automatically converts these to pounds.

```
Price in GBP = Price in GBp / 100
```

**Stocks quoted in pence:** BARC.L, BT-A.L, CNA.L, ANTO.L, HSBA.L

**ETFs like VUSA.L are already quoted in GBP** — no conversion needed.

**Example — Barclays (BARC.L), Yahoo Finance reports 452.85 GBp:**
```
Price in GBP = 452.85 / 100 = £4.5285
```
""")

# ── 9. XIRR ─────────────────────────────────────────────────────────────────
st.header("9. XIRR (Extended Internal Rate of Return)")
st.markdown("""
XIRR is the **annualised return** that accounts for the **timing and size** of
each cash flow (buy/sell). Unlike simple P&L %, it considers *when* money was
invested.

**How it works:**
- Each BUY is a **negative** cash flow (money going out) on the transaction date.
- Each SELL is a **positive** cash flow (money coming back) on the transaction date.
- If shares are still held, the current market value is treated as a positive
  cash flow on today's date.
- XIRR solves for the annual rate *r* that makes the net present value of all
  cash flows equal to zero.

**Per-holding XIRR** is calculated in the **native currency** (USD for US stocks,
GBP for UK stocks).

**Portfolio XIRR** is calculated in **GBP** across all transactions.

**Example — simplified:**
```
01-Jan-2024: BUY  100 shares @ $10 = -$1,000
01-Jul-2024: SELL  50 shares @ $12 =  +$600
01-Jan-2025: Remaining 50 shares worth $13 each = +$650

XIRR solves: -1000/(1+r)^0 + 600/(1+r)^0.5 + 650/(1+r)^1 = 0
Result: r ≈ 25% annualised
```

> The actual calculation uses the `pyxirr` library for precision.
""")

# ── 10. NAV ─────────────────────────────────────────────────────────────────
st.header("10. NAV (Net Asset Value)")
st.markdown("""
NAV is the **total value of the portfolio** on any given day.

```
NAV = Holdings Value (at market prices) + Cash on Hand
```

**Holdings Value** = For each stock held, Quantity x Closing Price on that day,
converted to GBP.

**Cash on Hand** = Cumulative proceeds from sales minus cost of purchases (in GBP).
When you buy, cash decreases. When you sell, cash increases.

**Investment** = Total **new money** put into the portfolio (cumulative).
If cash is available from prior sales, a new purchase uses that cash first —
only the shortfall counts as new investment.

**Profit** = NAV - Investment (combines unrealised and realised gains).

---

**Example — Day-by-day:**

| Day | Event | Holdings Value | Cash | NAV | Investment | Profit |
|-----|-------|---------------|------|-----|------------|--------|
| Day 1 | BUY 100 @ £10 | £1,000 | £0 | £1,000 | £1,000 | £0 |
| Day 2 | Price rises to £11 | £1,100 | £0 | £1,100 | £1,000 | £100 |
| Day 3 | SELL 50 @ £11 | £550 | £550 | £1,100 | £1,000 | £100 |
| Day 4 | BUY 30 @ £11 (from cash) | £880 | £220 | £1,100 | £1,000 | £100 |

> Notice on Day 3: selling doesn't change NAV — holdings drop but cash increases
> by the same amount. On Day 4: buying from cash doesn't increase Investment.
""")

# ── 11. Daily Change ────────────────────────────────────────────────────────
st.header("11. Daily Change")
st.markdown("""
```
Today's NAV = Current Market Value of All Holdings + Cash on Hand
Previous NAV = NAV at previous business day close (from NAV time series)

Daily Change (£) = Today's NAV - Previous NAV
Daily Change (%) = (Daily Change / Previous NAV) x 100
```

> This uses the **live** NAV (with current prices) compared against the
> **last historical** close, so it reflects intra-day movement.
""")

# ── 12. Max Drawdown ────────────────────────────────────────────────────────
st.header("12. Max Drawdown")
st.markdown("""
The largest **peak-to-trough decline** in NAV, expressed as a percentage.
It measures the worst loss you would have experienced.

```
Running Peak = Cumulative maximum of NAV up to each day
Drawdown on Day X = (NAV on Day X - Running Peak) / Running Peak x 100
Max Drawdown = Worst (most negative) drawdown across all days
```

**Example:**

| Day | NAV | Running Peak | Drawdown |
|-----|-----|-------------|----------|
| 1 | £10,000 | £10,000 | 0% |
| 2 | £11,000 | £11,000 | 0% |
| 3 | £9,500 | £11,000 | **-13.6%** |
| 4 | £10,200 | £11,000 | -7.3% |

```
Max Drawdown = -13.6%
```
""")

# ── 13. Sharpe Ratio ────────────────────────────────────────────────────────
st.header("13. Sharpe Ratio")
st.markdown("""
Measures **risk-adjusted return** — how much return you earn per unit of
volatility (risk). Higher is better.

```
Daily Returns     = Day-over-day % change in NAV
Risk-Free Rate    = 4% per annum (approx. UK gilt rate)
Daily Risk-Free   = (1 + 0.04) ^ (1/252) - 1
Excess Returns    = Daily Returns - Daily Risk-Free
Sharpe Ratio      = (Mean of Excess Returns / Std Dev of Excess Returns) x sqrt(252)
```

**Interpretation:**
| Sharpe Ratio | Meaning |
|---|---|
| < 0 | Returns below risk-free rate |
| 0 - 1 | Acceptable |
| 1 - 2 | Good |
| > 2 | Excellent |

> Requires at least 30 days of NAV history to compute.
""")

# ── 14. Annualised Return (Trade Profitability) ─────────────────────────────
st.header("14. Annualised Return (Per Trade)")
st.markdown("""
On the Trade Profitability page, each matched buy/sell pair shows an
**annualised return** — what the P&L % would be if scaled to a full year.

```
Holding Days = Sell Date - Buy Date (minimum 1 day)
Gross Multiple = Proceeds / Cost
Annualised Return = (Gross Multiple ^ (365 / Holding Days) - 1) x 100
```

**Example — SELL 16 MSFT held for 339 days, cost $5,765.92, proceeds $7,032.80:**
```
Gross Multiple  = 7,032.80 / 5,765.92 = 1.2197
Annualised      = (1.2197 ^ (365/339) - 1) x 100 = 23.85%
```

> Short-duration trades will show very high annualised returns because the
> gain is extrapolated over a full year.
""")

# ── 15. Cash on Hand ────────────────────────────────────────────────────────
st.header("15. Cash on Hand")
st.markdown("""
Running balance of cash generated from sales minus cash used for purchases,
all in GBP.

```
Starting Cash = £0
On each BUY:  Cash = max(Cash - Purchase Amount in GBP, 0)
On each SELL: Cash = Cash + Sale Proceeds in GBP
```

> If cash is insufficient for a purchase, the shortfall is counted as new
> **Investment** (see NAV section). Cash never goes negative.
""")

# ── Footer ──────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "All GBP holdings use direct prices. "
    "USD holdings are converted at the GBP/USD rate — historical rate for "
    "completed transactions, live rate for current valuations. "
    "Dates are displayed in dd-mm-yyyy format throughout the dashboard."
)
