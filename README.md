自动抓下保存 h.acfun（A岛） 上一个串，保存备份为单一的一个html文件到本地

初衷
----
A岛之前有一段时间无法访问，我以为被查水表了，想起有那么多好玩的串没有保存真是后悔。
这次恢复后立即写了个程序能够把整个串保存备份起来。
名字借鉴了一下印象笔记的那个xxxclip，嘛，我的命名品味还是一如既往的底...


用法
------
输入串的网址（请务必从浏览器上的地址栏上复制下来，或者请保证输入内容以http://开头）

文件保存在程序目录下的data文件夹内


注意
-----
现在是完整的备份了！
所以请 *理智* 对待大型的串。。。。


required
--------
- python3
- requests
- bs4

to do
------
- 把图片也抓下来这样就是完整的备份了！  ---->done
- 增加多线程提高效率
- 删掉不显示的html代码节省空间？
- 目前A岛有点问题，>>No.xxx 不相应，无法测试补上回复的串的功能》。。
- 做一个GUI？
- 我的markdown 怎么preview啊啊啊啊