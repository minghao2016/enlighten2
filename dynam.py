#!/usr/bin/env python3
import os
import sys
import argparse
import json
import utils
import sanderflow


def get_dynam_dir(system):
    postfix = ""
    i = 0
    while os.path.isdir(os.path.join(system, "dynam" + postfix)):
        i += 1
        postfix = str(i)
    return "dynam" + postfix


parser = argparse.ArgumentParser(
    description=""
    "Performs a fast equilibration of a simulation system "
    "prepared using prep.py. Does the following:"
    " - initial  brief minimization of hydrogens (100 steps)"
    " - simulated annealing (10000 steps)"
    " - final brief minimization (100 steps)",
    formatter_class=argparse.RawDescriptionHelpFormatter
)

parser.add_argument("system", help="name of the simulation system (as in prep.py)")
parser.add_argument("ligand", help="name of the ligand")
parser.add_argument('-relax', action='store_true')
parser.add_argument("params", help="additional parameters",
                    type=argparse.FileType(), nargs='?')
args = parser.parse_args()

if not os.path.isdir(args.system):
    print("Directory {} is not found. Please run prep first.".format(args.system),
          file=sys.stderr)
    print("If you HAVE run prep.sh, please run dynam.py "
          "from the same directory as prep.sh.",
          file=sys.stderr)
    exit(1)

params = {
    "belly_radius": 4.5,
    "central_atom": None
}

if args.params is not None:
    params = {**params, **json.load(args.params)}
    args.params.close()

if params["central_atom"] is None:
    bellymask = ":{} <@{}".format(args.ligand, params["belly_radius"])
else:
    bellymask = "@{} <@{}".format(params["central_atom"], params["belly_radius"])

belly = {"bellymask": bellymask}

relax_params = [
  {"name": "minimize_h_all", "template": "minh"},
  {"name": "minimize_h_in_sphere", "template": "minh_ibelly", "params": belly},
  {"name": "annealing_with_restraints", "template": "sa_ca", "params": belly},
  {"name": "annealing_without_restraints", "template": "sa", "params": belly},
  {"name": "minimize_all_in_sphere", "template": "min_ibelly", "params": belly}
]

dynam_params = [
    {"name": "heat", "template": "heat", "params": belly},
    {"name": "md", "template": "md", "params": belly},
    {"name": "minimize", "template": "min", "params": belly},
]

tleap_dir = os.path.abspath(os.path.join(args.system, 'tleap'))
prmtop = "{}/{}.sp20.top".format(tleap_dir, args.system)
mode = 'relax' if args.relax else 'dynam'

if mode == 'relax':
    crd = "{}/{}.sp20.rst".format(tleap_dir, args.system)
    sanderflow_params = relax_params
    working_dir = '{}/{}'.format(args.system, 'relax')
else:
    relax_dir = os.path.abspath(os.path.join(args.system, 'relax'))
    crd = "{}/{}_relax.rst".format(relax_dir, args.system)
    sanderflow_params = dynam_params
    working_dir = '{}/{}'.format(args.system, get_dynam_dir(args.system))

utils.set_working_directory(working_dir)
status, result = sanderflow.run(prmtop, crd, sanderflow_params)
if not status:
    sys.exit(1)

final_crd = "{system}_{mode}.rst".format(system=args.system, mode=mode)
os.system("cp {crd} {final_crd}".format(crd=result.crd, final_crd=final_crd))