import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from src.pipelines.face_pipeline import predict_attendance

@patch('src.pipelines.face_pipeline.get_all_students')
@patch('src.pipelines.face_pipeline.get_trained_model')
@patch('src.pipelines.face_pipeline.get_face_embeddings')
def test_predict_attendance(mock_get_face_embeddings, mock_get_trained_model, mock_get_all_students):
    # Mock face embeddings found in test image
    mock_get_face_embeddings.return_value = [np.array([0.1] * 128)]
    
    # Mock SVM classifier and training data
    mock_clf = MagicMock()
    mock_clf.predict.return_value = [42]
    
    mock_get_trained_model.return_value = {
        'clf': mock_clf,
        'X': [np.array([0.1] * 128)],
        'y': [42]
    }
    
    detected, all_ids, count = predict_attendance(np.zeros((100, 100, 3)))
    
    assert 42 in detected
    assert count == 1
    assert all_ids == [42]
