from logging import warning

import pandas as pd
from parsers.diann.diann_collection import DiannCollection
from typing import Dict, Optional, Union

from parsers.vneometh.lc_method_collection import VNeoMethodCollection


def map_lcms_methods(searchcollection: DiannCollection, 
                     sequences: Union[str, list[str]], 
                     existing='fillna', 
                     inplace=True
                     ) -> None:
    """In place function to map LCMS methods to DiannCollection from sequence csv file"""
    df_list = []

    if isinstance(sequences, str):
        sequences = [sequences]

    for sequence in sequences:
        df = pd.read_csv(sequence)
        df['lc meth'] = df['Instrument Method'].str.extract(r'.+\\(.+)$')
        df['sample'] = df['Result Path'].str.extract(r'.+\\(.+)\.d+')
        df['ms meth'] = df['MS Method'].str.extract(r'.+\\(.+?)(?:\.proteoscape)*\.m')
        df_list.append(df)
    df = pd.concat(df_list, ignore_index=True)

    #TODO: add function for filling in select missing valuees, ie if one sequences doesn't cover everything
    #TODO: add not inplace option that returns a new collection with the mapping instead of modifying in place
    
    for level in searchcollection.data.keys():
        ad = searchcollection.data[level]
        ad.var = ad.var.drop(columns=['lc meth', 'sample', 'ms meth'], errors='ignore')
        ad.var = ad.var.join(df[['lc meth', 'sample', 'ms meth']].set_index('sample'), how='left')
    
    return None

