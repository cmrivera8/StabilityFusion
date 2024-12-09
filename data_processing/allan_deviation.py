import allantools
import numpy as np

def get_stab(ts, values):
    rate = 1/np.mean(np.diff([ts.timestamp() for ts in ts]))
    (taus, devs, errs, ns) = allantools.oadev(values, rate=rate, data_type="freq", taus='decade')

    err_lo, err_hi = get_errorbars(values,taus,devs,rate=rate,alpha=0,d=2,dev_type="allan")
    error_bars = [np.array(err_lo),np.array(err_hi)]
    return taus, devs, error_bars

def get_errorbars(time_series, taus, devs, rate=1,alpha=0, d=2, dev_type="adev"):
    """
    Gets errorbars from Allan deviation data. Based on Greenhall equivalent degrees of freedom. Supposes the noise type is known.
    time_series: list of data
    taus: list of taus
    devs: list of deviations for the given taus
    rate: sampling rate in s
    alpha: defines the noise type --> (+2:White PM, +1:Flicker PM, 0:White FM, -1:Flicker FM, -2:Random Walk FM)
    d: deviation type (1:First-difference variance, 2:Allan variance, 3:Hadamard variance)
    """
    overlapping = False
    modified = False
    if dev_type =="modified":
        modified = True
    elif dev_type =="overlapping":
        overlapping = True

    cis = [] # Confidence interval
    edfs = [] # Greenhall equivalent degrees of freedom
    for (t, dev) in zip(taus, devs):
        edf = allantools.edf_greenhall(alpha=alpha, d=d, m=np.round(t*rate,3), N=len(
            time_series), overlapping=overlapping, modified=modified)
        edfs.append(edf)
        # with the known EDF we get CIs
        (lo, hi) = allantools.confidence_interval(dev=dev,  edf=edf)
        cis.append((lo, hi))
    err_lo = [d-ci[0] for (d, ci) in zip(devs, cis)] # lower errorbars list
    err_hi = [ci[1]-d for (d, ci) in zip(devs, cis)] # upper errorbars list
    return err_lo, err_hi