"""

"""

# Standard Library
import os
import inspect
import traceback
import functools
import subprocess
from math import floor
from time import time
from copy import deepcopy, copy

# Third Party

# Local

# if you're calling a file directly, include this code @ the top of the file
# so it can set sys.path and work properly
'''
import sys
import os

APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
SITE_PACKAGES = os.path.join(APP_PATH, 'site-packages')
if SITE_PACKAGES not in sys.path:
    # makes sure we have the site-packages as the 1st directory
    new_path = [APP_PATH, SITE_PACKAGES]
    new_path.extend(sys.path[:])
    sys.path = new_path
'''


def crumb(msg='', kill=False):
    # type: (str, bool) -> None
    """
    Quick method to output a 'breadcrumb' that shows the class, method, and line
    of the crumb for debugging

    :param str msg:
    :param bool kill:
    :rtype: None
    """
    out = ''
    try:
        stack = inspect.stack()[1]
        _self = stack[0].f_locals.get('self', False)
        klass = (stack[1] + ' - ') if not _self else \
            (_self.__class__.__name__ + '.')
        s = {'class': klass, 'line': stack[2], 'fn': stack[3]}
        info = '>>>>> {class}{fn}() - line {line!s}'.format(**s)
        _msg = '    - {}\n'.format(msg) if len(msg) else ''
        out = ('\n' + info + _msg + '\n')
    except Exception:
        traceback.print_exc()
        out = ('\n' + msg + '\n')
    print out
    if kill:
        raise SystemExit('\n\n----- KILLING -----\n\n')


def dump(data, include_dunders=False, kill=False):
    # type: (obj) -> None
    """
    Prints out an objects attributes -> values, similar to PHP's var_dump()

    :param obj data: The object to dump
    :param bool include_dunders: Flag to also output __xxx__ attributes.
                                 (Default ``False``)
    :param bool kill: Flag to raise ``SystemExit`` and kill the script. (Default
                      ``False``)
    """
    s = {}
    try:
        s = traceback.extract_stack()[-2]
        s = {'file': s[0], 'line': s[1], 'fn': s[2]}
    except Exception:
        pass

    marker = ('\n' + '{:-^80}'.format(' DEBUG.DUMP() ') + '\n')

    print marker
    if len(s):
        print ('Called from ' + s['file'] + ' in '
               + s['fn'] + ' on line ' + str(s['line'])
               + '\n')
    print 'Object info:\n'
    if hasattr(data, '__module__'):
        print '    - module:', data.__module__, '\n'
    if hasattr(data, '__class__'):
        print '    - class: ', data.__class__.__name__, '\n'
    print '    - type:  ', str(type(data)), '\n'
    attr_width = 0
    type_width = 0
    for attr in dir(data):
        try:
            if not include_dunders and attr.startswith('__'):
                continue
            tw = len(type(getattr(data, attr)).__name__)
            if tw > type_width:
                type_width = tw
            aw = len(attr)
            if aw > attr_width:
                attr_width = aw
        except Exception as ex:
            err = '    ---- Exception while getting len of attr {}: {!s}'
            print err.format(attr, ex)

    attr_width += 2     # increase by 2 for better legibility
    for attr in dir(data):
        try:
            if not include_dunders and attr.startswith('__'):
                continue
            av = getattr(data, attr)
            at = type(av).__name__
            tw = type_width - len(at)
            tw = tw if tw == 0 else tw + 1
            out = "    {:<%i} ({}){:<%i}: {}" % (attr_width, tw)
            # prevent errors from types that don't easily convert to string
            pv = av if hasattr(type(av), '__format__') else type(av)
            print out.format(attr, at, ' ', pv)
        except Exception as ex:
            err = '    ---- Exception while printing value of attr {}: {!s}'
            print err.format(attr, ex)
    if kill:
        msg = '{:-^80}'.format(' KILLING SCRIPT FOR DEBUG.DUMP() ')
        raise SystemExit(('\n\n' + msg + '\n\n'))
    print marker.replace('- D', ' /D', 1)


def printargs(sort=False):
    # type: (bool) -> str
    """
    Returns the arguments() data wrapped in header/footer lines for legibility

    :param bool sort:
    :return:
    """
    hfl = ''.join(['\n', '~'*50, '\n'])
    data = [hfl, arguments(sort=sort), '\n', hfl]
    print ''.join(data)


def arguments(sort=False):
    # type: (bool) -> str
    """
    Returns the functions arguments along with their values & value types
    at the time of this function call as a string that can be printed to stdout.

    :param bool sort: Flag to sort arguments alphabetically.
                      Default is declaration order.
    :return: Arguments, types, values in a formatted string
    :rtype: str
    """
    # get the call stack
    frames = inspect.stack()
    '''
        frame:
            0 - frame object
            1 - file
            2 - line #
            3 - function
            4 - list of context lines
            5 - index of current line in list
    '''
    # we don't want data from the printing method
    target_frame = frames[2] if frames[1][3] == 'printargs' else frames[1]
    fn_file_path = target_frame[1]
    called_on_line = target_frame[2]
    fn_name = target_frame[3]

    # we want that method's frame data
    frame = target_frame[0]
    arg_info = inspect.getargvalues(frame)  # type: inspect.ArgInfo
    # make a copy so we don't mess anything up
    fn_args = arg_info.args[:]  # type: list
    if sort:
        fn_args.sort()

    # for printed column widths
    max_alen = max_vlen = max_tlen = 0
    # since locals will have ALL available variables we have to grab args
    # specifically and then grab their values out of locals
    data = []
    p = 4  # padding for columns
    for a in fn_args:
        val = arg_info.locals.get(a, '-Unknown Value-')
        val_type = type(val)
        max_alen = max(len(a), max_alen)
        max_vlen = max(len(str(val)), max_vlen)
        max_tlen = max(len(str(val_type)), max_tlen)
        data.append((a, val_type, str(val)))

    lens = {'alen': max_alen + p, 'vlen': max_vlen + p, 'tlen': max_tlen + p}
    ln = '\nArguments for "{}()" @ line {} in "{}":\n'
    output = [ln.format(fn_name, called_on_line, fn_file_path)]
    for d in data:
        tmp = '    {0[0]:<{alen}}{0[1]:<{tlen}}{0[2]:<{vlen}}'
        output.append(tmp.format(d, **lens))
    return '\n'.join(output)


def timeit(iterations=1, verbose=False):
    """
    Wrapper for testing execution time of a function

    WARNING:

        To prevent issues when timing methods that work with objects 'by
        reference', the wrapped method will be passed a deepcopy version of
        ``args`` and ``kwargs`` values. The time required for making those
        copies is NOT included in the calculations.

    :param int iterations: # times to execute the function (Default ``1``)
    :param bool verbose: Output detailed timing info (Default ``False``)
    :return: A wrapped function
    :rtype: function
    """
    # this additional nested wrapper allows arg passing via the @decorator
    def _wrapper(fn):
        # type: (function) -> function

        # preserve wrapped function meta data
        @functools.wraps(fn)
        def wrapped(*args, **kwargs):
            def t(d):
                r, n = [], [('hr', 3600.0), ('min', 60.0), ('sec', 1.0)]
                if d >= 1:
                    for o in n:
                        if d >= o[1]:
                            z = floor(d / o[1])
                            r.append('{} {}'.format(int(z), o[0]))
                            d -= z * o[1]
                r.append('{} ms'.format(d * 1000))
                return ', '.join(r)

            result = None
            times = []
            for x in xrange(iterations):
                try:
                    copy_args = deepcopy(args)
                    copy_kwargs = deepcopy(kwargs)
                except TypeError:
                    # deepcopy uses pickle, which fails on 'thread.lock' objects
                    try:
                        copy_args = copy(args)
                        copy_kwargs = copy(kwargs)
                    except Exception as e:
                        import traceback
                        print str(e)
                        traceback.print_exc()
                        raise SystemExit('\n\nkilling for timeit copy error\n\n')
                except Exception as e:
                    import traceback
                    print str(e)
                    traceback.print_exc()
                    raise SystemExit('\n\nkilling for timeit deepcopy error\n\n')
                s = time()
                result = fn(*copy_args, **copy_kwargs)
                times.append(time() - s)

            total = sum(times)
            msg = ['\nTotal run time for {}: {}'.format(fn.__name__, t(total))]
            if iterations > 1:
                msg.append('    ({} iterations)'.format(iterations))
            if verbose:
                msg.extend([
                    '  Average run time: {}'.format(t(total/len(times))),
                    '  Longest run time: {}'.format(t(max(times))),
                    '  Shortest run time: {}'.format(t(min(times))),
                    ''
                ])
            print '\n'.join(msg)
            return result
        return wrapped
    return _wrapper


def diff(expected='', actual='', flags='-aywt', col_width=130):
    # type: (str, str, str, int) -> dict
    """
    Runs a diff on 2 strings|files and returns the output

    WARNING:

        https://www.gnu.org/software/bash/manual/bashref.html#Single-Quotes

        Section 3.1.2.2 Single Quotes

        "Enclosing characters in single quotes (`'`) preserves the literal value
        of each character within the quotes. A single quote may not occur
        between single quotes, even when preceded by a backslash."

        To work around this, ``expected`` and ``actual`` will be formatted
        using a concatenation 'workaround'
        e.g. 'I'm' = 'I'"'"'m' ('I' + "'" + 'm')


    :param str expected: Expected string
    :param str actual: String to compare against ``expected``
    :param str flags: Flags to pass in to ``diff`` (Default ``-ayw``)
                      -a = treat all files as text
                      -y = output 2 columns
                      -w = ignore all white space
                      -t = expand tabs into spaces
    :param int col_width: Max char per column (Default ``130``)
    :returns: A dict {out: '', err: '') where ``out`` is a side-by-side diff of
             ``expected`` vs ``actual`` and ``err`` is any errors
    :rtype: dict
    """
    def fix_str(text):
        return '<(echo \"{}\")'.format(text.replace("'", '\'"\'"\''))

    ename = aname = ''
    if os.path.isfile(expected):
        exp = ename = expected
    else:
        exp = fix_str(expected)
    if os.path.isfile(actual):
        act = aname = actual
    else:
        act = fix_str(actual)

    cmd = 'diff --width={!s} {} {} {}'.format(col_width, flags, exp, act)
    cmds = ['/bin/bash', '-c', cmd]
    p = subprocess.Popen(cmds, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    dif, err = p.communicate()
    if len(err):
        raise Exception(err)
    # there is a VERY good chance we'll get something not ascii codec compatible
    # so we have to force all diff data to be utf8 unicode
    dif = unicode(dif, encoding='utf8')

    # diff returns the text with \r as a newline and uses spaces to pad it out
    # <a line of text from expected>\r
    #                                   <a line of text from actual>
    # (# of spaces depends on allowed max width vs actual diff output width)
    # this doesn't play well with assigning the diff text to a list as part of
    # a larger section, so we have to tweak it slightly. This also makes it
    # harder to get the right column width for headers & separators.
    nlines = dif.split('\n')
    rlines = []
    for n in nlines:
        rlines.extend(n.split('\r'))
    dif_width = len(max(rlines, key=len))
    del rlines

    # -4 to account for the minimum spacing between columns
    exp_col_width = act_col_width = int((dif_width - 4) / 2)
    # if the diff width is an odd # the 'expected' column gets the remainder
    exp_col_width += 1 if dif_width % 2 else 0
    row_fmt = u'{{:=^{!s}}}'.format(dif_width)
    col_fmt = u'{{: <{!s}}}'
    exp_col_fmt = col_fmt.format(exp_col_width)
    act_col_fmt = col_fmt.format(act_col_width)
    hed_fmt = u'{{:-^{!s}}}'
    exp_hed_fmt = hed_fmt.format(exp_col_width)
    act_hed_fmt = hed_fmt.format(act_col_width)

    # there is always a minimum of 4 spaces between the columns. however, if the
    # total diff width is < max width, extra spacing is pre-pended to the actual
    # column equal to the floor of half that difference as filler padding
    act_col_start_idx = exp_col_width
    extra_padding, extra_spaces = 0, ''
    if dif_width < col_width:
        extra_padding = int(floor((col_width - dif_width) / 2))
        act_col_start_idx += extra_padding
        extra_spaces = ' '*extra_padding

    _dif = []
    for n in nlines:
        b = n.split('\r')
        if len(b) == 1:  # single line; no goofy \r formatting
            if extra_padding:  # if there's extra padding, we need to remove it
                n = n.replace(extra_spaces, '', 1)
            _dif.append(n)
        else:
            b[0] = exp_col_fmt.format(b[0])
            b[1] = act_col_fmt.format(b[1][act_col_start_idx:])
            _dif.append(''.join(b))
    del nlines

    out = ['\n', row_fmt.format(' DIFF() '), '\n\n']
    if ename:
        out.append('- Expected: {}\n\n'.format(ename))
    if aname:
        out.append('- Actual:   {}\n\n'.format(aname))
    out.extend([
        (exp_hed_fmt.format(' Expected ') + '    ' +
         act_hed_fmt.format(' Actual ') + '\n\n'),
        '\n'.join(_dif), '\n',
        (exp_hed_fmt.format(' /Expected ') + '    ' +
         act_hed_fmt.format(' /Actual ') + '\n\n'),
        row_fmt.format(' /DIFF() '), '\n',
    ])

    return {'out': ''.join(out).encode('utf8'), 'err': err}
