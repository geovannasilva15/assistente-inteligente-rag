import json
from dataclasses import replace

import pytest

from lab.ingestion import fingerprint, load_documents, split_documents
from lab.retrieval import IndexUnavailable, Retriever, build_index
from conftest import FakeEncoder


def test_read_clean_split_preserve_metadata(settings):
    docs = load_documents(settings.data_dir)
    chunks = split_documents(docs, 20, 4)
    assert len(docs) == 3
    assert len(chunks) > 12
    for c in chunks:
        assert len(c['text'].split()) <= 20
        assert c['source']['title'] and c['source']['url'] and c['section']
        assert c['source']['accessed'] == '2026-11-03'
    assert len({c['id'] for c in chunks}) == len(chunks)


def test_overlap_is_preserved(settings):
    doc = load_documents(settings.data_dir)[:1]
    chunks = split_documents(doc, 20, 4)
    assert chunks[0]['text'].split()[-4:] == chunks[1]['text'].split()[:4]


@pytest.mark.parametrize('size,overlap', [(0,0),(10,10),(10,-1)])
def test_invalid_chunk_settings(size, overlap):
    with pytest.raises(ValueError):
        split_documents([], size, overlap)


def test_empty_and_invalid_document(tmp_path):
    with pytest.raises(ValueError):
        load_documents(tmp_path)
    (tmp_path / 'broken.json').write_text('{}')
    with pytest.raises(ValueError):
        load_documents(tmp_path)


def test_empty_section_rejected(settings, tmp_path):
    doc = load_documents(settings.data_dir)[0]
    doc['sections'][0]['text'] = '   '
    (tmp_path / 'empty.json').write_text(json.dumps(doc), encoding='utf-8')
    with pytest.raises(ValueError):
        load_documents(tmp_path)


def test_index_persisted_without_encoder_rebuild(settings):
    build_index(settings, FakeEncoder())
    before = (settings.index_dir / 'index.npz').stat().st_mtime_ns
    loaded = Retriever(settings, FakeEncoder())
    results = loaded.search('Embeddings representam textos como vetores numéricos', 3)
    assert results[0]['section_id'] == 'embeddings'
    assert (settings.index_dir / 'index.npz').stat().st_mtime_ns == before
    assert loaded.manifest['corpus_sha256'] == fingerprint(settings.data_dir)


def test_missing_stale_corrupt_index(settings):
    with pytest.raises(IndexUnavailable):
        Retriever(settings)
    build_index(settings, FakeEncoder())
    with pytest.raises(IndexUnavailable):
        Retriever(replace(settings, model='outro'))
    (settings.index_dir / 'index.npz').write_bytes(b'corrupt')
    with pytest.raises(IndexUnavailable):
        Retriever(settings)


def test_corpus_change_requires_reindex(settings, tmp_path):
    build_index(settings, FakeEncoder())
    directory = tmp_path / 'other'; directory.mkdir()
    (directory / 'other.json').write_text('{}')
    with pytest.raises(IndexUnavailable):
        Retriever(replace(settings, data_dir=directory))
