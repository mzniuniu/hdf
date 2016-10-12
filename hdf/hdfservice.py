# -*- coding: utf-8 -*-
"""
    hdf.hdfservice
    ~~~~~~~~~~~~~~~~

    HDF Front Service

    :copyright: (c) 2016 by LiuZhaoHui.
    :license: BSD, see LICENSE for more details.
"""

import datetime
import redis
import signal
import string
import uuid


class HDFService(object):
    default_config = dict(
            SERVER_NAME=None,
            REDIS_MASTER_HOST='127.0.0.1',
            REDIS_MASTER_PORT=6379,
            REDIS_MASTER_DB=0,
            REDIS_SLAVE_HOST='127.0.0.1',
            REDIS_SLAVE_PORT=6379,
            REDIS_SLAVE_DB=0,
            TIME_OUT=30,
            TRAN_LIST={
                'TEST01': {'TIME_OUT': 10,
                           'REDIS_MASTER_HOST': '127.0.0.1',
                           'REDIS_MASTER_PORT': 6379,
                           'REDIS_SLAVE_HOST': '127.0.0.1',
                           'REDIS_SLAVE_PORT': 6379,}
            }
    )

    def __init__(self, config=None):
        self.config = {}
        self.config.update(self.default_config)
        if config:
            self.config.update(config)
        self.master_redis_pool = redis.ConnectionPool(host=self.config['REDIS_MASTER_HOST'],
                                                      port=self.config['REDIS_MASTER_PORT'],
                                                      db=self.config['REDIS_MASTER_DB'])
        self.master_redis = redis.StrictRedis(connection_pool=self.master_redis_pool)
        self.slave_redis_pool = redis.ConnectionPool(host=self.config['REDIS_SLAVE_HOST'],
                                                     port=self.config['REDIS_SLAVE_PORT'],
                                                     db=self.config['REDIS_SLAVE_DB'])
        self.slave_redis = redis.StrictRedis(connection_pool=self.slave_redis_pool)
        # self.request_pubsub = self.master_redis.pubsub()
        # self.status_pubsub = self.master_redis.pubsub()

    def run(self, trncde, indict):
        req_data = {}
        trninf = {}
        begin_time = datetime.datetime.now()
        trninf['begin_time'] = format_time(begin_time)

        if 'trnuid' in req_data and req_data['trnuid'] is not None:
            trnuid = req_data['trnuid']
        else:
            trnuid = uuid.uuid4().get_hex()
        if self.config['SERVER_NAME'] is not None:
            reqhst = self.config['SERVER_NAME']
        else:
            reqhst = 'hdf'

        trninf['front_server'] = reqhst

        req_data['trncde'] = trncde
        req_data['trnuid'] = trnuid
        req_data['indict'] = indict
        req_data['trninf'] = trninf

        # init transaction envir
        timeout = self.config['TIME_OUT']
        master_redis = self.master_redis
        slave_redis = self.slave_redis
        if trncde in self.config['TRAN_LIST']:
            if 'TIME_OUT' in self.config['TRAN_LIST'][trncde]:
                timeout = self.config['TRAN_LIST'][trncde]['TIME_OUT']

            if 'REDIS_MASTER_DB' in self.config['TRAN_LIST'][trncde]:
                master_redis_pool = redis.ConnectionPool(host=self.config['TRAN_LIST'][trncde]['REDIS_MASTER_HOST'],
                                                         port=self.config['TRAN_LIST'][trncde]['REDIS_MASTER_PORT'],
                                                         db=self.config['TRAN_LIST'][trncde]['REDIS_MASTER_DB'])
                master_redis = redis.StrictRedis(connection_pool=master_redis_pool)

            if 'REDIS_SLAVE_DB' in self.config['TRAN_LIST'][trncde]:
                slave_redis_pool = redis.ConnectionPool(host=self.config['TRAN_LIST'][trncde]['REDIS_SLAVE_HOST'],
                                                        port=self.config['TRAN_LIST'][trncde]['REDIS_SLAVE_PORT'],
                                                        db=self.config['TRAN_LIST'][trncde]['REDIS_SLAVE_DB'])
                slave_redis = redis.StrictRedis(connection_pool=slave_redis_pool)

        ret_data = self.get_response_data(trncde, trnuid, reqhst, req_data, master_redis, slave_redis, timeout)

        if 'trninf' not in ret_data:
            ret_data['trninf'] = {}
            ret_data['trninf'].update(trninf)
        end_time = datetime.datetime.now()
        ret_data['trninf']['end_time'] = format_time(end_time)
        ret_data['trninf']['elapsing_time'] = get_elapsing_time(begin_time, end_time)
        return ret_data

    def get_response_data(self, trncde, trnuid, reqhst, req_data, master_redis, slave_redis, timeout):
        request_pubsub = master_redis.pubsub()
        status_pubsub = master_redis.pubsub()
        request_channel = format_request_channel(trncde, trnuid, reqhst)
        response_channel = format_response_channel(trncde, trnuid, reqhst)
        status_channel = format_status_channel(trncde, trnuid, reqhst)
        status_pubsub.subscribe(status_channel)  # subscribe transation response status
        request_pubsub.psubscribe(response_channel)  # must subscribe result channel first,then publish request channel
        subscrible_count = master_redis.publish(request_channel, {'req_data': req_data})
        if subscrible_count > 0:
            print 'listener number:', subscrible_count
            if get_request_status(status_pubsub):
                ret_data = get_subscrible_data(request_pubsub, timeout)
            else:  # if transation has not been executed within 2 seconds,cancel this transation
                if master_redis.setnx(request_channel, 'transation has been canceld'):
                    master_redis.expire(request_channel, 60)
                    ret_data = dict(trninf=req_data['trninf'],
                                    result={'retcde': '-1',
                                            'retmsg': 'System is busying,please try again later'})  # system busy
                else:  # transation has been excuted,and try fetch transation result again
                    ret_data = get_subscrible_data(request_pubsub, timeout)
        else:
            ret_data = dict(trninf=req_data['trninf'],
                            result={'retcde': '-1', 'retmsg': 'backend server is not ready'})  # 监听服务未启动！
        request_pubsub.punsubscribe(response_channel)
        status_pubsub.unsubscribe(status_channel)
        return ret_data


def format_request_channel(trncde, trnuid, host):
    return 'request:%s:%s:%s' % (trncde, trnuid, host)


def format_response_channel(trncde, trnuid, host):
    return 'response:%s:%s:%s' % (trncde, trnuid, host)


def format_status_channel(trncde, trnuid, host):
    return 'request_status:%s:%s:%s' % (trncde, trnuid, host)


def get_subscrible_data(pubsub, timeout):
    ret_data = {'retcde': '-1', 'retmsg': u'交易超时'}
    signal.signal(signal.SIGALRM, timeout_handle)
    signal.alarm(timeout)
    try:
        for rsp in pubsub.listen():
            if rsp['type'] in ['pmessage', 'message']:
                # print 'receiving data',rsp['data']
                ret_data = eval(rsp['data'])
                break
    except TimeOutException:
        ret_data = {'retcde': '-1', 'retmsg': u'交易超时'}
    except Exception, ex:
        ret_data = {'retcde': '-1', 'retmsg': '%s' % ex}
    signal.alarm(0)
    return ret_data


# 是否处理状态,2秒内未有响应，则返回系统忙
def get_request_status(pubsub, timeout=2):
    retval = False
    ret_data = get_subscrible_data(pubsub, timeout)
    if ret_data['retcde'] == '0':
        retval = True
    return retval


class TimeOutException(Exception):
    pass


def timeout_handle(signum, frame):
    raise TimeOutException(u"运行超时！")
    # print "运行超时！"


def format_time(t):
    return '%s%s' % (t.strftime('%Y%m%d%H%M%S'),
                     ('000000%s' % t.microsecond)[-6:])


def get_elapsing_time(begin_time, end_time):
    ret_val = -1
    try:
        time_str = '%s' % (end_time - begin_time)
        v_microsecond = string.atoi(time_str.split('.')[1])
        v_time = (time_str.split('.')[0]).split(':')
        v_second = string.atoi(v_time[2])
        v_minute = string.atoi(v_time[1])
        v_hour = string.atoi(v_time[0])
        ret_val = (v_hour * 60 * 60 + v_minute * 60 + v_second) * 1000000 + v_microsecond
    except Exception, ex:
        print ex
    return ret_val
