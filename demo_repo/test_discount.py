from discount import calculate_total


def test_no_discount_below_threshold():
    assert calculate_total(10.0, 5) == 50.0


def test_ten_percent_discount_at_boundary():
    # Quantity exactly 10 must receive the 10% tier discount.
    assert calculate_total(10.0, 10) == 90.0


def test_ten_percent_discount_above_boundary():
    assert calculate_total(10.0, 15) == 135.0


def test_twenty_percent_discount_at_boundary():
    assert calculate_total(10.0, 20) == 160.0
