import pandas as pd

from app.services.financial_data_service import FinancialDataService


def test_frame_to_table_formats_rows():
    frame = pd.DataFrame(
        {"2024-12-31": [1000000.0], "2023-12-31": [900000.0]},
        index=["Total Revenue"],
    )
    table = FinancialDataService._frame_to_table("income_statement", frame)
    assert table.statement_type == "income_statement"
    assert table.rows[0]["line_item"] == "Total Revenue"
    assert table.rows[0]["2024-12-31"] == "1,000,000"
