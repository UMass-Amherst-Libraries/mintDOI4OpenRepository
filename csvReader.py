import polars as pl

def load_item_ids(csv_path: str, column: str = "item_uuid") -> list[str]:
    df = pl.read_csv(csv_path)
    ids = (
        df.select(pl.col(column).cast(pl.Utf8).str.strip_chars())
        .to_series()
        .drop_nulls()
        .to_list()
    )
    return [x for x in ids if x]