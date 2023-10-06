import torch
import torch.nn as nn
import numpy as np

from Modules.Layers.ResidualBlock import ResidualBlock

class BuildResidualDecoder(nn.Module):
    
    '''
    Builds a convolutional neural network (CNN) with residual units
    that deconvolves a latent vector into an image.
    
    Args:
        latent_dim:     integer dimensionality of latent space
        init_shape:     integer list/tuple with initial image shape
        layers:         list of integer layer sizes
        num_res_blocks: integer number of residual blocks
        activation:     instantiated activation function
        use_batchnorm:  boolean for batchnorm usage
    
    Inputs:
        batch: torch float tensor of input images
    
    Returns:
        batch: torch float tensor of output images
    '''
    
    def __init__(self, 
                 latent_dim,
                 init_shape,
                 layers, 
                 num_res_blocks=2,
                 activation=None, 
                 use_batchnorm=True,
                 use_preactivations=True):
        
        super().__init__()
        self.latent_dim = latent_dim
        self.init_shape = init_shape # (channels, height, width)
        self.input_channels = init_shape[0]
        self.layers = layers
        self.num_res_blocks = num_res_blocks
        self.activation = activation if activation is not None else nn.ReLU()
        self.use_batchnorm = use_batchnorm
        self.use_preactivations = use_preactivations
        
        # first convert the latent vector to initial image
        self.init_linear = nn.Linear(
            in_features=latent_dim, 
            out_features=np.prod(init_shape),
            bias=True)
        
        # list of operations in the model
        operations = []
        
        # pre-process initial image with conv layers
        operations.append(nn.Conv2d(
            in_channels=self.input_channels,
            out_channels=self.layers[0],
            kernel_size=3,
            stride=1,
            padding=1))
        if self.use_batchnorm:
            operations.append(nn.BatchNorm2d(num_features=self.layers[0]))
        operations.append(self.activation)
        operations.append(nn.Conv2d(
            in_channels=self.layers[0],
            out_channels=self.layers[0],
            kernel_size=3,
            stride=1,
            padding=1))
        if self.use_batchnorm:
            operations.append(nn.BatchNorm2d(num_features=self.layers[0]))
        operations.append(self.activation)
        self.input_channels = self.layers[0]
        
        # loop over blocks
        for i, layer in enumerate(layers): 
            
            # downsample
            operations.append(nn.Conv2d(
                in_channels=self.input_channels,
                out_channels=layer,
                kernel_size=2,
                stride=2,
                padding=0))
            
            # apply residual blocks
            for j in range(self.num_res_blocks):
                
                # add res block 
                operations.append(ResidualBlock(
                    features=layer, 
                    activation=self.activation,
                    use_batchnorm=self.use_batchnorm,
                    use_preactivation=self.use_preactivations))
                
            # update book keeping
            self.input_channels = layer
            
        # output linear layer for latent space
        operations.append(nn.Conv2d(
            in_channels=self.input_channels,
            out_channels=self.latent_dim,
            kernel_size=int(self.init_shape[1] / 2**len(self.layers)),
            stride=1,
            padding=0))
                    
        # convert list to sequential model
        self.model = nn.Sequential(*operations)
        
    def forward(self, batch):
        
        # convert latent vector to initial image
        batch = self.init_linear(batch).view(self.init_shape)
        
        # run the model and squeeze
        batch = self.model(batch).view(len(batch), -1)
        
        return batch
