from logging import warning

import pandas as pd
from parsers.search.search_collection import SearchCollection
from typing import Dict, Optional, Union

from parsers.vneometh.lc_method_collection import VNeoMethodCollection


def map_lcms_methods(searchcollection: SearchCollection, 
                     sequences: Union[str, list[str]], 
                     existing='fillna', 
                     inplace=True
                     ) -> None:
    """In place function to map LCMS methods to BPSCollection from sequence csv file
    
    Parameters:
    -----------
    searchcollection : BPSCollection
        The collection to add method mappings to
    sequences : str or list of str
        Path(s) to sequence CSV file(s)
    existing : str, default 'fillna'
        How to handle existing 'lc meth' and 'ms meth' columns:
        - 'fillna': Keep existing values, only fill NaN entries with new data
        - 'replace' or any other value: Drop existing columns and replace with new data
    inplace : bool, default True
        Whether to modify the collection in place (not yet implemented)
        
    Returns:
    --------
    pandas.DataFrame
        DataFrame with the mapping information from sequence files
    """
    df_list = []

    if isinstance(sequences, str):
        sequences = [sequences]

    if "diann" in searchcollection.search_type:
        sample_col = 'sample'
    else:
        sample_col = 'sample_name'

        
    for sequence in sequences:
        df = pd.read_csv(sequence)
        df['lc meth'] = df['Instrument Method'].str.extract(r'.+\\(.+)$')
        df[sample_col] = df['Result Path'].str.extract(r'.+\\(.+)\.d+')
        df['ms meth'] = df['MS Method'].str.extract(r'.+\\(.+?)(?:\.proteoscape)*\.m')

        if 'File Name' in df.columns:
            df['raw file'] = df['File Name'] + '.raw'
        df_list.append(df)
    df = pd.concat(df_list, ignore_index=True)

    #TODO: add function for filling in select missing valuees, ie if one sequences doesn't cover everything
    #TODO: add not inplace option that returns a new collection with the mapping instead of modifying in place
    

    for level in searchcollection.data.keys():
        ad = searchcollection.data[level]

        if "spectronaut" in searchcollection.search_type:
            temp = ad.var_names
            ad.var_names = ad.var['sample_name']

        # Handle existing columns based on the 'existing' parameter
        if existing == 'fillna':
            # Keep existing values and only fill NaN values with new data
            list = ['lc meth', 'ms meth']
            if 'File Name' in df.columns:
                list+= ['raw file']
                
            mapping_df = df[list + [sample_col]].set_index(sample_col)
            
            for col in list:
                if col in ad.var.columns:
                    # Merge and fill NaN values
                    ad.var = ad.var.join(mapping_df[[col]], how='left', rsuffix='_new')
                    mask = ad.var[col].isna()
                    ad.var.loc[mask, col] = ad.var.loc[mask, col + '_new']
                    ad.var = ad.var.drop(columns=[col + '_new'], errors='ignore')
                else:
                    # Column doesn't exist, add it normally
                    ad.var = ad.var.join(mapping_df[[col]], how='left')
        else:
            # Drop existing columns and replace with new data
            ad.var = ad.var.drop(columns=list, errors='ignore')
            ad.var = ad.var.join(df[list + [sample_col]].set_index(sample_col), how='left')
        if "spectronaut" in searchcollection.search_type:
            ad.var_names = temp
    return df

