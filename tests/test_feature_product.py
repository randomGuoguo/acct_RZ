from acct_rz.feature_product import BLACKLIST_WINDOWS, STABLE_ORG_TYPES, STABLE_PERF_TYPES


def test_feature_product_constants_expose_expected_defaults() -> None:
    assert BLACKLIST_WINDOWS == ("3m", "6m", "9m", "12m", "24m", "36m")
    assert STABLE_ORG_TYPES == ("bank", "rate24", "rate36")
    assert STABLE_PERF_TYPES == ("fpd", "dpd")
