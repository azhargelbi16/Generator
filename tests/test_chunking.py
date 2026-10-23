from generator.sources.chunking import chunk_text


def test_chunk_text_splits_long_text():
    chunks = chunk_text("a" * 7000, max_chars=3000)
    assert [c.id for c in chunks] == [0, 1, 2]
    assert all(len(c.text) <= 3000 for c in chunks)


def test_chunk_text_short_is_single():
    assert len(chunk_text("pendek")) == 1
    assert chunk_text("pendek")[0].id == 0


def test_chunk_text_teks_pendek_tetap_satu_chunk():
    text = "Ini adalah paragraf pendek yang tidak melebihi batas karakter."
    chunks = chunk_text(text, max_chars=3000)
    assert len(chunks) == 1
    assert chunks[0].id == 0
    assert chunks[0].text == text


def test_chunk_text_kalimat_utuh_tidak_terbelah():
    s1 = "Pertanian organik di Indonesia telah berkembang pesat dalam satu dekade terakhir."
    s2 = "Banyak petani lokal mulai beralih ke pupuk hayati alami guna menjaga kesuburan tanah."
    s3 = "Pemerintah pusat memberikan insentif penyuluhan berkelanjutan di berbagai daerah."
    text = f"{s1} {s2} {s3}"

    # Batas karakter diset pas di antara kalimat 1 dan 2
    max_chars = len(s1) + 25
    chunks = chunk_text(text, max_chars=max_chars, overlap=30)

    # Chunk pertama harus memuat s1 utuh dan berakhir tepat di tanda titik s1
    assert chunks[0].text == s1
    assert chunks[0].text.endswith(".")
    # Tidak boleh ada potongan kalimat yang terbelah di tengah
    assert s1 in chunks[0].text


def test_chunk_text_tidak_ada_kata_terpotong():
    words = [
        "pertanian", "berkelanjutan", "meningkatkan", "kesejahteraan",
        "masyarakat", "pedesaan", "secara", "signifikan", "dan", "merata"
    ]
    # Gabungkan menjadi teks panjang tanpa titik
    text = " ".join(words * 20)
    chunks = chunk_text(text, max_chars=150, overlap=40)

    for c in chunks:
        # Periksa bahwa setiap kata di chunk merupakan kata utuh dari daftar kata asli
        chunk_words = c.text.split()
        for w in chunk_words:
            assert w in words, f"Kata terpotong ditemukan: {w}"


def test_chunk_text_dua_chunk_berurutan_berbagi_overlap():
    s1 = "Pertanian ramah lingkungan memanfaatkan biopestisida nabati untuk menekan serangan hama wereng."
    s2 = "Penggunaan mulsa jerami efektif menjaga kelembaban tanah di musim kemarau panjang."
    s3 = "Sistem irigasi tetes menghemat penggunaan air bersih hingga empat puluh persen pada lahan kering."
    text = f"{s1} {s2} {s3}"

    chunks = chunk_text(text, max_chars=120, overlap=40)
    assert len(chunks) >= 2

    for i in range(len(chunks) - 1):
        c_current = chunks[i].text
        c_next = chunks[i + 1].text

        # Cari bagian yang beririsan (overlap)
        # Ambil akhiran c_current dan pastikan muncul di c_next
        overlap_found = False
        words_current = c_current.split()
        # Ambil 2 kata terakhir dari chunk saat ini
        last_two_words = " ".join(words_current[-2:])
        if last_two_words in c_next:
            overlap_found = True

        assert overlap_found, f"Tidak ada irisan overlap antara chunk {i} dan chunk {i+1}:\nChunk {i}: {c_current}\nChunk {i+1}: {c_next}"


def test_chunk_text_id_berurutan():
    text = "Kalimat pengantar pertama. Kalimat kedua yang lebih panjang. Kalimat ketiga sebagai penutup." * 10
    chunks = chunk_text(text, max_chars=100, overlap=30)
    assert len(chunks) > 1
    assert [c.id for c in chunks] == list(range(len(chunks)))
