import argparse
from io import StringIO
import os
import re
import sys
import unicodedata

#-----------------------------------------------------------------------------
# profiles are tuples of (Unicode-Normalization-Form)
_profiles = {'win': 'NFC',
             'mac': 'NFD'}
_Msg_BrokenData_Depth = 'Broken tree structure; depth %d after %d.' \
                        ' (file:%s, line:%d)'

#-----------------------------------------------------------------------------
class KeywordNode:
    def __init__(self, value, parent, depth):
        if value != None and not isinstance(value, str): raise
        if parent != None and not isinstance(parent, KeywordNode): raise
        if not isinstance(depth, int): raise
        self.value = value
        self.children = []
        self.parent = parent
        self.depth = depth

    def __repr__(self):
        return "<%d:%s>" % (self.depth, self.value)

    def __lt__(self, other):
        def _norm(kw):
            return kw.rstrip(']').lstrip('[').lower()

        if self.depth != other.depth:
            raise Exception('Nodes at different depth cannot be compared!' \
                            '({} and {})'.format(self, other))

        # Order synonym first!
        if self.value[0] == '{' and other.value[0] != '{':
            return True
        if self.value[0] != '{' and other.value[0] == '{':
            return False

        return _norm(self.value) < _norm(other.value)

    def append(self, node):
        if not isinstance(node, KeywordNode): raise
        self.children.append(node)

    def stringify(self, nform, buf=None, depth=0):
        if buf == None:
            buf = StringIO()
        for node in self.children:
            buf.write('\t' * depth)
            buf.write(unicodedata.normalize(nform, node.value))
            buf.write('\n')
            node.stringify(nform, buf, depth+1)
        return buf.getvalue()

def parse_keyword_file(filename):
    def _sort(node):
        node.children.sort()
        for n in node.children:
            _sort(n)

    pat_indent = re.compile('^(\t*)([^\t\r\n]+)')
    root = KeywordNode(None, None, -1)
    prev_node = root
    cur_depth = -1
    with open(filename, 'rt', encoding='utf-8', errors='replace') as f:
        for ln, line in enumerate(f):
            m = pat_indent.search(line)
            depth = len(m.group(1))
            keyword = m.group(2)
            if cur_depth == depth:
                node = KeywordNode(value=keyword,
                              parent=prev_node.parent,
                              depth=depth)
                prev_node.parent.children.append(node)
            elif cur_depth < depth:
                if prev_node.depth+1 != depth:
                    raise Exception(_Msg_BrokenData_Depth%(depth,
                                                           prev_node.depth, ########
                                                           filename,
                                                           ln))
                node = KeywordNode(value=keyword,
                              parent=prev_node,
                              depth=depth)
                prev_node.children.append(node)
                cur_depth += 1
            else:
                # Determine which node will be the next parent
                levels_to_go_up = prev_node.depth - depth
                new_parent = prev_node.parent
                for _ in range(levels_to_go_up):
                    new_parent = new_parent.parent

                # Append
                node = KeywordNode(value=keyword,
                              parent=new_parent,
                              depth=depth)
                new_parent.children.append(node)
                cur_depth = depth
            prev_node = node

    _sort(root)
    return root

if __name__ == '__main__':
    desc = 'Sorts a keyword file exported from Adobe Lightroom 5.'

    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('filename', type=str, nargs=1,
                        help='an exported keyword file.')
    parser.add_argument('-p', type=str, nargs=1, default=('win',),
                        dest='prof', choices=('win', 'mac'),
                        help='output text format.')

    args = parser.parse_args()
    filename = args.filename[0]
    nform = _profiles[args.prof[0]]

    keywords = parse_keyword_file(filename)
    sys.stdout.write(keywords.stringify(nform))
