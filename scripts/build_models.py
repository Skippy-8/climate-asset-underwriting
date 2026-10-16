"""Regenerate the workbooks in models/ from data/*_inputs.yaml.

openpyxl writes formulas but cannot calculate them, so a freshly written .xlsx carries no stored
results until a spreadsheet program opens it. With Microsoft Excel installed (macOS), this script
asks Excel to recalculate and save each workbook so the committed files open with values in any
viewer. Without Excel it writes formula-only files; Excel recalculates them on open
(fullCalcOnLoad), and the test suite evaluates them with the `formulas` package either way.

    python scripts/build_models.py            # build, then recalculate in Excel if available
    python scripts/build_models.py --no-excel
"""
import shutil
import subprocess
import sys
from pathlib import Path

from cau.inputs import load_inputs
from cau.xlsx import pf_book, property_book

ROOT = Path(__file__).resolve().parents[1]

RECALC = '''
set f to POSIX file "{path}"
tell application "Microsoft Excel"
    set display alerts to false
    open f
    set wb to active workbook
    calculate full
    save wb
    close wb saving no
end tell
'''


def excel_recalc(path: Path) -> bool:
    if sys.platform != "darwin" or not Path("/Applications/Microsoft Excel.app").exists():
        return False
    try:
        subprocess.run(["osascript", "-e", RECALC.format(path=path)], check=True, capture_output=True, timeout=180)
        return True
    except (subprocess.SubprocessError, OSError) as exc:
        print(f"  Excel recalculation skipped: {exc}")
        return False


def main() -> None:
    use_excel = "--no-excel" not in sys.argv
    built = [property_book.build(load_inputs("property"), ROOT / "models" / "property_underwriting.xlsx"),
             pf_book.build(load_inputs("solar_storage"), ROOT / "models" / "solar_storage_pf.xlsx")]
    for p in built:
        note = ""
        if use_excel:
            tmp = Path("/tmp") / p.name                  # Excel's sandbox reads /tmp without prompting
            shutil.copy(p, tmp)
            if excel_recalc(tmp):
                shutil.copy(tmp, p)
                note = " (recalculated in Excel; values stored)"
        print(f"wrote {p.relative_to(ROOT)}{note}")


if __name__ == "__main__":
    main()
