import sqlite3
from pathlib import Path

samples = Path("docs/engineering-change/material-change/samples")
print("samples", [item.name for item in samples.iterdir()])
connection = sqlite3.connect("data/stamping_costing.db")
print("parts", connection.execute("select count(*) from stamping_parts").fetchone()[0])
print(
    "target",
    list(
        connection.execute(
            "select part_number, material, thickness, stamping_supplier, version, "
            "effective_year, effective_month from stamping_parts "
            "where part_number in ('403014115AA', '403014116AA')"
        )
    ),
)
tables = [
    row[0]
    for row in connection.execute(
        "select name from sqlite_master where type='table' "
        "and (name like '%bom%' or name like '%procurement%' or name like '%engineering%')"
    )
]
print("--- snapshots ---")
for row in connection.execute("select * from bom_snapshots"):
    print(row)
print("--- procurement lists ---")
columns = [
    item[1] for item in connection.execute("pragma table_info(bom_procurement_object_lists)")
]
print(columns)
for row in connection.execute("select * from bom_procurement_object_lists"):
    print(row)
