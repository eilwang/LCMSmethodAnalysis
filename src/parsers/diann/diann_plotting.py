import numpy as np
import pandas as pd
from parsers.diann.diann_collection import DiannCollection
from typing import Optional, Tuple, Union
import seaborn as sns
import matplotlib.pyplot as plt
import anndata as ad

def bin(array, bin_width=15):
    bins = np.arange(0, np.nanmax(array) + bin_width, bin_width)
    labels = [int(b) for b in bins[:-1]]
    return pd.cut(array, bins=bins, labels=labels, right=False, ordered=False)

def layerdist(dc: DiannCollection,
         sample_name: str,
         binwidth: Optional[float],
         ax: Optional[plt.Axes] = None,
         figsize: Optional[Tuple[int, int]] = None,
         overall_dist: Optional[bool] = True,
         plot_type: str = 'violin',
         stat: Optional[str] = 'count',
         common_norm: Optional[bool] = True,
         quantity_layer: Optional[str] = 'Precursor.Quantity',
         log2 = False
         ) -> None:
    
    if ax is None:
        if figsize is None:
            figsize = (8, 5)
        fig, ax = plt.subplots(figsize=figsize)

    data = dc['precursor'][:, sample_name]

    if log2:
        arr = np.array(data.layers[quantity_layer], dtype=float)
        arr[arr <= 0] = np.nan
        layer_vals = np.log2(arr)
    else:
        layer_vals = data.layers[quantity_layer]

    # data = data[data.layers[quantity_layer] > 0]

    rt_bins = bin(data.layers['RT'].flatten(), bin_width=binwidth)

    if plot_type == 'violin':
        sns.violinplot(x = rt_bins, 
                    y=layer_vals.flatten(),
                    linewidth=1,
                    fill=False, 
                    inner='box',
                    ax = ax)
        
        if overall_dist:
            sns.violinplot(y=layer_vals.flatten(), ax = ax) 
        
    elif plot_type == 'hist':
        if overall_dist:
            sns.histplot(x = data.layers['RT'].flatten(),
                         binwidth=binwidth,
                         edgecolor=None,
                         color='lightgrey',
                         stat=stat,
                         ax=ax)

        sns.histplot(x = data.layers['RT'].flatten(),
                     hue=layer_vals.flatten(), 
                     binwidth=binwidth,
                     stat=stat,
                     element="step",
                     fill=False,
                     palette='viridis',
                     common_norm=common_norm,
                     alpha=0.75, 
                     ax=ax)
    elif plot_type == 'box':
        # Group by RT bin and sum layer values within each bin
        df = pd.DataFrame({'rt_bin': rt_bins, 'val': layer_vals.flatten()})
        df = df.dropna(subset=['rt_bin', 'val'])
        summed = df.groupby('rt_bin')['val'].sum().reset_index()
        if log2:
            summed['val'] = np.log2(summed['val'])
        sns.lineplot(x='rt_bin', y='val', data=summed, ax=ax)
    
    ax.set_xlabel('RT', fontsize=12)
    ax.set_ylabel(f'{quantity_layer}', fontsize=12)

# def check_dist(dc: DiannCollection, 
#                layer: str, 
#                samples: Optional[Union[list, str]] = None, 
#                figsize: Optional[Tuple[int, int]] = (10, 6),
#                ax: Optional[plt.Axes] = None,
#                split: Optional[bool] = False
#                ) -> None:
    
#     if ax is None:
#         if split:
#             fig, ax = plt.subplots(figsize=figsize)

#     df = dc.to_df(layer)
#     if samples is not None:
#         if isinstance(samples, str):
#             samples = [samples]
#         df = df.loc[:, samples]

#     df = df.melt(value_name=layer)

#     if split
#     for s in df.columns:
#         sns.violinplot(data = df, x = 'File.Name', y = layer, ax=ax)
    
#     plt.xticks(rotation=90)
