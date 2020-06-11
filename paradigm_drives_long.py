# -*- coding: utf-8 -*-
"""
Created on Mon Mar 05 13:41:23 2018

@author: DanielM
"""


from neuron import h, gui  # gui necessary for some parameters to h namespace 
import numpy as np
import net_ppdynamicsoff
from input_generator import inhom_poiss
import os
import argparse
import time
from analysis_main import time_stamps_to_signal
import pdb
tsts = time_stamps_to_signal

# Handle command line inputs with argparse
parser = argparse.ArgumentParser(description='Pattern separation paradigm')
parser.add_argument('-runs',
                    nargs=3,
                    type=int,
                    help='start stop range for the range of runs',
                    default=[0, 1, 1],
                    dest='runs')
parser.add_argument('-savedir',
                    type=str,
                    help='complete directory where data is saved',
                    default=os.getcwd(),
                    dest='savedir')
parser.add_argument('-seed',
                    nargs=3,
                    type=int,
                    help='the seed making the network reproducible',
                    default=[10006, 10007, 1],
                    dest='seed')
parser.add_argument('-pp_mod_rate',
                    type=int,
                    help='Frequency at which the input is modulated',
                    default=10,
                    dest='pp_mod_rate')
parser.add_argument('-pp_max_rate',
                    type=int,
                    help='The maximum frequency the input reaches',
                    default=100,
                    dest='pp_max_rate')
parser.add_argument('-W_pp_gc',
                    type=float,
                    help='the weight of the pp to gc connection',
                    default=2.5e-4,
                    dest='W_pp_gc')
parser.add_argument('-W_pp_bc',
                    type=float,
                    help='the weight of the pp to bc connection',
                    default=5e-4,
                    dest='W_pp_bc')
parser.add_argument('-rec_cond',
                    type=int,
                    help='number of hc to gc synapses',
                    default=0,
                    dest='rec_cond')

args = parser.parse_args()

# Where to search for nrnmech.dll file. Must be adjusted for your machine.
dll_files = [("/home/daniel/repos/pyDentate/mechs_7-6_linux/x86_64/.libs/libnrnmech.so"),
             ("C:\\Users\\Daniel\\repos\\pyDentate\\mechs_7-6_win\\nrnmech.dll")]
for x in dll_files:
    if os.path.isfile(x):
        dll_dir = x
print("DLL loaded from: " + str(dll_dir))
h.nrn_load_dll(dll_dir)

# Start the runs of the model
runs = range(args.runs[0], args.runs[1], args.runs[2])
initial_run = runs[0]
dt = 0.1
for seed in range(args.seed[0], args.seed[1], args.seed[2]):
    # Generate temporal patterns for the 100 PP inputs
    np.random.seed(seed)
    temporal_patterns_full = inhom_poiss(mod_rate=args.pp_mod_rate,
                                    max_rate=args.pp_max_rate,
                                    n_inputs=400,
                                    dur=1)
    for run in runs:
        start_proc_t = time.perf_counter()
        print("Run: " + str(run) + ". Total time: " + str(start_proc_t))
        temporal_patterns = temporal_patterns_full.copy()
        for idx in range(run+24,temporal_patterns.shape[0]):
            temporal_patterns[idx] = np.array([])
        for idx in range(run):
            temporal_patterns[idx] = np.array([])

        nw = net_ppdynamicsoff.TunedNetwork(seed=seed,
                                            W_pp_gc=args.W_pp_gc,
                                            W_pp_bc=args.W_pp_bc,
                                            temporal_patterns=temporal_patterns,
                                            rec_cond=True)

        # Run the model
        """Initialization for -2000 to -100"""
        h.cvode.active(0)
        h.steps_per_ms = 1.0/dt
        h.finitialize(-60)
        h.t = -2000
        h.secondorder = 0
        h.dt = 10
        while h.t < -100:
            h.fadvance()

        h.secondorder = 2
        h.t = 0
        h.dt = 0.1

        """Setup run control for -100 to 1500"""
        h.frecord_init()  # Necessary after changing t to restart the vectors

        while h.t < 1100:
            h.fadvance()
        end_proc_t = time.perf_counter()
        print("Done Running at " + str(end_proc_t) + " after " + str((end_proc_t - start_proc_t)/60) + " minutes")

        save_data_name = (f"{str(nw)}_"
                          f"{seed:06d}_"
                          f"{run:03d}_"
                          f"{args.W_pp_gc:08.5f}_"
                          f"{args.W_pp_bc:08.5f}_"
                          f"{args.pp_mod_rate:04d}_"
                          f"{args.pp_max_rate:04d}_")

        #if run == 0:
        fig = nw.plot_aps(time=1100)
        tuned_fig_file_name = save_data_name
        nw.save_ap_fig(fig, args.savedir, tuned_fig_file_name)

        pp_lines = np.empty(400, dtype = np.object)
        pp_lines[0+run:24+run] = temporal_patterns[0+run:24+run]

        curr_pp_ts = np.array(tsts(pp_lines, dt_signal=0.1, t_start=0, t_stop=1100), dtype = np.bool)
        curr_gc_ts = np.array(tsts(nw.populations[0].get_properties()['ap_time_stamps'], dt_signal=0.1, t_start=0, t_stop=1100), dtype = np.bool)
        curr_mc_ts = np.array(tsts(nw.populations[1].get_properties()['ap_time_stamps'], dt_signal=0.1, t_start=0, t_stop=1100), dtype = np.bool)
        curr_hc_ts = np.array(tsts(nw.populations[2].get_properties()['ap_time_stamps'], dt_signal=0.1, t_start=0, t_stop=1100), dtype = np.bool)
        curr_bc_ts = np.array(tsts(nw.populations[3].get_properties()['ap_time_stamps'], dt_signal=0.1, t_start=0, t_stop=1100), dtype = np.bool)

        np.savez(args.savedir + os.path.sep + "time-stamps_" + save_data_name,
                 pp_ts = np.array(curr_pp_ts),
                 gc_ts = np.array(curr_gc_ts),
                 mc_ts = np.array(curr_mc_ts),
                 bc_ts = np.array(curr_bc_ts),
                 hc_ts = np.array(curr_hc_ts))

        #del curr_pp_ts, curr_gc_ts, curr_mc_ts, curr_hc_ts, curr_bc_ts
        #del nw
