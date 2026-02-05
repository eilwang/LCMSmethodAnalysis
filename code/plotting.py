import anndata
from anndata import AnnData
import seaborn as sns
import matplotlib.pyplot as plt
from diann_collection import DiannCollection
class Plotter:
    def __init__(self):
        pass

    def precursor_hist(self, ad, samples, x='RT', mask=['Precursor.Quantity', 'mask'], ax=None, alpha=0.5):
        for s in samples:
            temp = ad[:, s]
            if ax:
                sns.histplot(temp.layers[x], ax=ax, alpha=0.5)
            else:
                sns.histplot(temp.layers[x], alpha=alpha)

    def precursor_scatter(self, ad, samples, x='RT', y='Intensity', mask=['Precursor.Quantity', 'mask'], ax=None, alpha=0.5):
        for s in samples:
            temp = ad[:, s]
            if ax:
                sns.scatterplot(x = temp.layers[x], y = temp.layers[y], ax=ax, alpha=0.5)
            else:
                sns.scatterplot(x = temp.layers[x], y = temp.layers[y], alpha=alpha)

    def precursor_hist(self, collection, level, samples, x='RT', ax=None, alpha=0.5):
        ad = collection.data[level]
        for s in samples:
            temp = ad[:, s]
            if ax:
                sns.histplot(temp.layers[x], ax=ax, alpha=0.5)
            else:
                sns.histplot(temp.layers[x], alpha=alpha)

    def plot_precursor_mz_im(self, 
                             ad, 
                             s, 
                             mscollection, 
                             ms_method: str ='sample', 
                             mz : str = 'Precursor.Calibrated.Mz', 
                             im: str = 'Exp.1/K0', 
                             hue: str ='Precursor.Charge', 
                             ax: plt.Axes = None,
                             kde: bool = True,
                             ):
        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 8))
        
        sample = ad[:, s]

        # 1. Plot DIA windows first (m/z × IM space)
        if kde:
            sns.kdeplot(x = sample.layers[mz].flatten(), 
                    y = sample.layers[im].flatten(),
                    s=1, 
                    alpha=0.3, 
                    color='grey',
                    ax=ax)

        if ms_method == 'sample':
            meth = ad.var.loc[s, 'ms meth']
            mscollection.plot_windows([meth], 
                                    color_by_method=True,
                                    alpha=0.4,
                                    show_labels=False, 
                                    ax=ax)

        if hue:
            # Scatter plot of precursors
            sns.scatterplot(
                x = sample.layers[mz][:, 0], 
                y = sample.layers[im][:, 0],
                hue = hue,
                palette=sns.color_palette("dark:salmon", as_cmap=True),
                s=5, 
                alpha=0.1,
                ax=ax)
        
            ax.legend(title=hue)

            legend = ax.legend_
            for lh in legend.legend_handles:
                lh.set_alpha(1) # Set alpha to 1 (fully opaque)
                lh._sizes = [250]

        else:
            sns.scatterplot(
                x = sample.layers[mz][:, 0], 
                y = sample.layers[im][:, 0],
                color="darkgray",
                s=5, 
                alpha=0.1,
                ax=ax)
            


        # plt.tight_layout()

    def scatterplot_difference(self, 
                        ad: AnnData, 
                        sample1: str, 
                        sample2: str,
                        layer: str,
                        x: str = None,
                        figsize: tuple = (10, 6),
                        x_shift: float = 0,
                        y_shift: float = 0,
                        ax= None
                        ):
        
        if ax is None:
            fig, ax = plt.subplots(figsize=figsize)

        df = ad.to_df(layer)

        if x == None:
            x_vals = df[sample1]
        else:
            x_vals  = ad.to_df(x)[sample1]

        sns.scatterplot(x = x_vals - x_shift,
                        y = df[sample2] - df[sample1] - y_shift,
                        s=2,
                        alpha=0.25,
                        edgecolor=None,
                        ax=ax)
        ax.set_xlabel(f'{sample1} {layer}')
        ax.set_ylabel(f'{layer} Difference ({sample2} - {sample1})')



        # sns.histplot(comp_df[sample2] , ax=ax2, alpha=0.3, edgecolor=None, color='grey')
