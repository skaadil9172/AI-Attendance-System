import pytest
import numpy as np
from src.pipelines.voice_pipeline import identify_speaker

def test_identify_speaker_success():
    # Setup test normalized embeddings (length 1)
    new_emb = np.array([1.0, 0.0, 0.0])
    candidates = {
        101: [1.0, 0.0, 0.0],
        102: [0.0, 1.0, 0.0],
    }
    
    sid, score = identify_speaker(new_emb, candidates, threshold=0.65)
    assert sid == 101
    assert pytest.approx(score) == 1.0

def test_identify_speaker_below_threshold():
    new_emb = np.array([0.5, 0.5, 0.0])  # Cosine similarity is 0.5
    candidates = {
        101: [1.0, 0.0, 0.0],
    }
    
    sid, score = identify_speaker(new_emb, candidates, threshold=0.65)
    assert sid is None
    assert pytest.approx(score) == 0.5

def test_identify_speaker_empty():
    sid, score = identify_speaker(None, {})
    assert sid is None
    assert score == 0.0
