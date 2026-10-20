from __future__ import annotations


def test_repair_kasus_nyata():
    from generator.textutil import repair_mojibake

    assert repair_mojibake("NemÃ©nyi") == "Neményi"


def test_teks_normal_tidak_berubah():
    from generator.textutil import repair_mojibake

    assert (
        repair_mojibake("Pertanian presisi mendukung produksi")
        == "Pertanian presisi mendukung produksi"
    )


def test_teks_tidak_parsial_tidak_diterima():
    from generator.textutil import repair_mojibake

    rusak = "suhu naik 2ÃƒÂ¢Ã‚Â°C"
    assert repair_mojibake(rusak) == rusak  # rusak berlapis: jangan maksa
