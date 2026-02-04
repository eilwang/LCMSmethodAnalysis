import pandas as pd

def map_lcms_methods(collection, sequence, existing='fillna'):
    """In place function to map LCMS methods to DiannCollection from sequence csv file"""
    df = pd.read_csv(sequence)
    df['lc meth'] = df['Instrument Method'].str.extract(r'.+\\(.+)$')
    df['sample'] = df['Result Path'].str.extract(r'.+\\(.+)\.d+')
    df['ms meth'] = df['MS Method'].str.extract(r'.+\\(.+?)(?:\.proteoscape)*\.m')

    #TODO: add function for filling in select missing valuees, ie if one sequences doesn't cover everything
    
    for level in collection.data.keys():
        ad = collection.data[level]
        ad.var = ad.var.drop(columns=['lc meth', 'sample', 'ms meth'], errors='ignore')
        ad.var = ad.var.join(df[['lc meth', 'sample', 'ms meth']].set_index('sample'), how='left')