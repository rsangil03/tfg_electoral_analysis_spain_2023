import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.cluster import KMeans
import numpy as np

class Autoencoder(nn.Module):
    """
    Stacked Autoencoder for feature representation.
    Network dimensions: d-16-16-32-m where d is input_dim and m is embedding_dim.
    ReLU activations are used for all layers except the final encoder and decoder layers.
    """
    def __init__(self, input_dim, embedding_dim):
        super(Autoencoder, self).__init__()
        
        # Encoder
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 16),
            nn.ReLU(),
            nn.Linear(16, 16),
            nn.ReLU(),
            nn.Linear(16, 32),
            nn.ReLU(),
            # No ReLU on the final encoder layer so the embedding retains full information
            nn.Linear(32, embedding_dim) 
        )
        
        # Decoder
        self.decoder = nn.Sequential(
            nn.Linear(embedding_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, input_dim),
            nn.ReLU(),
            # No ReLU on the final decoder layer to reconstruct input data (e.g., zero-mean images)
            nn.Linear(input_dim, input_dim) 
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
        
    def forward(self, x):
        z = self.autoencoder.encoder(x)
        q = self.clustering(z)
        return q, z

class DEC:

    def __init__(self, n_clusters, input_dim, embedding_dim=2):
        self.n_clusters = n_clusters
        self.input_dim = input_dim
        self.hidden_dim = embedding_dim
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = DECModel(n_clusters, input_dim, embedding_dim).to(self.device)

    def __target_distribution(self, q):
        """
        Computes the auxiliary target distribution p_ij.
        """
        # p_ij = (q_ij^2 / f_j) / sum_j' (q_ij'^2 / f_j')
        weight = q ** 2 / q.sum(0)
        return (weight.t() / weight.sum(1)).t()
    
    def __preprocess_data(self, X):
        # Move your entire raw data tensor to the GPU upfront
        X_tensor = torch.Tensor(X) # Ensure it's a PyTorch tensor
        X_tensor = X_tensor.to(self.device)

        # Create the dataset and dataloader using the GPU-resident tensor
        dataset = torch.utils.data.TensorDataset(X_tensor)
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=256, shuffle=True)

        return dataloader, X_tensor
    
    def __pretrain_autoencoder(self, dataloader, epochs):
        '''
        Pre-trains the autoencoder to learn a good feature representation before clustering.
        '''
        self.model.train()

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

    def __initialize_centroids(self, dataloader):
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
        
        kmeans = KMeans(n_clusters=self.n_clusters, n_init=20)
        kmeans.fit(features)
        self.model.clustering.centroids.data = torch.tensor(kmeans.cluster_centers_).to(self.device)

    def __optimize_clustering(self, dataloader, X_tensor, epochs, tol):
        '''
        Optimizes the clustering by minimizing KL divergence between soft assignments and target distribution.
        '''
        optimizer_dec = optim.SGD(self.model.parameters(), lr=0.01, momentum=0.9)
        kl_loss = nn.KLDivLoss(reduction='batchmean')

        old_labels = None
        
        for epoch in range(epochs*5):
            # Early Stopping Evaluation ---
            new_labels = self.__predict(X_tensor)

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
                q, _ = self.model(x)
                p = self.__target_distribution(q).detach()
                
                loss = kl_loss(q.log(), p)
                
                optimizer_dec.zero_grad()
                loss.backward()
                optimizer_dec.step()

    def __predict(self, X_tensor):
        self.model.eval()
        with torch.no_grad():
            q, _ = self.model(X_tensor)
            return torch.argmax(q, dim=1).cpu().numpy()

    def predict(self, X):
        """Public method to predict clusters for new data."""
        # Convert raw input to a tensor on the correct device
        X_tensor = torch.tensor(X, dtype=torch.float32).to(self.device)
        return self.__predict(X_tensor)

    def fit_predict(self, X, **kwargs):

        epochs = kwargs.get('epochs', 100)

        tol = kwargs.get('tol', 0.001)

        dataloader, X_tensor =self.__preprocess_data(X)

        self.__pretrain_autoencoder(dataloader, epochs)
                
        self.__initialize_centroids(dataloader)
        
        self.__optimize_clustering(dataloader, X_tensor, epochs, tol)
        
        return self.__predict(X_tensor)