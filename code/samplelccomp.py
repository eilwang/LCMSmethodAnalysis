import numpy as np
import matplotlib.pyplot as plt

def elution_param(lccollection, samplecollection, sample, dead_volume=None):
  # How much volume is pushed through the column at the RT of the first peptide that elutes
  # Essentially dead volume of the LC system

  ad = samplecollection.data['precursor'].copy()
  
  lcmethod = ad.var.loc[sample, 'lc meth']

  gradient = lccollection.get_method(lcmethod).gradient.copy()
  gradient['volume (nL)'] = np.interp(gradient['time [min]'], gradient['time [min]'], gradient['time [min]'] * gradient['Neo.PumpModule.Pump.Flow.Nominal [µl/min]']) * 1000  # convert to nL
  gradient['total volume (nL)'] = gradient['volume (nL)'].cumsum()

  min_rt = np.nanmin(ad[:, ad.var_names == sample].layers['RT'])

  if not dead_volume:
    dead_volume = np.interp(min_rt, gradient['time [min]'], gradient['total volume (nL)'])
  print(f"Total volume passed at rt_min ({min_rt:.2f} min): {dead_volume:.2f} nL")

  print(np.interp(min_rt, gradient['time [min]'], gradient['total volume (nL)']))

  # # Assuming that it actually takes a a certain %B to go from the pumps to the end of the column, assuming no deadvolume
  # meth['Nominal Time to %B'] = (meth['Time (min)'] + total_volume_at_rt_min / meth['Flow (nL/min)'])

  # How much volume passes through the system for elution, assuming no dead volume


  # total solvent volume that passes through the system including dead volume
  gradient['Total + Dead Volume (nL)'] = gradient['total volume (nL)'] + dead_volume
  # time it actually takes to elute the set %B through the end of the column, including dead volume
  gradient['Actual Time to Elute Nominal %B (min)'] = gradient['Total + Dead Volume (nL)'].apply(lambda x: np.interp(x, gradient['total volume (nL)'], gradient['time [min]']))

  gradient['Actual %B'] = gradient['time [min]'].apply(lambda x: np.interp(x, gradient['Actual Time to Elute Nominal %B (min)'], gradient['Neo.PumpModule.Pump.%B.Value [%]']))

#   df['Nominal Elution Volume (nL)'] = np.interp(df['Rt'], gradient['Time (min)'], gradient['Total Volume (nL)'])
#   # What %B a peptide theoretically elutes at assuming no dead volume
#   df['Nominal Elution %B'] = np.interp(df['Rt'], gradient['Time (min)'], gradient['%B'])

#   # What %B a peptide actually elutes at by subtracting the amount of time it takes for everything to pass through the system + column
#   ## hmm should this actually only take into account the column volume? not the fully system volume?
#   df['Actual Elution %B'] = np.interp(df['Rt'], gradient['Time (min)'], gradient['Actual %B'])

  return gradient

# def get_sample(sample_collection, sample={}):
  

# def plot_precursor_lc(lccollection, bpscollection, sample=None, sample_idx=None, ax=None, figsize=(10, 6)):
#   fig, ax = plt.subplots(figsize=(10,6))
#   ax2 = ax.twinx()
#   ax3 = ax.twinx()
#   ax4 = ax2.twinx()

#   #precursor RT distribution
#   sns.scatterplot(x = test[:, test.var['hystar_index'].isin(['14648'])].layers['RT'].flatten(),
#                   y= test[:, test.var['hystar_index'].isin(['14648'])].layers['RT'].flatten() - test[:, test.var['hystar_index'].isin(['14649'])].layers['RT'].flatten(),
#                   s=2,
#                   alpha=0.25,
#                   edgecolor=None,
#                   ax=ax)
#   ax.set_ylabel('RT Difference (Low flow - High Flow) in min')
#   sns.histplot(test[:, test.var['hystar_index'].isin(['14648'])].layers['RT'].flatten(), ax=ax2, alpha=0.3, edgecolor=None, color='grey')
#   sns.histplot(test[:, test.var['hystar_index'].isin(['14649'])].layers['RT'].flatten(), ax=ax2, alpha=0.3, edgecolor=None, color='blue')


#   lccollection.plot_gradients(['18p6m200nlv30'], y_cols = ['Neo.PumpModule.Pump.Flow.Nominal [µl/min]'], ax = ax3)
#   lccollection.plot_gradients(['18p6m200nlv30'], y_cols = ['Neo.PumpModule.Pump.%B.Value [%]'], ax = ax4)

#   sns.lineplot(data = df, x = 'Actual Time to Elute Nominal %B (min)', y='Neo.PumpModule.Pump.%B.Value [%]', ax=ax4, markers='o')
#   sns.lineplot(data = df, x = 'time [min]', y='Neo.PumpModule.Pump.%B.Value [%]', ax=ax4, color='orange', markers='o')

#   return df 