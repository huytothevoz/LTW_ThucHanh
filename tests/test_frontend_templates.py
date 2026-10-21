"""Smoke-test Jinja template expansion in VI and EN without needing Flask runtime."""
from pathlib import Path
from jinja2 import Environment,FileSystemLoader,select_autoescape
from src.i18n import translate

ROOT=Path(__file__).parents[1]


def test_all_web_templates_render_and_languages():
    env=Environment(loader=FileSystemLoader(str(ROOT/'templates')),autoescape=select_autoescape(['html']))
    env.globals['url_for']=lambda name,filename=None,**kw: '/static/'+str(filename)
    account={'id':1,'full_name':'Nguyễn Văn A','email':'test@example.com','created_at':'2026-10-21T00:00:00Z'}
    for locale in ('vi','en'):
        for name in ('index','auth','dashboard','books','saved','history','analytics','sources','settings','help','404','500'):
            user=account if name in {'dashboard','books','saved','history','analytics','sources','settings','help'} else None
            active={'dashboard':'overview','books':'catalog','saved':'bookmarks','history':'history','analytics':'analytics','sources':'sources','settings':'settings','help':'guide'}.get(name)
            output=env.get_template(name+'.html').render(t=lambda key:translate(key,locale),locale=locale,csrf='TEST',user=user,
                active_page=active,mode='login',prefs={'theme':'light','book_layout':'grid','locale':locale},reset_token='abcdef')
            assert '<html lang="'+locale+'"' in output,name
            assert 'CrawlInsight' in output,name
            assert '<main ' in output,name
            assert 'src="/static/js/common.js"' in output,name


def test_translations_cover_core_routes():
    required=['overview','catalog','history','analytics','sources','settings','guide','bookmarks','signin','signup','forgot','reset_password']
    for locale in ('vi','en'):
        assert all(translate(key,locale)!=key for key in required)
