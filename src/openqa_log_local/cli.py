import click
import logging
from .main import openQA_log_local


@click.group()
@click.option("--debug/--no-debug", default=False)
@click.pass_context
def cli(ctx, debug):
    """A simple CLI to interact with openQA logs."""
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
    """Get job details."""
    oll = openQA_log_local(host=host)
    details = oll.get_details(job_id)
    click.echo(details)


@cli.command()
@click.option("--host", required=True, help="The openQA host URL.")
@click.option("--job-id", required=True, type=int, help="The job ID.")
@click.option("--name-pattern", help="A regex pattern to filter log files.")
@click.pass_context
def get_log_list(ctx, host, job_id, name_pattern):
    """Get a list of log files for a job."""
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
    """Get the content of a log file."""
    oll = openQA_log_local(host=host)
    log_data = oll.get_log_data(job_id, filename)
    click.echo(log_data)


if __name__ == "__main__":
    cli(obj={})
