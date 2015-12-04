


import sys
from powertree import *
import re
import os

designs = ['vlsi-l1-b4-lov-pt', 'vlsi-l1-b4-hov-pt']

benchmarks = filter(lambda x: "power" in x, os.listdir(designs[0]))

#designs = ['vlsi-l1-b4-hov-pt']

#benchmarks = ['dfilter.riscv.power.avg.max.report']



top_lines_to_collect = {
        'Top': ["Top"],
        'Tile': ["RocketTile (RocketTile)"],
        'Hwacha': ["Hwacha (Hwacha)"],
        }



hwacha_lines_to_collect = {
        'Scalar + Frontend': ["rocc (RoCCUnit)", "icache (HwachaFrontend)", "VRU (VRU)", "scalar (ScalarUnit)"],
        'Functional Units': ["ALUSlice_", "FMASlice", "IMulSlice", "FCmpSlice", "FConvSlice", "FDivSlice", "IDivSlice"],
        'VMU': ["vxu_dcc", "vmu (VMU)"], # double counting handled below
        'Control': ["vxu_exp (Expander)", "ctrl (LaneCtrl)", "vxu_seq (LaneSequencer)", "mseq (MasterSequencer)"],
        'Banks': ["rf (BankRegfile"],
      }

#for x in hwacha_lines_to_collect.keys():
#    hwacha_lines_to_collect[x] = map(lambda z: re.escape(z), hwacha_lines_to_collect[x])

#hwacha_lines_to_collect['Control'][1] = hwacha_lines_to_collect['Control'][1][1:]


def add_powerdata(x, y):
    res = PowerData()
    res.name = x.name + "+" + y.name
    res.int_power = x.int_power + y.int_power
    res.switch_power = x.switch_power + y.switch_power
    res.leak_power = x.leak_power + y.leak_power
    res.total_power = x.total_power + y.total_power
    res.percent = x.percent + y.percent
    res.origdata = None
    return res

def sub_powerdata(x, y):
    res = PowerData()
    res.name = x.name + "-(" + y.name + ")"
    res.int_power = x.int_power - y.int_power
    res.switch_power = x.switch_power - y.switch_power
    res.leak_power = x.leak_power - y.leak_power
    res.total_power = x.total_power - y.total_power
    res.percent = x.percent - y.percent
    res.origdata = None
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
#    return lit
    return re.escape(lit)


if __name__ == '__main__':
    csv = open('output.csv', 'w')
    first = True

    for des in designs:
        for bench in benchmarks:
            """ get perf """
            pfile = open(des + "/" + bench.split(".power.")[0]+".out", 'r')
            cycleline = filter(lambda x: "cycle = " in x, pfile.readlines())
            pfile.close()
            benchmark_time = float(cycleline[0].split("=")[1].strip())/1000000000.0 # cycles to s @ 1ghz

            print des + "/" + bench
            hwacha_collectresult = {
                'Scalar + Frontend': [],
                'Functional Units': [],
                'VMU': [], # double counting handled below
                'Control': [],
                'Banks': [],
            }

            top_collectresult = dict()

            final_outputs = {
                'Hwacha Interconnect' : None,
                'Rocket + L1' : None, # RocketTile - Hwacha
                'L2' : None, # Top - Tile
            }
            l = log_to_tree(des + "/" + bench)

            hwacha_item = []
            for x in hwacha_lines_to_collect.keys():
                for y in hwacha_lines_to_collect[x]:
                    searchres = l.child_prune_search(lit_to_reg(y))
                    if searchres == []:
                        print "ERR " + y + " not found!"
                        exit(1)
                    hwacha_item += searchres
                    hwacha_collectresult[x] += searchres

            for x in hwacha_collectresult.keys():
                hwacha_collectresult[x] = map(lambda x: x.data, hwacha_collectresult[x])
                hwacha_collectresult[x] = reduce(add_powerdata, hwacha_collectresult[x])



            print "Printing any overlaps below. Make sure you handle these in the code:\n------"
            double_counted = n_to_n_ancestor_check(hwacha_item)
            print "------\nPrinted any overlaps above."
            
            ## YOU WILL MANUALLY NEED TO FIX ANY DOUBLE COUNTED ITEMS HERE
            ## this is an example where we know that all the double counting happens in 
            ## VMU, so fix it
            dc = map(lambda x: x.data, double_counted)
            sum_sub = reduce(add_powerdata, dc)
            hwacha_collectresult['VMU'] = sub_powerdata(hwacha_collectresult['VMU'], sum_sub)
            double_counted = []


            ## END HANDLING DOUBLE COUNTED ITEMS
            assert len(double_counted) == 0, "You have double counted items. You must manually fix and then pop them \nfrom double_counted before the script will proceed"

            collected_sum = reduce(add_powerdata, hwacha_collectresult.values())
            print collected_sum
            real_hwacha_tot = l.child_prune_search(lit_to_reg("Hwacha (Hwacha)"))[0].data
            print hwacha_collectresult
            final_outputs['Hwacha Interconnect'] = sub_powerdata(real_hwacha_tot, collected_sum)
            for x in hwacha_collectresult.keys():
                final_outputs[x] = hwacha_collectresult[x]


            for x in top_lines_to_collect.keys():
                top_collectresult[x] = l.child_prune_search(lit_to_reg(top_lines_to_collect[x][0]))[0].data

            final_outputs['Rocket + L1'] = sub_powerdata(top_collectresult['Tile'], top_collectresult['Hwacha'])
            final_outputs['L2'] = sub_powerdata(top_collectresult['Top'], top_collectresult['Tile'])


            tot = 0
            for x in final_outputs.keys():
                tot += final_outputs[x].percent
            print tot

            for x in final_outputs.keys():
                final_outputs[x] = final_outputs[x].total_power - final_outputs[x].leak_power

            final_outputs['Leakage'] = top_collectresult['Top'].leak_power
            print final_outputs

            bench = bench.split(".")[0]

            outheader = "Design,Benchmark,"
            outdata = des + "," + bench + ","
            for x in final_outputs.keys():
                outheader += x + ","
                outdata += str(final_outputs[x]*benchmark_time) + ","
            print benchmark_time 
            if first:
                csv.write(outheader + "\n")
                first = False
            csv.write(outdata + "\n")
    csv.close()
