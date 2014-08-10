__author__ = 'zz'

from bs4 import BeautifulSoup as bs
import os
import requests
import re

import logging
logging.basicConfig(level=logging.WARNING, format='%(message)s',)

########## CONFIG ##################

TIMEOUT = 20
MAX_REQUESTS_TIMES = 3
AJAX_HOST = 'http://h.acfun.tv/homepage/ref'

####################################


def mk_dir(parentpath, name):
    path = os.path.join(parentpath, name)
    try:
        os.mkdir(path)
    except FileExistsError:
        pass
    return path

def set_path(model, imgpath, thumbpath):
    model.imgpath = imgpath
    model.thumbpath = thumbpath

def download(url,filepath):

    def write_file(contents):
        with open(filepath,'wb') as f:
            f.write(contents)

    trytimes = 0
    print('downloading and save to ', filepath)
    while trytimes < MAX_REQUESTS_TIMES:
        try:
            content = requests.get(url, timeout=TIMEOUT).content
        except requests.exceptions.Timeout:
            trytimes += 1
        else:
            write_file(content)

            break

BASEDATA_DIR = mk_dir(os.getcwd(), 'data')
patttern = re.compile(r'>>No\.(\d+)')


class Board:

    imgpath = 'img'
    thumbpath = 'thumb'

    def __init__(self, table):
        self.table = table
        self.support = False
        self.check_support()

    def check_support(self):
        try:
            self.table + 'test_support'
        except TypeError:
            self.support = True


    def reply2table(self):

        if not self.support:
            return self.table

        self.blockquote = self.table.find('blockquote')
        logging.debug(str(self.blockquote))
        reply_number = self.find_reply()
        if reply_number:
            ajaxtable = self.get_replytable(reply_number)
            ajaxtable['border'] = '1'
            self.blockquote.insert(0, ajaxtable)

        return self.table



    def get_replytable(self, reply_number):
        self.url = AJAX_HOST + '?tid=' + reply_number
        logging.debug(self.url)
        return HtmlCLip(self.url).beautifulsoup_contents()[0]

    def dealwith_img(self):
        """
        tag_img  -->  thumb
        tag_a    -->  img

        """
        if not self.support:
            return

        def reset_link():
            self.tag_a['href'] = os.path.join('img', os.path.basename(self.imgfile_path))
            self.tag_img['src'] = os.path.join('thumb', os.path.basename(self.thumbfile_path))


        self.tag_img = self.table.find('img')

        #logging.debug(str(self.tag_img),str(type(self.tag_img)))
        if self.tag_img:
            self.tag_a = self.tag_img.parent
            self._new_linkpath()


            download(self.tag_img.get('src'), self.thumbfile_path)
            download(self.tag_a.get('href'), self.imgfile_path)
            reset_link()

    def _new_linkpath(self):
        def _get_imgname(s):
            return s.split('/')[-1]

        self.imgfile_path = os.path.join(self.imgpath, _get_imgname(self.tag_a.get('href')))
        self.thumbfile_path = os.path.join(self.thumbpath, _get_imgname(self.tag_img.get('src')))

    def result(self):
        self.dealwith_img()
        self.reply2table()
        return self.table

    def find_reply(self):
        if not self.blockquote:
            return None
        group = patttern.search(self.blockquote.text)
        if group:
            return group.groups()[0]
        else:
            return None



class HtmlCLip:
    """ find table board
    """
    def __init__(self, url, threadsnumber='0', firstpage=False):
        #self.content = self.bsresponse(url)
        self.url = url
        self.firstpage = firstpage
        self.threadsnumber = threadsnumber
        self.content = self.bsresponse(url)

    def board_parse(self):

        self.find_board()
        parsed = []
        for i in self.board:
            parsed.append(Board(i).result())
        self.parsed_board = parsed
        return parsed

    def find_board(self):
        self.board = self.content.find_all('table', {'id': True, 'border': '0'})

        if self.firstpage:
            temp = []
            for i in self.get_maincontent().children:
                if i in self.board:
                    break
                else:
                    temp.append(i)
            self.board = temp + self.board
        return self.board

    def bsresponse(self, url):
        req = requests.get(url)
        return bs(req.content)

    def get_maincontent(self):
        return self.content.find('div', class_='threads_' + self.threadsnumber)

    def beautifulsoup_contents(self):
        return self.board_parse()

    def str_contents(self):
        self.board_parse()
        return [str(item) for item in self.parsed_board]

    def isendpage(self):
        if not self.content.find('a', text='下一页'):
            return True
        else:
            return False


class MainThreads:
    """whole threads"""

    def __init__(self, url):
        self.page = 1
        self.url = self.clean_url(url)
        self.threads = self.get_threads()
        self.init_path()
        set_path(Board, imgpath=self.imgpath, thumbpath=self.thumbpath)
        self.filepath = os.path.join(self.workpath, self.threads + '.html')

    #context manager
    def __enter__(self):
        with open(self.filepath, 'w', encoding='utf8')as f:
            f.write('<div>')

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.write_html('</div>')

    def init_path(self):
        self.workpath = mk_dir(BASEDATA_DIR, self.threads)
        self.imgpath = mk_dir(self.workpath, 'img')
        self.thumbpath = mk_dir(self.workpath, 'thumb')

    def travelandwrite_html(self):

        while True:
            requesturl = self.make_requesturl()
            new_html = HtmlCLip(requesturl)

            self.print_info()

            if self.page == 1:
                new_html.threadsnumber = self.threads
                new_html.firstpage = True

            for item in new_html.str_contents():
                self.write_html(item)
            if new_html.isendpage():
                break
            self.page += 1

    def write_html(self, content):
        with open(self.filepath, 'a', encoding='utf8') as f:
            f.write(content)

    def make_requesturl(self):
        return self.url + '?page=' + str(self.page)

    def clean_url(self, url):
        return url.split('?')[0]

    def get_threads(self):
        """return str threads"""
        return str(self.url.split('/')[-1])

    def print_info(self):
        print('dealing with page', self.page)


def main():
    url = input('please input the url start with http://! \n')
    mainthreads = MainThreads(url)
    with mainthreads:
        mainthreads.travelandwrite_html()
        print('done!')

if __name__ == '__main__':
    main()
