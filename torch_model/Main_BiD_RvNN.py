# -*- coding: utf-8 -*-
"""
@object: Twitter
@task: Main function of recursive NN (4 classes)
@author: majing
@structure: Top-Down recursive Neural Networks
@variable: Nepoch, lr, obj, fold
@time: Jan 24, 2018
"""

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import BiD_RvNN
import math
import torch
import BU_loadData
import TD_loadData
import tree_loader

import numpy as np
import TD_RvNN
import time
import random
import torch.optim as optim
import datetime
from evaluate import *

obj = "Twitter15" # choose dataset, you can choose either "Twitter15" or "Twitter16"
fold = "3" # fold index, choose from 0-4
tag = ""
vocabulary_size = 5000
hidden_dim = 100
Nclass = 4
Nepoch = 600
lr = 0.005

unit="BU_RvNN-"+obj+str(fold)+'-vol.'+str(vocabulary_size)+tag

treePath = '../resource/data.BU_RvNN.vol_'+str(vocabulary_size)+tag+'.txt'

trainPath = "../nfold/RNNtrainSet_"+obj+str(fold)+"_tree.txt"
testPath = "../nfold/RNNtestSet_"+obj+str(fold)+"_tree.txt"
labelPath = "../resource/"+obj+"_label_All.txt"

##################################### MAIN ####################################        
## 1. load tree & word & index & label
# BU_tree_train, BU_word_train, BU_index_train, BU_y_train, BU_tree_test, BU_word_test, BU_index_test, BU_y_test = BU_loadData.loadData(treePath,labelPath,trainPath,testPath)
TD_tree_train, TD_word_train, TD_index_train, TD_leaf_idxs_train, TD_y_train, TD_tree_test, TD_word_test, TD_index_test, TD_leaf_idxs_test, TD_y_test = TD_loadData.loadData(treePath,labelPath,trainPath,testPath)
# it can be tried to combine the BU_tree and the TD_tree to output an adjacent matrix, parent matrix should be the transposition matrix of children matrix
# print("first BU tree:", BU_tree_train[0])
print("first TD tree:", TD_tree_train[0])
# print("first BU words:", BU_word_train[0])
print("first TD words:", TD_word_train[0])
# print("first BU indexs:", BU_index_train[0])
print("first TD indexs:", TD_index_train[0])
TD_tree_train = [tree_loader.Tree(l) for l in TD_tree_train]
TD_tree_test = [tree_loader.Tree(l) for l in TD_tree_test]

def CompLoss(pred, ylabel):
    return (torch.tensor(ylabel, dtype=torch.float) - pred).pow(2).sum()

## 2. ini RNN model
t0 = time.time()
model = BiD_RvNN.RvNN(vocabulary_size, hidden_dim, Nclass)
t1 = time.time()
print 'Recursive model established,', (t1-t0)/60

## 3. looping SGD
paras = [{'param':parameter, 'lr':0.1, 'weight_decay':0.001} if not 'E_bu' in name else {'param':parameter, 'lr':0.05} for name, parameter in model.named_parameters()]
optimizer = optim.Adagrad(model.parameters())
losses_5, losses = [], []
num_examples_seen = 0
batch_size = 5
best_test_acc = 0.0

indexs = [i for i in range(len(TD_y_train))]
for epoch in range(Nepoch):
    ## one SGD
    model.train()
    random.shuffle(indexs)
    for i in range(0, len(indexs), batch_size):
        batch_indexs = indexs[i:min(i+batch_size, len(indexs))]
        loss = torch.tensor(0.0)
        for i in batch_indexs:
            pred = model.forward(TD_word_train[i], TD_index_train[i], TD_tree_train[i])
            loss += CompLoss(pred, TD_y_train[i])
        loss = loss/(1.0*len(batch_indexs))
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        losses.append(float(loss.data))
        num_examples_seen += 1
        print("epoch=%d: idx=%d,loss=%f"%( epoch, i, np.mean(losses)))
    sys.stdout.flush()

    model.eval()
    ## cal loss & evaluate
    if epoch % 1 == 0:
       losses_5.append((num_examples_seen, np.mean(losses)))
       time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
       print("%s: Loss after num_examples_seen=%d epoch=%d: %f" % (time, num_examples_seen, epoch, np.mean(losses)))
       sys.stdout.flush()
       prediction = []
       for j in range(len(TD_y_test)):
           prediction.append(model.forward(TD_word_test[j], TD_index_test[j], TD_tree_test[j]).data.tolist() )
       res = evaluation_4class(prediction, TD_y_test)
       if best_test_acc < res[1]:
           best_test_acc = res[1]
           print("best_performance:")
           torch.save(model, "../resource/GRU_%.3f.pkl"%best_test_acc)
       print('results:', res)
       sys.stdout.flush()
       ## Adjust the learning rate if loss increases
       if len(losses_5) > 1 and losses_5[-1][1] > losses_5[-2][1]:
          lr = lr * 0.5
          print("Setting learning rate to %f" % lr)
          sys.stdout.flush()
    sys.stdout.flush()
    losses = []
model.SaveModels('ModelStorage/Initial.MIXmodel')
