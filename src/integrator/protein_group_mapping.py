# Enhanced mapping utility for protein group names and protein names with isoform handling
import re

def map_protein_group_to_protein(df, group_col='protein_group_name', protein_col='protein_name', verbose=True):
    """
    Map protein_group_name to protein_name 1:1, but if the base (before '-') of group names are the same,
    allow mapping to the same protein name (isoforms). Warn if there are mismatches.
    Handles mismatched splits by mapping all group names to a single protein if only one protein is present, otherwise skips or warns.
    Returns a dictionary mapping group name to protein name, and a set of ambiguous bases.
    """
    mapping = {}
    base_to_names = {}
    ambiguous_bases = set()
    import re
    for idx, row in df.iterrows():
        groups = str(row[group_col]).split(';')
        proteins = str(row[protein_col]).split(';')
        if len(groups) != len(proteins):
            if len(proteins) == 1:
                # Map all group names to the single protein name
                for g in groups:
                    g = g.strip()
                    p = proteins[0].strip()
                    base = re.split(r'-', g)[0]
                    if base not in base_to_names:
                        base_to_names[base] = set()
                    base_to_names[base].add(p)
                    mapping[g] = p
                if verbose:
                    print(f"Row {idx}: mapped {groups} to single protein {proteins[0]}")
            else:
                if verbose:
                    print(f"Row {idx}: Skipped mismatched entries: {groups} vs {proteins}")
                continue
        else:
            for g, p in zip(groups, proteins):
                g = g.strip()
                p = p.strip()
                base = re.split(r'-', g)[0]
                if base not in base_to_names:
                    base_to_names[base] = set()
                base_to_names[base].add(p)
                mapping[g] = p
    # Find ambiguous bases (map to >1 protein name)
    for base, names in base_to_names.items():
        if len(names) > 1:
            ambiguous_bases.add(base)
    return mapping, ambiguous_bases

# Example usage:
# mapping, ambiguous = map_protein_group_to_protein_isoform(test, 'protein_group_name', 'protein_name')
# print(mapping)
# print('Ambiguous bases:', ambiguous)
