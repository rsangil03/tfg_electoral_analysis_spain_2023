import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.colors as mcolors

from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans, AgglomerativeClustering, DBSCAN, SpectralClustering
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score
import torch

from src.config import *

from src.DEC import DEC

def preprocess_data(gdf, variables, handle_nans='drop'):
    """
    Preprocess data for clustering.
    handle_nans: 'impute' (median) or 'drop'
    """
    df_cluster = gdf[variables].copy()
    
    # Handle NaNs
    if handle_nans == 'drop':
        # Drop rows with any NaNs in the selected variables
        valid_idx = df_cluster.dropna().index
        df_cluster = df_cluster.loc[valid_idx]
        gdf_filtered = gdf.loc[valid_idx].copy()
    else:
        # Impute with median
        imputer = SimpleImputer(strategy='median')
        df_cluster = pd.DataFrame(imputer.fit_transform(df_cluster), columns=variables, index=df_cluster.index)
        gdf_filtered = gdf.copy()
        
    # Standard Scaler
    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(df_cluster)
    
    return scaled_data, gdf_filtered

def reduce_dimensions(scaled_data, n_components=2):
    pca = PCA(n_components=n_components)
    return pca.fit_transform(scaled_data)

def evaluate_clusters(data, labels):
    # Only evaluate if we have more than 1 cluster and noise is not all there is
    unique_labels = np.unique(labels)
    valid_labels = unique_labels[unique_labels != -1]
    
    if len(valid_labels) < 2:
        return {'silhouette': None, 'davies_bouldin': None, 'calinski_harabasz': None}
    
    # Exclude noise points (-1) for evaluation
    mask = labels != -1
    if len(np.unique(labels[mask])) < 2:
         return {'silhouette': None, 'davies_bouldin': None, 'calinski_harabasz': None}

    eval_data = data[mask]
    eval_labels = labels[mask]
    
    sil = silhouette_score(eval_data, eval_labels)
    db = davies_bouldin_score(eval_data, eval_labels)
    ch = calinski_harabasz_score(eval_data, eval_labels)
    
    return {
        'silhouette': sil,
        'davies_bouldin': db,
        'calinski_harabasz': ch
    }

def compute_centroids(scaled_data, labels, variables):
    """
    Compute the centroid (mean) of each cluster in the scaled feature space.
    Noise points (label == -1, from DBSCAN) are excluded.
    
    Returns a DataFrame of shape (n_clusters, n_variables) indexed by cluster label.
    """
    df = pd.DataFrame(scaled_data, columns=variables)
    df['cluster'] = labels
    centroids = (
        df[df['cluster'] != -1]
        .groupby('cluster')[variables]
        .mean()
    )
    return centroids

def perform_clustering(gdf, variables=None, algorithm='kmeans', handle_nans='drop', 
                       apply_pca=False, pca_components=2, **kwargs):
    if variables is None:
        variables = V_CLUSTERING_BASE
        
    # Filter to numeric columns only just in case non-numeric variables like CCAA code are passed
    numeric_vars = []
    for v in variables:
        if v in gdf.columns and pd.api.types.is_numeric_dtype(gdf[v]):
            numeric_vars.append(v)
    variables = numeric_vars

    scaled_data, gdf_filtered = preprocess_data(gdf, variables, handle_nans)
    
    clustering_data = scaled_data

    # Always keep a reference to the pre-PCA data for metric evaluation and centroids
    eval_data = scaled_data
    
    if apply_pca:
        clustering_data = reduce_dimensions(clustering_data, n_components=pca_components)
        
    if algorithm == 'kmeans':
        n_clusters = kwargs.get('n_clusters', 3)
        random_state = kwargs.get('random_state', 42)
        n_init = kwargs.get('n_init', 20)
        model = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=n_init)
        labels = model.fit_predict(clustering_data)
    elif algorithm == 'spectral':
        n_clusters = kwargs.get('n_clusters', 3)
        random_state = kwargs.get('random_state', 42)
        model = SpectralClustering(n_clusters=n_clusters, random_state=random_state, affinity='nearest_neighbors')
        labels = model.fit_predict(clustering_data)
    elif algorithm == 'hierarchical':
        n_clusters = kwargs.get('n_clusters', 3)
        model = AgglomerativeClustering(n_clusters=n_clusters)
        labels = model.fit_predict(clustering_data)
    elif algorithm == 'dbscan':
        eps = kwargs.get('eps', 0.5)
        min_samples = kwargs.get('min_samples', 5)
        model = DBSCAN(eps=eps, min_samples=min_samples)
        labels = model.fit_predict(clustering_data)
    elif algorithm == 'gaussian':
        n_components = kwargs.get('n_clusters', 3) # Using n_clusters for consistency
        random_state = kwargs.get('random_state', 42)
        model = GaussianMixture(n_components=n_components, random_state=random_state)
        labels = model.fit_predict(clustering_data)
    elif algorithm == 'autoencoder':
        embedding_dim = kwargs.get('embedding_dim', 8)
        epochs = kwargs.get('epochs', 100)
        tol = kwargs.get('tol', 0.001)
        n_clusters = kwargs.get('n_clusters', 3)
        random_state = kwargs.get('random_state', 42)
        model = DEC(n_clusters=n_clusters, input_dim=len(variables), embedding_dim=embedding_dim)
        labels = model.fit_predict(clustering_data, epochs=epochs, tol=tol, random_state=random_state)
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")
        
    gdf_filtered['cluster'] = labels
    
    # Calculate evaluation metrics on the pre-PCA scaled data
    metrics = evaluate_clusters(eval_data, labels)
    print(f"Clustering Metrics for {algorithm}" + (f" with PCA of {pca_components}" if apply_pca else "") + ":")
    print(f"  Silhouette Score: {metrics['silhouette']}")
    print(f"  Davies-Bouldin Index: {metrics['davies_bouldin']}")
    print(f"  Calinski-Harabasz Index: {metrics['calinski_harabasz']}")

    # Compute centroids in the original scaled feature space (pre-PCA)
    centroids = compute_centroids(eval_data, labels, variables)
    print(f"\nCluster Centroids (scaled feature space):")
    print(centroids.to_string())
    
    return gdf_filtered, metrics, centroids

def plot_cluster_map(gdf, cluster_col='cluster', title='Clustering Map', 
                     cmap='Accent', ax=None, legend_title='Cluster'):
    """
    Plots a map of Spain colored by cluster with insets for Canarias, Ceuta, and Melilla.
    """
    import matplotlib.patches as mpatches
    
    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
    else:
        fig = ax.figure

    gdf = gdf.copy()
    
    # Treat cluster as categorical string to enforce discrete colors
    gdf[cluster_col] = gdf[cluster_col].astype(str)
    unique_clusters = sorted(gdf[cluster_col].dropna().unique())
    colormap_obj = plt.colormaps.get_cmap(cmap)
    
    # Generate discrete colors for the entire map
    color_dict = {}
    for i, c in enumerate(unique_clusters):
        if hasattr(colormap_obj, 'colors'):
            color_dict[str(c)] = mcolors.to_hex(colormap_obj.colors[i % len(colormap_obj.colors)])
        else:
            color_dict[str(c)] = mcolors.to_hex(colormap_obj(i / max(1, len(unique_clusters)-1)))
            
    gdf['plot_color'] = gdf[cluster_col].map(lambda x: color_dict.get(str(x), 'lightgrey'))
    
    gdf_main = gdf[~gdf[V_CCAA].isin([C_CCAA_CANARIAS, C_CCAA_CEUTA, C_CCAA_MELILLA])]
    gdf_canarias = gdf[gdf[V_CCAA] == C_CCAA_CANARIAS]
    gdf_ceuta = gdf[gdf[V_CCAA] == C_CCAA_CEUTA]
    gdf_melilla = gdf[gdf[V_CCAA] == C_CCAA_MELILLA]

    if not gdf_main.empty:
        gdf_main.plot(
            color=gdf_main['plot_color'],
            linewidth=0,
            ax=ax
        )
        
    # Create custom legend
    handles = [mpatches.Patch(color=color_dict[str(c)], label=str(c)) for c in unique_clusters]
    handles.append(mpatches.Patch(color='lightgrey', label='No Data'))
    ax.legend(handles=handles, title=legend_title, loc='lower right')

    if title:
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)

    # Expand borders to make room for insets
    if not gdf_main.empty:
        minx, miny, maxx, maxy = gdf_main.total_bounds
        width, height = maxx - minx, maxy - miny
        ax.set_xlim(minx - (width * 0.35), maxx)
    ax.set_axis_off()

    # Create Inset Axes
    ax_canarias = fig.add_axes([0.15, 0.15, 0.25, 0.2]) 
    ax_ceuta = fig.add_axes([0.25, 0.4, 0.05, 0.05])    
    ax_melilla = fig.add_axes([0.25, 0.5, 0.05, 0.05])   

    insets = [
        (gdf_canarias, ax_canarias, "Canarias", 12),
        (gdf_ceuta, ax_ceuta, "Ceuta", 10),
        (gdf_melilla, ax_melilla, "Melilla", 10)
    ]

    for data, inset_ax, label, f_size in insets:
        if not data.empty:
            data.plot(
                color=data['plot_color'],
                linewidth=0,
                ax=inset_ax,
                edgecolor='none'
            )
            
            i_minx, i_miny, i_maxx, i_maxy = data.total_bounds
            x_buff = (i_maxx - i_minx) * 0.1
            y_buff = (i_maxy - i_miny) * 0.1
            inset_ax.set_xlim(i_minx - x_buff, i_maxx + x_buff)
            inset_ax.set_ylim(i_miny - y_buff, i_maxy + y_buff)
        
        inset_ax.set_facecolor('white') 
        for spine in inset_ax.spines.values():
            spine.set_visible(True)          
            spine.set_edgecolor('#cccccc')    
            spine.set_linewidth(0.8)         
        
        inset_ax.set_xticks([])
        inset_ax.set_yticks([])
        inset_ax.set_title(label, fontsize=f_size, pad=5, color='#333333')

    return fig, ax

def plot_cluster_scatter(gdf, x, y, cluster_col='cluster', title=None, 
                         cmap='Accent', alpha=0.5, ax=None):
    """
    Plots a scatterplot of two variables colored by cluster.
    """
    sns.set_theme(style="white")

    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 6))
        
    gdf_copy = gdf.copy()
    gdf_copy[cluster_col] = gdf_copy[cluster_col].astype(str)
    
    # Sort for consistent hue ordering
    unique_clusters = sorted(gdf_copy[cluster_col].unique())
    
    sns.scatterplot(data=gdf_copy, x=x, y=y, hue=cluster_col, palette=cmap, 
                    hue_order=unique_clusters, alpha=alpha, s=40, edgecolor=None, ax=ax)
    
    if title:
        ax.set_title(title)
        
    sns.despine()
    
    return ax

if __name__ == "__main__":
    print("Clustering module loaded successfully.")
    print(f"PyTorch available: {torch.__version__}, CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA device: {torch.cuda.get_device_name(0)}")
        print(f"CUDA version: {torch.version.cuda}")
