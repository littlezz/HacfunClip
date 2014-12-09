from functools import partial
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
#################################


@retry_connect(retry_times=3, timeout=2)
def requests_get(url, **kwargs):
    return _get(url, **kwargs)


def get_beautifulsoup_content(url):
    return BeautifulSoup(requests_get(url).content)


@prepare_dir(DATA_DIRNAME)
def mkdir_with_dirname(dirname):
    """在确保DATA_DIRNAME的情况下创建dirname"""
    if not os.path.exists(dirname):
        os.mkdir(dirname)


class AsyncImageDownload:
    sentinel = object()

    def __init__(self, threading_num=4):
        self._q = Queue()
        self.threading_num = threading_num
        self._cache = set()
        self._lock = threading.Lock()

    def start(self):
        for i in range(self.threading_num):
            t = threading.Thread(target=self._process)
            t.start()

    @loop
    def _process(self):
        img_url, img_path = self._q.get()

        # exit
        if img_url == self.sentinel:
            self._q.put((self.sentinel,) * 2)
            return True

        if os.path.exists(img_path) or img_url in self._cache:
            logging.debug('pass download %s', img_path)
            return False
        else:
            logging.debug('Star Download %s', img_url)
            with self._lock:
                self._cache.add(img_url)

            imgdata = requests_get(img_url).content
            with open(img_path, 'wb')as file:
                file.write(imgdata)

    def put_data(self, img_url_img_path: tuple):
        """
        data: (img_url, img_path)
        """
        self._q.put(img_url_img_path)

    def stop(self):
        self.put_data((self.sentinel,) * 2)


class AjaxContentManager:
    """
    缓存 reply ajax 的内容.
    """
    def __init__(self):
        self._cache = weakref.WeakValueDictionary()

    def get(self, url):
        """
        :return: response from requests
        """
        if url not in self._cache:
            ret = requests_get(url)
            self._cache[url] = ret
            return ret
        else:
            return self._cache[url]


class Board:
    acmanager = AjaxContentManager()

    # AsyncImageDownload
    aidmanager = None

    # 会在主函数中设置.
    img_dir = None
    thumb_dir = None

    enable_plugin = [
        '_plugin_img_download',
        '_plugin_complete_replyid',
        '_plugin_del_useless_html',
        '_plugin_reply_insert',
    ]

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
    def set_aidmanager(cls, aid_object: AsyncImageDownload):
        setattr(cls, 'aidmanager', aid_object)

    @classmethod
    def set_img_download_info(cls, img_dir, thumb_dir):
        """设置 图片下载需要的两个文件夹地址"""

        cls.img_dir = img_dir
        cls.thumb_dir = thumb_dir

    def _plugin_complete_replyid(self):
        link = self.bs.find('a', 'h-threads-info-id')
        link['href'] = BASE_SITE + link['href']

    def _plugin_reply_insert(self):
        reply_content = self.bs.find('div', 'h-threads-content')
        if self.replyref_pat.search(reply_content.text):
            reply_num = self.replyref_pat.search(reply_content.text).group(1)

            # 返回响应的对象 Response
            ajax_resp = self.acmanager.get(AJAX_HOST + reply_num)

            if ajax_resp.ok:

                # 增加id, 让回复带上边框
                ajax_content = BeautifulSoup(ajax_resp.content).find('div', class_='h-threads-item-reply-main')
                ajax_content['id'] = 'replyembedded'

                ajax_board = Board(ajax_content)
                ajax_board.run()
                reply_content.insert(0, ajax_board.bs)

    # FIXME: 是不是可以采用注入参数的方法?
    def _plugin_img_download(self):

        def _package_work(filepath_prefix, url, aidmanager):
            """返回修改后的图片文件地址, 向异步图片下载推送相应的信息"""

            filename = url.split('/')[-1]
            save_path = os.path.join(filepath_prefix, filename)
            aidmanager.put_data((url, save_path))

            # 需要替换的html 相对地址
            new_path = os.path.join(os.path.basename(filepath_prefix), filename)
            return new_path

        # 注入参数
        _package_work = partial(_package_work, aidmanager=self.aidmanager)

        if self.aidmanager is None:
            raise TypeError('No aidmanager')

        imgbox = self.bs.find('div', class_='h-threads-img-box') or None

        if imgbox:
            # <img> --> thumb
            htmltag_img = imgbox.find('img')
            htmltag_img['src'] = _package_work(self.thumb_dir, htmltag_img['src'])

            # <a> --> img
            # uk tool <a>
            htmltag_a = imgbox.find('a', class_='h-threads-img-tool-btn')
            htmltag_a['href'] = _package_work(self.img_dir, htmltag_a['href'])

            #link <a>
            htmltag_a = imgbox.find('a', class_='h-threads-img-a')
            htmltag_a['href'] = _package_work(self.img_dir, htmltag_a['href'])

    def _plugin_del_useless_html(self):
        """
        删除管理者才能看到的html文本内容.
        """
        self.bs.find('span', class_='h-admin-tool').extract()


class Page:
    def __init__(self, baseurl, pn=1):
        """bs is BeautifulSoup object
        pn: int
        """
        self._baseurl = baseurl
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
        # 返回包裹的html
        ret = '<div class="h-threads-item uk-clearfix" data-threads-id="{data-threads-id}">'
        return ret.format_map(self.bs.find('div', class_='h-threads-item uk-clearfix').attrs)

    @property
    def final_content_str(self):
        """
        返回处理后整合的页面.
        """

        # 调用.run()
        def board_run(board):
            """单独让每一个board.run"""
            board.run()
            return board

        return ''.join(str(board_run(board)) for board in self._boards())

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
        logging.debug('next page %s', str(self.pn))

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
    def __set__(self, instance, value):
        """
        with plugin that mkdir.
        """
        super().__set__(instance, value)

        mkdir_with_dirname(value)


class UserInput:
    """
    img_dir 存放大图的目录地址,
    thunm_dir 小图的目录地址.
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
    file.write(page.final_content_str)
    if page.is_endpage():
        return True

    page.next()


@contextmanager
def extrawork_page_go(page: Page, file):
    """
    添加<head>连接到A岛的css , 补足标签欠缺的包裹的div
    """

    # 在头信息中加入回复的边框样式, 直接修改了bs内容, 和后面的添加头没有冲突

    css_content = """#replyembedded{border: 2px solid;}"""

    style_tag = BeautifulSoup().new_tag('style')
    style_tag.string = css_content
    page.bs.head.append(style_tag)

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

    #set up plugin img dir
    Board.set_img_download_info(user_input.img_dir, user_input.thumb_dir)

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