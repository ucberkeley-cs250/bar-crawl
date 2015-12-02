


import sys
from powertree import *
import re



lines_to_collect = {
        'Top': ["Top"],
        'Tile': ["RocketTile (RocketTile)"],
        'Hwacha': ["Hwacha (Hwacha)"],
        'frontend': ["rocc (RoCCUnit)", "icache (HwachaFrontend)", "VRU (VRU)", "scalar (ScalarUnit)"],
        'func_unit': ["ALUSlice_", "FMASlice", "IMulSlice", "FCmpSlice", "FConvSlice", "FDivSlice", "IDivSlice"],
        'mem': ["vxu_dcc", "vmu (VMU)"], # double counting handled below
        'control': ["vxu_exp (Expander)", "ctrl (LaneCtrl)", "vxu_seq (LaneSequencer)", "mseq (MasterSequencer)"],
        'banks': ["rf (BankRegfile"],
      }



def add_powerdata(x, y):
    res = PowerData()
    res.name = x.name + "+" + y.name
    res.int_power = x.int_power + y.int_power
    res.switch_power = x.switch_power + y.switch_power
    res.leak_power = x.leak_power + y.leak_power
    res.total_power = x.total_power + y.total_power
    res.percent = x.percent + y.percent
    res.origdata = "Not constructed from Line"
    return res

def sub_powerdata(x, y):
    res = PowerData()
    res.name = x.name + "-(" + y.name + ")"
    res.int_power = x.int_power - y.int_power
    res.switch_power = x.switch_power - y.switch_power
    res.leak_power = x.leak_power - y.leak_power
    res.total_power = x.total_power - y.total_power
    res.percent = x.percent - y.percent
    res.origdata = "Not constructed from Line"
    return res



def n_to_n_ancestor_check(res):
    """ check if we're double counting """
    double_counted = []
    for x in xrange(len(res)):
        for y in xrange(len(res)):
            if res[x].is_ancestor(res[y]):
                print str(res[y].data.name) + " is ancestor of " + str(res[x].data.name)
                double_counted.append(res[x])
    return double_counted

def lit_to_reg(lit):
    """ assume the above literals to search for are:
    1) starting at beginning of line
    2) should be escaped
    """
    return "^" + re.escape(lit)

if __name__ == '__main__':
    l = log_to_tree(sys.argv[1])
    #l.print_tree()

    all_item = []
    for x in lines_to_collect.keys():
        for y in lines_to_collect[x]:
            all_item += l.search(lit_to_reg(y))

    print "Printing any overlaps below:\n------"
    n_to_n_ancestor_check(all_item)
    print "------\nPrinted any overlaps above."

    hwachachunks = ['frontend', 'func_unit', 'mem', 'control', 'banks']
    hwachapieces = []
    for k in hwachachunks:
        for y in lines_to_collect[k]:
            r = l.search(lit_to_reg(y))
            if r == []:
                print "ERR " + y + " Not found"
            hwachapieces += r

    dat = map(lambda x: x.data, hwachapieces)
    a = reduce(add_powerdata, dat)
    print a
    print l.search(lit_to_reg("Hwacha (Hwacha)"))
    double_counted = n_to_n_ancestor_check(hwachapieces)
    dc = map(lambda x: x.data, double_counted)
    sum_sub = reduce(add_powerdata, dc)
    print double_counted
    print sum_sub
    out = sub_powerdata(a, sum_sub)
    print out
    print l.search(lit_to_reg("Hwacha (Hwacha)"))



