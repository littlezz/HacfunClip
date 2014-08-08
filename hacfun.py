__author__ = 'zz'

from bs4 import BeautifulSoup as bs
import os
import requests
import re

########## CONFIG ##################

TIMEOUT = 2
AJAX_HOST = 'http://h.acfun.tv/homepage/ref'

####################################


def mkandcd_dir(parentpath, name):
    path = os.path.join(parentpath, name)
    try:
        os.mkdir(path)
    except FileExistsError:
        os.chdir(path)

BASEDATA_DIR = os.path.join(os.getcwd(), 'data')
mkandcd_dir(os.getcwd(), 'data')
patttern = re.compile(r'>>No\.(\d+)')


class Board:
    def __init__(self, table):
        self.table = table

    def reply2table(self):
        try:
            self.table + 'test'
        except TypeError:

            self.blockquote = self.table.find('blockquote')
            reply_number = self.find_reply()
            if reply_number:
                ajaxtable = self.get_replytable(reply_number)
                self.blockquote.insert(0, ajaxtable)

            return self.table

        else:
            return self.table

    def get_replytable(self, reply_number):
        url = AJAX_HOST + '?id=' + reply_number
        return HtmlCLip(url).beautifulsoup_contents()[0]

    def result(self):
        self.reply2table()
        return self.table

    def find_reply(self):
        group = patttern.search(str(self.blockquote))
        if group:
            return group.groups()[0]
        else:
            return None
    #def result(self):


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
        self.board = self.content.find_all('table', {'id':True, 'border':'0'})

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
        self.filepath = os.path.join(BASEDATA_DIR, self.threads, self.threads + '.html')

    #context manager
    def __enter__(self):
        mkandcd_dir(BASEDATA_DIR, self.threads)
        with open(self.filepath, 'w', encoding='utf8')as f:
            f.write('<div>')

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.write_html('</div>')

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
        print('dealing with page',self.page)

def main():
    url = input(r'please input the url start with http://! ')
    mainthreads = MainThreads(url)
    with mainthreads:
        mainthreads.travelandwrite_html()
        print('done!')

if __name__ == '__main__':
    main()