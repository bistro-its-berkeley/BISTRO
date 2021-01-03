import functools


def lazyprop(fn):
    # From https://stackoverflow.com/questions/3012421/python-memoising-deferred-lookup-property-decorator
    attr_name = '_lazy_' + fn.__name__

    @property
    @functools.wraps(fn)
    def _lazyprop(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, fn(self))
        return getattr(self, attr_name)

    return _lazyprop
