
status
----------------
由于新版A岛, 我正在对整个程序进行一重写 ---2014-11-19
目前可以使用, 无法备份图片,增加了头文件使用A岛的排版. ------2014-11-28

自动抓下保存 h.acfun（A岛） 上一个串，保存备份为单一的一个html文件到本地

初衷
----
A岛之前有一段时间无法访问，我以为被查水表了，想起有那么多好玩的串没有保存真是后悔。  
这次恢复后立即写了个程序能够把整个串保存备份起来。  
名字借鉴了一下印象笔记的那个xxxclip，嘛，我的命名品味还是一如既往的低...  


用法
------
 输入串的网址（请务必从浏览器上的地址栏上复制下来，或者请保证输入内容以http://开头）  
 输入要起的名字（直接按回车可以跳过）  
 文件保存在程序目录下的data文件夹内  
 


注意
-----
现在是完整的备份了！  
所以请 *理智* 对待大型的串。。。。  
点击帖子的id会在新标签打开对应的串，某索引串方便使用成为可能。σ`∀´)σ  

required
--------
- python3
- requests
- beautifulsoup4 >= 4.3.2
- lxml

to do
------
- 把图片也抓下来这样就是完整的备份了！            ---->done
- 增加多线程提高效率                            ---->done
- 减少不必要的连接：不要下载重复的图片和保留访问过的回复 -------->done!
- 将帖子的id连接转化为完整的连接  ------>done!
- 修正多线程产生的小bug  ------>done!
- ~~目前A岛有点问题，>>No.xxx 不相应，无法测试补上回复的串的功能》。。~~
- 做一个GUI？
- ~~我的markdown 怎么preview啊啊啊啊~~

版本
-----
v1.33 单线程   
v2.33 多线程，多加了一个可以定义名称的输入等待。2014-8-13  
v2.34 修正找不到页面会出错的bug，另外不重复下载图片已经在2.33完成 8-17  
v3.17 优化效率，缓存访问过的串减少重复访问时间。  
v3.71 帖子id转为完整连接，修复多线程引发的bug。  8-22  
v3.72 删减一些没有的代码，更新依赖关系，确保安装lxml库，默认线程数设置为4。   8-

