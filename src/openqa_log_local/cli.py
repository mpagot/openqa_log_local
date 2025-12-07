import click
import logging
import json
from .main import openQA_log_local


@click.group()
@click.option(
    "--host", required=True, help="The openQA host URL (e.g., openqa.example.com)."
)
@click.option(
    "--log-level",
    default="ERROR",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    help="Set the logging level.",
)
@click.pass_context
def cli(ctx, host, log_level):
    """A CLI to locally collect and inspect logs from openQA.

    Files will be locally cached on disk, downloaded and read transparently.
    """
    ctx.ensure_object(dict)
    ctx.obj["HOST"] = host

    # Convert string log level to logging module's constant
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")
    logging.basicConfig(level=numeric_level)


@cli.command()
@click.option("--job-id", required=True, type=int, help="The job ID.")
@click.pass_context
def get_details(ctx, job_id):
    """Get job details for a specific openQA job."""
    oll = openQA_log_local(host=ctx.obj["HOST"])
    details = oll.get_details(str(job_id))
    if details is None:
        click.echo(f"Job {job_id} not found.", err=True)
        ctx.exit(1)
    click.echo(json.dumps(details, indent=4))


@cli.command()
@click.option("--job-id", required=True, type=int, help="The job ID.")
@click.option("--name-pattern", help="A regex pattern to filter log files.")
@click.pass_context
def get_log_list(ctx, job_id, name_pattern):
    """Get a list of log files associated to an openQA job.

    This command does not download any log file.
    """
    oll = openQA_log_local(host=ctx.obj["HOST"])
    log_list = oll.get_log_list(str(job_id), name_pattern)
    for log in log_list:
        click.echo(log)


@cli.command()
@click.option("--job-id", required=True, type=int, help="The job ID.")
@click.option("--filename", required=True, help="The name of the log file.")
@click.pass_context
def get_log_data(ctx, job_id, filename):
    """Get content of a single log file.

    The file is downloaded to the cache if not already available locally.
    All the log file content is returned.
    """
    oll = openQA_log_local(host=ctx.obj["HOST"])
    log_data = oll.get_log_data(str(job_id), filename)
    click.echo(log_data)


@cli.command()
@click.option("--job-id", required=True, type=int, help="The job ID.")
@click.option("--filename", required=True, help="The name of the log file.")
@click.pass_context
def get_log_filename(ctx, job_id, filename):
    """Get absolute path with filename of a single log file from the cache.

    The file is downloaded to the cache if not already available locally.
    """
    oll = openQA_log_local(host=ctx.obj["HOST"])
    log_filename = oll.get_log_filename(str(job_id), filename)
    click.echo(log_filename)


if __name__ == "__main__":
    cli(obj={})
