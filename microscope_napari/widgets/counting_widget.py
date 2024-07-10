import numpy as np
import cv2
from typing import List

from magicgui import magicgui

from napari import Viewer
from napari.layers import Image
from napari_plugin_engine import napari_hook_implementation

from microscope_napari.utils import create_table_with_csv_export, MAIN_CHANNEL_CHOICES, OPTIONAL_NUCLEAR_CHANNEL_CHOICES, CP_STRINGS


def widget_wrapper():
  try:
    from torch import no_grad
  except ImportError:
    def no_grad():
      def _deco(func):
          return func
      return _deco

  from napari.qt.threading import thread_worker

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

     return np.array(masks), [np.max(mask) for mask in masks]
  
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
  
  @magicgui(
    call_button='get counts',
    layout='vertical',
    selected_image_layers = dict(widget_type="ListEdit", label="choose image layers", layout="vertical", annotation=List[Image]),
    model_path = dict(widget_type='FileEdit', label='model path: ', tooltip='specify model path here'),
    use_regression_model = dict(widget_type='CheckBox', text='use regression model (lower settings are for cellpose only)', value=False),
    main_channel = dict(widget_type='ComboBox', label='channel to segment', choices=MAIN_CHANNEL_CHOICES, value=0, tooltip='choose channel with cells'),
    optional_nuclear_channel = dict(widget_type='ComboBox', label='optional nuclear channel', choices=OPTIONAL_NUCLEAR_CHANNEL_CHOICES, value=0, tooltip='optional, if available, choose channel with nuclei of cells'),
    cellprob_threshold = dict(widget_type='FloatSlider', name='cellprob_threshold', value=0.0, min=-8.0, max=8.0, step=0.2, tooltip='cell probability threshold (set lower to get more cells and larger cells)'),
    model_match_threshold = dict(widget_type='FloatSlider', name='model_match_threshold', value=27.0, min=0.0, max=30.0, step=0.2, tooltip='threshold on gradient match to accept a mask (set lower to get more cells)'),
    output_outlines = dict(widget_type='CheckBox', text='output outlines', value=True),
    clear_previous_segmentations = dict(widget_type='CheckBox', text='clear previous results', value=True),
  )
  def widget(
    viewer: Viewer,
    selected_image_layers,
    model_path,
    use_regression_model,
    main_channel,
    optional_nuclear_channel,
    cellprob_threshold,
    model_match_threshold,
    output_outlines,
    clear_previous_segmentations
  ):
      def show_outlines(outlines):
          for image_layer, outline in zip(selected_image_layers, outlines):
            print(outline)
            viewer.add_labels(outline, name=image_layer.name + "_cp_outlines", visible=image_layer.visible, scale=image_layer.scale)

      def show_table(cell_counts):
        table_data = []
        for layer, count in zip(selected_image_layers, cell_counts):
          table_data.append([layer.name, count])
        result_widget = create_table_with_csv_export(["Name", "Cell count"], table_data)
        viewer.window.add_dock_widget(result_widget, name="cell counting result")
      
      def clear_previous():
        if clear_previous_segmentations:
          layer_names = [layer.name for layer in viewer.layers]
          for layer_name in layer_names:
            if any([cp_string in layer_name for cp_string in CP_STRINGS]):
              viewer.layers.remove(viewer.layers[layer_name])

      def cellpose_calculation_finished_callback(result):
        from cellpose.utils import masks_to_outlines

        masks, cell_counts = result
        if output_outlines:
          show_outlines(masks_to_outlines(masks) * masks)
        show_table(cell_counts)
      
      def regression_calculation_finished_callback(result):
        show_table(result)

      images = []
      for layer in selected_image_layers:
        images.append(layer.data)

      if use_regression_model:
        cp_worker = get_cell_counts_regression(images, model_path)
        cp_worker.returned.connect(regression_calculation_finished_callback)
      else:
        clear_previous()
        cp_worker = get_masks_and_cell_counts_cellpose(
          images, str(model_path.resolve()), [max(0, main_channel), max(0, optional_nuclear_channel)],
          cellprob_threshold=cellprob_threshold, model_match_threshold=model_match_threshold)
        cp_worker.returned.connect(cellpose_calculation_finished_callback)
      cp_worker.start()

  return widget


@napari_hook_implementation()
def napari_experimental_provide_dock_widget():
    return widget_wrapper, {'name': 'cell counting'}

