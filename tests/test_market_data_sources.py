from __future__ import annotations

import csv
import io
import zipfile

import pytest

from src.io.market_data_sources import (
    build_company_aliases,
    diff_issuer_masters,
    filter_edinet_documents,
    normalize_security_code,
    parse_alpha_vantage_daily,
    parse_edinet_code_zip,
    parse_gdelt_gkg_zip,
    parse_gdelt_last_update,
    query_gdelt_events,
)


def make_zip(name: str, data: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, data)
    return buf.getvalue()


def edinet_fixture() -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ダウンロード実行日", "2026-08-20"])
    writer.writerow([])
    writer.writerow(
        [
            "ＥＤＩＮＥＴコード",
            "提出者種別",
            "上場区分",
            "決算日",
            "提出者名",
            "提出者名（英字）",
            "提出者業種",
            "証券コード",
            "提出者法人番号",
        ]
    )
    writer.writerow(
        [
            "E00001",
            "内国法人・組合",
            "上場",
            "03-31",
            "テスト株式会社",
            "TEST CORP",
            "電気機器",
            "12340",
            "1234567890123",
        ]
    )
    return make_zip("EdinetcodeDlInfo.csv", buf.getvalue().encode("cp932"))


def test_edinet_master_and_normalized_join_code() -> None:
    master = parse_edinet_code_zip(edinet_fixture(), retrieved_at="2026-08-20T00:00:00Z")
    assert master["issuer_count"] == 1
    assert master["issuers"][0]["security_code"] == "1234"
    assert master["issuers"][0]["edinet_security_code"] == "12340"
    assert len(master["source_sha256"]) == 64


def test_edinet_master_rejects_duplicate_security_code() -> None:
    payload = edinet_fixture()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        text = archive.read("EdinetcodeDlInfo.csv").decode("cp932")
    duplicate = text + "E00002,内国法人・組合,上場,03-31,別会社,OTHER,銀行業,12340,9999999999999\n"
    with pytest.raises(ValueError, match="duplicate security_code"):
        parse_edinet_code_zip(make_zip("EdinetcodeDlInfo.csv", duplicate.encode("cp932")))


def test_diff_tracks_modified_and_added() -> None:
    before = {
        "issuers": [
            {"security_code": "1234", "issuer_name": "A", "industry": "銀行業", "edinet_code": "E1"}
        ]
    }
    after = {
        "issuers": [
            {"security_code": "1234", "issuer_name": "A", "industry": "保険業", "edinet_code": "E1"},
            {"security_code": "5678", "issuer_name": "B", "industry": "小売業", "edinet_code": "E2"},
        ]
    }
    diff = diff_issuer_masters(before, after)
    assert diff["change_count"] == 2
    assert {row["change"] for row in diff["changes"]} == {"modified", "added"}


def test_document_filter_is_incremental_and_joins_master() -> None:
    payload = {
        "results": [
            {
                "docID": "S1",
                "edinetCode": "E1",
                "secCode": "12340",
                "docTypeCode": "120",
                "docDescription": "有価証券報告書－第1期",
                "submitDateTime": "2026-08-20 10:00",
                "xbrlFlag": "1",
                "parentDocID": None,
            },
            {"docID": "S2", "edinetCode": "E1", "docDescription": "その他書類"},
        ]
    }
    rows = filter_edinet_documents(
        payload,
        known_doc_ids=set(),
        issuer_by_edinet_code={"E1": {"security_code": "1234", "issuer_name": "A"}},
    )
    assert [row["doc_id"] for row in rows] == ["S1"]
    assert rows[0]["security_code"] == "1234"
    assert rows[0]["parent_doc_id"] is None
    assert (
        filter_edinet_documents(
            payload,
            known_doc_ids={"S1"},
            issuer_by_edinet_code={"E1": {"security_code": "1234"}},
        )
        == []
    )


def test_gdelt_last_update_and_candidate_mapping() -> None:
    latest = (
        "1 2 http://data.gdeltproject.org/gdeltv2/20260820120000.export.CSV.zip\n"
        "1 2 http://data.gdeltproject.org/gdeltv2/20260820120000.gkg.csv.zip\n"
    )
    assert parse_gdelt_last_update(latest).endswith(".gkg.csv.zip")
    master = {
        "issuers": [
            {
                "security_code": "1234",
                "issuer_name": "テスト株式会社",
                "issuer_name_en": "TEST CORP",
                "industry": "電気機器",
            }
        ]
    }
    cols = [
        "r1",
        "20260820120000",
        "1",
        "example.com",
        "https://example.com/a",
        "",
        "",
        "THEME",
        "",
        "",
        "",
        "",
        "",
        "TEST CORP",
        "",
    ]
    result = parse_gdelt_gkg_zip(
        make_zip("sample.gkg.csv", ("\t".join(cols) + "\n").encode()),
        issuer_master=master,
        source_url="https://example/gkg.zip",
    )
    assert result["event_count"] == 1
    assert result["events"][0]["mapping_status"] == "candidate"
    assert result["events"][0]["security_code"] == "1234"


def test_alias_builder_ignores_too_short_aliases() -> None:
    assert build_company_aliases(
        {"issuers": [{"security_code": "1", "issuer_name": "ABC", "issuer_name_en": None}]}
    ) == {}


def test_alpha_vantage_parser_preserves_provider_states() -> None:
    assert parse_alpha_vantage_daily({"Note": "limit"}, security_code="1", symbol="1").status == "rate_limited"
    assert parse_alpha_vantage_daily({"Error Message": "bad"}, security_code="1", symbol="1").status == "unsupported"
    payload = {"Time Series (Daily)": {"2026-08-20": {"1. open": "1"}}}
    assert parse_alpha_vantage_daily(payload, security_code="1", symbol="1").observations == 1


def test_security_code_preserves_non_filler_forms() -> None:
    assert normalize_security_code("285A") == "285A"
    assert normalize_security_code("72030") == "7203"


def test_query_gdelt_events_dedup_and_filters() -> None:
    row = {
        "gdelt_record_id": "1",
        "observed_at": "20260820120000",
        "article_url": "https://example.com/a",
        "security_code": "7203",
        "industry": "輸送用機器",
        "mapping_status": "candidate",
    }
    rows = query_gdelt_events(
        [{"events": [row]}, {"events": [row]}],
        security_code="7203",
        industry="輸送用機器",
        observed_from="20260820000000",
        observed_to="20260820235959",
    )
    assert rows == [row]
