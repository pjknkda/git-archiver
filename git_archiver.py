__version__ = '19.6.4.0'

import asyncio
import functools
import logging
import os
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor

import docker
from aiohttp import web

logger = logging.getLogger(__name__)

GIT_ARCHIVER_ARCHIVE_VOLUME_PATH = os.getenv('GIT_ARCHIVER_ARCHIVE_VOLUME_PATH', '/tmp')
GIT_ARCHIVER_CONCURRENT_WORKERS = int(os.getenv('GIT_ARCHIVER_CONCURRENT_WORKERS', 8))
GIT_ARCHIVER_MAX_DISK_QUOTA = int(os.getenv('GIT_ARCHIVER_MAX_DISK_QUOTA', 50 * 2**20))
GIT_ARCHIVER_DOCKER_URI = os.getenv('GIT_ARCHIVER_DOCKER_URI', 'unix://var/run/docker.sock')
GIT_ARCHIVER_DOCKER_WORKER_IMAGE = os.getenv('GIT_ARCHIVER_DOCKER_WORKER_IMAGE', 'elice/git-and-zip:alpine')
GIT_ARCHIVER_TIMEOUT = int(os.getenv('GIT_ARCHIVER_TIMEOUT', 60))
GIT_ARCHIVER_ACCESS_KEY = os.getenv('GIT_ARCHIVER_ACCESS_KEY', '')

app = web.Application()
app_routes = web.RouteTableDef()

docker_client = docker.DockerClient(GIT_ARCHIVER_DOCKER_URI, version='auto')

thread_executor = ThreadPoolExecutor(GIT_ARCHIVER_CONCURRENT_WORKERS * 2)

concurrent_job_semaphore = asyncio.Semaphore(GIT_ARCHIVER_CONCURRENT_WORKERS)

WORKER_CMD_TEMPLATE = '''
#!/bin/bash

set -ex
git clone {clone_options} {repo} /tmpfs_mnt
zip -r {archive_filename} /tmpfs_mnt
chmod 777 {archive_filename}
'''.strip()


@app_routes.get('/archive')
async def archive_get_routing(request: web.Request) -> web.StreamResponse:
    if (GIT_ARCHIVER_ACCESS_KEY
            and request.headers.get('Authorization', '') != 'Bearer %s' % GIT_ARCHIVER_ACCESS_KEY):
        return web.HTTPUnauthorized()

    try:
        repo = request.query['repo'].strip()
        clone_options = request.query.get('clone_options', '').strip()
        disk_quota = int(request.query.get('disk_quota', GIT_ARCHIVER_MAX_DISK_QUOTA))
    except Exception:
        return web.HTTPBadRequest(text='Failed to parse all required parameters')

    if not (0 < disk_quota <= GIT_ARCHIVER_MAX_DISK_QUOTA):
        return web.HTTPBadRequest(text='Invalid `disk_quota` parameter')

    loop = asyncio.get_event_loop()
    with tempfile.NamedTemporaryFile('w', dir=GIT_ARCHIVER_ARCHIVE_VOLUME_PATH, encoding='utf-8') as run_sh_file:
        archive_name = '%s.zip' % uuid.uuid4().hex

        run_sh_file.write(
            WORKER_CMD_TEMPLATE.format(
                repo=repo,
                clone_options=clone_options,
                archive_filename='/output_mnt/%s' % archive_name
            )
        )

        run_sh_file.flush()

        archive_host_filename = os.path.join(GIT_ARCHIVER_ARCHIVE_VOLUME_PATH, archive_name)

        worker_container = None
        try:
            async with concurrent_job_semaphore:
                worker_container = await loop.run_in_executor(
                    thread_executor,
                    functools.partial(
                        docker_client.containers.create,
                        GIT_ARCHIVER_DOCKER_WORKER_IMAGE,
                        ['bash', '/run.sh'],
                        mounts=[
                            docker.types.Mount('/run.sh', run_sh_file.name, type='bind', read_only=True),
                            docker.types.Mount('/output_mnt', GIT_ARCHIVER_ARCHIVE_VOLUME_PATH, type='bind'),
                            docker.types.Mount('/tmpfs_mnt', '', type='tmpfs', tmpfs_size=disk_quota)
                        ],
                        user=os.getuid()  # type: ignore
                    )
                )

                await loop.run_in_executor(
                    thread_executor,
                    worker_container.start
                )

                worker_result = await loop.run_in_executor(
                    thread_executor,
                    functools.partial(
                        worker_container.wait,
                        timeout=GIT_ARCHIVER_TIMEOUT
                    )
                )

                worker_logs = await loop.run_in_executor(
                    thread_executor,
                    worker_container.logs
                )
                worker_logs = worker_logs.decode('utf-8')

            if worker_result['StatusCode'] != 0:
                return web.HTTPBadRequest(text='Worker is terminated with non-zero status code\n===\n%s' % worker_logs)

            if not os.path.exists(archive_host_filename):
                return web.HTTPBadRequest(text='Archive file is not created\n===\n%s' % worker_logs)

            resp = web.FileResponse(
                archive_host_filename,
                headers={
                    'Content-Disposition': 'attachment; filename="%s"' % archive_name
                }
            )
            await resp.prepare(request)

            # TODO: dirty hack to prevent double calling of `FileResponse.prepare()`
            async def _dummy_prepare(request):
                return None
            resp.prepare = _dummy_prepare  # type: ignore

            # From here, `archive_host_filename` doesn't need to be accessbiel anymore

            return resp

        except asyncio.CancelledError:
            logger.debug('The request is cancelled')
            raise

        except Exception:
            logger.exception('Failed to archive git repo')
            return web.HTTPServerError(text='Unexpected error is occured')

        finally:
            if worker_container is not None:
                await loop.run_in_executor(
                    thread_executor,
                    functools.partial(
                        worker_container.remove,
                        force=True
                    )
                )

            if os.path.exists(archive_host_filename):
                os.unlink(archive_host_filename)


app.add_routes(app_routes)

if __name__ == '__main__':
    web.run_app(app)
