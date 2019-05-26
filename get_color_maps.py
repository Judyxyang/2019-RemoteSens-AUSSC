# -*- coding: utf-8 -*-
import numpy as np
import scipy.io as sio
import matplotlib.pyplot as plt
from sklearn import metrics, preprocessing
from Utils import aucn_model, record, extract_samll_cubic, cliquenet
import tensorflow as tf
from keras.utils.np_utils import to_categorical


def sampling(proportion, ground_truth):
    train = {}
    test = {}
    labels_loc = {}
    m = max(ground_truth)
    for i in range(m):
        indexes = [j for j, x in enumerate(ground_truth.ravel().tolist()) if x == i + 1]
        np.random.shuffle(indexes)
        labels_loc[i] = indexes
        nb_val = int(proportion * len(indexes))
        train[i] = indexes[:-nb_val]
        test[i] = indexes[-nb_val:]
    train_indexes = []
    test_indexes = []
    for i in range(m):
        train_indexes += train[i]
        test_indexes += test[i]
    np.random.shuffle(train_indexes)
    np.random.shuffle(test_indexes)
    return train_indexes, test_indexes


def classification_map(map, ground_truth, dpi, save_path):
    fig = plt.figure(frameon=False)
    fig.set_size_inches(ground_truth.shape[1]*2.0/dpi, ground_truth.shape[0]*2.0/dpi)

    ax = plt.Axes(fig, [0., 0., 1., 1.])
    ax.set_axis_off()
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)
    fig.add_axes(ax)

    ax.imshow(map)
    fig.savefig(save_path, dpi=dpi)

    return 0


def list_to_colormap(x_list):
    y = np.zeros((x_list.shape[0], 3))
    for index, item in enumerate(x_list):
        if item == 0:
            y[index] = np.array([255, 0, 0]) / 255.
        if item == 1:
            y[index] = np.array([0, 255, 0]) / 255.
        if item == 2:
            y[index] = np.array([0, 0, 255]) / 255.
        if item == 3:
            y[index] = np.array([255, 255, 0]) / 255.
        if item == 4:
            y[index] = np.array([0, 255, 255]) / 255.
        if item == 5:
            y[index] = np.array([255, 0, 255]) / 255.
        if item == 6:
            y[index] = np.array([192, 192, 192]) / 255.
        if item == 7:
            y[index] = np.array([128, 128, 128]) / 255.
        if item == 8:
            y[index] = np.array([128, 0, 0]) / 255.
        if item == 9:
            y[index] = np.array([128, 128, 0]) / 255.
        if item == 10:
            y[index] = np.array([0, 128, 0]) / 255.
        if item == 11:
            y[index] = np.array([128, 0, 128]) / 255.
        if item == 12:
            y[index] = np.array([0, 128, 128]) / 255.
        if item == 13:
            y[index] = np.array([0, 0, 128]) / 255.
        if item == 14:
            y[index] = np.array([255, 165, 0]) / 255.
        if item == 15:
            y[index] = np.array([255, 215, 0]) / 255.
        if item == 16:
            y[index] = np.array([0, 0, 0]) / 255.

    return y


def into_batch(data, batch_size):
    batch_count = len(data) // batch_size
    batches_data = np.split(data[:batch_count * batch_size], batch_count)
    batches_data.append(data[batch_count * batch_size:])
    if len(data) % batch_size == 0:
        batch_count = batch_count
    else:
        batch_count += 1

    return batches_data, batch_count


global Dataset
data_set = input('Please input the name of data set(IN, SS or KSC):')
Dataset = data_set.upper()
if Dataset == 'IN':
    mat_data = sio.loadmat('datasets/Indian_pines_corrected.mat')
    data_hsi = mat_data['indian_pines_corrected']
    mat_gt = sio.loadmat('datasets/Indian_pines_gt.mat')
    gt_hsi = mat_gt['indian_pines_gt']
    TOTAL_SIZE = 10249
    VALIDATION_SPLIT = 0.8

if Dataset == 'KSC':
    KSC = sio.loadmat('datasets/KSC.mat')
    gt_KSC = sio.loadmat('datasets/KSC_gt.mat')
    data_hsi = KSC['KSC']
    gt_hsi = gt_KSC['KSC_gt']
    TOTAL_SIZE = 5211
    VALIDATION_SPLIT = 0.8

if Dataset == 'SS':
    Salinas = sio.loadmat('datasets/Salinas_corrected.mat')
    gt_Salinas = sio.loadmat('datasets/Salinas_gt.mat')
    data_hsi = Salinas['salinas_corrected']
    gt_hsi = gt_Salinas['salinas_gt']
    TOTAL_SIZE = 54129
    VALIDATION_SPLIT = 0.996453  # 200：0.996453 400：


print(data_hsi.shape)
data = data_hsi.reshape(np.prod(data_hsi.shape[:2]), np.prod(data_hsi.shape[2:]))
gt = gt_hsi.reshape(np.prod(gt_hsi.shape[:2]),)
nb_classes = max(gt)
print('The class numbers of the HSI data is:', nb_classes)

print('-----Importing Setting Parameters-----')
batch_size = 16
nb_epoch = 400
ITER = 1
PATCH_LENGTH = 4

img_rows = 2*PATCH_LENGTH+1
img_cols = 2*PATCH_LENGTH+1
img_channels = data_hsi.shape[2]
INPUT_DIMENSION = data_hsi.shape[2]

ALL_SIZE = data_hsi.shape[0] * data_hsi.shape[1]
VAL_SIZE = int(0.5*TRAIN_SIZE)
TEST_SIZE = TOTAL_SIZE - TRAIN_SIZE

data = preprocessing.scale(data)
data_ = data.reshape(data_hsi.shape[0], data_hsi.shape[1], data_hsi.shape[2])
whole_data = data_
padded_data = np.lib.pad(whole_data, ((PATCH_LENGTH, PATCH_LENGTH), (PATCH_LENGTH, PATCH_LENGTH), (0, 0)),
                         'constant', constant_values=0)

num = input('Please enter the number of model:')
print('the model is:' + Dataset + '_aucn_'+str(num)+'.ckpt')
best_weights_path = 'models/' + Dataset + '_aucn_' + str(num) + '@1.ckpt'
seeds = [1331, 1332, 1333, 1334, 1335, 1336, 1337, 1338, 1339, 1340, 1341]

for index_iter in range(ITER):
    train_indices, test_indices = sampling(VALIDATION_SPLIT, gt)

    y_train_raw = gt[train_indices]
    y_train = to_categorical(np.asarray(y_train_raw))

    y_test_raw = gt[test_indices]
    y_test = to_categorical(np.asarray(y_test_raw))

    all_data = extract_samll_cubic.select_small_cubic(ALL_SIZE, range(ALL_SIZE), whole_data,
                                                      PATCH_LENGTH, padded_data, INPUT_DIMENSION)

    print('--------Load trained model----------')
    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True
    with tf.Session(config=config) as sess:
        saver = tf.train.import_meta_graph(best_weights_path+'.meta')
        saver.restore(sess, best_weights_path)
        graph = tf.get_default_graph()
        input_hsi = graph.get_operation_by_name('input_hsi').outputs[0]
        is_train = graph.get_operation_by_name('is_train').outputs[0]
        keep_prob = graph.get_operation_by_name('keep_prob').outputs[0]
        pred = tf.get_collection('pred')[0]
        all_data = all_data.reshape(all_data.shape[0], all_data.shape[1], all_data.shape[2], all_data.shape[3], 1)
        print(all_data.shape)
        all_data_bitch, batch_count = into_batch(all_data, batch_size)
        pred_test = []
        for batch_id in range(batch_count):
            data_per_batch = all_data_bitch[batch_id]
            result_per_batch = sess.run(pred, feed_dict={input_hsi: data_per_batch, is_train: False, keep_prob: 1})
            for i in range(len(result_per_batch)):
                pred_test.append(result_per_batch[i])
            if batch_id % 100 == 0:
                print('%3d/%3d:Get predicting result' % (batch_id + 1, batch_count))

    x = np.ravel(pred_test)
    gt = gt_hsi.flatten()
    for i in range(len(gt)):
        if gt[i] == 0:
            gt[i] = 17

    gt = gt[:]-1
    print('-------Save the result in mat format--------')
    x_re = np.reshape(pred_test, (gt_hsi.shape[0], gt_hsi.shape[1]))
    sio.savemat('mat/' + Dataset + '_+ str(num) + .mat', {Dataset: x_re})

    y_list = list_to_colormap(x)
    y_gt = list_to_colormap(gt)

    y_re = np.reshape(y_list, (gt_hsi.shape[0], gt_hsi.shape[1], 3))
    gt_re = np.reshape(y_gt, (gt_hsi.shape[0], gt_hsi.shape[1], 3))

    classification_map(y_re, gt_hsi, 300,
                        'classification_maps/'+Dataset+'_'+str(num)+'.png')
    classification_map(gt_re, gt_hsi, 300,
                       'classification_maps/' + Dataset + '_gt.png')
    print('------Get classification maps successful-------')
