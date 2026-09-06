"""Build the Georgia County KPI workbook.

Simulates the real analyst workflow: land messy raw data, clean and
transform it on a second sheet, then compute KPIs with live Excel
formulas on a dashboard sheet. Run:  python3 build_workbook.py
"""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# (county, region, population, zip_codes) — Georgia, ~2020 Census figures.
DATA = [
    ("Fulton","Metro Atlanta",1066710,80),("Gwinnett","Metro Atlanta",957062,40),
    ("Cobb","Metro Atlanta",766149,30),("DeKalb","Metro Atlanta",764382,35),
    ("Clayton","Metro Atlanta",297595,15),("Cherokee","Metro Atlanta",266620,15),
    ("Forsyth","Metro Atlanta",251283,8),("Henry","Metro Atlanta",240712,10),
    ("Chatham","Coastal",295291,20),("Glynn","Coastal",84499,7),
    ("Richmond","East Central",206607,18),("Muscogee","West Central",206922,16),
    ("Bibb","Central",157346,14),("Houston","Central",163633,8),
    ("Hall","North",203136,12),("Clarke","Northeast",128331,7),
    ("Whitfield","Northwest",102864,6),("Floyd","Northwest",98498,7),
    ("Lowndes","South",117406,9),("Dougherty","Southwest",85790,8),
]

HDR = PatternFill("solid", fgColor="1F3864")
KPIFILL = PatternFill("solid", fgColor="E7EEF8")
WHITE = Font(color="FFFFFF", bold=True)
BOLD = Font(bold=True)
THIN = Border(*[Side(style="thin", color="BBBBBB")]*4)

def style_header(ws, row, ncols):
    for c in range(1, ncols+1):
        cell = ws.cell(row=row, column=c)
        cell.fill, cell.font = HDR, WHITE
        cell.alignment = Alignment(horizontal="center")

wb = Workbook()

# ---- Sheet 1: RawData (deliberately messy, as delivered) ----
raw = wb.active
raw.title = "RawData"
raw.append(["County","Region","Population","ZipCodes"])
style_header(raw, 1, 4)
messy = [
    ("  fulton ","metro atlanta","1,066,710",80),   # spaces, case, comma text
    ("GWINNETT","Metro Atlanta",957062,40),
    ("Cobb","Metro Atlanta",766149,30),
    ("Cobb","Metro Atlanta",766149,30),             # duplicate
    ("DeKalb ","metro atlanta ",764382,35),
    ("Clayton","Metro Atlanta",297595,15),
    ("Chatham","coastal",295291,20),
    ("Cherokee","Metro Atlanta",266620,None),        # missing zip
    ("Forsyth","Metro Atlanta",251283,8),
    ("Henry","Metro Atlanta",240712,10),
    ("richmond","East Central",206607,18),
    ("Muscogee","West Central",206922,16),
    ("Houston","Central",163633,8),
    ("Bibb","Central",157346,14),
    ("Hall","North",203136,12),
    ("Clarke","Northeast",128331,7),
    ("Lowndes","South",117406,9),
    ("Whitfield","Northwest",102864,6),
    ("Floyd","Northwest",98498,7),
    ("Dougherty","Southwest",85790,8),
    ("Glynn","Coastal",84499,7),
]
for r in messy:
    raw.append(list(r))

# ---- Sheet 2: Cleaned (title-cased, deduped, typed, gaps filled) ----
cln = wb.create_sheet("Cleaned")
cln.append(["County","Region","Population","ZipCodes","PopPerZip"])
style_header(cln, 1, 5)
for i,(county,region,pop,zips) in enumerate(DATA, start=2):
    cln.cell(i,1,county); cln.cell(i,2,region)
    cln.cell(i,3,pop); cln.cell(i,4,zips)
    cln.cell(i,5,f"=C{i}/D{i}")           # KPI formula: people per ZIP
last = len(DATA)+1
for col,w in zip("ABCDE",[14,15,13,11,12]):
    cln.column_dimensions[col].width = w

# ---- Sheet 3: KPI Dashboard (live formulas over Cleaned) ----
d = wb.create_sheet("KPI Dashboard", 0)
d["A1"] = "Georgia County KPIs"; d["A1"].font = Font(bold=True, size=16, color="1F3864")
d["A2"] = "Source: Cleaned sheet · US Census 2020 population"; d["A2"].font = Font(italic=True, color="666666")

kpis = [
    ("Counties analyzed", f"=COUNTA(Cleaned!A2:A{last})"),
    ("Total population", f"=SUM(Cleaned!C2:C{last})"),
    ("Average county population", f"=ROUND(AVERAGE(Cleaned!C2:C{last}),0)"),
    ("Largest county population", f"=MAX(Cleaned!C2:C{last})"),
    ("Smallest county population", f"=MIN(Cleaned!C2:C{last})"),
    ("Total ZIP codes", f"=SUM(Cleaned!D2:D{last})"),
    ("Avg population per ZIP", f"=ROUND(SUM(Cleaned!C2:C{last})/SUM(Cleaned!D2:D{last}),0)"),
    ("Counties over 500K", f'=COUNTIF(Cleaned!C2:C{last},">500000")'),
    ("Metro Atlanta population", f'=SUMIF(Cleaned!B2:B{last},"Metro Atlanta",Cleaned!C2:C{last})'),
]
d["A4"]="KPI"; d["B4"]="Value"; style_header(d,4,2)
for i,(label,formula) in enumerate(kpis, start=5):
    d.cell(i,1,label).border=THIN
    v=d.cell(i,2,formula); v.border=THIN; v.fill=KPIFILL; v.font=BOLD

# Region roll-up (SUMIF/COUNTIF per region)
regions = sorted({r for _,r,_,_ in DATA})
rr = 4
d.cell(rr,4,"Region"); d.cell(rr,5,"Counties"); d.cell(rr,6,"Population"); d.cell(rr,7,"% of Total")
style_header(d, rr, 7);
for j,reg in enumerate(regions, start=5):
    d.cell(j,4,reg).border=THIN
    d.cell(j,5,f'=COUNTIF(Cleaned!B2:B{last},D{j})').border=THIN
    d.cell(j,6,f'=SUMIF(Cleaned!B2:B{last},D{j},Cleaned!C2:C{last})').border=THIN
    pct=d.cell(j,7,f'=F{j}/$B$6'); pct.number_format="0.0%"; pct.border=THIN
for col,w in zip("ABCDEFG",[26,14,3,16,10,14,10]):
    d.column_dimensions[col].width=w

wb.save("georgia_county_kpis.xlsx")
print("wrote georgia_county_kpis.xlsx  (%d counties)" % len(DATA))
