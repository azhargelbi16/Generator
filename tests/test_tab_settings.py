import pytest

from generator.gui.tab_settings import parse_temperature


def test_parse_temperature_accepts_comma_and_dot():
    assert parse_temperature("0,2") == pytest.approx(0.2)
    assert parse_temperature("1.0") == pytest.approx(1.0)
    assert parse_temperature(" 2 ") == pytest.approx(2.0)


def test_parse_temperature_rejects_non_number():
    with pytest.raises(ValueError, match="angka"):
        parse_temperature("abc")


def test_parse_temperature_rejects_out_of_range():
    with pytest.raises(ValueError, match="0"):
        parse_temperature("2.5")
    with pytest.raises(ValueError, match="0"):
        parse_temperature("-0,5")
