import csv
from pathlib import Path
from dataclasses import asdict
from typing import Any, Callable, Optional, Sequence

from Api_ingestion.ports import ReadingStorage


class CsvRepository(ReadingStorage):
    def __init__(self, filepath: Path, fieldnames):
        self.filepath = filepath
        self.fieldnames = fieldnames
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

    def append(
        self,
        readings: Sequence[Any],
        transform: Optional[Callable[[dict], dict]] = None,
    ) -> None:
        if not readings:
            return

        exists = self.filepath.exists()
        with open(self.filepath, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            if not exists:
                writer.writeheader()

            for reading in readings:
                row = asdict(reading)
                if transform is not None:
                    row = transform(row)
                writer.writerow(row)