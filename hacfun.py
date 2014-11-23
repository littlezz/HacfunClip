from urllib import parse as urllib_parse
from bs4 import BeautifulSoup


import os
from zzlib.decorators import retry_connect, prepare_dir
from requests import get as _get
from zzlib.utils import SafeString

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


@prepare_dir(DATA_DIRNAME)
def mkdir_with_dirname(dirname):
    os.mkdir(os.path.join(DATA_DIRNAME, dirname))



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


class BaseDescriptor:
    def __init__(self, name):
        self.name = name

    def __get__(self, instance, owner):
        return instance.__dict__[self.name]

    def __set__(self, instance, value):
        instance.__dict__[self.name] = value


class UrlDescriptor(BaseDescriptor):
    def __set__(self, instance, value):
        parsed_url = urllib_parse.urlparse(value)
        if not (parsed_url.scheme and parsed_url.netloc):
            raise TypeError('unvalid url')
        else:
            super().__set__(instance, value)


class DirnameDescriptor(BaseDescriptor):
    plugings = [mkdir_with_dirname, ]
    safe_string = SafeString()

    def __set__(self, instance, value):
        """
        safe dirname set
        """
        value = self.safe_string.sanitized_dirname(value)
        super().__set__(instance, value)

        for plugin_func in self.plugings:
            plugin_func(value)


class UserInput:
    url = UrlDescriptor('url')
    dirname = DirnameDescriptor('dirname')

    def collect_input(self):
        self.url = input('输入串的网址\n')
        self.dirname = input('输入自定义的名字, 直接回车跳过\n')





