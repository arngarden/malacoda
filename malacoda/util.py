
def enum(*sequential, **named):
    """
    Usage:
    >>> types = enum(type1=1, type2=2, type3='three')
    >>> types.type1
    1
    >>> types.type2
    2
    >>> types.type3
    three
    >>> types.reverse_mapping['1']
    'type1'
    >>> types.reverse_mapping['three']
    'type3'
    """
    enums = dict(zip(sequential, range(len(sequential))), **named)
    reverse = dict((value, key) for key, value in enums.iteritems())
    enums['reverse_mapping'] = reverse
    return type('Enum', (), enums)
