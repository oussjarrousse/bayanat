import pytest

from app import create_app

@pytest.fixture
def app():
    '''The enferno flask app fixture'''
    app = create_app()
    return app