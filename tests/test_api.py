"""Flask integration contract. Executed when Flask/Scrapy dependencies are installed.
External Scrapy process is never actually started by these tests.
"""
from unittest.mock import patch
import pytest
flask=pytest.importorskip('flask')
from app import app
from src import db

@pytest.fixture
def client(isolated_db):
    app.config.update(TESTING=True)
    return app.test_client()


def csrf(client):
    client.get('/login')
    with client.session_transaction() as sess:return sess['csrf']


def req(client,path,data,method='POST'):
    return client.open(path,method=method,json=data,headers={'X-CSRF-Token':csrf(client)})


def register(client,email='duy@example.com',full_name='Phạm Ngọc Duy'):
    resp=req(client,'/api/auth/register',{'full_name':full_name,'email':email,'password':'abcDEF12345!'})
    assert resp.status_code==201, resp.get_json()
    return resp.get_json()['user']


def test_public_landing_auth_and_csrf(client):
    assert client.get('/').status_code==200
    assert client.get('/register').status_code==200
    assert client.get('/forgot-password').status_code==200
    assert client.get('/workspace').status_code==302
    assert client.get('/api/books').status_code==401
    assert client.post('/api/auth/register',json={}).status_code==403
    assert client.get('/?lang=en').status_code==200
    assert b'CrawlInsight' in client.get('/').data


def test_register_pages_and_all_workspaces(client):
    register(client)
    for path in ['/workspace','/books','/saved','/history','/analytics','/sources','/settings','/help']:
        response=client.get(path)
        assert response.status_code==200, (path,response.data[:400])
    assert client.get('/api/summary').get_json()['total_books']==0
    assert client.get('/api/bookmarks').get_json()['total']==0
    assert client.get('/api/history').get_json()['items']==[]
    assert client.get('/api/analytics').get_json()['prices']['total']==0
    assert client.get('/api/sources').get_json()['items'][0]['allowed_host']=='books.toscrape.com'


def test_api_job_validations_and_owner(client):
    u=register(client)
    for item in ({},{'max_pages':0},{'max_pages':4},{'max_pages':'2'},{'max_pages':1,'url':'https://evil.test'}):
        assert req(client,'/api/jobs',item).status_code==400
    with patch('app.subprocess.Popen') as proc:
        response=req(client,'/api/jobs',{'max_pages':2})
        assert response.status_code==202,response.get_json()
        job_id=response.get_json()['job']['id']
        args=proc.call_args.args[0]
        assert args[-2:]==['--job-id',str(job_id)]
        assert req(client,'/api/jobs',{'max_pages':1}).status_code==409
    assert client.get('/api/jobs/'+str(job_id)).status_code==200
    assert client.get('/api/jobs/99999').status_code==404
    assert client.get('/api/history').get_json()['items'][0]['id']==job_id


def test_two_accounts_have_separate_bookmarks_and_sessions(client,example_book):
    a=register(client)
    job=db.create_job(1);db.mark_job_running(job['id']);db.save_book_for_job(job['id'],example_book);db.finish_job(job['id'],'COMPLETED')
    bookid=client.get('/api/books').get_json()['items'][0]['id']
    assert req(client,f'/api/bookmarks/{bookid}',{}).status_code==200
    assert client.get('/api/bookmarks').get_json()['total']==1
    assert req(client,'/api/auth/logout',{}).status_code==200
    register(client,'quy@example.com','Nguyễn Trọng Quý')
    assert client.get('/api/bookmarks').get_json()['total']==0
    assert client.get('/api/books').get_json()['total']==1  # global source catalogue is shared
    assert client.get('/api/history').get_json()['items']==[]
    assert client.get('/api/books/'+str(bookid)).status_code==200


def test_login_settings_saved_filters_and_csv(client,example_book):
    register(client)
    assert req(client,'/api/me/preferences',{'theme':'dark','locale':'en','book_layout':'list'},'PATCH').status_code==200
    assert client.get('/settings').status_code==200
    assert req(client,'/api/saved-searches',{'name':'My first','q':'testing','min_price':'10','max_price':'20'}).status_code==201
    assert client.get('/api/saved-searches').get_json()['items'][0]['name']=='My first'
    assert client.get('/api/exports/books.csv').status_code==200
    assert req(client,'/api/auth/logout',{}).status_code==200
    assert req(client,'/api/auth/login',{'email':'duy@example.com','password':'abcDEF12345!'}).status_code==200
    assert client.get('/api/saved-searches').get_json()['items'][0]['name']=='My first'


def test_password_reset_and_force_reauth(client):
    register(client)
    resp=req(client,'/api/auth/request-reset',{'email':'duy@example.com'})
    assert resp.status_code==200,resp.get_json()
    token=resp.get_json()['local_test_link'].rsplit('/',1)[-1]
    reset=req(client,'/api/auth/reset-password',{'token':token,'password':'NewPass98765'})
    assert reset.status_code==200
    assert client.get('/api/auth/me').get_json()['user'] is None
    assert req(client,'/api/auth/login',{'email':'duy@example.com','password':'NewPass98765'}).status_code==200
    assert req(client,'/api/auth/reset-password',{'token':token,'password':'AnotherPass123'}).status_code==400
