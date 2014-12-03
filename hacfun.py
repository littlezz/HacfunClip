from queue import Queue
import re
import threading
from urllib import parse as urllib_parse
import weakref
from bs4 import BeautifulSoup
import os
from zzlib.decorators import retry_connect, prepare_dir, loop
from requests import get as _get
from zzlib.utils import SafeString
from contextlib import contextmanager
import logging
logging.basicConfig(level=logging.DEBUG, format='%(threadName)s %(message)s')

__author__ = 'zz'

# new version for new A island!

########### CONFIG ###############
DATA_DIRNAME = 'data'
BASE_SITE = 'http://h.acfun.tv'
AJAX_HOST = 'http://h.acfun.tv/homepage/ref?tid='
#####################3


@retry_connect(retry_times=3, timeout=2)
def requests_get(url, **kwargs):
    return _get(url, **kwargs)


def get_beautifulsoup_content(url):
    return BeautifulSoup(requests_get(url).content)


@prepare_dir(DATA_DIRNAME)
def mkdir_with_dirname(dirname):
    if not os.path.exists(dirname):
        os.mkdir(dirname)



class AsyncImageDownload:
    sentinel = object()

    def __init__(self, threading_num=4):
        self._q = Queue()
        self.threading_num = threading_num

    def start(self):
        for i in range(self.threading_num):
            t = threading.Thread(target=self._process)
            t.start()

    @loop
    def _process(self):
        #exit
        data = self._q.get()
        if data == self.sentinel:
            self._q.put(data)
            return True
        img_url, img_path = data

        if os.path.exists(img_path):
            return False
        else:
            imgdata = requests_get(img_url).content
            with open(img_path, 'wb')as file:
                file.write(imgdata)

    def put_data(self, data):
        """
        data: (img_url, img_path)
        """
        self._q.put(data)

    def stop(self):
        self.put_data(self.sentinel)


class AjaxContentManager:
    """
    缓存 reply ajax 的内容.
    """
    def __init__(self):
        self._cache = weakref.WeakValueDictionary()

    def get(self, url):
        """
        返回的是BeautifulSoup instance
        """
        if url not in self._cache:
            bs = get_beautifulsoup_content(url)
            return bs
        else:
            return self._cache[url]


class Board:
    acmanager = AjaxContentManager()
    aidmanager = None
    enable_plugin = ['_plugin_complete_replyid', '_plugin_reply_insert']
    replyref_pat = re.compile(r'>>No\.(\d+)')

    def __init__(self, board_bs: BeautifulSoup):
        self.bs = board_bs

    def __str__(self):
        return str(self.bs)

    def run(self):

        #run plugin
        for plugin_name in self.enable_plugin:
            getattr(self, plugin_name)()

    @classmethod
    def set_aidmanager(cls, aid_object):
        setattr(cls, 'aidmanager', aid_object)

    def _plugin_complete_replyid(self):
        link = self.bs.find('a', 'h-threads-info-id')
        link['href'] = BASE_SITE + link['href']

    def _plugin_reply_insert(self):
        reply_content = self.bs.find('div', 'h-threads-content')
        if self.replyref_pat.search(reply_content.text):
            reply_num = self.replyref_pat.search(reply_content.text).group(1)
            logging.debug('reply number: %s', reply_num)
            ajax_board = Board(self.acmanager.get(AJAX_HOST + reply_num))
            ajax_board.run()
            reply_content.insert(0, ajax_board.bs)

    #TODO: write imgdownload plugin
    def _plugin_img_download(self):
        pass


class Page:
    def __init__(self, url, pn=1):
        """bs is BeautifulSoup object
        pn: int
        """
        self._baseurl = url
        self.pn = pn
        self.bs = get_beautifulsoup_content(self.url)

    @property
    def url(self):
        return self._baseurl + '?page=' + str(self.pn)

    @property
    def html_head_str(self):
        return str(self.bs.head)

    @property
    def html_wrap_div_str(self):
        ret = '<div class="h-threads-item uk-clearfix" data-threads-id="{data-threads-id}">'
        return ret.format_map(self.bs.find('div', class_='h-threads-item uk-clearfix').attrs)

    @property
    def final_content_str(self):
        """
        单独让每一个board.run, 为后续多线程留出空间
        返回整合的页面.
        """
        board_str_list = []
        for board in self._boards():
            board.run()
            board_str_list.append(str(board))

        return ''.join(board_str_list)

    def _boards(self):
        """
        :return: a list of the instance of Board
        """
        if self.pn == 1:
            yield Board(self.bs.find('div', class_='h-threads-item-main'))
        for reply in self.bs.find_all('div', class_='h-threads-item-reply'):
            yield Board(reply)

    def next(self):
        """ 翻页, 获取内容"""
        self.pn += 1
        self.bs = get_beautifulsoup_content(self.url)

    def is_endpage(self):
        return False if self.bs.find('a', text='下一页') else True


class BaseDescriptor:
    def __init__(self, name):
        self.name = name

    # no need to define __get__
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
    """
    img_dir 存放大图的目录地址,
    thunm_dir 小兔的目录地址.
    base_dir 是串的名字的地址.
    filepath 是html文件的地址.
    """
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
def page_go(page: Page, file):
    """
    名字有点奇葩...我懂...我懂..
    好吧, 我只是单纯的想用loop 修饰器而已...
    """
    file.write(str(page.final_content_str))
    if page.is_endpage():
        return True

    page.next()


@contextmanager
def extrawork_page_go(page: Page, file):
    """
    添加<head> , 补足标签之类的.
    """

    # 添加head里的链接, 添加css的包裹div
    pat = re.compile(r'(?<==\")(/.*?)(?=\")', flags=re.DOTALL)
    html_head = pat.sub(lambda x: BASE_SITE + x.group(1), page.html_head_str)

    wrap_div = page.html_wrap_div_str

    # FIXME: 这个部分应该再考虑, replyes的div应该在po的后面, 但是目前这样没有问题.
    wrap_div_replys = '<div class="h-threads-item-replys">'
    file.write(html_head + wrap_div + wrap_div_replys)
    yield

    # 两个wrap_div
    file.write('</div></div>')


def main():
    user_input = UserInput()
    user_input.collect_input()
    page = Page(user_input.url)

    # start image download threading!
    aid = AsyncImageDownload()
    Board.set_aidmanager(aid)
    aid.start()

    with open(user_input.filepath, 'w', encoding='utf8') as file:
        with extrawork_page_go(page, file):
            page_go(page, file)

    aid.stop()

if __name__ == '__main__':
    main()