import time


def do_with_retry(max_retry, error_msg, log, func, kargs=(), kwargs={}, dfunc=None, dfunc_kargs=(),
                  dfunc_kwargs={}, interval=5):
    retries = max_retry
    while retries:
        try:
            return func(*kargs, **kwargs)
        except Exception as e:
            log.error("%s, exception <%s>, msg <%s>", error_msg, type(e), e)
            time.sleep(interval)
            retries -= 1
    if callable(dfunc):
        return dfunc(*dfunc_kargs, **dfunc_kwargs)
