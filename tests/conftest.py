import hashlib
import re
from dataclasses import replace

import numpy as np
import pytest

from lab.config import Settings
from lab.retrieval import Retriever, build_index
from lab.service import Service


class FakeEncoder:
    """Substituto lexical deterministico: NAO e teste de qualidade semantica."""
    def vector(self, text):
        v = np.zeros(256, dtype=np.float32)
        for token in re.findall(r"\w+", text.casefold()):
            v[int(hashlib.sha256(token.encode()).hexdigest(), 16) % len(v)] += 1
        return v

    def documents(self, texts):
        return np.array([self.vector(t) for t in texts])

    def query(self, text):
        return self.vector(text)


@pytest.fixture
def settings(tmp_path):
    return replace(Settings(), index_dir=tmp_path / "index", reports_dir=tmp_path / "reports", min_similarity=.1)


@pytest.fixture
def service(settings):
    encoder = FakeEncoder()
    build_index(settings, encoder)
    return Service(settings, Retriever(settings, encoder))
