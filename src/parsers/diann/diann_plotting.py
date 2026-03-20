import numpy as np
import pandas as pd
from parsers.diann.diann_collection import DiannCollection
from typing import Optional, Tuple
import seaborn as sns
import matplotlib.pyplot as plt
import anndata as ad

def bin(array, bin_width=15):
    bins = np.arange(0, np.nanmax(array) + bin_width, bin_width)
    labels = [int(b) for b in bins[:-1]]
    return pd.cut(array, bins=bins, labels=labels, right=False, ordered=False)

def fwhmdist(bpscollection: DiannCollection,
         sample_name: str,
         binwidth: Optional[float],
         ax: Optional[plt.Axes] = None,
         figsize: Optional[Tuple[int, int]] = None,
         overall_dist: Optional[bool] = True,
         plot_type: str = 'violin',
         stat: Optional[str] = 'count',
         common_norm: Optional[bool] = True
         ) -> None:
    
    if ax is None:
        if figsize is None:
            figsize = (8, 5)
        fig, ax = plt.subplots(figsize=figsize)

    data = bpscollection['precursor'][:, sample_name]

    # data = data[data.layers['Precursor.Quantity'] > 0]

    rt_bins = bin(data.layers['RT'].flatten(), bin_width=binwidth)

    if plot_type == 'violin':
        sns.violinplot(x = rt_bins, 
                    y=data.layers['Precursor.FWHM'].flatten(),
                    linewidth=1,
                    fill=False, 
                    inner='box',
                    ax = ax)
        
        if overall_dist:
            sns.violinplot(y=data.layers['Precursor.FWHM'].flatten(), ax = ax) 
        
    elif plot_type == 'hist':
        if overall_dist:
            sns.histplot(x = data.layers['RT'].flatten(),
                         binwidth=binwidth,
                         edgecolor=None,
                         color='lightgrey',
                         stat=stat,
                         ax=ax)

        sns.histplot(x = data.layers['RT'].flatten(),
                     hue=data.layers['Precursor.FWHM'].flatten(), 
                     binwidth=binwidth,
                     stat=stat,
                     element="step",
                     fill=False,
                     palette='viridis',
                     common_norm=common_norm,
                     alpha=0.75, 
                     ax=ax)
    
    ax.set_xlabel('RT', fontsize=12)
    ax.set_ylabel('# MS2 Across FWHM', fontsize=12)
