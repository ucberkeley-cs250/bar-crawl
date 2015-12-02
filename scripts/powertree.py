""" Properly extract data from pt-pwr results """

import re

class PowerData:
    def __init__(self, line=None):
        if line is not None:
            self.origdata = line
            l = line.split()
            self.name =  " ".join(l[0 : -5])
            self.int_power = float(l[-5])
            self.switch_power = float(l[-4])
            self.leak_power = float(l[-3])
            self.total_power = float(l[-2])
            self.percent = float(l[-1])
        else:
            # otherwise, "empty" PowerData
            self.origdata = ""
            self.name = ""
            self.int_power = 0.0
            self.switch_power = 0.0
            self.leak_power = 0.0
            self.total_power = 0.0
            self.percent = 0.0

    def __repr__(self):
        if self.origdata is not None:
            return self.origdata
        else:
            if len(self.name) > 100:
                truncatename = self.name[:100] + "..."
            else:
                truncatename = self.name
            return str([truncatename, self.int_power, self.switch_power, self.leak_power, self.total_power, self.percent])

    def __str__(self):
        return self.__repr__()

class TreeNode:
    """ Simple tree structure for python representation of pt-pwr report. """

    def __init__(self, parent, nest_level, data):
        # parent = None for root 
        # nest_level = indent in log. 0 for root, 2, 4, 6, ...
        # next level is not autoadjusted when nodes are moved around, only 
        # correct at tree construction time
        
        self.parent = parent
        self.children = []
        self.nest_level = nest_level
        self.data = PowerData(data.strip())

    def is_ancestor(self, potential_ancestor):
        """ Useful to prevent accidentally double counting """
        nextpar = self.parent
        while nextpar is not None:
            if nextpar == potential_ancestor:
                return True
            nextpar = nextpar.parent
        return False

    def add_child(self, ch):
        assert ch.nest_level - 2 == self.nest_level, "CHILD ADDED WITH INCORRECT NEST LEVEL"
        self.children.append(ch)

    def get_root(self):
        c = self
        while c.parent != None:
            c = c.parent
        return c

    def __repr__(self):
        return " " * self.nest_level + repr(self.data)

    def __str__(self):
        return self.__repr__()

    def print_tree(self):
        """ DFS to print the full tree as it appears in the pt-pwr output """
        visit = [self]
        while visit != []:
            curr = visit.pop(0)
            print curr
            visit = curr.children + visit

    def search(self, query):
        """ search """
        collect = []
        visit = [self]
        while visit != []:
            curr = visit.pop(0)
            #if query in curr.data.name:
            #    collect.append(curr)
            if re.search(query, curr.data.name) is not None:
                collect.append(curr)
            visit = curr.children + visit
        return collect

## two spaces = one indent level in the log

def start_line_match(linesarr, ind):
    l1 = "Hierarchy                             Power    Power    Power     Power    %"
    l2 = "--------------------------------------------------------------------------------"
    return l1 in linesarr[ind] and l2 in linesarr[ind+1]

def get_line_indent_level(line):
    return len(line) - len(line.lstrip(' '))


def log_to_tree(pt_pwr_file):
    """ Build a Tree from the pt-pwr output """
    f = open(pt_pwr_file, 'r')
    g = f.readlines()
    f.close()

    removefront = 0
    for x in xrange(len(g)):
        if start_line_match(g, x):
            removefront = x + 2
            break

    # g now consists only of the power info, remove the top of the file and 
    # the last line containing only "1"
    g = g[removefront : -1]

    # now start actually processing the data into a tree
    current = None

    for line in g:
        indent = get_line_indent_level(line)
        if current == None:
            current = TreeNode(None, indent, line)
        else:
            # here, compare the indent level to current and decide what to do
            # compare is always the last node added
            if indent == current.nest_level:
                n = TreeNode(current.parent, indent, line)
                current.parent.add_child(n)
                current = n
            elif indent == current.nest_level + 2:
                n = TreeNode(current, indent, line)
                current.add_child(n)
                current = n
            else:
                # here, we're "unindenting"
                while current.nest_level != indent:
                    current = current.parent
                n = TreeNode(current.parent, indent, line)
                current.parent.add_child(n)
                current = n


    return current.get_root()

