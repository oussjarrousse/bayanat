import pytest
from flask import url_for

@pytest.mark.public
@pytest.mark.views
def test_index(client):
    assert client.get(url_for('public.index')).status_code == 200

@pytest.mark.public
@pytest.mark.views
def test_feedback(client):
    assert client.get(url_for('public.feedback')).status_code == 200

@pytest.mark.public
@pytest.mark.views
def test_static_from_root(client):
    assert client.get(url_for('public.static_from_root')).status_code == 200