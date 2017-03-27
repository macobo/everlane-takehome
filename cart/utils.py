import click
import simplejson as json

from functools import wraps
from pygments import highlight, lexers, formatters
from sys import exit

colorize = lambda data: highlight(
    unicode(json.dumps(data, indent=2), 'UTF-8'),
    lexers.JsonLexer(),
    formatters.TerminalFormatter())

def json_output(command):
    @wraps(command)
    def _inner(*args, **kw):
        output = None
        exit_code = 0
        try:
            output = command(*args, **kw)
            output['success'] = True
        except Exception as e:
            output = {'success': False, 'error': str(e)}
            exit_code = 1
        output['command'] = command.__name__
        click.echo(colorize(output))
        exit(exit_code)
    return _inner

def proxy_to_dict(result_proxy, omit_keys=frozenset()):
    return [{key: value for (key, value) in row.items() if key not in omit_keys} for row in result_proxy]

def max_length(maxlen):
    def validator(ctx, param, value):
        if len(value) > maxlen:
            raise click.BadParameter('Should be at most {} characters'.format(maxlen))
        return value
    return validator

def option(flagname, helptext, **kw):
    "Wrapper for `click.option` for auto-prompting."
    if 'required' not in kw:
        kw['required'] = True
    if 'prompt' not in kw:
        kw['prompt'] = helptext
    return click.option(flagname, help=helptext, show_default=True, **kw)
