#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 14 18:49:00 2018

@author: manoj
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 10 13:04:34 2018

@author: manoj
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from torch.nn import Parameter
import torch.nn.init as init


#from .lang_new import QuestionEmbedding,WordEmbedding


class NeuralAccumulatorCell(nn.Module):
    """A Neural Accumulator (NAC) cell [1].
    Attributes:
        in_dim: size of the input sample.
        out_dim: size of the output sample.
    Sources:
        [1]: https://arxiv.org/abs/1808.00508
    """
    def __init__(self, in_dim, out_dim):
        super().__init__()
        self.in_dim = in_dim
        self.out_dim = out_dim

        self.W_hat = Parameter(torch.Tensor(self.out_dim, self.in_dim))
        self.M_hat = Parameter(torch.Tensor(self.out_dim, self.in_dim))
        self.W = Parameter(torch.tanh(self.W_hat) * torch.sigmoid(self.M_hat))
        self.register_parameter('bias', None)
        init.kaiming_uniform_(self.W_hat, a=np.sqrt(5))
        init.kaiming_uniform_(self.M_hat, a=np.sqrt(5))

    def forward(self, input):
        return F.linear(input, self.W, self.bias)

    def extra_repr(self):
        return 'in_dim={}, out_dim={}'.format(
            self.in_dim, self.out_dim
        )


class NAC(nn.Module):
    """A stack of NAC layers.
    Attributes:
        num_layers: the number of NAC layers.
        in_dim: the size of the input sample.
        hidden_dim: the size of the hidden layers.
        out_dim: the size of the output.
    """
    def __init__(self, num_layers, in_dim, hidden_dim, out_dim):
        super().__init__()
        self.num_layers = num_layers
        self.in_dim = in_dim
        self.hidden_dim = hidden_dim
        self.out_dim = out_dim

        layers = []
        for i in range(num_layers):
            layers.append(
                NeuralAccumulatorCell(
                    hidden_dim if i > 0 else in_dim,
                    hidden_dim if i < num_layers - 1 else out_dim,
                )
            )
        self.model = nn.Sequential(*layers)

    def forward(self, x):
        out = self.model(x)
        return out




class RN(nn.Module):
    def __init__(self,Ncls):
        super().__init__()

        I_CNN = 2048
        Q_GRU_out = 1024
        Q_embedding = 300
        self.Ncls = Ncls
        self.QRNN = nn.GRU(Q_embedding,Q_GRU_out,num_layers=1,bidirectional=False)        
        self.lin1 = nn.Linear(in_features = I_CNN + Q_GRU_out , out_features=1)
        NUM_LAYERS = 2
        HIDDEN_DIM = 100
        OUT_DIM = 1
        
        self.nac = NAC(
            num_layers=NUM_LAYERS,
            in_dim= 100,
            hidden_dim= HIDDEN_DIM,
            out_dim= OUT_DIM,
        )
        

    def forward(self,wholefeat,pooled,box_feats,q_feats,box_coords,index):


        enc2,_ = self.QRNN(q_feats.permute(1,0,2))
        q_rnn = enc2[-1]
        
        b,d,k = box_feats.size()
        qst  =  q_rnn.unsqueeze(1)
        qst = qst.repeat(1, d, 1)        
        b_full = torch.cat([qst,box_feats],-1)   
        c = self.lin1(b_full)
        c = c.view(b,-1)            
        counts = self.nac(c)
        return  counts.squeeze(1)
