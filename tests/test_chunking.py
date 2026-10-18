from generator.sources.chunking import chunk_text


def test_chunk_text_splits_long_text():
    chunks = chunk_text("a" * 7000, max_chars=3000)
    assert [c.id for c in chunks] == [0, 1, 2]
    assert all(len(c.text) <= 3000 for c in chunks)


def test_chunk_text_short_is_single():
    assert len(chunk_text("pendek")) == 1
