import numpy as np
import pandas as pd
import os
import glob
import math
import pickle
import datetime
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestRegressor
from keras.callbacks import ModelCheckpoint
from keras import backend as K
from keras.layers import Input, Embedding, LSTM, Dense,Flatten, Dropout, merge,Convolution1D,MaxPooling1D,Lambda
from keras.layers.normalization import BatchNormalization
from keras.optimizers import SGD
from keras.layers.advanced_activations import PReLU,LeakyReLU,ELU,SReLU
from keras.models import Model
from keras.utils.visualize_util import plot
from ml_metrics import rmse
seed = 1024
np.random.seed(seed)

if __name__ == '__main__':

    use_all=False
    
    path = "E:\\RSdata\\"
    features = ['uid','iid']
    score = 'score'

    X_train = pd.read_csv(path+"X_train.csv")
    X_test = pd.read_csv(path+"X_test.csv")
    test = pd.read_csv(path+"test.csv")

    y_train = X_train[score].values
    X_train = X_train[features].values

    y_test = X_test[score].values
    X_test = X_test[features].values

    test = test[features].values

    

    
    
    X = np.concatenate([X_train,X_test,test])

    user_le = LabelEncoder()
    item_le = LabelEncoder()

    user_le.fit(X[:,0])
    item_le.fit(X[:,1])

    X_train[:,0] = user_le.transform(X_train[:,0])
    X_train[:,1] = item_le.transform(X_train[:,1])


    X_test[:,0] = user_le.transform(X_test[:,0])
    X_test[:,1] = item_le.transform(X_test[:,1])


    if use_all:
        X_train = np.concatenate([X_train,X_test])
        y_train = np.concatenate([y_train,y_test])


    test[:,0] = user_le.transform(test[:,0])
    test[:,1] = item_le.transform(test[:,1])

    u_train,i_train = X_train[:,0],X_train[:,1]
    u_test,i_test = X_test[:,0],X_test[:,1]



    num_u = len(np.unique(X[:,0]))
    num_i = len(np.unique(X[:,1]))

    del X

    u_train = np.expand_dims(u_train,1)
    i_train = np.expand_dims(i_train,1)
    u_test = np.expand_dims(u_test,1)
    i_test = np.expand_dims(i_test,1)

    uinput = Input(shape=(1,), dtype='int32')
    iinput = Input(shape=(1,), dtype='int32')

    embed_u = Embedding(
                    num_u,
                    256,
                    dropout=0.2,
                    input_length=1
                    )(uinput)

    embed_i = Embedding(num_i,
                    256,
                    dropout=0.2,
                    input_length=1
                    )(iinput)

    # conv_1u = Convolution1D(nb_filter=128,
    #                     filter_length=3,
    #                     border_mode='same',
    #                     activation='relu',
    #                     subsample_length=1)(embed_u)
    
    # conv_1i = Convolution1D(nb_filter=128,
    #                     filter_length=3,
    #                     border_mode='same',
    #                     activation='relu',
    #                     subsample_length=1)(embed_i)
    
    # # pool_1u = MaxPooling1D(pool_length=2)(conv_1u)
    # # pool_1i = MaxPooling1D(pool_length=2)(conv_1i)

    # merge_ui =  merge([pool_1u,pool_1i],mode="concat")

    # flatten_1 = Flatten()(merge_ui)
    # def max_1d(X):
    #     return K.max(X, axis=1)

    # lambda_1u = Lambda(max_1d, output_shape=(128,))(conv_1u)
    # lambda_1i = Lambda(max_1d, output_shape=(128,))(conv_1i)
    flatten_u = Flatten()(embed_u)
    flatten_i = Flatten()(embed_i)


    merge_ui =  merge([flatten_u,flatten_i],mode="concat")

    fc1 = Dense(512)(merge_ui)
    fc1 = SReLU()(fc1)
    dp1 = Dropout(0.5)(fc1)

    fc1_1 = Dense(256)(dp1)
    fc1_1 = SReLU()(fc1_1)
    dp1_1 = Dropout(0.5)(fc1_1)

    fc1_1 = Dense(512)(dp1_1)
    fc1_1 = SReLU()(fc1_1)
    dp1_1 = Dropout(0.5)(fc1_1)

    
    dp1 = merge([dp1,dp1_1],mode='sum')

    fc1_1 = Dense(256)(dp1)
    fc1_1 = SReLU()(fc1_1)
    dp1 = Dropout(0.5)(fc1_1)

    dp1 = merge([dp1,merge_ui],mode='concat')

    fc2 = Dense(128)(dp1)
    fc2 = SReLU()(fc2)
    dp2 = Dropout(0.5)(fc2)



    output = Dense(1)(dp2)

    model = Model(input=[uinput, iinput], output=output)
    sgd = SGD(lr=0.05, decay=1e-6, momentum=0.9, nesterov=True)
    # model.compile(optimizer=sgd,
    #           loss='mse')
    model.compile(optimizer='adam',
              loss='mse')

    model_name = 'mlp.hdf5'
    model_checkpoint = ModelCheckpoint(path+model_name, monitor='val_loss', save_best_only=True)
    plot(model, to_file=path+'%s.png'%model_name.replace('.hdf5',''),show_shapes=True)


    nb_epoch = 5
    batch_size = 1024*6
    load_model = False

    if load_model:
        model.load_weights(path+model_name)

        
    model.fit([u_train,i_train], y_train, batch_size=batch_size, nb_epoch=nb_epoch, verbose=1, shuffle=True,
                      callbacks=[model_checkpoint],
                      validation_data=([u_test,i_test],y_test)
                      )
    
    
    
    u_test_t,i_test_t = test[:,0],test[:,1]
    y_preds = model.predict([u_test_t,i_test_t]).ravel()
    print('y_preds shape',y_preds.shape)
    # d = {'score':y_preds}
    submission = pd.DataFrame()
    submission['score'] = y_preds
    submission.to_csv(path+"submission_mlp.csv",index=False)


    # 0.83557 for old
    y_preds = model.predict([u_test,i_test]).ravel()
    score = rmse(y_test,y_preds)
    print('mlp rmse score',score)


    # inputs = [uinput,iinput,K.learning_phase()]
    # outputs = [fc2]
    # # print inputs,outputs
    # func = K.function(inputs, outputs)


    # print('X_train before shape',X_train.shape)
    # i = 0
    # s = []
    # while i*batch_size<X_train.shape[0]:
    #     tmp = func([u_train[i*batch_size:(i+1)*batch_size],i_train[i*batch_size:(i+1)*batch_size],0])[0]
    #     s.append(tmp)
    # X_train = np.vstack(s)
    # print('X_train after shape',X_train.shape)
    

    # i = 0
    # s = []
    # while i*batch_size<X_train.shape[0]:
    #     tmp = func([u_test[i*batch_size:(i+1)*batch_size],i_test[i*batch_size:(i+1)*batch_size],0])[0]
    #     s.append(tmp)
    # X_test = np.vstack(s)

    # # X_test = func([u_test,i_test,0])[0]
    

    # rf = RandomForestRegressor(n_estimators = 100,max_depth=12,n_jobs=7,random_state=seed)
    # rf.fit(X_train,y_train)
    # y_preds = rf.predict(X_test).ravel()
    # score = rmse(y_test,y_preds)
    # print('rf rmse score',score)

