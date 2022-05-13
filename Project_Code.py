# -*- coding: utf-8 -*-
"""ECE 520.638 Final Project .ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/15sCLCNcuP5qwfRxssOcbAE2236hdEad2

## ECE 520.638 Final Project 
## Team: Chongyu Qu, Daijie Bao, Runtian Tang

## Part 1: Facial Expression Recognition
"""

## Mount Google Drive Data 
try:
    from google.colab import drive
    drive.mount('/content/drive')
except:
    print("Mounting Failed.")

## Import external libraries
import numpy as np
import torch 
import torch.nn as nn 
from torch.utils.data import DataLoader,Subset,random_split
from torchvision import datasets, models, transforms
import matplotlib.pyplot as plt
import torch.optim as optim
from collections import Counter
import pandas as pd
import seaborn as sns
from sklearn.metrics import confusion_matrix

# Setup the GPU device 
device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

pwd

"""## Data preprocess for facial expression recognition """

## Preprocessing dataset for facial expression recognition
## import data from google drive
train_data_path = '/content/drive/My Drive/DL_final_Project_AffectNet/train_class'
test_data_path = '/content/drive/My Drive/DL_final_Project_AffectNet/val_class'
## parameters for preprocessing 
train_batchsize = 32
val_batchsize = 32
test_batchsize = 32
## data transform 
image_transforms = {
    "train": transforms.Compose([
        transforms.Resize((224,224)),
        transforms.ToTensor(),
        transforms.Normalize((0.5241, 0.4233, 0.3762),
                             (0.2880, 0.2604, 0.2550))
    ]),
    "test": transforms.Compose([
        transforms.Resize((224,224)),
        transforms.ToTensor(),
        transforms.Normalize((0.5300, 0.4297, 0.3842),
                             (0.2899, 0.2625, 0.2579))
        ])
}

# Load image data for training and validation 
training_dataset = datasets.ImageFolder(train_data_path, transform = image_transforms["train"])
test_dataset = datasets.ImageFolder(test_data_path, transform = image_transforms["test"])
# Dataloader for training and validation 
# training_dataloader = DataLoader(training_dataset, batch_size=train_batchsize, shuffle=True)
# validation_dataloader = DataLoader(validation_dataset, batch_size = validation_batchsize, shuffle=False)
print(len(training_dataset))
print(len(test_dataset))

# random select 5000 from training dataset and 2000 from validation dataset
torch.manual_seed(111)
subset_idx = torch.randint(0,len(training_dataset),(2000,))
training_subset = Subset(training_dataset,subset_idx)
train_set,val_set = random_split(training_subset,[1600,400])

# Dataloader for training and validation 
training_dataloader = DataLoader(train_set, batch_size=train_batchsize, shuffle=True)
validation_dataloader = DataLoader(val_set, batch_size = val_batchsize, shuffle=True)
test_dataloader = DataLoader(test_dataset,batch_size=test_batchsize,shuffle=False)

"""## Visualize dataset distribution"""

dic = training_dataloader.dataset.dataset.dataset.class_to_idx
print(dic)
print(len(dic))
num_class = len(dic)
idx2class = {v: k for k, v in dic.items()}
print(idx2class)

def find_data_distribution(dataloader,dic):
    targets = []
    for _, target in dataloader:
        target = target.to(device)
        targets.append(target)
    targets = torch.cat(targets)
    dis = targets.unique(return_counts=True)
    count = dict(zip(dic.keys(),dis[1].cpu().numpy()))
    return count

train_dist=find_data_distribution(training_dataloader,dic)
print(train_dist)

validation_dist=find_data_distribution(validation_dataloader,dic)
print(validation_dist)

def visualize_data_distribution(dic,flag):
    plt.figure(figsize=(15,8))
    sns.set_style('darkgrid')
    sns.barplot(data = pd.DataFrame.from_dict([dic]).melt(), x = "variable", y="value", hue="variable")
    plt.title(flag+'set distribution')

visualize_data_distribution(train_dist,'training')

visualize_data_distribution(validation_dist,'validation')

"""## Normalize the input data"""

## define a function to calculate mean and std of dataset
def get_mean_and_std(dataloader):
    channels_sum, channels_squared_sum, num_batches = 0, 0, 0
    for data, _ in dataloader:
        data = data.to(device)
        channels_sum += torch.mean(data, dim=[0,2,3])
        channels_squared_sum += torch.mean(data**2, dim=[0,2,3])
        num_batches += 1  
    mean = channels_sum / num_batches
    std = (channels_squared_sum / num_batches - mean ** 2) ** 0.5
    return mean, std

mean_train,std_train = get_mean_and_std(training_dataloader)
mean_val,std_val = get_mean_and_std(validation_dataloader)
mean_test,std_test = get_mean_and_std(test_dataloader)

print(mean_train)
print(std_train)
print(mean_val)
print(std_val)
print(mean_test)
print(std_test)

# visualize image data
mean= torch.tensor([0.5241, 0.4233, 0.3762])
std = torch.tensor([0.2880, 0.2604, 0.2550])
dataiter = iter(training_dataloader)
images,labels = dataiter.next()
print(images.shape)
fig = plt.figure(figsize=(12,4))
for idx in np.arange(10):
    ax = fig.add_subplot(2, 5, idx+1, xticks=[], yticks=[])
    plt.imshow(np.transpose((images[idx]* std[:, None, None] + mean[:, None, None]),
                            (1,2,0)))
    for key,value in dic.items():
        if value==labels[idx].item():
            ax.set_title(key)

"""## Fine-tune pretrained ResNet18"""

## Load pretrained ResNet18 model 
LR = 0.0001
classfication_model_res18 = models.resnet18(pretrained=True)
classfication_model_res18.fc = nn.Linear(512,num_class)
classfication_model_res18.to(device)
Loss_criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(classfication_model_res18.parameters(),lr=LR)
print(classfication_model_res18)

## Load pretrained vgg16 model 
LR = 0.0001
classfication_model = models.vgg16(pretrained=True)
classfication_model.classifier[6] = nn.Linear(in_features=4096, out_features=num_class)
classfication_model.to(device)
Loss_criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(classfication_model.parameters(),lr=LR)
print(classfication_model)

"""## Model training and validation """

## Define a fit function for training and validation
num_epochs = 30

def fit(training_load,testing_load,no_epochs,optimizer,model,loss_function):
    history = []
    for epoch in range(no_epochs):
        train_loss,test_loss = 0,0
        correct_train,correct_test = 0,0
        total_train,total_test = 0,0 
        for i, (train_in,train_labels) in enumerate(training_load):
            model.train()
            train_in,train_labels = train_in.to(device),train_labels.to(device)
            optimizer.zero_grad()
            train_out = model(train_in)
            batch_loss_train = loss_function(train_out,train_labels)
            batch_loss_train.backward()
            optimizer.step()
            train_loss += batch_loss_train.item()
            _,predicted_train = torch.max(train_out.data,1)
            total_train += train_labels.size(0)
            correct_train += predicted_train.eq(train_labels).sum().item()

        for i, (test_in,test_labels) in enumerate(testing_load):
            model.eval()
            test_in,test_labels = test_in.to(device),test_labels.to(device)
            test_out = model(test_in)
            _,predicted_test = torch.max(test_out.data,1)
            batch_loss_test = loss_function(test_out,test_labels)
            test_loss += batch_loss_test.item()
            total_test += test_labels.size(0)
            correct_test += predicted_test.eq(test_labels).sum().item()

        total_train_loss = train_loss/len(training_load)
        train_accu = 100.*correct_train/total_train
        total_test_loss = test_loss/len(testing_load)
        test_acc = 100.*correct_test/total_test
        print(f"Epoch [{epoch + 1}/{no_epochs}] => train_loss:{total_train_loss}, train_accuracy:{train_accu},val_loss: {total_test_loss},val_accuracy:{test_acc}")
        history.append({"train_loss": total_train_loss,
                        "train_accuracy": train_accu,
                        "val_loss": total_test_loss,
                        "val_accuracy":test_acc,
                        })
    return history

classfication_his = fit(training_dataloader,validation_dataloader,num_epochs,optimizer,classfication_model,Loss_criterion)

classfication_his_res18 = fit(training_dataloader,validation_dataloader,num_epochs,optimizer,classfication_model_res18,Loss_criterion)

torch.save(classfication_model.state_dict(), '/content/drive/My Drive/model_demo/classifier.pth')

def visualize_loss(his,num_epochs):
    train_loss = []
    validation_loss = []
    for x in his:
        train_loss.append(x["train_loss"])
        validation_loss.append(x["val_loss"])
    epochs = np.arange(num_epochs)
    sns.set_style('darkgrid')
    plt.plot(epochs, train_loss)
    plt.plot(epochs, validation_loss)
    plt.xlabel("Epochs")
    plt.ylabel("Loss")
    plt.title("Loss of training and validation over epochs")
    plt.legend(["training", "validation"])
    plt.show()

def visualize_accuracy(his,num_epochs):
    train_accu = []
    validation_accu = []
    for x in his:
        train_accu.append(x["train_accuracy"])
        validation_accu.append(x["val_accuracy"])
    epochs = np.arange(num_epochs)
    sns.set_style('darkgrid')
    plt.plot(epochs, train_accu)
    plt.plot(epochs, validation_accu)
    plt.xlabel("Epochs")
    plt.ylabel("accuracy")
    plt.title("accuracy of training and validation over epochs")
    plt.legend(["training", "validation"])
    plt.show()

visualize_loss(classfication_his_res18,num_epochs)

visualize_accuracy(classfication_his_res18,num_epochs)

with torch.no_grad():
    true_labels = []
    pred_labels= []
    for i, (img,labels) in enumerate(test_dataloader):
        img,labels = img.to(device),labels.to(device)
        output = classfication_model_res18(img)
        _,pred = torch.max(output,1)
        true_labels.append(labels)
        pred_labels.append(pred)
    true_labels = torch.cat(true_labels)
    pred_labels = torch.cat(pred_labels)

cf_matrix = confusion_matrix(true_labels.cpu().numpy(),pred_labels.cpu().numpy())
df_cm = pd.DataFrame(cf_matrix, index = [i for i in dic.keys()],
                  columns = [i for i in dic.keys()])
plt.figure(figsize = (10,7))
sns.heatmap(df_cm, annot=True,cmap="YlGnBu")

"""## Part 2: Face detection with MTCNN"""

## Install MTCNN Package 
! pip install mtcnn

# Commented out IPython magic to ensure Python compatibility.
## Import external libraries for face detection 
import mtcnn
from mtcnn.mtcnn import MTCNN
import matplotlib.pyplot as plt
import matplotlib
# %matplotlib inline

matplotlib.rc_file_defaults()

# load image from file
image_path = '/content/drive/MyDrive/model_demo/waitress.jpg'

## MTCNN Face detector
def face_detector(image):
    image_pixels = plt.imread(image)
    detector = MTCNN()
    detection_coordinate = detector.detect_faces(image_pixels)
    print('The key detection coordinates are ', detection_coordinate)
    return detection_coordinate

## Get face detection result
detection_coordinate_set = face_detector(image_path)

## Create a bounding box for detection result
def bounding_box_creator(image_path, coordinate_set,new_path):
    data = plt.imread(image_path)
    plt.imshow(data)
    ax = plt.gca()
    for coordinate in coordinate_set:
        x, y, width, height = coordinate['box']
        rect = plt.Rectangle((x, y), width, height, fill=False, color='red')
        ax.add_patch(rect)
    plt.savefig(new_path)
    plt.show()

## Print out Face detection result 
bounding_box_creator(image_path, detection_coordinate_set,'/content/drive/MyDrive/model_demo/waitress_new.jpg')

"""Personal data testing"""

trent_path = '/content/drive/MyDrive/model_demo/happy.JPG'

data = plt.imread(trent_path)
plt.imshow(data)
plt.show()

detection_coordinate_set_trent = face_detector(trent_path)

bounding_box_creator(trent_path, detection_coordinate_set_trent,'/content/drive/MyDrive/model_demo/trent_happy.jpg')

face = data[165: 165+85,295:295+62]

convert_tensor = transforms.Compose([transforms.ToTensor(), transforms.Resize((224,224))])
face_input = convert_tensor(face)

plt.imshow(np.transpose(face_input,(1,2,0)))
plt.savefig('/content/drive/MyDrive/model_demo/trent_croped.jpg')

plt.show()

trent_mean = torch.mean(face_input, dim=[1,2])
trent_std = torch.std(face_input,dim=[1,2])

print(trent_mean)
print(trent_std)

face_input_norm=(face_input-trent_mean[:, None, None])/trent_std[:, None, None]

state_dic=torch.load('/content/drive/MyDrive/model_demo/classifier.pth')

classfication_model.load_state_dict(state_dic)

with torch.no_grad():
    out = classfication_model(face_input_norm.to(device).unsqueeze(0))
    _,predicted_label = torch.max(out.data,1)

idx2class[predicted_label.cpu().item()]