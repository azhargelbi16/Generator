from pathlib import Path

p = Path("tests/test_content.py")
content = p.read_text(encoding="utf-8")

new_test = '''

def test_compose_citation_smoothing_meredam_repetisi_beruntun():
    from generator.ai.content import Paragraph, Sentence, compose

    # 4 kalimat berturut-turut dari sumber [0]
    p = Paragraph([
        Sentence("Kalimat pertama membahas isu.", "q1", [0]),
        Sentence("Kalimat kedua memperdalam analisis.", "q2", [0]),
        Sentence("Kalimat ketiga menjelaskan metode.", "q3", [0]),
        Sentence("Kalimat keempat menyajikan temuan.", "q4", [0]),
    ])
    out = compose(p, {0: "(Kalfas et al., 2024)"})
    # Hanya kalimat terakhir yang ditempeli sitasi parentetikal
    assert out == (
        "Kalimat pertama membahas isu. "
        "Kalimat kedua memperdalam analisis. "
        "Kalimat ketiga menjelaskan metode. "
        "Kalimat keempat menyajikan temuan (Kalfas et al., 2024)."
    )
'''

content += new_test
p.write_text(content, encoding="utf-8")
print("Added citation smoothing test to test_content.py")
