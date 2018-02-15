#!/usr/bin/env python

import scipy as sp
import scipy.linalg
import fitsio
import argparse

from picca.utils import cov

if __name__ == '__main__':

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--data1', type = str, default = None, required=True,
                        help = 'data file #1')

    parser.add_argument('--data2', type = str, default = None, required=True,
                        help = 'data file #2')

    parser.add_argument('--out', type = str, default = None, required=True,
                        help = 'output file')
    args = parser.parse_args()


    data = {}
    
    ### Read data
    for i,p in enumerate([args.data1,args.data2]):
        h = fitsio.FITS(p)
        da  = sp.array(h[2]['DA'][:])
        we  = sp.array(h[2]['WE'][:])
        hep = sp.array(h[2]['HEALPID'][:])
        data[i] = {'DA':da, 'WE':we, 'HEALPID':hep}
        h.close()

    ### Add unshared healpix as empty data
    for i in sorted(list(data.keys())):
        j = (i+1)%2
        w = sp.logical_not( sp.in1d(data[j]['HEALPID'],data[i]['HEALPID']) )
        if w.sum()>0:
            new_healpix = data[j]['HEALPID'][w]
            nb_new_healpix = new_healpix.size
            nb_bins = data[i]['DA'].shape[1]
            print("Some healpix are unshared in data {}: {}".format(i,new_healpix))
            data[i]['DA']      = sp.append(data[i]['DA'],sp.zeros((nb_new_healpix,nb_bins)),axis=0)
            data[i]['WE']      = sp.append(data[i]['WE'],sp.zeros((nb_new_healpix,nb_bins)),axis=0)
            data[i]['HEALPID'] = sp.append(data[i]['HEALPID'],new_healpix)

    ### Sort the data by the healpix values
    for i in sorted(list(data.keys())):
        sort = sp.array(data[i]['HEALPID']).argsort()
        data[i]['DA']      = data[i]['DA'][sort]
        data[i]['WE']      = data[i]['WE'][sort]
        data[i]['HEALPID'] = data[i]['HEALPID'][sort]
        
    ### Append the data
    da  = sp.append(data[0]['DA'],data[1]['DA'],axis=1)
    we  = sp.append(data[0]['WE'],data[1]['WE'],axis=1)
    
    ### Compute the covariance
    co = cov(da,we)
    
    ### Get the cross-covariance
    size1 = data[0]['DA'].shape[1]
    cross_co = co.copy()
    cross_co = cross_co[:,size1:]
    cross_co = cross_co[:size1,:]
    
    ### Get the cross-correlation
    var = sp.diagonal(co)
    cor = co/sp.sqrt(var*var[:,None])
    cross_cor = cor.copy()
    cross_cor = cross_cor[:,size1:]
    cross_cor = cross_cor[:size1,:]

    ### Test if valid
    try:
        scipy.linalg.cholesky(co)
    except:
        print("Matrix is not positive definite")

    ### Save
    h = fitsio.FITS(args.out,'rw',clobber=True)
    h.write([cross_co,cross_cor],names=['CO','COR'])
    h.close()