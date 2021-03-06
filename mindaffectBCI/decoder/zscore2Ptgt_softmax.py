import numpy as np
#@function
def zscore2Ptgt_softmax(f, softmaxscale=2, validTgt=None, marginalizemodels=True):
    '''
    convert normalized output scores into target probabilities
    Inputs:
     f - (nM,nTrl,nDecis,nY) [#Y x #decisPts x #Trials x #Models] normalized accumulated scores]
     softmaxscale - float, slope to scale from scores to probabilities
     validtgtTrl = (nTrl,nY) [nY x #Trl]:bool which targets are valid in which trials 
    Outputs:
     Ptgt - (nTrl,nY) [#Y x #Trials] - target probability for each trial
    '''

    # fix the nuisance parameters to get per-output per trial score
    # pick the model

    # make 4d->3d for simplicity
    if f.ndim > 3:
        origf = f.copy()
        if f.shape[0] > 1:
            # WARNING: assume that have unique model for each output..
            # WARNING: f must have same mean and scale for this to be valid!!
            f=np.zeros(f.shape[1:])
            for mi in range(origf.shape[0]):
                f[..., mi]=origf[mi, :, :, mi]
        else:
            f = f[0, ...]
    elif f.ndim == 2:
        f = f[np.newaxis, :]
    elif f.ndim == 1:
        f = f[np.newaxis, np.newaxis, :]
    # Now : f= (nTrl,nDecis,nY)

    if validTgt is None: # get which outputs are used in which trials..
        validTgt = np.any(f != 0, 1) # (nTrl,nY)
    elif validTgt.ndim == 1:
        validTgt = validTgt[np.newaxis, :]

    noutcorr = softmax_nout_corr(np.sum(validTgt,1)) # (nTrl,)
    softmaxscale = softmaxscale * noutcorr[:,np.newaxis,np.newaxis] #(nTrl,1,1)

    # get the prob each output conditioned on the model
    Ptgteptimdl = softmax(f*softmaxscale,validTgt)
    
    if (marginalizemodels and
        (Ptgteptimdl.shape[1] > 1 or # mulitple decis points 
        (Ptgteptimdl.ndim > 3 and Ptgteptimdl.shape[0] > 1))): # multiple models
        # need to remove the nusiance parameters to get per-trial Y-prob
        ftgt=np.zeros((Ptgteptimdl.shape[0], Ptgteptimdl.shape[2])) # (nTrl,nY) [ nY x nTrl]
        for ti in range(Ptgteptimdl.shape[0]): # loop over trials
            Ptgtepmdl = Ptgteptimdl[ti, :, :] # (nDecis,nY) [ nY x nDecis ]
            # compute entropy over outputs for each decision point
            ent = 1 - np.sum(Ptgtepmdl*np.log(np.maximum(Ptgtepmdl, 1e-08)), 1) / -np.log(Ptgtepmdl.shape[1]) # (nDecis)
            # find when hit max-ent decison
            epidx = np.argmax(ent)
            wght = np.ones(Ptgtepmdl.shape[0]) # [ nDecis ]
            wght[:epidx] = 0
            # BODGE 1: just do weighted sum over decis points with more data than max-ent point
            ftgt[ti, :] = np.dot(wght, f[ti, :, :]) / np.sum(wght)

        Ptgt = np.exp(softmaxscale*(ftgt-np.max(ftgt, -1, keepdims=True))) # (nTrl,nY) [ nY x nTrl ]
        if not all(validTgt):
            Ptgt = Ptgt*validTgt
        Ptgt = Ptgt/np.sum(Ptgt, -1) # [nY x nTrl ]
    else:
        Ptgt = Ptgteptimdl

    if any(np.isnan(Ptgt.ravel())):
        if not all(np.isnan(Ptgt.ravel())):
            print('Error NaNs in target probabilities')
        Ptgt[:] = 0
    return Ptgt


def softmax(f,validTgt=None):
    ''' simple softmax over final dim of input array, with compensation for missing inputs with validTgt mask. '''
    Ptgteptimdl=np.exp(f-np.max(f, -1, keepdims=True)) # (nTrl,nDecis,nY) [ nY x nDecis x nTrl ]
    # cancel out the missing outputs
    if validTgt is not None and not all(validTgt.ravel()):
        Ptgteptimdl = Ptgteptimdl * validTgt[..., np.newaxis, :]
    # convert to softmax, with guard for div by zero
    Ptgteptimdl = Ptgteptimdl / np.maximum(np.sum(Ptgteptimdl, -1, keepdims=True),1e-6)
    return Ptgteptimdl

def softmax_nout_corr(n):
    ''' approximate correction factor for probabilities out of soft-max to correct for number of outputs'''
    return np.minimum(2.45,1.25+np.log2(np.maximum(1,n))/5.5)/2.45

#@function
def testcase():
    import numpy as np
    nY = 10
    nM = 1
    nEp = 340
    nTrl = 100
    noise = np.random.standard_normal((nM,nTrl,nEp,nY))
    noise = noise - np.mean(noise.ravel())
    noise = noise / np.std(noise.ravel())

    sigamp=0.25*np.ones(noise.shape[-2]) # [ nEp ]
    # no signal ast the start of the trial
  #startupNoise_samp=nEp*.5;
  #sigamp((1:size(sigamp,2))<startupNoise_samp)=0;
    Fy = np.copy(noise)
    # add the signal
    Fy[0, :, :, 0] = Fy[0, :, :, 0] + sigamp
    #print("Fy={}".format(Fy))
    
    sFy=np.cumsum(Fy,-2)
    from normalizeOutputScores import normalizeOutputScores
    ssFy,scale_sFy,N,_,_=normalizeOutputScores(Fy,minDecisLen=-1,filtLen=0)
    #print('ssFy={}'.format(ssFy.shape))
    from zscore2Ptgt_softmax import zscore2Ptgt_softmax, softmax
    smax = softmax(ssFy)
    #print("{}".format(smax.shape))
    Ptgt=zscore2Ptgt_softmax(ssFy,marginalizemodels=False) # (nTrl,nEp,nY)
    #print("Ptgt={}".format(Ptgt.shape))
    import matplotlib.pyplot as plt
    plt.clf()
    tri=1
    plt.subplot(411);plt.cla();
    plt.plot(sFy[0,tri,:,:])
    plt.plot(scale_sFy[0,tri,:],'k')
    plt.title('ssFy')
    plt.grid()
    plt.subplot(412);plt.cla();
    plt.plot(ssFy[0,tri,:,:])
    plt.title('ssFy')
    plt.grid()
    plt.subplot(413);plt.cla()
    plt.plot(smax[0,tri,:,:])
    plt.title('softmax')
    plt.grid()
    plt.subplot(414);plt.cla()
    plt.plot(Ptgt[tri,:,:])
    plt.title('Ptgt')
    plt.grid()
    plt.show()
    
    maxP=np.max(Ptgt,-1) # (nTrl,nEp) [ nEp x nTrl ]
    estopi=[ np.flatnonzero(maxP[tri,:]>.9)[-1] for tri in range(Ptgt.shape[0])]

if __name__=="__main__":
    testcase()
