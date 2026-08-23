#!/usr/bin/env python3
from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from scripts import alphazerobeta_train as trainer
from src.research.alphazerobeta import WalkForwardFold
from src.research.alphazerobeta import make_walk_forward_folds as canonical_folds

TRAIN_MONTHS = 12
VALIDATION_MONTHS = 3
TEST_MONTHS = 3


def japan_free_folds(
    dates: Iterable[str | np.datetime64 | pd.Timestamp],
    *,
    test_start: str,
    test_end: str,
    train_months: int = 36,
    validation_months: int = 6,
    test_months: int = 6,
) -> list[WalkForwardFold]:
    del train_months, validation_months, test_months
    return canonical_folds(
        dates,
        test_start=test_start,
        test_end=test_end,
        train_months=TRAIN_MONTHS,
        validation_months=VALIDATION_MONTHS,
        test_months=TEST_MONTHS,
    )


def main() -> None:
    trainer.make_walk_forward_folds = japan_free_folds
    trainer.main()


if __name__ == "__main__":
    main()
