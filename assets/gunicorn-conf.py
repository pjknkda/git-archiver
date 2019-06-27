bind = '0.0.0.0:80'
workers = 2
worker_class = 'aiohttp.GunicornUVLoopWebWorker'
accesslog = '-'
