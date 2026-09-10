"""Build the loan amortization + ROI workbook with LIVE Excel formulas.

Every derived figure is a formula, not a pasted value: change a cell on
Assumptions and the whole workbook recalculates. Run: python3 build_workbook.py
"""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

HDR   = PatternFill("solid", fgColor="1F3864")
INPUT = PatternFill("solid", fgColor="FFF2CC")     # yellow = editable input
CALC  = PatternFill("solid", fgColor="E7EEF8")
WHITE = Font(color="FFFFFF", bold=True)
BOLD  = Font(bold=True)
THIN  = Border(*[Side(style="thin", color="BBBBBB")] * 4)
USD   = '"$"#,##0.00'
USD0  = '"$"#,##0'
PCT   = '0.00%'

N = 360          # rows of schedule

def header(ws, row, cols):
    for i, c in enumerate(cols, 1):
        cell = ws.cell(row, i, c)
        cell.fill, cell.font = HDR, WHITE
        cell.alignment = Alignment(horizontal="center", wrap_text=True)

wb = Workbook()

# ------------------------------------------------------ 1. Assumptions
a = wb.active; a.title = "Assumptions"
a["A1"] = "Loan & Investment Assumptions"; a["A1"].font = Font(bold=True, size=15, color="1F3864")
a["A2"] = "Yellow cells are inputs — change them and every sheet recalculates."
a["A2"].font = Font(italic=True, color="666666")

rows = [
    ("Loan principal",        320000,  USD0),
    ("Annual interest rate",  0.065,   PCT),
    ("Term (years)",          30,      "0"),
    ("Extra principal / month", 200,   USD0),
    ("Investment return (annual)", 0.07, PCT),
]
a["A4"], a["B4"] = "Input", "Value"; header(a, 4, ["Input", "Value"])
for i, (label, val, fmt) in enumerate(rows, start=5):
    a.cell(i, 1, label).border = THIN
    c = a.cell(i, 2, val); c.fill, c.font, c.border, c.number_format = INPUT, BOLD, THIN, fmt

A = "Assumptions!"
P, R, Y, X, IR = f"{A}$B$5", f"{A}$B$6", f"{A}$B$7", f"{A}$B$8", f"{A}$B$9"

a["A11"] = "Derived"; a["A11"].font = BOLD
derived = [
    ("Monthly rate",        f"={R}/12", PCT),
    ("Number of payments",  f"={Y}*12", "0"),
    ("Monthly payment",     f"=-PMT({R}/12,{Y}*12,{P})", USD),
    ("Payment + extra",     f"=B13+{X}", USD),
]
for i, (label, f, fmt) in enumerate(derived, start=12):
    a.cell(i, 1, label).border = THIN
    c = a.cell(i, 2, f); c.fill, c.border, c.number_format, c.font = CALC, THIN, fmt, BOLD
a.column_dimensions["A"].width = 26; a.column_dimensions["B"].width = 16

PMT_CELL = f"{A}$B$13"
PMTX     = f"{A}$B$14"

# ------------------------------------ 2 & 3. Two amortization schedules
def build_schedule(ws, title, extra_ref):
    ws["A1"] = title; ws["A1"].font = Font(bold=True, size=13, color="1F3864")
    header(ws, 3, ["Month", "Opening balance", "Payment", "Interest",
                   "Principal", "Closing balance", "Cumulative interest"])
    pay = PMT_CELL if extra_ref is None else PMTX
    for m in range(1, N + 1):
        r = m + 3
        prev = f"F{r-1}" if m > 1 else P
        ws.cell(r, 1, m)
        # once the balance hits zero every later row stays zero
        ws.cell(r, 2, f"=IF({prev}<=0,0,{prev})")
        # final payment is capped at whatever is actually left
        ws.cell(r, 3, f"=IF(B{r}<=0,0,MIN({pay},B{r}+D{r}))")
        ws.cell(r, 4, f"=IF(B{r}<=0,0,B{r}*{R}/12)")
        ws.cell(r, 5, f"=IF(B{r}<=0,0,C{r}-D{r})")
        ws.cell(r, 6, f"=IF(B{r}<=0,0,B{r}-E{r})")
        ws.cell(r, 7, f"=IF(B{r}<=0,G{r-1},{f'G{r-1}+' if m>1 else ''}D{r})")
        for col in "BCDEG":
            ws[f"{col}{r}"].number_format = USD
        ws[f"F{r}"].number_format = USD
    for col, w in zip("ABCDEFG", [8, 17, 14, 13, 13, 17, 18]):
        ws.column_dimensions[col].width = w

s1 = wb.create_sheet("Amortization")
build_schedule(s1, "Standard schedule — scheduled payment only", None)
s2 = wb.create_sheet("With Extra Payment")
build_schedule(s2, "Accelerated schedule — scheduled payment plus extra principal", True)

LAST = N + 3

# ------------------------------------------------------------ 4. Summary
s = wb.create_sheet("Summary", 1)
s["A1"] = "Results"; s["A1"].font = Font(bold=True, size=15, color="1F3864")
s["A2"] = "Every figure below is a formula over the two schedules."
s["A2"].font = Font(italic=True, color="666666")

header(s, 4, ["Metric", "Standard", "With extra"])
metrics = [
    ("Monthly payment",      f"={PMT_CELL}",                    f"={PMTX}", USD),
    ("Months to payoff",     f"=COUNTIF(Amortization!C4:C{LAST},\">0\")",
                             f"=COUNTIF('With Extra Payment'!C4:C{LAST},\">0\")", "0"),
    ("Years to payoff",      "=B6/12",                          "=C6/12", "0.0"),
    ("Total interest",       f"=SUM(Amortization!D4:D{LAST})",
                             f"=SUM('With Extra Payment'!D4:D{LAST})", USD),
    ("Total paid",           f"={P}+B8",                        f"={P}+C8", USD),
]
for i, (label, f1, f2, fmt) in enumerate(metrics, start=5):
    s.cell(i, 1, label).border = THIN
    for col, f in ((2, f1), (3, f2)):
        c = s.cell(i, col, f); c.fill, c.border, c.number_format, c.font = CALC, THIN, fmt, BOLD

s["A11"] = "Effect of the extra payment"; s["A11"].font = BOLD
eff = [("Interest saved", "=B8-C8", USD), ("Months saved", "=B6-C6", "0"),
       ("Years saved", "=(B6-C6)/12", "0.0")]
for i, (label, f, fmt) in enumerate(eff, start=12):
    s.cell(i, 1, label).border = THIN
    c = s.cell(i, 2, f); c.fill, c.border, c.number_format, c.font = CALC, THIN, fmt, BOLD

s["A16"] = "Prepay vs. invest — equal monthly outflow, valued at month 360"
s["A16"].font = BOLD
s["A17"] = ("Both paths spend the same amount every month. Invest: pay the scheduled "
            "payment for all 360 months and invest the extra. Prepay: pay extra until "
            "the loan ends, then invest the whole freed-up payment.")
s["A17"].font = Font(italic=True, color="666666", size=9)
s["A17"].alignment = Alignment(wrap_text=True); s.row_dimensions[17].height = 30

roi = [
    ("Invest the extra for 360 months", f"=FV({IR}/12,{Y}*12,-{X},0)", USD),
    ("Prepay, then invest the payment", f"=FV({IR}/12,B13,-{PMTX},0)", USD),
    ("Advantage of investing",          "=B19-B20", USD),
]
for i, (label, f, fmt) in enumerate(roi, start=19):
    s.cell(i, 1, label).border = THIN
    c = s.cell(i, 2, f); c.fill, c.border, c.number_format, c.font = CALC, THIN, fmt, BOLD

# ---------------------------------------------------- 5. Rate sensitivity
sen = wb.create_sheet("Rate Sensitivity")
sen["A1"] = "Payment and total interest across rates"
sen["A1"].font = Font(bold=True, size=13, color="1F3864")
sen["A2"] = "Recomputed independently of the schedules, so it stays live too."
sen["A2"].font = Font(italic=True, color="666666")
header(sen, 4, ["Rate", "Monthly payment", "Total interest", "vs. base rate"])
for i, rate in enumerate([r / 1000 for r in range(45, 96, 5)], start=5):
    sen.cell(i, 1, rate).number_format = PCT
    sen.cell(i, 2, f"=-PMT(A{i}/12,{Y}*12,{P})").number_format = USD
    sen.cell(i, 3, f"=B{i}*{Y}*12-{P}").number_format = USD
    sen.cell(i, 4, f"=C{i}-(-PMT({R}/12,{Y}*12,{P})*{Y}*12-{P})").number_format = USD
    for col in "ABCD":
        sen[f"{col}{i}"].border = THIN
for col, w in zip("ABCD", [10, 17, 16, 16]):
    sen.column_dimensions[col].width = w

for col, w in zip("ABC", [40, 17, 17]):
    s.column_dimensions[col].width = w

wb.save("loan_roi_model.xlsx")
print(f"wrote loan_roi_model.xlsx — {len(wb.sheetnames)} sheets, {N} schedule rows")
