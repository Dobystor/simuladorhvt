"""Property-based tests for weight classification and validation.

Requirements: 9.3, 9.6
"""

from hypothesis import given
from hypothesis import strategies as st

from app.services.event_constructor import (
    classify_weighing_result,
    validate_gross_weight,
)

finite_float = st.floats(
    min_value=0, max_value=2000, allow_nan=False, allow_infinity=False
)


# Property 10: Weight classification applies the 2.5-tonne threshold — Req 9.6
@given(gross=finite_float, empty=finite_float)
def test_weight_classification(gross, empty):
    result = classify_weighing_result(gross, empty)
    if abs(gross - empty) > 2.5:
        assert result == "net_load"
    else:
        assert result == "tare_update"


@given(a=finite_float, b=finite_float)
def test_weight_classification_symmetric(a, b):
    # Classification depends only on the absolute difference.
    assert classify_weighing_result(a, b) == classify_weighing_result(b, a)


# Property 11: Standard weighing validates weight range — Req 9.3
@given(
    w=st.floats(
        min_value=-100, max_value=2000, allow_nan=False, allow_infinity=False
    )
)
def test_validate_gross_weight(w):
    assert validate_gross_weight(w) is (0 < w <= 999.99)


def test_validate_gross_weight_boundaries():
    assert validate_gross_weight(0) is False
    assert validate_gross_weight(0.01) is True
    assert validate_gross_weight(999.99) is True
    assert validate_gross_weight(1000.0) is False
    assert validate_gross_weight(-5) is False
