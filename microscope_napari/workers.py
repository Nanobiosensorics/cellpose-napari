try:
    from torch import no_grad
except ImportError:
  def no_grad():
    def _deco(func):
        return func
    return _deco

import numpy as np
import cv2

from napari.qt.threading import thread_worker
from cellpose import utils


@thread_worker()
@no_grad()
def get_masks_and_cell_counts_cellpose(images, model_path, channels, cellprob_threshold, model_match_threshold):
    from cellpose import models

    flow_threshold = (31.0 - model_match_threshold) / 10.

    CP = models.CellposeModel(pretrained_model=model_path, gpu=True)
    masks, _, _ = CP.eval(
      images,
      channels=channels,
      flow_threshold=flow_threshold,
      cellprob_threshold=cellprob_threshold
    )

    return masks, [np.max(mask) for mask in masks]


@thread_worker()
def get_cell_counts_regression(images, model_path):
  import pickle

  avg_intensities = []
  for image in images:
    if len(image.shape) == 3: # convert to grayscale if necessary
      image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    avg_intensities.append(np.mean(image))
  avg_intensities = np.array(avg_intensities)

  with open(model_path, "rb") as file:
    result = pickle.load(file)
  
  f = lambda x, m, c: m * x + c
  return np.round(f(avg_intensities, **result["params"])).astype(int)


@thread_worker()
def get_cell_shape_info(image_names, masks):
    result = []
    for name, mask in zip(image_names, masks):
        mask = np.array(mask)
        cell_count = np.max(mask)
        
        # The area will be the count of each cell id (without zero).
        _, counts = np.unique(mask, return_counts=True)
        areas = counts[1:]

        # Calculating cell perimeters with cellpose utils.
        perimeters = np.zeros(cell_count, dtype=np.uint32)
        outlines = utils.outlines_list_multi(mask)
        for i in range(cell_count):
          perimeters[i] = outlines[i].shape[0]

        # Combining the two into results.
        for i in range(cell_count):
           result.append([name, i+1, areas[i], perimeters[i]])
    
    return result

