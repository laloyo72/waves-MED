import sys
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASES_FILE = ROOT / "config" / "cases.yml"

case_name = sys.argv[1]
parameter = sys.argv[2]

with open(CASES_FILE) as f:
    cases = yaml.safe_load(f)

value = cases[case_name]

for key in parameter.split("."):
    value = value[key]

print(value)
