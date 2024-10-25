from loguru import logger as LOG


LOG.add(
    sink='logs/logs.json',
    level='DEBUG',
    # level='TRACE',
    rotation='7 day',
    serialize=True,
    encoding='utf-8',
    colorize=True
)
