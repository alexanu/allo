import six
import datetime
import numpy as np
import pandas as pd 
from dateutil.relativedelta import relativedelta


def trpei():
    """Load TRPEI target returns data
    """
    df = pd.read_csv("data_parser/_TRPEI.csv")
    df.columns = ["Year"] + [j+1 for j in range(12)] + ["Temp"]
    df = df.drop(["Temp"], axis = 1)
    df.set_index("Year", inplace = True)

    first_year = int(df.index[0])
    target_ret_dict = {}
    for i in range(df.shape[0]):
        for j in range(df.shape[1]):
            dt = datetime.datetime(first_year + i, 1+j, 1) + relativedelta(months = 1) - datetime.timedelta(days = 1) 
            raw_val = df.iloc[i,j]
            if not df.isna().iloc[i,j]:
                ret = float(raw_val.replace("%", ""))/100
                target_ret_dict[dt] = ret
    tdf = pd.Series(target_ret_dict)
    tdf = pd.DataFrame(tdf)
    tdf.columns = ["TRPEI"]

    return target_ret_dict, tdf


def get(identifier):
    """Get the `identifier` allocation function.
    # Arguments
        identifier: None or str, name of the function.
    # Returns
        The allocation function, `CRP` if `identifier` is None.
    # Raises
        ValueError if unknown identifier
    """
    if identifier is None:
        raise Exception(f"Cannot find {identifier} in parser.load_parse")
    if isinstance(identifier, six.string_types):
        identifier = str(identifier)
        return globals().get(identifier)
    elif callable(identifier):
        # if isinstance(identifier, Layer):
        #     warnings.warn(
        #         'Do not pass a layer instance (such as {identifier}) as the '
        #         'activation argument of another layer. Instead, advanced '
        #         'activation layers should be used just like any other '
        #         'layer in a model.'.format(
        #             identifier=identifier.__class__.__name__))
        return identifier
    else:
        raise ValueError('Could not interpret '
                         'parser.load_parse function identifier:', identifier)