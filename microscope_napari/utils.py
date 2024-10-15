import numpy as np
import csv
import cv2
import os
import pickle

from magicgui.widgets import FloatSlider
from PyQt5.QtWidgets import QWidget, QFileDialog, QTableWidget, QVBoxLayout, QPushButton, QTableWidgetItem, QLabel, QHBoxLayout
from microscope_napari.workers import get_cell_shape_info


CP_STRINGS = [
  '_cp_masks', '_cp_outlines', '_cp_flows', '_cp_cellprob'
]
MAIN_CHANNEL_CHOICES = [
  ('average all channels', 0), ('0=red', 1), ('1=green', 2), ('2=blue', 3),
  ('3', 4), ('4', 5), ('5', 6), ('6', 7), ('7', 8), ('8', 9)
]
OPTIONAL_NUCLEAR_CHANNEL_CHOICES = [
  ('none', 0), ('0=red', 1), ('1=green', 2), ('2=blue', 3),
  ('3', 4), ('4', 5), ('5', 6), ('6', 7), ('7', 8), ('8', 9)
]


def generate_colormap(num_classes):
  colormap = np.zeros((num_classes + 1, 3))
  colormap[0] = np.zeros(3)
  for i in range(1, num_classes + 1):
    colormap[i] = np.random.randint(0, 256, size=3)
  return colormap


def csv_export_table(headers, rows):
  options = QFileDialog.Options()
  file_name, _ = QFileDialog.getSaveFileName(None, "Save CSV", "", "CSV Files (*.csv);;All Files (*)", options=options)

  if not bool(file_name): return

  with open(file_name, mode='w', newline='') as file:
    writer = csv.writer(file, delimiter=";")

    writer.writerow(headers)

    for row in rows:
      writer.writerow(row)


def export_images_with_masks(image_names, images, masks, opacity):
  folder = QFileDialog.getExistingDirectory(None, "Select folder")

  if not bool(folder): return

  for name, image, mask in zip(image_names, images, masks):
    image, mask = np.array(image), np.array(mask)

    # Generating colormap for mask
    num_classes = np.max(mask)
    colormap = generate_colormap(num_classes)
    
    # Creating the resulting image
    result_image = np.zeros_like(image)
    not_blending, blending = (mask == 0, mask != 0)
    result_image[not_blending] = image[not_blending]
    result_image[blending] = (1 - opacity) * image[blending] + opacity * colormap[mask[blending]]

    # Exporting the image
    export_path = os.path.join(folder, name + ".jpg")
    cv2.imwrite(export_path, result_image)


def export_pickle(data):
  options = QFileDialog.Options()
  file_name, _ = QFileDialog.getSaveFileName(None, "Save Pickle", "", "Pickle Files (*.pickle);;All Files (*)", options=options)

  if not bool(file_name): return

  with open(file_name, mode='wb') as file:
    pickle.dump(data, file)


def create_table_with_exports(header, data, images=None, masks=None) -> QWidget:
  # Csv export button
  export_csv_button = QPushButton("export to csv")
  export_csv_button.clicked.connect(lambda: csv_export_table(header, data))

  # Export masks opacity slider
  export_masks_opacity = QWidget()
  export_masks_opacity_layout = QHBoxLayout()
  export_masks_opacity_label = QLabel("exporting opacity")
  export_masks_opacity_slider = FloatSlider(min=0.0, max=1.0, step=0.01, value=0.5)

  export_masks_opacity_layout.addWidget(export_masks_opacity_label)
  export_masks_opacity_layout.addWidget(export_masks_opacity_slider.native)
  export_masks_opacity.setLayout(export_masks_opacity_layout)

  # Masks export button
  image_names = [row[0] for row in data]
  export_masks_button = QPushButton("export masks")

  def export_masks_clicked_callback():
    export_masks_button.setText("running...")
    export_images_with_masks(image_names, images, masks, export_masks_opacity_slider.value)
    export_masks_button.setText("export masks")

  export_masks_button.clicked.connect(export_masks_clicked_callback)

  # Shape export button
  export_shape_button = QPushButton("export shape info")

  def export_shape_clicked_callback():
    export_shape_button.setText("running...")
    worker = get_cell_shape_info(image_names, masks)
    worker.returned.connect(lambda result: csv_export_table(["Image name", "Cell Id", "Area", "Perimeter"], result))
    worker.returned.connect(lambda _: export_shape_button.setText("export shape info"))
    worker.start()
  
  export_shape_button.clicked.connect(export_shape_clicked_callback)

  # Cell counts table
  table_widget = QTableWidget()
  table_widget.setRowCount(len(data))
  table_widget.setColumnCount(len(header))
  table_widget.setHorizontalHeaderLabels(header)

  for i in range(len(data)):
    for j in range(len(data[i])):
      table_widget.setItem(i, j, QTableWidgetItem(str(data[i][j])))
  
  # Layout
  layout = QVBoxLayout()

  if images != None and masks != None:
    layout.addWidget(export_masks_opacity)
    layout.addWidget(export_masks_button)
    layout.addWidget(export_shape_button)
  
  layout.addWidget(export_csv_button)
  layout.addWidget(table_widget)

  # Container widget
  container_widget = QWidget()
  container_widget.setLayout(layout)

  return container_widget

