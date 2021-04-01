'''
This is a part of the supplementary material uploaded along with 
the manuscript:
    "Semantic Segmentation of Pathological Lung Tissue with Dilated Fully Convolutional Networks"
    M. Anthimopoulos, S. Christodoulidis, L. Ebner, A. Christe and S. Mougiakakou
    IEEE Journal of Biomedical and Health infomatics (2018)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

For more information please read the README file. The files can also 
be found at: https://github.com/intact-project/LungNet
'''
import itertools
import numpy as np
from functools import partial
# keras
from keras.models import Model
from keras.optimizers import Adam
from keras.layers.core import Activation
from keras.layers import Input, Dropout, MaxPooling2D, UpSampling2D
from keras.layers.convolutional import Conv2D
from keras.layers.merge import Add, Concatenate
from tensorflow.keras import models, layers
# custom
import custom_metrics as M
from custom_layers import BatchNormalization, Softmax4D
# debug
from ipdb import set_trace as bp

def bn_block(x):
    return Add()([x, BatchNormalization(axis=-1, mode=2)(x)])

def conv_block(x, nb_filter, filter_size, atrous_rate=(1, 1)):
    x = Conv2D(nb_filter, filter_size,dilation_rate=atrous_rate, kernel_initializer='he_normal', padding='same')(x)
    x = bn_block(x)
    x = Activation('relu')(x)
    return x

def get_model(n_classes, class_weights, unsuper_weight=0):
    

    model = models.Sequential()
    model.add(layers.Conv2D(64, (3, 3), activation='relu', input_shape=(None, None, 3), padding='same'))
    model.add(layers.MaxPooling2D((2, 2)))
    model.add(layers.Conv2D(64, (3, 3), activation='relu', padding='same'))
    model.add(layers.MaxPooling2D((2, 2)))
    model.add(layers.Conv2D(64, (3, 3), activation='relu', padding='same'))
    model.add(layers.MaxPooling2D((2, 2)))
    model.add(layers.Conv2D(64, (1, 1), activation='relu', padding='same'))
    model.add(layers.Conv2D(n_classes, (1, 1), activation='relu'))
    model.add(UpSampling2D((8,8)))
    model.add(Softmax4D())

    
    #model = Model(inputs=[i], outputs=[o1])

    loss = M.loss(weights=class_weights, unsuper_weight=unsuper_weight, unsuper_channel=-1)
    wcce = M.wcceOA(weights=class_weights)
    uentr = M.entrONA(unsuper_channel=-1)
    wacc = M.waccOA(weights=class_weights)

    model.compile(optimizer=Adam(0.01), loss=loss, metrics=[wcce, uentr, wacc])

    return model

def sample_generator(db_path, augment=True):
    db = np.load(db_path, allow_pickle=True)['db'][()]
    X = db['X']
    Y = db['Y']

    numClasses = Y[0][0].shape[-1]
    flip = [(lambda x: x), np.fliplr]
    rotate = [partial(np.rot90, k=0), partial(np.rot90, k=1), partial(np.rot90, k=2), partial(np.rot90, k=3)]
    augmentations = list(itertools.product(flip, rotate))

    while 1:
        # suffling samples
        idxs = np.random.permutation(len(X))
        for rs in idxs: # looping over shuffled samples
            if augment:
                # selecting augmentation
                aug = augmentations[np.random.randint(len(augmentations))]

                # flip rotate augmentation
                x = aug[1](aug[0](np.squeeze(X[rs])))
                y = aug[1](aug[0](np.squeeze(Y[rs])))

            else:
                x = np.squeeze(X[rs])
                y = np.squeeze(Y[rs])

            if x.ndim == 2: 
                tmp = np.zeros((x.shape[0],x.shape[1],3))
                for i in range(3):
                    tmp[:,:,i] = x
                x = tmp

            yield (x[None,:,:,:], y[None,:,:,:])
