import pandas as pd

def map_lcms_methods(collection, 
                     sequence, 
                     existing='fillna', 
                     join_on=None):
    """In place function to map LCMS methods to DiannCollection from sequence csv file"""
    if isinstance(sequence, list):
        df_collection = []
        for i in sequence:
            df_collection.append(pd.read_csv(i))
        df = pd.concat(df_collection, ignore_index=True)
    else:
        df = pd.read_csv(sequence)
    df['lc meth'] = df['Instrument Method'].str.extract(r'.+\\(.+)$')
    df['sample'] = df['Result Path'].str.extract(r'.+\\(.+)\.d+')
    df['ms meth'] = df['MS Method'].str.extract(r'.+\\(.+?)(?:\.proteoscape)*\.m')

    #TODO: add function for filling in select missing valuees, ie if one sequences doesn't cover everything
    
    for level in collection.data.keys():
        ad = collection.data[level]

        if join_on:
            temp = ad.var_names
            ad.var_names = ad.var[join_on]
        ad.var = ad.var.drop(columns=['lc meth', 'sample', 'ms meth'], errors='ignore')
        ad.var = ad.var.join(df[['lc meth', 'sample', 'ms meth']].set_index('sample'), how='left')
        
        if join_on:
            ad.var_names = temp