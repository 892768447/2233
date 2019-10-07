#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Created on 2019/10/6
@author: Irony
@site: https://pyqt5.com , https://github.com/892768447
@email: 892768447@qq.com
@file: main
@description: 
"""
import json
import os
import socket
import urllib.request
from random import choice, randint

from PyQt5.QtCore import QUrl, QUrlQuery, QThread, Qt, pyqtSlot
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtWebEngineCore import QWebEngineUrlRequestInterceptor
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile


class ApiRequestInterceptor(QWebEngineUrlRequestInterceptor):
    # 没有用http服务,采用自身拦截url请求来达到模拟效果
    # 参考api.php文件

    def __init__(self, port, *args, **kwargs):
        super(ApiRequestInterceptor, self).__init__(*args, **kwargs)
        self.port = port

    def get_live2d_data(self, p, model, r18):
        """
        # 参考api.php文件
        :param p: 人物 22或者33
        :param model: 模式 rand表示随机
        :param r18: 18禁
        :return:
        """
        persons = [22, 33]
        try:
            p = int(p)
            if p not in persons:
                p = choice(persons)
        except Exception as e:
            print(e)
            p = choice(persons)
        idle3 = 100 if p == 22 else 1000
        tap1 = 150 if p == 22 else 500
        tap2 = 100 if p == 22 else 200
        ra = randint(1, 15) if r18 else randint(1, 14)
        open('model/model.json', 'wb').write(json.dumps({
            'model': 'model/{p}/{p}.v2.moc'.format(p=p),
            'textures': [
                'model/{p}/textures/texture_00.png'.format(p=p),
                'model/{p}/textures/texture_01/{ra}.png'.format(p=p, ra=ra if model == 'rand' else 1),
                'model/{p}/textures/texture_02/{ra}.png'.format(p=p, ra=ra if model == 'rand' else 1),
                'model/{p}/textures/texture_03/{ra}.png'.format(p=p, ra=ra if model == 'rand' else 12)
            ],
            'hit_areas_custom': {
                'head_x': [-0.35, 0.6],
                'head_y': [0.19, -0.2],
                'body_x': [-0.3, -0.25],
                'body_y': [0.3, -0.9]
            },
            'layout': {
                'center_x': -0.05,
                'center_y': 0.25,
                'height': 2.7
            },
            'motions': {
                'idle': [{
                    'file': 'model/{p}/{p}.v2.idle-01.mtn'.format(p=p),
                    'fade_in': 2000,
                    'fade_out': 2000
                }, {
                    'file': 'model/{p}/{p}.v2.idle-02.mtn'.format(p=p),
                    'fade_in': 2000,
                    'fade_out': 2000
                }, {
                    'file': 'model/{p}/{p}.v2.idle-03.mtn'.format(p=p),
                    'fade_in': idle3,
                    'fade_out': idle3
                }
                ],
                'tap_body': [{
                    'file': 'model/{p}/{p}.v2.touch.mtn'.format(p=p),
                    'fade_in': tap1,
                    'fade_out': tap2
                }
                ],
                'thanking': [{
                    'file': 'model/{p}/{p}.v2.thanking.mtn'.format(p=p),
                    'fade_in': 2000,
                    'fade_out': 2000
                }
                ]
            }
        }).encode())

    def interceptRequest(self, info):
        url = info.requestUrl()
        if url.hasQuery() and url.path().endswith('api'):
            query = QUrlQuery(url.query())
            p = query.queryItemValue('p')
            model = query.queryItemValue('model')
            r18 = query.queryItemValue('r18')
            self.get_live2d_data(p, model, r18)
            # 重定向
            info.redirect(QUrl('http://127.0.0.1:{0}/model/model.json'.format(self.port)))


class HttpServer(QThread):

    def __init__(self, port, *args, **kwargs):
        super(HttpServer, self).__init__(*args, **kwargs)
        self.port = port

    def run(self):
        print(int(self.currentThreadId()))
        from http.server import test, CGIHTTPRequestHandler
        test(HandlerClass=CGIHTTPRequestHandler, port=self.port, bind='')


class Window(QWebEngineView):

    def __init__(self, *args, **kwargs):
        super(Window, self).__init__(*args, **kwargs)
        self.resize(246, 305)
        rect = QApplication.instance().desktop().availableGeometry()
        self.move(rect.width() - 246, rect.height() - 305)
        self.setAttribute(Qt.WA_QuitOnClose, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)  # 设置父控件Widget背景透明
        # 去掉边框
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setContextMenuPolicy(Qt.NoContextMenu)
        self.port = 8000
        self.get_avaliable_port()  # 生成随机端口
        # 设置url拦截器
        QWebEngineProfile.defaultProfile().setUrlRequestInterceptor(ApiRequestInterceptor(self.port, self))
        # window.close 关闭窗口
        self.page().windowCloseRequested.connect(self.close)
        # 透明
        self.page().setBackgroundColor(Qt.transparent)
        # 交互
        self.channel = QWebChannel(self)
        # 把自身对象传递进去
        self.channel.registerObject('Bridge', self)
        # 设置交互接口
        self.page().setWebChannel(self.channel)
        # 本地http静态服务器
        self.http_server = HttpServer(self.port, self)
        self.http_server.start()
        while 1:
            # 等待http服务
            try:
                if urllib.request.urlopen('http://127.0.0.1:{0}/index.html'.format(self.port)).read():
                    break
            except:
                pass
        self.load(QUrl('http://127.0.0.1:{0}/index.html'.format(self.port)))

    def get_avaliable_port(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('', 0))
        s.listen(1)
        self.port = s.getsockname()[1]
        s.close()

    def close(self):
        self.http_server.terminate()
        self.http_server.deleteLater()
        super(Window, self).close()

    @pyqtSlot(str)
    def open(self, url):
        QDesktopServices.openUrl(QUrl(url))

    @pyqtSlot()
    def stayTop(self):
        if self.windowFlags() & Qt.WindowStaysOnTopHint:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

    @pyqtSlot(float, float, bool)
    def moveTo(self, left, top, jump=False):
        left = int(left)
        top = int(top)
        if jump:
            pass
        else:
            self.move(self.x() + left, self.y() + top)


if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication

    os.chdir('res')

    app = QApplication(sys.argv)
    app.setApplicationDisplayName('2233')
    app.setApplicationName('2233')
    app.setQuitOnLastWindowClosed(True)
    app.lastWindowClosed.connect(app.quit)
    w = Window()
    w.show()
    sys.exit(app.exec_())
