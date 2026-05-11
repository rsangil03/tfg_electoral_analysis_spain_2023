import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.cluster import KMeans
import numpy as np

# Deep Embedded Clustering (DEC) implementation in PyTorch
# This implementation is inspired by the original DEC paper (Xie et al., 2016) and 
# on the Improved DEC paper (Guo et al., 2017), but has been simplified and
# adapted for our specific use case of clustering Spanish municipalities based on socio-demographic and electoral data.

class Autoencoder(nn.Module):
    """
    Stacked Autoencoder for feature representation.
    Network dimensions: d-16-16-m where d is input_dim and m is embedding_dim.
    ReLU activations are used for all layers except the final encoder and decoder layers.
    """
    def __init__(self, input_dim, embedding_dim):
        super(Autoencoder, self).__init__()
        
        # Encoder
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 16),
            nn.ReLU(),
            nn.Linear(16, embedding_dim)
            # No ReLU on the final encoder layer so the embedding retains full information
        )
        
        # Decoder
        self.decoder = nn.Sequential(
            nn.Linear(embedding_dim, 16),
            nn.ReLU(),
            nn.Linear(16, input_dim),
            nn.ReLU(),
            nn.Linear(input_dim, input_dim) 
            # No ReLU on the final decoder layer to reconstruct input data
        )

    def forward(self, x):
        z = self.encoder(x)
        x_recon = self.decoder(z)
        return z, x_recon

class ClusteringLayer(nn.Module):
    """
    Computes the soft assignment between embedded points and cluster centroids.
    """
    def __init__(self, n_clusters, embedding_dim, alpha=1.0):
        super(ClusteringLayer, self).__init__()
        self.n_clusters = n_clusters
        self.alpha = alpha
        self.centroids = nn.Parameter(torch.Tensor(n_clusters, embedding_dim))
        
    def forward(self, z):
        # Calculate the Student's t-distribution kernel
        # q_ij = (1 + ||z_i - u_j||^2 / alpha)^(-(alpha+1)/2) / sum(...)
        # alpha is set to 1
        dist = torch.cdist(z, self.centroids, p=2) ** 2
        q = 1.0 / (1.0 + dist / self.alpha)
        q = q ** ((self.alpha + 1.0) / 2.0)
        q = q / torch.sum(q, dim=1, keepdim=True)
        return q

class DECModel(nn.Module):
    def __init__(self, n_clusters, input_dim, embedding_dim):
        super(DECModel, self).__init__()
        self.autoencoder = Autoencoder(input_dim, embedding_dim)
        self.clustering = ClusteringLayer(n_clusters, embedding_dim)
        self._initialize_weights()

    def _initialize_weights(self, random_state=42):
        torch.manual_seed(random_state)
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_normal_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
        
    def forward(self, x):
        z, x_recon = self.autoencoder(x)
        q = self.clustering(z)
        return q, x_recon

class DEC:

    def __init__(self, n_clusters, input_dim, embedding_dim=8):
        self.n_clusters = n_clusters
        self.input_dim = input_dim
        self.hidden_dim = embedding_dim
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = DECModel(n_clusters, input_dim, embedding_dim).to(self.device)

    def _target_distribution(self, q):
        """
        Computes the auxiliary target distribution p_ij.
        """
        # p_ij = (q_ij^2 / f_j) / sum_j' (q_ij'^2 / f_j')
        weight = q ** 2 / q.sum(0)
        return (weight.t() / weight.sum(1)).t()
    
    def _preprocess_data(self, X, random_state=42):
        # Move your entire raw data tensor to the GPU upfront
        X_tensor = torch.Tensor(X) # Ensure it's a PyTorch tensor
        X_tensor = X_tensor.to(self.device)

        # Create an array of indices [0, 1, 2, ..., N-1]
        indices = torch.arange(X_tensor.size(0)).to(self.device)

        # Create the dataset and dataloader using the GPU-resident tensor
        dataset = torch.utils.data.TensorDataset(X_tensor, indices)
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=256, shuffle=True, generator=torch.manual_seed(random_state))

        return dataloader, X_tensor
    
    def _pretrain_autoencoder(self, dataloader, epochs, random_state):
        '''
        Pre-trains the autoencoder to learn a good feature representation before clustering.
        '''
        self.model.train()
        self.model._initialize_weights(random_state) # Re-initialize weights for reproducibility

        optimizer_ae = optim.SGD(self.model.autoencoder.parameters(), lr=0.1, momentum=0.9)
        mse_loss = nn.MSELoss()
        
        for epoch in range(epochs): # Simplified pre-training loop
            for batch in dataloader:
                x = batch[0]
                _, x_recon = self.model.autoencoder(x)
                loss = mse_loss(x_recon, x)
                
                optimizer_ae.zero_grad()
                loss.backward()
                optimizer_ae.step()

    def _initialize_centroids(self, dataloader, random_state):
        '''
        Initializes cluster centroids using K-Means on the embedded features.
        '''
        self.model.eval()

        features = []
        with torch.no_grad():
            for batch in dataloader:
                x = batch[0]
                z = self.model.autoencoder.encoder(x)
                features.append(z.cpu().numpy())
        features = np.vstack(features)
        
        kmeans = KMeans(n_clusters=self.n_clusters, n_init=20, random_state=random_state)
        kmeans.fit(features)
        self.model.clustering.centroids.data = torch.tensor(kmeans.cluster_centers_).to(self.device)

    def _optimize_clustering(self, dataloader, X_tensor, epochs, tol):
        '''
        Optimizes the clustering by minimizing KL divergence between soft assignments and target distribution.
        '''
        optimizer_dec = optim.SGD(self.model.parameters(), lr=0.01, momentum=0.9)
        kl_loss = nn.KLDivLoss(reduction='batchmean')
        mse_loss = nn.MSELoss()

        old_labels = None
        
        for epoch in range(epochs*5):

            self.model.eval() # Switch to evaluation mode to compute soft assignments and target distribution
            with torch.no_grad():
                # Get soft assignments (q) for the ENTIRE dataset at once
                q_global, _ = self.model(X_tensor)
                new_labels = torch.argmax(q_global, dim=1).cpu().numpy()
                
                # Calculate the target distribution (p) globally and hold it constant for this epoch
                p_global = self._target_distribution(q_global).detach()

            if old_labels is not None:
                # Calculate the fraction of points that changed clusters
                delta = np.mean(new_labels != old_labels)
                if delta < tol:
                    print(f"Early stopping at epoch {epoch}: Label change delta ({delta:.5f}) is below tolerance ({tol}).")
                    break
                    
            old_labels = new_labels

            self.model.train() # Switch back to training mode

            for batch in dataloader:            
                x = batch[0]
                idx = batch[1] # Get the corresponding indices for this batch
                q, x_recon = self.model(x)

                p = p_global[idx] # Get the corresponding target distribution for this batch
                
                loss = mse_loss(x_recon, x) + kl_loss(q.log(), p)
                
                optimizer_dec.zero_grad()
                loss.backward()
                optimizer_dec.step()

    def _predict(self, X_tensor):
        self.model.eval()
        with torch.no_grad():
            q, _ = self.model(X_tensor)
            return torch.argmax(q, dim=1).cpu().numpy()

    def predict(self, X):
        """Public method to predict clusters for new data."""
        # Convert raw input to a tensor on the correct device
        X_tensor = torch.tensor(X, dtype=torch.float32).to(self.device)
        return self._predict(X_tensor)

    def fit_predict(self, X, **kwargs):

        epochs = kwargs.get('epochs', 100)

        tol = kwargs.get('tol', 0.001)

        random_state = kwargs.get('random_state', 42)

        dataloader, X_tensor = self._preprocess_data(X, random_state)

        self._pretrain_autoencoder(dataloader, epochs, random_state)
                
        self._initialize_centroids(dataloader, random_state)
        
        self._optimize_clustering(dataloader, X_tensor, epochs, tol)
        
        return self._predict(X_tensor)