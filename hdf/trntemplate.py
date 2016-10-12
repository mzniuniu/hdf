# -*- coding: utf-8 -*-
"""
    hdf.trntemplate
    ~~~~~~~~~~~~~~~~

    Transaction Class Template

    :copyright: (c) 2016 by LiuZhaoHui.
    :license: BSD, see LICENSE for more details.
"""


class TrnTemplate(object):
    def __init__(self, trncde, trnuid, indict):
        self.trncde = trncde  # 交易代码
        self.trnuid = trnuid  # 系统交易流水号
        self.indict = indict  # 进参，DICT格式
        self.ret_data = {}  # 返回的DICT格式数据
        self.isdict = True  # 是否返回DICT格式数据，False返回LIST格式
        self.ret_list = []  # 返回的LIST格式数据
        # self.rows=None        #初始的返回记录
        self.total = None  # 初始的返回记录数
        self.retcde = None  # 初始的返回代码
        self.retmsg = None  # 初始的返回信息

    def service(self):
        self.run()
        if self.isdict:
            if self.ret_list:
                self.ret_data['rows'] = self.ret_list
            if self.total is not None:
                self.ret_data['total'] = self.total
            if self.retcde is not None:
                self.ret_data['retcde'] = self.retcde
            if self.retmsg is not None:
                self.ret_data['retmsg'] = self.retmsg
            # self.ret_data['success'] = True if self.retcde >= 0 else False
            return self.ret_data  # 返回DICT数据格式
        else:
            return self.ret_list  # 返回LIST数据格式

    def run(self):  # 交易执行过程
        pass
