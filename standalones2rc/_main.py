# UNRESOLVED ISSUES:
# 	* Issues when slavesch has several dates inbetween two dates in Standalone input.

import argparse

from ._create_rc_model import create_rc_model

###################
# Parse arguments #
###################


def main():
    parser = argparse.ArgumentParser(
        description="Creates a RC (Reservoir Coupled) model from different stand alone models."
    )

    parser.add_argument(
        "outputfolder", type=str, help="Output directory for the RC model."
    )
    parser.add_argument(
        "casename", type=str, help="Case name (without .DATA extension)."
    )
    parser.add_argument("schfile", type=str, help="Master schedule file.")
    parser.add_argument("summaryfile", type=str, help="Master summary file.")
    parser.add_argument(
        "--datafiles",
        type=str,
        nargs="+",
        help="Path to standalone .DATA files.",
        required=True,
    )
    parser.add_argument(
        "--slavenames",
        type=str,
        nargs="+",
        help="Names of the different slaves in the RC model.",
        required=True,
    )
    parser.add_argument(
        "--cpus",
        type=int,
        nargs="+",
        help="Number of CPUs to be used for the different slaves.",
        required=True,
    )
    parser.add_argument(
        "--rptrst",
        action="store_true",
        help="Keep RPTRST keywords from the standalone input.",
        default=False,
    )
    parser.add_argument(
        "--wconprod",
        action="store_true",
        help="Keep original item 3 in WCONPRODs in slaves (i.e. do not change to 'GRUP').",
        default=False,
    )
    parser.add_argument(
        "--wefac",
        action="store_true",
        help="Keep original WEFAC in slaves (otherwise removed).",
        default=False,
    )
    parser.add_argument(
        "--gefac",
        action="store_true",
        help="Keep original GEFAC in slaves (otherwise removed).",
        default=False,
    )
    parser.add_argument(
        "--slavesch",
        type=str,
        help="File containing additional schedule keywords for the slaves.",
        default=None,
    )

    args = parser.parse_args()

    args.slavenames = [x.upper().replace("'", "") for x in args.slavenames]

    if args.outputfolder[-1] == "/":
        args.outputfolder = args.outputfolder[:-1]

    if not len(args.datafiles) == len(args.slavenames):
        raise ValueError(
            'The arguments "datafiles" and "slavenames" must have the same number of entries.'
        )

    if not len(args.datafiles) == len(args.cpus):
        raise ValueError(
            'The arguments "datafiles" and "cpus" must have the same number of entries.'
        )

    if len(args.slavenames) > len(set(args.slavenames)):
        raise ValueError('All the names in "slavenames" must be unique.')

    for slavename in args.slavenames:
        if len(slavename) > 8:
            raise ValueError(
                "Slavename " + slavename + " contains more than 8 characters."
            )

    if "MASTER" in args.slavenames:
        raise ValueError(
            "Please do not have a slavename called MASTER (this name is restricted to the automatically created RC MASTER .DATA-file)."
        )

    create_rc_model(
        outputfolder=args.outputfolder,
        casename=args.casename,
        schfile=args.schfile,
        summaryfile=args.summaryfile,
        slavesch=args.slavesch,
        datafiles=args.datafiles,
        cpus=args.cpus,
        slavenames=args.slavenames,
        rptrst=args.rptrst,
        wconprod=args.wconprod,
        wefac=args.wefac,
        gefac=args.gefac,
    )
