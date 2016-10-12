# -*- coding: utf-8 -*-
"""
    hdf.trnservice
    ~~~~~~~~~~~~~~~~

    Transaction Service

    :copyright: (c) 2016 by LiuZhaoHui.
    :license: BSD, see LICENSE for more details.
"""
import importlib
import redis


class TRNService(object):
    #: Default configuration parameters.
    default_config = dict(
            SERVER_NAME='default_server',
            REDIS_MASTER_HOST='127.0.0.1',
            REDIS_MASTER_PORT=6379,
            REDIS_MASTER_DB=0,
            REDIS_SLAVE_HOST='127.0.0.1',
            REDIS_SLAVE_PORT=6379,
            REDIS_SLAVE_DB=0,
            TRNCDE_PATTERN=['*'],

            # transaction table
            # format 'trncde':{'module':'python module','class':'transaction class','desc':'description'}
            TRNTBL={}
    )

    def __init__(self, config):
        self.config = {}
        self.config.update(self.default_config)
        if config:
            self.config.update(config)
        self.server_name = self.config['SERVER_NAME']
        self.trncde_pattern = self.config['TRNCDE_PATTERN']
        self.trntbl = self.config['TRNTBL']
        self.init_redis(self.config)

    def init_redis(self, config):
        self.master_redis_pool = redis.ConnectionPool(host=config['REDIS_MASTER_HOST'],
                                                      port=config['REDIS_MASTER_PORT'], db=config['REDIS_MASTER_DB'])
        self.slave_redis_pool = redis.ConnectionPool(host=config['REDIS_SLAVE_HOST'], port=config['REDIS_SLAVE_PORT'],
                                                     db=config['REDIS_SLAVE_DB'])
        self.master_redis = redis.StrictRedis(connection_pool=self.master_redis_pool)
        self.slave_redis = redis.StrictRedis(connection_pool=self.slave_redis_pool)

    def service(self):
        # subscribe request message
        print '\n%s listening %s' % (self.server_name, self.trncde_pattern)
        request_pubsub = self.slave_redis.pubsub()
        for channel_pattern in self.trncde_pattern:
            request_pubsub.psubscribe('request:%s:*' % channel_pattern)
        for message in request_pubsub.listen():
            if message['type'] in ['pmessage', 'message']:
                channel = message['channel'].split(':')
                if channel[0] == 'request' and self.master_redis.setnx(message['channel'], self.server_name) == 1:
                    self.master_redis.expire(message['channel'], 60)
                    print '\n%s: receiving transaction request' % (self.server_name)
                    self.send_status_message(message)
                    ret_data = self.get_service_result(message)
                    self.send_result_message(message, ret_data)

    # send transaction request has been accepted message to front server
    def send_status_message(self, request_message):
        channel = request_message['channel'].split(':')
        channel[0] = 'request_status'
        request_status_channel = ':'.join(channel)
        self.master_redis.publish(request_status_channel, {'retcde': '0', 'retmsg': 'request has been accepted'})

    # fetch transaction result from backend server
    def get_service_result(self, message):
        trninf = {}
        try:
            req_data = eval(message['data'])['req_data']
            trncde = req_data['trncde']
            indict = req_data['indict']
            trnuid = req_data['trnuid']
            trninf.update(req_data['trninf'])
            trn_result = self.tran_invoke(trncde=trncde, trnuid=trnuid, indict=indict)
        except Exception, ex:
            print ex
            trn_result = dict(retcde='-1',
                              retmsg='%s' % ex)
        trninf['backend_server'] = self.server_name
        ret_data = dict(
                result=trn_result,
                trninf=trninf
        )
        return ret_data

    # send the result to front server
    def send_result_message(self, request_message, ret_data):
        channel = request_message['channel'].split(':')
        channel[0] = 'response'
        response_channel = ':'.join(channel)
        self.master_redis.publish(response_channel, ret_data)

    def tran_invoke(self, trncde, trnuid, indict):
        trnclass_info = self.get_trnclass_info(trncde)
        if trnclass_info is None:
            print u'交易类未定义！交易码:%s' % trncde
            return {'retcde': '-1', 'retmsg': u'交易类未定义！交易码:%s' % trncde}
        else:
            try:
                trnclass = getattr(importlib.import_module(trnclass_info['module']), trnclass_info['class'])
                if trnclass is not None:
                    print 'running transaction,trncde:%s,class:%s.%s' % (
                        trncde, trnclass_info['module'], trnclass_info['class'])
                    ret_data = trnclass(trncde=trncde, trnuid=trnuid, indict=indict).service()
                else:
                    ret_data = {'retcde': '-1',
                                'retmsg': u'交易类不存在！交易码:%s,交易类:%s.%s' % (
                                    trncde, trnclass_info['module'], trnclass_info['class'])}
            except Exception, ex:
                ret_data = {'retcde': '-1', 'retmsg': '%s' % ex}
            return ret_data

    # 获取交易信息
    def get_trnclass_info(self, trncde):
        if trncde in self.trntbl:
            return self.trntbl[trncde]
        else:
            return None
