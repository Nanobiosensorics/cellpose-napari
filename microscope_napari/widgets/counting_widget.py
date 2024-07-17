import cv2
import numpy as np
import weakref

from typing import List

from magicgui import magicgui

from napari import Viewer
from napari.layers import Image
from napari_plugin_engine import napari_hook_implementation


def widget_wrapper():
  from microscope_napari.workers import get_masks_and_cell_counts_cellpose, get_cell_counts_regression
  from microscope_napari.utils import create_table_with_exports, MAIN_CHANNEL_CHOICES, OPTIONAL_NUCLEAR_CHANNEL_CHOICES, CP_STRINGS
  
  @magicgui(
    layout='vertical',
    selected_image_layers = dict(widget_type="ListEdit", label="choose image layers", layout="vertical", annotation=List[Image]),
    model_path = dict(widget_type='FileEdit', label='model path: ', tooltip='specify model path here'),
    use_regression_model = dict(widget_type='CheckBox', text='use regression model (lower settings are for cellpose only)', value=False),
    main_channel = dict(widget_type='ComboBox', label='channel to segment', choices=MAIN_CHANNEL_CHOICES, value=0, tooltip='choose channel with cells'),
    optional_nuclear_channel = dict(widget_type='ComboBox', label='optional nuclear channel', choices=OPTIONAL_NUCLEAR_CHANNEL_CHOICES, value=0, tooltip='optional, if available, choose channel with nuclei of cells'),
    cellprob_threshold = dict(widget_type='FloatSlider', name='cellprob_threshold', value=0.0, min=-8.0, max=8.0, step=0.2, tooltip='cell probability threshold (set lower to get more cells and larger cells)'),
    model_match_threshold = dict(widget_type='FloatSlider', name='model_match_threshold', value=27.0, min=0.0, max=30.0, step=0.2, tooltip='threshold on gradient match to accept a mask (set lower to get more cells)'),
    output_masks = dict(widget_type='CheckBox', text='output masks', value=True),
    should_clear_previous_results = dict(widget_type='CheckBox', text='clear previous results', value=True),
    call_button='start calculation'
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
    output_masks,
    should_clear_previous_results
  ):
      # cell counting result widgets (table and export button)
      if not hasattr(widget, "result_widgets"):
        widget.result_widgets = []

      # when async calculation starts we disable call button
      def disable_call_button():
        widget.call_button.native.setEnabled(False)
        widget.call_button.native.setText("running...")

      # after async calculation finished call button is enabled again
      def enable_call_button():
        widget.call_button.native.setEnabled(True)
        widget.call_button.native.setText("get counts")

      # adds cellpose masks to the napari viewer
      def show_masks(masks):
        for image_layer, mask in zip(selected_image_layers, masks):
          viewer.add_labels(mask, name=image_layer.name + "_cp_masks", visible=image_layer.visible, scale=image_layer.scale)

      # shows the report table with the cell counts and export
      def show_table(cell_counts, images=None, masks=None):
        table_data = []
        for layer, count in zip(selected_image_layers, cell_counts):
          table_data.append([layer.name, count])
        dock_widget = create_table_with_exports(["Name", "Cell count"], table_data, images, masks)
        result_widget = viewer.window.add_dock_widget(dock_widget, name="cell counting results")
        widget.result_widgets.append(weakref.ref(result_widget))
      
      # clears previous results if necessary
      def clear_previous_results():
        if not should_clear_previous_results: return

        # removing result widgets
        for result_widget_ref in widget.result_widgets:
          if result_widget_ref() != None:
            viewer.window.remove_dock_widget(widget=result_widget_ref())
        widget.result_widgets.clear()

        # removing mask layers
        layer_names = [layer.name for layer in viewer.layers]
        for layer_name in layer_names:
          if any([cp_string in layer_name for cp_string in CP_STRINGS]):
            viewer.layers.remove(viewer.layers[layer_name])

      # showing results after cellpose finished (table and masks)
      def cellpose_calculation_finished_callback(result):
        masks, cell_counts = result
        enable_call_button()
        if output_masks:
          show_masks(masks)
        show_table(cell_counts, images, masks)
      
      # showing results when regression finished (table)
      def regression_calculation_finished_callback(result):
        enable_call_button()
        show_table(result)

      # before starting any calculation we should disable call button
      disable_call_button()

      # extracting images from the selected napari layers
      images = []
      for layer in selected_image_layers:
        image = np.array(layer.data)
        # convert to RGB if needed
        if len(image.shape) == 2:
          image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB) # grayscale
        elif len(image.shape) == 3 and image.shape[-1] == 4:
          image = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB) # rgba
        images.append(image)

      # clearing masks and tables if necessary
      clear_previous_results()

      # running the corresponding calculations
      if use_regression_model:
        cp_worker = get_cell_counts_regression(images, model_path)
        cp_worker.returned.connect(regression_calculation_finished_callback)
      else:
        cp_worker = get_masks_and_cell_counts_cellpose(
          images, str(model_path.resolve()), [max(0, main_channel), max(0, optional_nuclear_channel)],
          cellprob_threshold=cellprob_threshold, model_match_threshold=model_match_threshold)
        cp_worker.returned.connect(cellpose_calculation_finished_callback)
      cp_worker.start()

  return widget


@napari_hook_implementation()
def napari_experimental_provide_dock_widget():
    return widget_wrapper, {'name': 'cell counting'}