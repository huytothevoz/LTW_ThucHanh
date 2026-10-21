"""Flask request/response contract; mock only process spawning (not DB)."""
from unittest.mock import patch

import pytest

flask = pytest.importorskip("flask")
from app import app
from src import db


@pytest.fixture
def client(isolated_db):
    app.config.update(TESTING=True)
    return app.test_client()


def test_initial_dashboard_api(client):
    assert client.get('/').status_code == 200
    assert client.get('/books').status_code == 200
    data = client.get('/api/summary').get_json()
    assert data['total_books'] == 0
    assert data['last_job'] is None
    assert data['recent_jobs'] == []


@pytest.mark.parametrize('payload', [{}, {'max_pages': 0}, {'max_pages': 4},
                                      {'max_pages': '2'}, {'max_pages': 2.0},
                                      {'max_pages': True}, {'max_pages': None},
                                      {'max_pages': 1, 'url': 'https://example.com'}])
def test_invalid_post_rejected(client, payload):
    response = client.post('/api/jobs', json=payload)
    assert response.status_code == 400
    assert response.get_json()['error']['code'] == 'INVALID_MAX_PAGES'
    assert db.summary()['recent_jobs'] == []


def test_post_and_duplicate_job(client):
    with patch('app.subprocess.Popen') as popen:
        response = client.post('/api/jobs', json={'max_pages': 2})
        assert response.status_code == 202
        job_id = response.get_json()['job']['id']
        popen.assert_called_once()
        args = popen.call_args.args[0]
        assert args[-2:] == ['--job-id', str(job_id)]
        assert popen.call_args.kwargs['shell'] is False
        duplicate = client.post('/api/jobs', json={'max_pages': 1})
        assert duplicate.status_code == 409
        assert duplicate.get_json()['error']['code'] == 'JOB_ALREADY_ACTIVE'
    assert client.get(f'/api/jobs/{job_id}').get_json()['job']['status'] == 'PENDING'
    assert client.get('/api/jobs/99999').status_code == 404


def test_filters_and_empty_pages(client, example_book):
    job = db.create_job(1)
    db.mark_job_running(job['id'])
    db.save_book_for_job(job['id'], example_book)
    response = client.get('/api/books?q=testing&min_price=10&max_price=20&page=1')
    assert response.status_code == 200
    assert response.get_json()['total'] == 1
    assert response.get_json()['items'][0]['price_pence'] == 1234
    assert client.get('/api/books?min_price=20&max_price=10').status_code == 400
    assert client.get('/api/books?page=2').get_json()['items'] == []
    assert client.get('/api/books?page=abc').status_code == 400
    assert client.get('/api/books?q=%3Cscript%3E').get_json()['items'] == []
