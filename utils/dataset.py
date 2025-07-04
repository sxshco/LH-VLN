from torch.utils.data import Dataset, DataLoader
from functools import reduce
import os
import gzip
import json
from PIL import Image
import numpy as np


def read_json_gz(file_path):
    with gzip.open(file_path, 'rt', encoding='utf-8') as f:
        data = json.load(f)
    return data

class TaskDataset(Dataset):
    def __init__(self, args, mode):
        assert mode in ['train', 'test', 'valid']
        self.mode = mode

        self.task_data = args.task_data
        self.step_task_data = args.step_task_data
         
        if mode == 'train':
            self.batch = args.train_batch
        elif mode == 'valid':
            self.batch = args.val_batch
        else:
            self.batch = args.test_batch

        self.data = []
        for batch in self.batch:
            data = self.load_data(self.task_data, batch)
            for i in range(len(data)):
                subtask = data[i]['Subtask list']
                obj = []
                region_id = []
                for task in subtask:
                    if "Move_to" in task:
                        obj_id  = task[9:-2].split("_")
                        obj.append(obj_id[0])
                        region_id.append(obj_id[1])
                rooms = []
                for room in data[i]["Object"]:
                    rooms.append(room[1].split(': ')[1])
                data[i]['Object'] = obj
                data[i]['Region'] = region_id
                data[i]['Batch'] = batch
                data[i]['Room'] = rooms
            self.data.append(data)

        self.tasks = reduce(lambda x, y: x + y, self.data)
        
        self.step_data = []
        for batch in self.batch:
            self.step_data.append(self.load_step_task(batch))
        self.step_tasks = reduce(lambda x, y: x + y, self.step_data)
    
    def __getitem__(self, index):
        # data = self.preprocess(self.data[index]) # 如果需要预处理数据的话
        return self.tasks[index], self.step_tasks[index]

    
    def __len__(self):
        return len(self.tasks)
    
    def load_data(self, file, batch):
        task = []
        file = file + batch
        nums = os.listdir(file)
        for num in nums:
            task_names = os.listdir(file + "/" + num)
            for task_name in task_names:
                f = file + "/" + num + "/" + task_name + "/config.json"
                with open(f, "r", encoding='utf-8') as r:
                    task.append(json.load(r))
        return task 

    def load_step_task(self, batch):
        step_tasks = []
        path = self.step_task_data + batch
        index = self.batch.index(batch)
        for task in self.data[index]:
            step_task_list = os.listdir(path)
            step_tasks_list = []
            for step_task in step_task_list:
                step_task_path = path + "/" + step_task
                with open(step_task_path, "r", encoding='utf-8') as r:
                    config = json.load(r)
                if task['Task instruction'] in config["trajectory path"]:
                    config["trajectory path"] = self.task_data + batch + '/' + str(len(task['Object'])) + '/' + '/'.join(config["trajectory path"].split('/')[-3:])
                    config['Batch'] = batch
                    config['Object'] = config['target']

                    step_tasks_list.append(config)
            step_tasks.append(step_tasks_list)
        
        return step_tasks

      
    def preprocess(self, data):
        # 将data 做一些预处理
        pass

class EpisodeDataset(Dataset):
    def __init__(self, args, mode):
        assert mode in ['train', 'test', 'valid']
        self.mode = mode
        self.episode_data = args.episode_data

        if mode == 'train':
            self.batch = args.train_batch
        elif mode == 'valid':
            self.batch = args.val_batch
        else:
            self.batch = args.test_batch

        self.data = []
        self.step_data = []
        for batch in self.batch:
            data, step_data = self.load_data(self.episode_data, batch)
            for i in range(len(data)):
                subtask = data[i]['Subtask list']
                obj = []
                region_id = []
                for task in subtask:
                    if "Move_to" in task:
                        obj_id  = task[9:-2].split("_")
                        obj.append(obj_id[0])
                        region_id.append(obj_id[1])
                rooms = []
                for room in data[i]["Object"]:
                    rooms.append(room[1].split(': ')[1])
                data[i]['Object'] = obj
                data[i]['Region'] = region_id
                data[i]['Batch'] = batch
                data[i]['Room'] = rooms
            self.data.append(data)
            self.step_data.append(step_data)

        self.tasks = reduce(lambda x, y: x + y, self.data)
        self.step_tasks = reduce(lambda x, y: x + y, self.step_data)
    
    def __getitem__(self, index):
        # data = self.preprocess(self.data[index]) # 如果需要预处理数据的话
        return self.tasks[index], self.step_tasks[index]

    
    def __len__(self):
        return len(self.tasks)
    
    def load_data(self, file, batch):
        task = []
        step_tasks = []
        file = file + batch + '.json.gz'
        raw_dic = read_json_gz(file)
        for key, value in raw_dic.items():
            task.append(value['lh_task'])
            step_tasks_list = []
            for step_task in value['st_task']:
                step_task['Batch'] = batch
                step_task['Object'] = step_task['target']
                step_tasks_list.append(step_task)
            step_tasks.append(step_tasks_list)
        return task, step_tasks

    def preprocess(self, data):
        # 将data 做一些预处理
        pass

# return obs for step "step" in traj "path"
def get_obs(step, path):
    action_path = path
    actions = os.listdir(action_path)
    action_dic = {}
    stop_steps = [len(actions)-2]
    for action in actions:
        if 'json' in action:
            continue
        if "_".join(action.split('_')[1:-2]) == 'stop' and action.split('_')[0] != '-1':
            stop_steps.append(int(action.split('_')[0]))
        else:
            action_dic[int(action.split('_')[0])] = ["_".join(action.split('_')[1:-2]), action.split('_')[-1]]  
    # for step in range(len(actions)-1):
    #     if action_dic[step][1] != action_dic[step-1][1]:
    #         stop_steps.append(step-1)
    if step + 1 > len(action_dic):
        return 0, 0, 0, 0
    obs = {}
    img_list = os.listdir(action_path + '/' + str(step-1) + "_" + action_dic[step-1][0] + "_for_" + action_dic[step-1][1])
    for img in img_list:
        img_name = img.split('.')[0]
        img_path = action_path + '/' + str(step-1) + "_" + action_dic[step-1][0] + "_for_" + action_dic[step-1][1] + '/' + img
        obs[img_name] = Image.open(img_path)
    if step + 1 == len(action_dic):
        action_ = action_dic[step-1][0]
        obj_ = action_dic[step-1][1]
    else:
        if step not in action_dic:
            return 0, 0, 0, 0
        action_ = action_dic[step][0]
        obj_ = action_dic[step][1]

    return [obs["left"], obs["front"], obs["right"]], action_, obj_, step in stop_steps

def split_datasets_by_scene(dataset_list):
    """
    Split multiple TaskDataset or EpisodeDataset instances into three datasets 
    based on 'Scene' labels in self.tasks elements
    
    Args:
        dataset_list: List containing multiple TaskDataset or EpisodeDataset instances
    
    Returns:
        tuple: (dataset_0_700, dataset_700_800, dataset_800_plus) Three redistributed dataset lists
    """
    # Collect all tasks and step_tasks from all datasets
    all_tasks = []
    all_step_tasks = []
    
    for dataset in dataset_list:
        all_tasks.extend(dataset.tasks)
        all_step_tasks.extend(dataset.step_tasks)
    
    # Classify by Scene labels
    tasks_0_700 = []
    step_tasks_0_700 = []
    tasks_700_800 = []
    step_tasks_700_800 = []
    tasks_800_plus = []
    step_tasks_800_plus = []
    
    for i, task in enumerate(all_tasks):
        # Extract Scene ID from task, assume it's an integer field
        scene_id = int(task['Scene'][:5])  

        if 0 <= scene_id < 700:
            tasks_0_700.append(task)
            step_tasks_0_700.append(all_step_tasks[i])
        elif 700 <= scene_id < 800:
            tasks_700_800.append(task)
            step_tasks_700_800.append(all_step_tasks[i])
        else:  # scene_id >= 800
            tasks_800_plus.append(task)
            step_tasks_800_plus.append(all_step_tasks[i])
    
    return (tasks_0_700, step_tasks_0_700), (tasks_700_800, step_tasks_700_800), (tasks_800_plus, step_tasks_800_plus)

def create_split_datasets(dataset_list, args):
    """
    Create three new dataset instances containing data split by Scene
    
    Args:
        dataset_list: Original dataset list
        args: Original arguments
    
    Returns:
        tuple: Three new dataset instances
    """
    # Get split data
    (tasks_0_700, step_tasks_0_700), (tasks_700_800, step_tasks_700_800), (tasks_800_plus, step_tasks_800_plus) = split_datasets_by_scene(dataset_list)
    
    # Determine dataset class type
    dataset_class = type(dataset_list[0])
    
    # Create three new dataset instances
    dataset_0_700 = dataset_class.__new__(dataset_class)
    dataset_700_800 = dataset_class.__new__(dataset_class)
    dataset_800_plus = dataset_class.__new__(dataset_class)
    
    mode = ['train', 'valid', 'test']
    # Initialize basic attributes for all three datasets
    for i, dataset in enumerate([dataset_0_700, dataset_700_800, dataset_800_plus]):
        dataset.mode = mode[i]
        
        # Copy attributes based on dataset type
        if hasattr(dataset_list[0], 'task_data'):
            dataset.task_data = dataset_list[0].task_data
        if hasattr(dataset_list[0], 'step_task_data'):
            dataset.step_task_data = dataset_list[0].step_task_data
        if hasattr(dataset_list[0], 'episode_data'):
            dataset.episode_data = dataset_list[0].episode_data
        
        # Set batch size based on mode
        if mode == 'train':
            dataset.batch = args.train_batch
        elif mode == 'valid':
            dataset.batch = args.val_batch
        else:
            dataset.batch = args.test_batch
    
    # Assign task data to each dataset
    dataset_0_700.tasks = tasks_0_700
    dataset_0_700.step_tasks = step_tasks_0_700
    dataset_0_700.data = []  # Can be reorganized based on needs
    dataset_0_700.step_data = []
    
    dataset_700_800.tasks = tasks_700_800
    dataset_700_800.step_tasks = step_tasks_700_800
    dataset_700_800.data = []
    dataset_700_800.step_data = []
    
    dataset_800_plus.tasks = tasks_800_plus
    dataset_800_plus.step_tasks = step_tasks_800_plus
    dataset_800_plus.data = []
    dataset_800_plus.step_data = []
    
    return dataset_0_700, dataset_700_800, dataset_800_plus
