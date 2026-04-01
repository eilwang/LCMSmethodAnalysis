import numpy as np
import pandas as pd
from parsers.diann.diann_collection import DiannCollection
from typing import Optional, Tuple, Union
import seaborn as sns
import matplotlib.pyplot as plt
import anndata as ad

def bin(array, bin_width=15):
    bins = np.arange(0, np.nanmax(array) + bin_width, bin_width)
    labels = [float(b) for b in bins[:-1]]
    return pd.cut(array, bins=bins, labels=labels, right=False, ordered=False)

def rtdist(dc: DiannCollection,
         sample_name: str,
         binwidth: Optional[float],
         ax: Optional[plt.Axes] = None,
         figsize: Optional[Tuple[int, int]] = None,
         overall_dist: Optional[bool] = True,
         plot_type: str = 'violin',
         stat: Optional[str] = 'count',
         common_norm: Optional[bool] = True,
         quantity_layer: Optional[str] = None,
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
        # Create violin plot with proper numeric x-axis alignment
        rt_data = data.layers['RT'].flatten()
        
        # Create bins and get their centers for plotting
        bin_edges = np.arange(0, np.nanmax(rt_data) + binwidth, binwidth)
        bin_centers = bin_edges[:-1] + binwidth/2
        
        # Bin the data and collect values for each bin
        digitized = np.digitize(rt_data, bin_edges) - 1
        violin_data = []
        positions = []
        
        for i, bin_center in enumerate(bin_centers):
            mask = digitized == i
            if np.any(mask) and np.sum(mask) > 1:  # Need at least 2 points
                bin_values = layer_vals.flatten()[mask]
                violin_data.append(bin_values[~np.isnan(bin_values)])
                positions.append(bin_center)
        
        if violin_data:
            # Use matplotlib's violinplot for proper numeric positioning
            parts = ax.violinplot(violin_data, positions=positions, 
                                 widths=binwidth*0.8, showmeans=False, 
                                 showmedians=True, showextrema=False)
            
            # Style the violins
            for pc in parts['bodies']:
                pc.set_facecolor('lightblue')
                pc.set_alpha(0.7)
                pc.set_edgecolor('black')
                pc.set_linewidth(1)
        
        # Set continuous x-axis
        ax.set_xlim(0, np.nanmax(rt_data))
        
        if overall_dist and len(layer_vals.flatten()) > 1:
            # Add overall distribution violin at the end
            overall_x = np.nanmax(rt_data) + binwidth
            overall_data = layer_vals.flatten()[~np.isnan(layer_vals.flatten())]
            if len(overall_data) > 1:
                overall_parts = ax.violinplot([overall_data], positions=[overall_x], 
                                            widths=binwidth*0.8, showmeans=False, 
                                            showmedians=True, showextrema=False)
                for pc in overall_parts['bodies']:
                    pc.set_facecolor('gray')
                    pc.set_alpha(0.7)
                    pc.set_edgecolor('black')
                    pc.set_linewidth(1) 
        
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
        df = pd.DataFrame({'rt_bin': pd.to_numeric(rt_bins, errors='coerce'), 'val': layer_vals.flatten()})
        df = df.dropna(subset=['rt_bin', 'val'])
        summed = df.groupby('rt_bin')['val'].sum().reset_index()
        if log2:
            summed['val'] = np.log2(summed['val'])
        sns.lineplot(x='rt_bin', y='val', data=summed, ax=ax)
    
    ax.set_xlabel('RT', fontsize=12)
    ax.set_ylabel(f'{quantity_layer}', fontsize=12)
    ax.set_title(sample_name)

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
