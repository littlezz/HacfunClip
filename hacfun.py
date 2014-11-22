from bs4 import BeautifulSoup

__author__ = 'zz'

# new version for new A island!

from zzlib.decorators import retry_connect
from requests import get as _get


@retry_connect(retry_times=3, timeout=2)
def requests_get(url, **kwargs):
    return _get(url, **kwargs)


def get_beautifulsoup_content(url):
    return BeautifulSoup(requests_get(url).content)


class Page:
    def __init__(self, url, is_first_page=True):
        self.is_first_page = is_first_page
        self.url = url

    @property
    def html_boards(self):
        self.bs = get_beautifulsoup_content(self.url)

        if self.is_first_page:
            print('text')
            yield self.bs.find('div', class_='h-threads-item-main')

        for reply in self.bs.find_all('div', class_='h-threads-item-reply'):
            yield reply

    def is_endpage(self):
        return False if self.bs.find('a', text='下一页') else True




