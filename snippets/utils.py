# -*- coding: utf-8 -*-

"""
Collection of commonly used/shared utilities
"""

# Standard Library
import os
from lxml import etree
import email.mime.text
from pprint import PrettyPrinter
from cStringIO import StringIO

# Third Party
import suds
import six

# Local
import vars
from extensions import AttributeDict, StrOrEtree

PP = PrettyPrinter()


def create_file(path=None, mode=0777):
    # type: (str, int) -> None
    """
    Creates a file, recursively creating the directory path if required

    :param str path: Full path to the file to create
    :param int mode: Octal notation for the file/directories mode (Default 0777)
    :returns: None
    """
    if path is None:
        err = 'No path defined for `create_file()`'
        raise vars.DMSIKnownFatalException(err)
    fp, fn = os.path.split(path)
    try:
        os.makedirs(fp, mode)
    except Exception:
        pass
    if not os.path.isfile(path):
        with open(path, 'w+') as fh:
            pass
        os.chmod(path, mode)


def update_dict(target, source):
    # type: (dict, dict) -> dict
    """
    Like ``dict.update()`` but does not create new keys in ``target``

    :param dict target: Dict with values to update
    :param dict source: Dict with new values to use in ``target``
    :returns: The updated ``target`` dict, even though this works in-place
    :rtype: dict
    """
    target.update((k, source[k]) for k in target.viewkeys() & source.viewkeys())
    return target


def subdivide_list(data, size=5):
    # type: (list, int) -> list
    """
    Divides a list into a list of smaller lists with len ``size``

    E.g.::

        >>> data = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
        >>> subdivide_list(data, 3)
        [['a', 'b', 'c'], ['d', 'e', 'f'], ['g', 'h']]

    :param list data: The list to break into sub-lists
    :param int size: Length of each sub-list
    :return: A new list made up of lists with len ``size``
    :rtype: list
    """
    if not isinstance(data, list):
        data = list(data)
    size = int(size)
    return [data[x:x + size] for x in xrange(0, len(data), size)]


def strip_namespaces(xml_string=None):
    # type: (StrOrEtree) -> etree._Element
    """
    Remove namespaces from an XML string.

    :param str | etree._ElementTree xml_string: XML to remove namespaces from
    :returns: etree object without namespaces
    :rtype: etree._Element
    """
    if xml_string is None or not len(str(xml_string)):
        return xml_string
    xslt = os.path.join(vars.ETC_PATH, 'common', 'RemoveNamespacesOnly.xsl')
    result = apply_xslt(xslt, xml_string)
    return result


def apply_xslt(xslt, xml, params=None, xml_dec=True):
    # type: (str, Any, dict, bool) -> etree._Element
    """
    Apply a stylesheet to a provided XML document using the provided parameters.

    NOTE:
        If you're passing in a StringIO object you will have to close it.
        If you pass in a :class:`str` or :class:`etree._Element` object, a
          StringIO object will be created & closed automatically.

    :param str xslt: Either a path to a XSLT file or raw XSLT to apply
    :param str | etree._Element | StringIO xml: XML to transform
    :param dict params: Optional params to pass on to the etree.XSLT object
    :param bool xml_dec: Optional flag to require XML declaration
    :returns: XML modified by the xslt document
    :rtype: etree._Element
    """
    klass = '' if not hasattr(xml, '__class__') else str(xml.__class__)
    autoclose = False
    if 'StringIO' not in klass:
        autoclose = True
        xml = xml_as_stringio(xml)
    try:
        xslt = xml_as_etree(xslt)
        transformer = etree.XSLT(xslt.getroot())
        base_doc = xml_as_etree(xml)
        if params is not None:
            params = {k: '"{}"'.format(v) for k, v in six.iteritems(params)}
            result = transformer(base_doc.getroot(), **params)
        else:
            result = transformer(base_doc.getroot())
        result_root = result.getroot()
        if result_root is not None:
            result = result_root
        if autoclose:
            xml.close()
        return result
    except etree.XMLSyntaxError:
        # if it has no < character, it's probably a string.
        # we need to raise the string, not the XMLSyntaxError.
        xml = xml_as_str(xml)
        if "<" not in xml:
            raise TypeError(xml)
        raise


def dict_to_etree(data={}, root_name=None):
    # type: (dict, str) -> etree._ElementTree
    """
    Converts a dict into an etree object

    WARNING:

        This is a _VERY_ basic converter, and is only meant to handle simple
        dicts.

    :param dict data: Data used to build the etree
    :param str root_name: Optional name to give the root node. If ``None`` the
                          top-level dict key will be used. If multiple top-level
                          keys exist in the dict it will default to ``root``.
    :rtype: etree._ElementTree
    """
    def to_etree(d=None, n=None):
        # type: (Any, etree._Element) -> etree._Element
        if d is None:
            return n
        # this has to come first otherwise the int check catches it
        if isinstance(d, bool):
            n.text = 'True' if d else 'False'
        elif isinstance(d, (six.string_types, int, float, long, complex)):
            n.text = d
        elif isinstance(d, (list, set, tuple)):
            for i in d:
                to_etree(d=i, n=n)
        elif isinstance(d, dict):
            for k, v in six.iteritems(d):
                sub = etree.SubElement(n, k)
                to_etree(d=v, n=sub)
        elif hasattr(d, '__class__'):
            n.text = d.__class__.__name__
        else:
            n.text = ('Unhandled type: ' + type(d))
        return n

    if root_name is None:
        if len(data.keys()) == 1:
            root_name = data.keys()[0]
            data = data.values()[0]
        if not len(root_name):
            root_name = 'root'

    xml = etree.Element(root_name)
    to_etree(d=data, n=xml)
    return xml


def etree_to_dict(xml):
    # type: (etree._ElementTree, bool) -> AttributeDict
    """
    Converts an etree object into an ``AttributeDict`` so it can be parsed
    similarly to soap responses where ``retxml=False``

    :param etree._ElementTree xml:
    :param bool stripped: Internal use flag indicating the xml has already
                          had namespaces removed. Default is ``True`` so we
                          don't have to muck around with partials
    :rtype: AttributeDict
    """
    def convert(_xml):
        tag = _xml.tag
        txt = _xml.text if _xml.text is not None and len(_xml.text) else ''
        d = AttributeDict({tag: map(convert, _xml.iterchildren())})
        d.update(('@' + k, v) for k, v in _xml.attrib.iteritems())
        # set text as value for tag so . notation works
        if not len(d[tag]) and len(txt):
            d[tag] = txt
        # don't make the xml children be in a list, again so . notation works
        elif isinstance(d[tag], list):
            d[tag] = {k: v for child in d[tag] for k, v in six.iteritems(child)}
        return d

    # sanitize for safety
    xml = strip_namespaces(xml)  # type: etree._Element
    xml_dict = convert(xml)
    # top level node is the first dict entry, which needs to bump up a level
    keys = xml_dict.keys()
    root = xml_dict if not len(keys) else xml_dict[keys[0]]
    return root


def xml_as_str(xml, pretty=False):
    # type: (Any, bool) -> str
    """
    Returns XML as a string

    :param Any xml: (:py:class:`str` | :py:class:`etree._ElementTree`) XML to
                    get back as a string
    :param bool pretty: Optional flag to pretty format the xml
    :rtype: str
    """
    return get_xml_as(xml, fmt='string', pretty=pretty)


def xml_as_etree(xml):
    # type: (Any) -> etree._ElementTree
    """
    Returns XML as an etree._ElementTree object

    :param Any xml: (:py:class:`str` | :py:class:`etree._ElementTree`) XML to
                    get back as an etree._ElementTree
    :rtype: etree._ElementTree
    """
    return get_xml_as(xml, fmt='etree')


def xml_as_stringio(xml, pretty=False):
    # type: (Any, bool) -> StringIO
    """
    Converts ``xml`` to a file-like StringIO object

    WARNING:
        Be sure to close the StringIO object after modifications.

    :param Any xml: XML in :class:`str` or :class:`etree._Element` or
                    :class:`StringIO` format
    :param bool pretty: Set ``True`` to use pretty-printed :class:`str` or
                        :class:`etree._Element` ``xml`` values in the StringIO
                        object (Default ``False``)
    :returns: StringIO object, converting :class:`str` or
              :class:`etree._Element` values if required
    :rtype: StringIO
    """
    klass = '' if not hasattr(xml, '__class__') else str(xml.__class__)
    try:
        if 'StringIO' not in klass:
            xml_str = xml_as_str(xml, pretty=pretty)
            xml = StringIO(xml_str)
        return xml
    except Exception as e:
        err = 'Error converting {} to StringIO:\n{!s}'.format(klass, e)
        raise vars.DMSIException(err, inc_tb=True)


def get_pretty_xml(xml):
    # type: (Any) -> str
    """
    Returns pretty-printed XML from a string or etree._ElementTree object

    :param Any xml: (:py:class:`str` | :py:class:`etree._ElementTree`) XML to
                    prettify
    :rtype: str
    """
    return get_xml_as(xml, fmt='string', pretty=True)


def get_xml_as(xml, fmt='', pretty=False):
    # type: (Any, str, bool) -> Any
    """
    Makes sure ``xml`` is in ``fmt``, with the option to be pretty

    :param Any xml: (:py:class:`str` | :py:class:`etree._ElementTree`) XML to
                    convert
    :param str fmt: Format to return ``xml`` in ('string', 'etree')
    :param bool pretty: Flag to pretty format ``xml`` if ``fmt`` is ``string``
    :returns: ``xml`` in format ``fmt``
    :rtype: Any
    """
    if xml is None or not len(str(xml)):
        return xml
    astree = True if fmt == 'etree' else False
    klass = '' if not hasattr(xml, '__class__') else str(xml.__class__)
    # This is VERY important; we sometimes get XML back with random new line
    # characters that prevent etree from pretty printing and this is the ONLY
    # reliable way to fix it.
    parser = etree.XMLParser(remove_blank_text=True)
    try:
        if isinstance(xml, six.string_types):
            xml = xml.strip()
            if os.path.isfile(xml):
                mxml = etree.parse(xml)
            else:
                if isinstance(xml, unicode):
                    xml = xml.encode('utf8')
                mxml = etree.XML(xml, parser=parser)
        elif 'etree' in klass or 'lxml' in klass:
            mxml = xml
        elif 'StringIO' in klass:
            mxml = etree.parse(xml)
        elif isinstance(xml, file):
            mxml = etree.parse(xml, parser=parser)
        else:
            err = 'unhandled type in _get_xml_as(): {}'.format(type(xml))
            raise ValueError(err)
        return mxml if astree else etree.tostring(mxml, pretty_print=pretty)
    except etree.XMLSyntaxError as ex:
        # the WeOwe.read deal request sometimes returns XML with undefined
        # namespaces; all we can do is return whatever we were given
        return xml
    except ValueError:
        # kick it back up; used by prettify()
        raise
    except Exception:
        raise


def prettify(data):
    # type: (Any) -> str
    """
    Safely pretty-prints most any object

    :param Any data:
    :returns: A pretty-printed text version of ``data``
    :rtype: str
    """
    try:
        klass = '' if not hasattr(data, '__class__') else str(data.__class__)
        if 'suds' in klass:
            client = suds.client.Client
            data = client.dict(data) if 'sudsobject' in klass else str(data)
    except Exception:
        pass

    if isinstance(data, (list, dict, tuple, set)):
        return PP.pformat(data)

    if isinstance(data, six.string_types):
        data = data.strip()
        if not len(data):
            return data
        if isinstance(data, unicode):
            data = data.encode('utf8')
        if not data.startswith('<'):
            return data

    try:
        return get_pretty_xml(data)
    except ValueError:
        pass
    except etree.XMLSyntaxError:
        pass

    try:
        return PP.pformat(str(data))
    except Exception:
        pass

    return data


def get_attr(xml=None, target=None, attr=None, squash=False):
    # type: (Any, str, str, bool) -> str
    """
    Find ``target`` node in ``xml`` and get its ``attr`` value

    If squash is ``True``, None will be returned in lieu of raising exceptions

    :param Any xml: (:py:class:`str` | :py:class:`etree._Element`) XML
                    to search in
    :param str target: Target node to look in
    :param str attr: Element attribute whose value you want
    :param bool squash: If True exceptions will be swallowed
    :returns: The value of the ``attr`` node or None
    :rtype: str
    :raises: Exception
    """
    xml = xml_as_etree(xml)  # type: etree._Element
    node = xml.find(target)  # type: etree._Element
    if node is None:
        if squash:
            return None
        raise Exception('{} not found in xml'.format(target))
    val = node.get(attr)
    if val is None:
        if squash:
            return None
        raise Exception('{} was not found in {}'.format(attr, node))
    return val


def send_email(subject='', from_addr='', to_addr='', body='', cc_list=None):
    # type: (str, str, str, str, str) -> None
    """
    Send an email

    :param str subject:
    :param str from_addr:
    :param str to_addr:
    :param str body:
    :param str cc_list:
    :rtype: None
    """
    message = email.mime.text.MIMEText(body.strip(), 'html')
    message['Subject'] = subject
    message['From'] = from_addr
    message['To'] = to_addr
    if cc_list:
        message['CC'] = cc_list
        to_addr += ',{}'.format(cc_list)
    print 'Email to be sent: {}\n\n{}'.format(subject, body)
    # smtp = smtplib.SMTP('mailrelay.stoneeagle.com')
    # smtp.sendmail(message['From'], to_addr.split(','), message.as_string())
    # smtp.quit()


def get_data_from_stdin():
    # type: () -> str
    """
    Gets data from stdin

    Paste the data into the terminal and press `CTRL+D` to submit.

    This is an alternative to using --deal_xml to pass in a path to a file
    with the information.

    :rtype: str
    """
    def prompt():
        """Prevents ``raw_input`` from re-printing the prompt each time
        it finds a newline"""
        return raw_input() if len(data) else raw_input('REQUEST XML> ')
    data = []
    try:
        for line in iter(prompt, u'\u0004'):  # EOF character - CTRL+D
            data.append(line)
    except EOFError:
        pass
    return '\n'.join(data)

