import numpy as np

default_filters = {'precursor': 
                   {'Q.Value': (0.01, 'max'),
                    'Lib.Q.Value': (0.01, 'max'),
                    'Precursor.MaxLFQ': (0, min)
                    },
                    'protein': 
                    {'PG.Q.Value': (0.05, 'max'),
                     'PG.Q.Value': (0.05, 'max'),
                     'PG.MaxLFQ': (0, min)
                     }
}

def filter_mask(ad, filter_name = 'mask', strict=False, layer_threshold={'Q.Value': (0.01, 'max'),'PG.Q.Value': (0.05, 'max'), 'Lib.Q.Value': (0.01, 'max'), 'Lib.PG.Q.Value': (0.05, 'max')}):
    """Create a mask layer that can be applied and checks that values satisfy all the given thresholds"""
    mask_list = []
    for layer, threshold in layer_threshold.items():
        mask = None
        layer_exists = layer in ad.layers

        if not layer_exists:
            if strict:
                raise ValueError(f"Layer '{layer}' not found in AnnData layers.")
            else:
                print(f"Warning: Layer '{layer}' not found in AnnData layers. Skipping this threshold.")
                continue
        
        #TODO: print number of filterd values. make sure to distinguish between not idnetiifed in the first place vs filterd out
        if threshold[1] == 'max':
            mask = (ad.layers[layer] <= threshold[0])
            mask_list.append(mask)
        elif threshold[1] == 'min':
            mask = (ad.layers[layer] >= threshold[0])
            mask_list.append(mask)
        elif threshold[1] == 'equal':
            mask = (ad.layers[layer] == threshold[0])
            mask_list.append(mask)
    
    ad.layers[filter_name] = np.logical_and.reduce(mask_list)