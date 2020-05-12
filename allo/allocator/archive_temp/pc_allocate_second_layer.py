import datetime
import numpy as np
import pandas as pd
import rebalance.pc_allocate as alloc
from rebalance.pc_helper import set_default
from functools import reduce

import cxtpy
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

sharpe = cxtpy.metrics_functions.sharpe
vol = cxtpy.metrics_functions.volatility
maxdd = cxtpy.metrics_functions.max_drawdown_2

def single_cluster(data_df, a1, a2, **kwargs):
    cluster_df = pd.DataFrame(dict(name = data_df.names.values))
    cluster_df["cluster"] = "c_1"
    return cluster_df

def knn_cluster(data_df, a1, a2, **kwargs):
    # pre-defined parameters
    top_n_pca_features = kwargs.get("top_n_pca_features")
    n_cluster = kwargs.get("n_cluster")        
    
    # Set default for kwargs
    top_n_pca_features = set_default(top_n_pca_features, 20)
    n_cluster = set_default(n_cluster, 10)
    
    # merge returns
    df_list = [d.loc[a1:a2] for d in data_df.df.values]
    strategy_list = data_df.names.values
    
    fdf = reduce(lambda x, y: pd.merge(x, y, on = 'Date', how = "outer"), df_list)
    fdf = fdf.loc[:, strategy_list] ## may break if strategy_list name is different
    
    fdf = fdf.sort_index() #.loc[a1:a2]
    fdf = fdf.fillna(0)
    
    # create features
    maxdd_df = fdf.resample("45d").apply(lambda x: maxdd(x))
    mean_df = fdf.resample("45d").apply(lambda x: np.mean(x)).fillna(0)
    std_df = fdf.resample("45d").apply(lambda x: np.std(x)).fillna(0)
    ff = pd.concat([maxdd_df.T, mean_df.T, std_df.T], axis = 1)
    names = ff.reset_index()["index"]
    
    # compress the features using PCA 
    pca = PCA()
    pca.fit(ff.values)
    features = pca.fit_transform(ff.values)
    features_kmean = features[:, 0:top_n_pca_features]
    
    try:
        km = KMeans(n_clusters = n_cluster, random_state = 123)
        km.fit(features_kmean)
    except: 
        k = int(0.7*len(strategy_list))
        print("knn n_clusters > n_sample. Changing n_clusters to 70% of n_sample: {}".format(k))
        km = KMeans(n_clusters = k, random_state = 123)
        km.fit(features_kmean)
    
    cluster = km.predict(features_kmean)
    
    # create final cluster df
    cluster_df = pd.DataFrame(dict(x = features[:, 0], y = features[:, 1], name = strategy_list, name2 = names))
    cluster_df["cluster"] = ["c_" + str(j) for j in cluster]
    
    #output cluster_df 
#     print(cluster_df)
    return cluster_df


def two_layer_weight(data_df, a1, a2, cluster_df, allocation_method):
    fcdf = pd.merge(data_df, cluster_df, left_on = "names", right_on = "name")
    
    cluster_names = fcdf.cluster.unique()
    cluster_df_list = [fcdf[fcdf.cluster == j].copy() for j in cluster_names]
    
    # define weights for each cluster (inter-cluster weight)
    ## assume equal for now
    n_clusters = len(cluster_df_list)
    weight_clusters = {c:1/n_clusters for c in cluster_names}
    
    weight_df_list = []
    # compute weights for strategies in each cluster (intra-cluster weight)
    for c in cluster_df_list:
        cdf = c.copy()
        if allocation_method == "risk parity":
            sd_list = []
            for df, strategy_list in zip(cdf.df.values, cdf.name.values):
                rdf = df.loc[a1:a2]
                sd = rdf.std()[0]
                sd_list.append(sd)
            w = alloc.risk_parity(sd_list, upperbound = 1)
            cdf["weight_intra"] = w
        else:
            # assume equal weight
            n = cdf.shape[0]
            cdf["weight_intra"] = 1/float(n)
#             print(cdf[["weight_intra", "name", "cluster"]])
            
        weight_df_list.append(cdf)
    wdf = pd.concat(weight_df_list)
    wdf["weight_inter"] = wdf["cluster"].replace(weight_clusters)
    wdf["weight"] = wdf["weight_inter"]*wdf["weight_intra"] 
    w = {name:weight for name, weight in zip(wdf["name"], wdf["weight"])}
    return w, wdf