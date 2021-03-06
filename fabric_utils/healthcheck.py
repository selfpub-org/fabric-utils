from time import sleep
from typing import Tuple, Callable

from fabric.api import puts, settings, hide
from fabric.operations import run
from fabric.tasks import execute
from fabric.utils import error


def check_uwsgi_is_200_ok(healthcheck_url, uwsgi_port, status='200 OK'):
    with settings(hide('stdout')):
        command = f'uwsgi_curl 127.0.0.1:{uwsgi_port} {healthcheck_url} | head -n 1 | grep "{status}"'
        result = run(command, warn_only=True, shell=False)
        return result


def check_http_is_200_ok(healthcheck_url, status='200 OK'):
    with settings(hide('stdout')):
        command = f'curl -sSL -D - {healthcheck_url} -o /dev/null | head -n 1 | grep "{status}"'
        result = run(command, warn_only=True, shell=False)
        return result


def check_role_is_up(role: str, task: Callable) -> Tuple[dict, str]:
    is_uwsgi_up_results = execute(task, role=role)
    per_hosts_success = {
        host: res.succeeded
        for host, res in is_uwsgi_up_results.items()
    }
    joint_stderr = '\n'.join(r.stdout for r in is_uwsgi_up_results.values())
    return per_hosts_success, joint_stderr


def wait_until_role_is_up(*, role: str, task: Callable, poll_interval: int = 3, max_wait: int = 20) -> bool:
    waiting_seconds = 0
    stderr = '-'

    puts(f'waiting for {role} to be up for as long as {max_wait} seconds')
    while waiting_seconds < max_wait:
        # skip waiting on the first iteration, uwsgi may already be up
        up_hosts, stderr = check_role_is_up(role, task)
        if all(up_hosts.values()):
            puts(f'role {role} is up after {waiting_seconds} seconds')
            return True
        else:
            failed_hosts = ', '.join([host for host, status in up_hosts.items() if not status])
            puts(f'role {role} is not up after {waiting_seconds} seconds: failed hosts: {failed_hosts}')

        sleep(poll_interval)
        waiting_seconds += poll_interval

    with settings(warn_only=False):
        error(f'waited for {waiting_seconds} seconds, role {role} is not up. Aborting \n {stderr}')

    return False
