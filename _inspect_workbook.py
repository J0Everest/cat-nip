import openpyxl

from config import WORKBOOK_PATH

wb = openpyxl.load_workbook(WORKBOOK_PATH, data_only=False, keep_vba=True)
print("SHEETS:")
for s in wb.sheetnames:
    print("-", s)

print("\nDEFINED_NAMES (first 60):")
names = list(wb.defined_names.keys())
for n in names[:60]:
    print("-", n)

print("\nTOTAL_DEFINED_NAMES:", len(names))
