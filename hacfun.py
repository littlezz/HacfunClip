from urllib import parse
from bs4 import BeautifulSoup


import os
from zzlib.decorators import retry_connect, prepare_dir
from requests import get as _get

__author__ = 'zz'

# new version for new A island!


########### CONFIG ###############
DATA_DIRNAME = 'data'

#####################3


@retry_connect(retry_times=3, timeout=2)
def requests_get(url, **kwargs):
    return _get(url, **kwargs)


def get_beautifulsoup_content(url):
    return BeautifulSoup(requests_get(url).content)



class Board:

    def __init__(self, board_bs: BeautifulSoup):
        self.bs = board_bs

    def run(self):
        pass


class Page:
    def __init__(self, url, is_first_page=True):
        self.is_first_page = is_first_page
        self.url = url
        self.bs = None

    @property
    def _boards(self):
        """
        :return: a list of the instance of Board
        """
        self.bs = get_beautifulsoup_content(self.url)

        if self.is_first_page:
            print('text')
            yield self.bs.find('div', class_='h-threads-item-main')

        for reply in self.bs.find_all('div', class_='h-threads-item-reply'):
            yield reply

    def is_endpage(self):
        return False if self.bs.find('a', text='下一页') else True


    def complete_page_output(self):
        """
        单独让每一个board.run, 为后续多线程留出空间
        :return:
        """
        for board in self._boards:
            board.run()
            yield board


class UrlDescriptor:
    def __init__(self, name):
        self.name = name

    def __get__(self, obj, owner):
        return obj.__dict__[self.name]

    def __set__(self, obj, value):
        parsed_url = parse.urlparse(value)
        if not (parsed_url.scheme and parsed_url.netloc):
            raise TypeError('unvalid url')
        else:
            obj.__dict__[self.name] = value

class UserInput:
    url = UrlDescriptor('url')

    def __init__(self, url, dirname=None):
        self.url = url
        self.dirname = dirname

    # TODO:
    @staticmethod
    @prepare_dir(DATA_DIRNAME)
    def mkdir_with_username():
        pass




