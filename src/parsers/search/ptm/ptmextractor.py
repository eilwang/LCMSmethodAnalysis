import re
import pandas as pd
from typing import Optional, Union

def get_mod_indices(mod_seq, 
                    protein_start,  
                    mod_regex = r"n?(\(UniMod:\d+\))",
                    ptm_id = True,
                    unimod_dict = None, 
                    remove = (r"[\(\)]", r"^n")):
    """
    Extracts the positions, modified amino acids, and modifications from a single peptide sequence with modifications.

    Parameters:
    -----------
    mod_seq : str
        Peptide sequence with modifications
    protein_start : int
        Start position of the protein, if not available or undesired, set to 0
    mod_regex : str
        Regular expression to identify modifications
        ex. for msstats ptm, use r"n?(\(UniMod:\d+\))"
        ex2. for diann ptm, use r"(\d+\.\d+)"
    ptm_id : bool
        Whether to convert to some other mod naming convention using the unimod_dict
    unimod_dict : dict, optional
        Dictionary mapping UniMod IDs to modification names
    remove: str or tuple, optional
        Certain regex patterns to remove from the modification name, most commonly the n-term label and brackets
        Use tuple to specify multiple patterns to remove (and maintain order of operation), or a single string for one pattern

    Returns:
    --------
    position_list : list
        List of modification positions within the protein or stripped peptide sequence if protein_start == 0
        starting index is 1, 0 refers to n-term
        assuming n-term mod is listed prior to modification
    mod_aa_list : list
        List of modified amino acids
    mods_list : list
        List of modifications
    """
    
    if not isinstance(mod_seq, str):
        return [], [], []
    
    position_list = []
    mod_aa_list = []
    mods_list = []

    matches = re.finditer(mod_regex, mod_seq)
    for m in matches:
        mod = m.group(1)
        aa_before = re.sub(mod_regex, "", mod_seq[:m.start()])
        position = len(aa_before) + protein_start
        if isinstance(remove, (str, tuple)):
            if isinstance(remove, str):
                remove = (remove,)
            else:   
                for pattern in remove:
                    mod = re.sub(pattern, "", mod)
            
        if not ptm_id:
            mod = ""
        elif unimod_dict and mod in unimod_dict:
            mod = unimod_dict[mod]

        mod_aa = aa_before[-1] if len(aa_before) > 0 else 'n'
        position_list.append(position)
        mod_aa_list.append(mod_aa)
        mods_list.append(mod)

    if len(position_list) == 0:
        return [], [], []
    return position_list, mod_aa_list, mods_list

def get_localization_scores(df: pd.DataFrame, 
                            protein_start_col: Optional[Union[None, str]] = 'Protein.Start',
                            localization_score_regex: str = r"(n?\(\d+\.\d+\))",
                            ptm_cols = ['n:42.0106', 'M:15.9949', 'STY:79.96633'],
                            in_place=False) -> Union[pd.DataFrame, None]:
    """
    Extracts localization scores from specified PTM columns in a DataFrame and adds them as new columns.

    Parameters:
    -----------
    df : pd.DataFrame
        Input DataFrame containing individual columns for each PTM type, with localization scores for each possible site
    protein_start_col : Optional[Union[None, str]]
        Column name for the protein start position
        If none, protein_start is assumed to be 0
    localization_score_regex : str
        Regular expression to identify localization scores within the PTM columns
    ptm_cols : list or str
        List of PTM column names or a regex pattern to extract them from the DataFrame
    in_place : bool
        If True, modifies the DataFrame in place; otherwise, returns a new DataFrame
    Returns:
    --------
    pd.DataFrame
        DataFrame with added localization score columns: 'loc_index', 'loc_aa', 'loc_score' 
    """
    
    if not in_place:
        df = df.copy(deep=True)

    if not isinstance(ptm_cols, list): # if not a list of column names, assume that it is a regex pattern to extract the column names
        ptm_cols = df.columns.str.extract(ptm_cols, regex=True)
        
    for col in ptm_cols:
        if col in df.columns:
            temp = df.apply(
                lambda row: get_mod_indices(row[col], 
                                            protein_start=row[protein_start_col] if protein_start_col else 0, 
                                            mod_regex=localization_score_regex),
                axis=1, result_type='expand'
            )
            if any(c not in df.columns for c in ['loc_index', 'loc_aa', 'loc_score']):
                df[['loc_index', 'loc_aa', 'loc_score']] = temp.values
            else:
                df['loc_index'] = df['loc_index'] + temp[0]
                df['loc_aa'] = df['loc_aa'] + temp[1]
                df['loc_score'] = df['loc_score'] + temp[2]

    df['loc_score'] = df.apply(lambda row: [float(row['loc_score'][n]) for n, i in enumerate(row['loc_index']) if i in row['mod_index']], axis=1)
    df.drop(columns = ['loc_aa', 'loc_index'], inplace=True)
    if not in_place:
        return df
    
    
def list_df_filter(df: pd.DataFrame, 
                   col: str, 
                   list_mask: pd.Series) -> pd.Series:
    """
    Filters the lists in a specified DataFrame column of lists based on an array of boolean lists

    Parameters:
    -----------
    df : pd.DataFrame 
        Input DataFrame containing a column of lists to be filtered
    col : str
        Name of the column containing lists to be filtered
    mask : pd.Series
        Series of boolean lists indicating which elements of each list in each element of the column to keep in the corresponding lists in the specified column

    Returns:
    --------
    pd.Series
        Series containing the filtered lists from the specified column
    """

    temp = pd.DataFrame({col: df[col], 'mask': list_mask})
    return temp.apply(lambda row: [row[col][n] for n in row['mask'] if len(row[col]) > 0], axis=1)

def filter_mods(df: pd.DataFrame, 
                target_mods: Optional[Union[list, str, None]] = None, # remove any peptides that do not have the target mod(s)
                keep_only_target_mods: bool = True, # remove any mods that are not the target mod(s) in the peptide
                filter_individual_site: str = 'any', #;all: remove entire entry if any site on the peptide does not meet localization score threshold, or only remove sites that do not meet localization score threshold
                score_threshold: float = 0.75,
                in_place: bool = True) -> Union[pd.DataFrame, None]:
    """
    Filters the DataFrame based on target modifications and localization score thresholds.
    
    Parameters:
    -----------
    df : pd.DataFrame
        Input DataFrame containing modification information
    target_mods : list or str, optional
        List of target modifications to filter by; if None, no filtering is applied
    keep_only_target_mods : bool
        If True, only keeps the target modifications in the DataFrame; if False, keeps all modifications
        Ex. if True, and a peptide has both an Ox(M) and Phos(S), and the target mod is Phos, the Ox(M) will be removed from the entry
    filter_individual_site : str
        'any': removes entire entry if any site on the peptide does not meet localization score threshold
        'all': removes entire entry if all sites on the peptide do not meet localization score threshold
    score_threshold : float
        Localization score threshold for filtering modifications
    in_place : bool
        If True, modifies the DataFrame in place; otherwise, returns a new DataFrame
    Returns:
    --------
    pd.DataFrame
        Filtered DataFrame based on the specified criteria
    """

    if not in_place:
        df = df.copy(deep=True)

    if target_mods:
        if isinstance(target_mods, str):
            target_mods = [target_mods]
        has_target = df.apply(lambda row: [n for n, m in enumerate(row['mod']) if m in target_mods], axis=1)

        target_filter = has_target.apply(lambda x: len(x) > 0)
        df = df[target_filter]

        if keep_only_target_mods:
            # Positions of target mods; used to match against loc_index (which may differ in length from mod)
            has_target = has_target[target_filter]

            for col in ['mod', 'mod_aa', 'mod_index','loc_score']:
                df[col] = list_df_filter(df, col, has_target)
        
    if score_threshold > 0:
        above_threshold = df.apply(lambda row: [i for i, m in enumerate(row['loc_score']) if m >= score_threshold], axis=1)

        if filter_individual_site == 'any':
            for col in ['mod_aa', 'loc_score']:
                df[col] = list_df_filter(df, col, above_threshold)

        elif filter_individual_site == 'all':
            all_threshold_mask = above_threshold.apply(lambda x: np.all(x))
            df = df[all_threshold_mask]

    remove_empty = df['mod'].apply(lambda x: len(x) > 0)
    df = df[remove_empty]

    if not in_place:
        return df
    
def join_protein_mod_loc(df: pd.DataFrame,
                        name_col: str ='ProteinName',
                        index_col: str ='mod_index',
                        aa_col: str = 'mod_aa',
                        score_col: str = 'loc_score',
                        mod_col: str = 'mod',
                        singly_modified: bool = True,
                        protein_mod_col: str = 'ProteinName_Mod',
                        include_mod: bool = False,
                        include_score: bool = False,
                        in_place: bool = False):
    
    """
    For classifying modifications as modification sites within proteins or columns, 
    this function joins the protein/peptide name with the modification information, 
    including the modified amino acid, modification type, and localization score.

    Parameters:
    -----------
    df : pd.DataFrame
        Input DataFrame containing protein/peptide names and modification information
    name_col : str
        Column name for protein/peptide names
    index_col : str
        Column name for modification indices
    aa_col : str
        Column name for modified amino acids
    score_col : str
        Column name for localization scores
    mod_col : str
        Column name for modification types
    singly_modified : bool
        If True, creates a new row for each modification on a peptide; if False, allows for multiple modifications
    protein_mod_col : str
        Column name for the resulting protein-modification string
    include_mod : bool
        If True, includes the modification type in the resulting string
    include_score : bool
        If True, includes the localization score in the resulting string
    in_place : bool
        If True, modifies the DataFrame in place; otherwise, returns a new DataFrame    
    Returns:
    --------
    pd.DataFrame
        DataFrame with the protein-modification string added as a new column
    """
    
    if not in_place:
        df = df.copy(deep=True)
    
    cols = [aa_col, index_col]

    if include_mod:
        cols.append(mod_col)
    if include_score:
        cols.append(score_col)

    if singly_modified:
        df = df.explode([aa_col, index_col, mod_col, score_col])
        df['mod_str'] = df[cols].astype(str).agg("".join, axis=1)
        joined = df['mod_str']
    else:
        df['mod_str'] = [[''.join(str(x) for x in tup) for tup in zip(*lsts)]for lsts in zip(*[df[col] for col in cols])]
        joined = df['mod_str'].str.join('_')

    joined = joined.apply(lambda x: '_' + x if len(x) > 0 else '')

    df[protein_mod_col] = df[protein_col].str.cat(joined)
    return df

def clean_msstats_ptm(msstats_ptm_path,
                      protein_col='ProteinName',
                      protein_start_col='Protein.Start',
                      mod_peptide_col='PeptideSequence',
                      ptm_cols = r'([A-Za-z]+\d+\.\d+)',
                      fixed_mod_regex = r"\(UniMod:4\)",
                      mod_regex = r"(\(UniMod:\d+\))",
                      localization_score_regex: str = r"(n?\(\d+\.\d+\))",
                      target_mods=['UniMod:21'],
                      score_threshold=0.75,
                      output_path=None):
    
    df = pd.read_csv(msstats_ptm_path)

    df[mod_peptide_col] = df[mod_peptide_col].str.replace(fixed_mod_regex, "", regex=True)
    df[['mod_index', 'mod_aa', 'mod']] = df.apply(lambda row: get_mod_indices(row[mod_peptide_col], protein_start=row[protein_start_col], regex=mod_regex), axis=1, result_type='expand')

    df = get_localization_scores(df, 
                                 protein_start_col = protein_start_col,
                                 localization_score_regex = localization_score_regex,
                                 ptm_cols = ptm_cols,
                                 in_place=False)

    df = filter_mods(df,
            target_mods=target_mods, 
            keep_only_target_mods=True,
            filter_individual_site='any',
            score_threshold=score_threshold,
            in_place=False)
    
    df = join_protein_mod_loc(df,
                     protein_col=protein_col,
                     index_col ='mod_index',
                     aa_col = 'mod_aa',
                     score_col = 'loc_score',
                     mod_col = 'mod',
                     protein_mod_col = 'ProteinName_Mod',
                     include_mod = False,
                     include_score = False,
                     in_place=False)
    
    if output_path:
        df.to_csv(output_path, index=False)

    return df
