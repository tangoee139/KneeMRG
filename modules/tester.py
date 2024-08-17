import logging
import os
from abc import abstractmethod
import numpy as np
import time

import cv2
import torch

from .metrics_clinical import CheXbertMetrics
import pandas as pd

class BaseTester(object):
    def __init__(self, model, criterion_cls, metric_ftns, args, device):
        self.args = args
        self.model = model
        self.device = device

        self.chexbert_metrics = CheXbertMetrics('./checkpoints/stanford/chexbert/chexbert.pth', args.batch_size, device)

        logging.basicConfig(format='%(asctime)s - %(levelname)s - %(name)s -   %(message)s',
                            datefmt='%m/%d/%Y %H:%M:%S', level=logging.INFO)
        self.logger = logging.getLogger(__name__)


        self.criterion_cls = criterion_cls
        self.metric_ftns = metric_ftns

        self.epochs = self.args.epochs
        self.save_dir = self.args.save_dir

    @abstractmethod
    def test(self):
        raise NotImplementedError

    @abstractmethod
    def plot(self):
        raise NotImplementedError

class Tester(BaseTester):
    def __init__(self, model, criterion_cls, metric_ftns, args, device, test_dataloader):
        super(Tester, self).__init__(model, criterion_cls, metric_ftns, args, device)
        self.test_dataloader = test_dataloader

    def test_blip(self):
        self.logger.info('Start to evaluate in the test set.')
        log = dict()
        self.model.eval()
        with torch.no_grad():
            rows, test_gts, test_res = [], [], []
            file_name = self.args.save_dir + '/test_output.csv'

            for batch_idx, (images, captions, cls_labels, clip_memory) in enumerate(self.test_dataloader):
                images = images.to(self.device) 
                clip_memory = clip_memory.to(self.device) 
                ground_truths = captions
                reports, _, _ = self.model.generate(images, clip_memory, sample=False, num_beams=self.args.beam_size, max_length=self.args.gen_max_len, min_length=self.args.gen_min_len)

                test_res.extend(reports)
                test_gts.extend(ground_truths)
                for tes, gts in zip(reports, ground_truths):
                    new_row = {'generated': tes, 'original': gts}
                    rows.append(new_row)  
                if batch_idx % 10 == 0:
                    print('{}/{}'.format(batch_idx, len(self.test_dataloader)))
            df = pd.DataFrame(rows)
            df.to_csv(file_name)    
            # test_met = self.metric_ftns({i: [gt] for i, gt in enumerate(test_gts)},
            #                             {i: [re] for i, re in enumerate(test_res)})
            # log.update(**{'test_' + k: v for k, v in test_met.items()})

            # if self.args.dataset_name != 'mri':
            #     test_ce = self.chexbert_metrics.compute(test_gts, test_res)
            
            #     log.update(**{'test_' + k: v for k, v in test_ce.items()})
        return log

