import pytest

from rag.chunking import chunk_text


def test_chunks_respect_size_and_cover_text():
    text = " ".join(f"Sentence number {i} about coverage." for i in range(200))
    chunks = chunk_text(text, chunk_size=300, overlap=60)
    assert len(chunks) > 5
    assert all(len(c) <= 301 for c in chunks)
    assert "Sentence number 0 " in chunks[0] and "Sentence number 199 " in chunks[-1]


def test_overlap_repeats_trailing_sentence():
    text = "Alpha one is here. Beta two is here. Gamma three is here. Delta four is here."
    chunks = chunk_text(text, chunk_size=40, overlap=25)
    assert len(chunks) == 3
    assert chunks[0].endswith("Beta two is here.") and chunks[1].startswith("Beta two is here.")


def test_oversized_sentence_is_split():
    chunks = chunk_text("word " * 500, chunk_size=100, overlap=10)
    assert all(len(c) <= 101 for c in chunks) and len(chunks) > 10


def test_unbreakable_token_is_split():
    assert all(len(c) <= 50 for c in chunk_text("x" * 230, chunk_size=50, overlap=5))


def test_empty_and_invalid():
    assert chunk_text("   \n ") == []
    with pytest.raises(ValueError):
        chunk_text("abc", chunk_size=10, overlap=10)
