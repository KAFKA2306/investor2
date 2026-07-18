"""Validate the 2010s paper collection catalog without asserting empirical validity."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).parents[1]
CATALOG = ROOT / "docs" / "research" / "2010s_paper_catalog.json"


def validate_catalog(path: Path = CATALOG) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    papers = data.get("papers")
    if not isinstance(papers, list) or not papers:
        return ["papers must be a non-empty list"]

    ids: list[str] = []
    dois: list[str] = []
    counts: Counter[str] = Counter()
    for index, paper in enumerate(papers):
        label = f"papers[{index}]"
        required = ("id", "title", "authors", "publication_year", "venue", "source_url", "themes", "role", "validation_status")
        for key in required:
            if not paper.get(key):
                errors.append(f"{label}.{key} is required")
        paper_id = paper.get("id")
        if paper_id:
            ids.append(paper_id)
        year = paper.get("publication_year")
        if not isinstance(year, int) or not 2010 <= year <= 2019:
            errors.append(f"{label}.publication_year must be between 2010 and 2019")
        source_url = paper.get("source_url", "")
        parsed = urlparse(source_url)
        if parsed.scheme != "https" or not parsed.netloc:
            errors.append(f"{label}.source_url must be an https URL")
        doi = paper.get("doi")
        if doi:
            dois.append(doi.lower())
        counts[str(year)] += 1

    if len(ids) != len(set(ids)):
        errors.append("paper ids must be unique")
    if len(dois) != len(set(dois)):
        errors.append("DOIs must be unique")
    if counts != Counter(data.get("coverage_by_publication_year", {})):
        errors.append("coverage_by_publication_year does not match papers")
    if set(counts) != {str(year) for year in range(2010, 2020)}:
        errors.append("every year from 2010 through 2019 must be represented")
    return errors


def main() -> int:
    errors = validate_catalog()
    if errors:
        print("paper catalog: INVALID")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"paper catalog: VALID ({len(json.loads(CATALOG.read_text(encoding='utf-8'))['papers'])} papers)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
