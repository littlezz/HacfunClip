from urllib import parse as urllib_parse
from bs4 import BeautifulSoup
import os
from zzlib.decorators import retry_connect, prepare_dir, loop
from requests import get as _get
from zzlib.utils import SafeString
import logging
logging.basicConfig(level=logging.DEBUG, format='%(message)s')

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
    os.mkdir(dirname)



class Board:

    def __init__(self, board_bs: BeautifulSoup):
        self.bs = board_bs

    def __str__(self):
        return str(self.bs)

    def run(self):
        pass



class Page:
    def __init__(self, url, pn=1):
        """bs is BeautifulSoup object

        pn: int
        """
        self._baseurl = url
        self.bs = None
        self.pn = pn

    @property
    def url(self):
        return self._baseurl + '?page=' + str(self.pn)

    @property
    def _boards(self):
        """
        :return: a list of the instance of Board
        """
        self.bs = get_beautifulsoup_content(self.url)

        if self.pn <= 1:
            yield Board(self.bs.find('div', class_='h-threads-item-main'))

        for reply in self.bs.find_all('div', class_='h-threads-item-reply'):
            yield Board(reply)

    def next(self):
        self.pn += 1

    def is_endpage(self):
        return False if self.bs.find('a', text='下一页') else True

    @property
    def finally_boards(self):
        """
        单独让每一个board.run, 为后续多线程留出空间
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
            # clean url
            value = value.split('?')[0]

            super().__set__(instance, value)


class PathDescriptor(BaseDescriptor):
    plugings = [mkdir_with_dirname, ]

    def __set__(self, instance, value):
        """
        with plugin that mkdir.
        """
        super().__set__(instance, value)

        for plugin_func in self.plugings:
            plugin_func(value)


class UserInput:
    url = UrlDescriptor('url')
    base_dir = PathDescriptor('base_dir')
    img_dir = PathDescriptor('img_dir')
    thumb_dir = PathDescriptor('thumb_dir')

    def __init__(self):
        self.filepath = ''

    def collect_input(self):
        self.url = input('输入串的网址\n')

        default_dirname = self.url.split('/')[-1]

        dirname_ = input("输入自定义的名字(默认为'{}'), 直接回车跳过\n".format(default_dirname))
        dirname = SafeString().sanitized_dirname(dirname_) if dirname_ else default_dirname

        self.base_dir = os.path.join(DATA_DIRNAME, dirname)
        self.filepath = os.path.join(self.base_dir, dirname + '.html')

        logging.debug('base_dir: %s', self.base_dir)
        logging.debug('filepath: %s', self.filepath)

        # setup inner dir
        self.img_dir = os.path.join(self.base_dir, 'img')
        self.thumb_dir = os.path.join(self.base_dir, 'thumb')

        logging.debug('img_dir: %s', self.img_dir)



@loop
def page_go(page, file):
    """
    名字有点奇葩...我懂...我懂..
    好吧, 我只是单纯的想用loop 修饰器而已...
    """
    for board in page.finally_boards:
        file.write(str(board))

    if page.is_endpage():
        return True
    page.next()


def main():
    user_input = UserInput()
    user_input.collect_input()
    page = Page(user_input.url)

    with open(user_input.filepath, 'w', encoding='utf8') as f:
        page_go(page, f)

if __name__ == '__main__':
    main()