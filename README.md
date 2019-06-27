# git-archiver

A simple webserver to make an archive for git repository under the quota limitation.


## Requirements

- Docker 17.06 or above.
- Linux-based OS to use Docker's tmpfs mount.
- Free memory spcae at least `{concurrent_workers} * {maximum_disk_quota_per_repo}`.


## Configuration

These configuration keys can be passed through environment variables.

- GIT_ARCHIVER_ARCHIVE_VOLUME_PATH : The writable path to be shared with worker containers and the webserver. (default: `/tmp`)
- GIT_ARCHIVER_CONCURRENT_WORKERS : Maximum allowed concurrent workers for cloning and archiving. (default: `8`)
- GIT_ARCHIVER_DOCKER_URI : Docker URI. (default: `unix://var/run/docker.sock`)
- GIT_ARCHIVER_DOCKER_WORKER_IMAGE : Docker image to be used in worker containers. `bash`, `git`, and `zip` command should be avilable. (default: `elice/git-and-zip:alpine`)
- GIT_ARCHIVER_MAX_DISK_QUOTA : Maximum allowed disk quota for repos in bytes. (default: `50MB`)
- GIT_ARCHIVER_TIMEOUT : Maximum allowed time for cloning and archiving in seconds. (default: `60`)


## API

- `GET /archive`
    - Request parametesr
        - `repo` : the remote address of target repository in any avilable format for `git clone`.
        - `clone_options` : the URL-encoded string to be passed to `git clone` as options.
        - `disk_quota` : the disk quota allowed to clone in bytes.
        - The worker will call `git clone {clone_options} {repo} /tmpfs_mnt`.
        - If any request parameter is wronly formatted, HTTP 400 error will occur.
    - Response
        - The archive file response with HTTP 200 status code.
        - If the archiving process is failed, returns HTTP 400 status code.


## License

MIT