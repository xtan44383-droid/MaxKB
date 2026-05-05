from pathlib import Path

from celery.signals import heartbeat_sent, worker_ready, worker_shutdown

from maxkb.const import PROJECT_DIR

# 本地源码开发无 /opt/maxkb-app/tmp，统一写到仓库根下 tmp，避免 FileNotFoundError
_worker_tmp = Path(PROJECT_DIR) / 'tmp'
_worker_tmp.mkdir(parents=True, exist_ok=True)


@heartbeat_sent.connect
def heartbeat(sender, **kwargs):
    worker_name = sender.eventer.hostname.split('@')[0]
    heartbeat_path = _worker_tmp / 'worker_heartbeat_{}'.format(worker_name)
    heartbeat_path.touch()


@worker_ready.connect
def worker_ready(sender, **kwargs):
    worker_name = sender.hostname.split('@')[0]
    ready_path = _worker_tmp / 'worker_ready_{}'.format(worker_name)
    ready_path.touch()


@worker_shutdown.connect
def worker_shutdown(sender, **kwargs):
    worker_name = sender.hostname.split('@')[0]
    for signal in ['ready', 'heartbeat']:
        path = _worker_tmp / 'worker_{}_{}'.format(signal, worker_name)
        path.unlink(missing_ok=True)
