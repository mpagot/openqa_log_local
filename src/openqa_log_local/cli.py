import click
import logging
from .main import openQA_log_local


@click.group()
@click.option("--debug/--no-debug", default=False)
@click.pass_context
def cli(ctx, debug):
    """A CLI to locally collect and inspect logs from openQA.

    Files will be locally cached on disk, downloaded and read transparently.
    """
    ctx.ensure_object(dict)
    ctx.obj["DEBUG"] = debug
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)


@cli.command()
@click.option("--host", required=True, help="The openQA host URL.")
@click.option("--job-id", required=True, type=int, help="The job ID.")
@click.pass_context
def get_details(ctx, host, job_id):
    """Get job details for a specific openQA job."""
    oll = openQA_log_local(host=host)
    details = oll.get_details(job_id)
    if details is None:
        click.echo(f"Job {job_id} not found.", err=True)
        ctx.exit(1)
    click.echo(details)


@cli.command()
@click.option("--host", required=True, help="The openQA host URL.")
@click.option("--job-id", required=True, type=int, help="The job ID.")
@click.option("--name-pattern", help="A regex pattern to filter log files.")
@click.pass_context
def get_log_list(ctx, host, job_id, name_pattern):
    """Get a list of log files associated to an openQA job.

    This command does not download any log file.
    """
    oll = openQA_log_local(host=host)
    log_list = oll.get_log_list(job_id, name_pattern)
    for log in log_list:
        click.echo(log)


@cli.command()
@click.option("--host", required=True, help="The openQA host URL.")
@click.option("--job-id", required=True, type=int, help="The job ID.")
@click.option("--filename", required=True, help="The name of the log file.")
@click.pass_context
def get_log_data(ctx, host, job_id, filename):
    """Get content of a single log file.

    The file is downloaded to the cache if not already available locally.
    All the log file content is returned.
    """
    oll = openQA_log_local(host=host)
    log_data = oll.get_log_data(job_id, filename)
    click.echo(log_data)


@cli.command()
@click.option("--host", required=True, help="The openQA host URL.")
@click.option("--job-id", required=True, type=int, help="The job ID.")
@click.option("--filename", required=True, help="The name of the log file.")
@click.pass_context
def get_log_filename(ctx, host, job_id, filename):
    """Get absolute path with filename of a single log file from the cache.

    The file is downloaded to the cache if not already available locally.
    """
    oll = openQA_log_local(host=host)
    log_filename = oll.get_log_filename(job_id, filename)
    click.echo(log_filename)


if __name__ == "__main__":
    cli(obj={})
