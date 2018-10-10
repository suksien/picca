#!/usr/bin/env python

import os
from os.path import basename, dirname, stat
import glob
import argparse

class batch:
    def __init__(self):
        self.outdir = None
        self.do_deltas = None
        self.cf = []
        self.export = []
        self.dmat = []
        self.xcf = []
        self.xdmat = []
        self.xexport = []
 
def get_header(time, name, email=None, queue="regular"):
    header = ""
    header += "#!/bin/bash\n"
    header += "#SBATCH -N 1\n"
    header += "#SBATCH -C haswell\n"
    header += "#SBATCH -q {}\n".format(queue)
    header += "#SBATCH -J {}\n".format(name)
    if email != None:
        header += "#SBATCH --mail-user={}\n".format(email)
        header += "#SBATCH --mail-type=ALL\n"
    header += "#SBATCH -t {}\n".format(time)
    header += "#SBATCH -L project\n"
    header += "#SBATCH -A desi\n"
    header += "#OpenMP settings:\n"
    header += "export OMP_NUM_THREADS=1\n"

    return header

def do_deltas(b,time, in_dir, out_dir, drq, email=None,debug=False):
    header = get_header(time, name="do_deltas", email=email)
    header += "srun -n 1 -c 64 do_deltas.py " + \
                "--in-dir {} --drq {} ".format(in_dir, drq) + \
                "--out-dir deltas --mode desi "
    if debug:
        header += "--nspec 10000"
    header += "\n" 
    b.do_deltas = "do_deltas.batch"
    fout = open(out_dir+"/do_deltas.batch","w")
    fout.write(header)
    fout.close()

def cf(b,time, zint, outdir, email=None):
    for zz in zint:
        zmin,zmax = zz.split(":")
        out = "cf_z_{}_{}.fits".format(zmin,zmax)
        exp_batch = export("00:10:00",
                "cf_z_{}_{}.fits".format(zmin,zmax),
                "dmat_z_{}_{}.fits".format(zmin,zmax),
                outdir+"/cf_z_{}_{}-exp.fits".format(zmin,zmax))
        header = get_header(time, name=out, email=email)
        srun = header + "srun -n 1 -c 64 do_cf.py --in-dir deltas " +\
                "--z-cut-min {} --z-cut-max {} ".format(zmin,zmax) +\
                "--out {} --nproc 32\n".format(out)

        print(out)
        fbatch = outdir+"/"+out.replace(".fits",".batch")
        b.cf.append(basename(fbatch))
        b.export.append(basename(exp_batch))

        fout = open(fbatch,"w")
        fout.write(srun)
        fout.close()

def dmat(b,time, zint, outdir, email=None, rej=0.99):
    for zz in zint:
        zmin,zmax = zz.split(":")
        out = "dmat_z_{}_{}.fits".format(zmin,zmax)
        header = get_header(time, name=out, email=email)
        srun = header + "srun -n 1 -c 64 do_dmat.py --in-dir deltas " +\
                "--z-cut-min {} --z-cut-max {} ".format(zmin,zmax) +\
                "--out {} --rej {} --nproc 32\n".format(out,rej)
        fbatch = outdir+"/"+out.replace(".fits",".batch")
        b.dmat.append(basename(fbatch))

        fout = open(fbatch,"w")
        fout.write(srun)
        fout.close()
    
def xcf(b,time, drq, zint, outdir, email=None):
    for zz in zint:
        zmin,zmax = zz.split(":")
        out = "xcf_z_{}_{}.fits".format(zmin,zmax)
        header = get_header(time, name=out, email=email)
        exp_batch = export("00:10:00",
                "xcf_z_{}_{}.fits".format(zmin,zmax),
                "xdmat_z_{}_{}.fits".format(zmin,zmax),
                outdir+"/xcf_z_{}_{}-exp.fits".format(zmin,zmax))
        srun = header + "srun -n 1 -c 64 do_xcf.py " +\
            "--drq {} --in-dir deltas ".format(drq) +\
             "--z-cut-min {} --z-cut-max {} ".format(zmin, zmax) +\
             "--out {} --nproc 32\n".format(out)
        fbatch = outdir+"/"+out.replace(".fits",".batch")
        b.xcf.append(basename(fbatch))
        b.xexport.append(basename(exp_batch))

        fout = open(fbatch,"w")
        fout.write(srun)
        fout.close()
    
def xdmat(b,time, drq, zint, outdir, email=None, rej=0.95):
    for zz in zint:
        zmin, zmax = zz.split(":")
        out = "xdmat_z_{}_{}.fits".format(zmin,zmax)
        header = get_header(time, name=out, email=email)
        srun = header + "srun -n 1 -c 64 do_xdmat.py " +\
            "--drq {} --in-dir deltas ".format(drq) +\
            "--z-cut-min {} --z-cut-max {} ".format(zmin, zmax) +\
            "--out {} --rej {} --nproc 32\n".format(out,rej)
        fbatch = outdir+"/"+out.replace(".fits",".batch")
        b.xdmat.append(basename(fbatch))

        fout = open(fbatch,"w")
        fout.write(srun)
        fout.close()
        
def export(time, cf_file, dmat_file, out):
    header = get_header(time, name=basename(out), queue="regular")
    cc = glob.glob(cf_file)
    dd = glob.glob(dmat_file)
    srun = header + "srun -n 1 -c 64 export.py "+\
            "--data {} --dmat {} ".format(cf_file,dmat_file)+\
            "--out {}\n".format(basename(out))
    chi2_ini = do_ini(dirname(out), basename(out))
    srun += "srun -n 1 -c 64 fitter2 {}\n".format(chi2_ini)
    fbatch = out.replace(".fits",".batch")
    fout = open(fbatch,"w")
    fout.write(srun)
    fout.close()

    return fbatch

def do_ini(outdir, cf_file):
    fout = open(outdir+"/"+cf_file.replace(".fits",".ini"),"w")
    fout.write("[data]\n")
    fout.write("name = {}\n".format(basename(cf_file).replace(".fits","")))
    fout.write("tracer1 = LYA\n")
    fout.write("tracer1-type = continuous\n")
    if "xcf" in cf_file:
        fout.write("tracer2 = QSO\n")
        fout.write("tracer2-type = continuous\n")
    else:
        fout.write("tracer2 = LYA\n")
        fout.write("tracer2-type = continuous\n")
    fout.write("filename = {}\n".format(cf_file))
    fout.write("ell-max = 6\n")

    fout.write("[cuts]\n")
    fout.write("rp-min = -200\n")
    fout.write("rp-max = 200\n")

    fout.write("rt-min = 0\n")
    fout.write("rt-max = 200\n")

    fout.write("r-min = 10\n")
    fout.write("r-max = 180\n")

    fout.write("mu-min = -1\n")
    fout.write("mu-max = 11\n")

    fout.write("[model]\n")
    fout.write("model-pk = pk_kaiser\n")
    fout.write("z evol LYA = bias_vs_z_std\n")
    fout.write("growth function = growth_factor_no_de\n")
    if "xcf" in cf_file:
        fout.write("model-xi = xi_drp\n")
        fout.write("z evol QSO = qso_bias_vs_z_croom\n")
    else:
        fout.write("model-xi = cached_xi_kaiser\n")


    fout.write("[parameters]\n")

    fout.write("ap = 1. 0.1 0.5 1.5 free\n")
    fout.write("at = 1. 0.1 0.5 1.5 free\n")
    fout.write("bias_LYA = -0.17 0.017 None None free\n")
    fout.write("beta_LYA = 1. 0.1 None None free\n")
    fout.write("alpha_LYA = 2.9 0.1 None None fixed\n")
    fout.write("growth_rate = 0.962524 0.1 None None fixed\n")

    fout.write("sigmaNL_per = 3.24 0.1 None None fixed\n")
    fout.write("1+f = 1.966 0.1 None None fixed\n")

    fout.write("par binsize {} = 4. 0.4 None None fixed\n".format(cf_file.replace(".fits","")))
    fout.write("per binsize {} = 4. 0.4 None None fixed\n".format(cf_file.replace(".fits","")))

    fout.write("bao_amp = 1. 0.1 None None fixed\n")
    if "xcf" in cf_file:
        fout.write("drp = 0. 0.1 None None free\n")
        fout.write("croom_par0 = 0.53 0.1 None None fixed\n")
        fout.write("croom_par1 = 0.289 0.1 None None fixed\n")
    fout.close()

    chi2_ini = outdir+"/chi2_{}".format(cf_file.replace(".fits",".ini"))
    fout = open(chi2_ini,"w")
    fout.write("[data sets]\n")
    fout.write("zeff = 2.310\n")
    fout.write("ini files = {}\n".format(cf_file.replace(".fits",".ini")))

    fout.write("[fiducial]\n")
    fout.write("filename = /global/homes/n/nbusca/igmhub/picca/py/picca/fitter2/models/PlanckDR12/PlanckDR12.fits\n")

    fout.write("[verbosity]\n")
    fout.write("level = 0\n")

    fout.write("[output]\n")
    fout.write("filename = {}\n".format(cf_file.replace(".fits",".h5")))

    fout.write("[cosmo-fit type]\n")
    fout.write("cosmo fit func = ap_at\n")
    fout.close()

    return basename(chi2_ini)

def submit(b):
    out_name = b.outdir+"/submit.sh"
    fout = open(out_name,"w")
    fout.write("#!/bin/bash\n")
    if b.do_deltas is not None:
        fout.write("do_deltas=$(sbatch --parsable {})\n".format(b.do_deltas))
    for cf_batch, dmat_batch,exp_batch in zip(b.cf, b.dmat, b.export):
        var_cf = cf_batch.replace(".batch","").replace(".","_")
        var_dmat = dmat_batch.replace(".batch","").replace(".","_")
        if b.do_deltas is not None:
            fout.write("{}=$(sbatch --parsable --dependency=afterok:$do_deltas {})\n".format(var_cf,cf_batch))
            fout.write("{}=$(sbatch --parsable --dependency=afterok:$do_deltas {})\n".format(var_dmat,dmat_batch))
        else:
            fout.write("{}=$(sbatch --parsable {})\n".format(var_cf,cf_batch))
            fout.write("{}=$(sbatch --parsable {})\n".format(var_dmat,dmat_batch))
        fout.write("sbatch --dependency=afterok:${},afterok:${} {}\n".format(var_cf,var_dmat,exp_batch))
        
    for xcf_batch, xdmat_batch,xexp_batch in zip(b.xcf, b.xdmat, b.xexport):
        var_xcf = xcf_batch.replace(".batch","").replace(".","_")
        var_xdmat = xdmat_batch.replace(".batch","").replace(".","_")
        if b.do_deltas is not None:
            fout.write("{}=$(sbatch --parsable --dependency=afterok:$do_deltas {})\n".format(var_xcf,xcf_batch))
            fout.write("{}=$(sbatch --parsable --dependency=afterok:$do_deltas {})\n".format(var_xdmat,xdmat_batch))
        else:
            fout.write("{}=$(sbatch --parsable {})\n".format(var_xcf,xcf_batch))
            fout.write("{}=$(sbatch --parsable {})\n".format(var_xdmat,xdmat_batch))
        fout.write("sbatch --dependency=afterok:${},afterok:${} {}\n".format(var_cf,var_dmat,xexp_batch))
        
    fout.close()
    os.chmod(out_name,stat.S_IRWXU | stat.S_IRWXG)

parser = argparse.ArgumentParser()

parser.add_argument("--in-dir", type=str, default=None, required=True, 
        help="absolute path to spectra-NSIDE directory "+\
                "(including spectra-NSIDE)")

parser.add_argument("--drq", type=str,default=None, required=True,
        help="absolute path to drq file")

parser.add_argument("--out-dir", type=str, default=None, required=True, 
        help="absolute path to spectra-NSIDE directory " +\
                "(including spectra-NSIDE)")

parser.add_argument("--email", type=str, default=None, required=False,
        help="your email address (optional)")

parser.add_argument("--to-do", type=str, nargs="*",
        default=["cf","xcf"],
        required=False, help="what to do")

parser.add_argument("--zint", type=str, 
        default=["0:2.35","2.35:2.65","2.65:3.05","3.05:10"],
        required=False, help="redshifts intervals")
 
parser.add_argument("--debug", 
        action="store_true", default=False)

parser.add_argument("--no-deltas",
        action="store_true", default=False,
        help="do not run do_deltas (because they were already run)")

args = parser.parse_args()

try:
    os.makedirs(args.out_dir+"/deltas")
except:
    pass

b = batch()
b.outdir = args.out_dir

time_debug = "00:10:00"
if "cf" in args.to_do:
    time = "03:30:00"
    if args.debug:
        time = time_debug
    cf(b,time, args.zint, args.out_dir, email=args.email)

    time = "02:00:00"
    if args.debug:
        time = time_debug
    dmat(b,time, args.zint, args.out_dir, email=args.email)

if "xcf" in args.to_do:
    time = "01:30:00"
    if args.debug:
        time = time_debug
    xcf(b,time, args.drq, args.zint, args.out_dir, email=args.email)

    time = "03:00:00"
    if args.debug:
        time = time_debug
    xdmat(b,time, args.drq, args.zint, args.out_dir, email=args.email)

time = "01:30:00"
if args.debug:
    time = time_debug
if not args.no_deltas:
    do_deltas(b,time,args.in_dir, args.out_dir,args.drq,
            email=args.email, debug=args.debug)

submit(b)
