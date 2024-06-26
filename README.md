# Installation

Napari needs to be set up on your machine in order to install this plugin.

If you do not have napari installed it can be done following [this article](https://napari.org/stable/tutorials/fundamentals/installation.html).

## Napari plugin manager (recommended)

Search for `microscope-napari` and click install. 
After completed napari needs to be restarted to activate the plugin.

![kép](https://github.com/Nanobiosensorics/microscope-napari/assets/65455148/5438235d-522e-458e-806d-89eaaa027be2)

## Pip package manager

You can install the plugin in the environment where napari is set up with command.
```
pip install microscope-napari
```
If you have a conda environment use anaconda prompt.

# Usage

You can access plugin's functionalities in the upper menu.

![kép](https://github.com/Nanobiosensorics/microscope-napari/assets/65455148/dace1014-6ac0-4797-b0b5-00a56cbc6b61)

## Cellpose

Images can be segmented with custom and built-in cellpose models.

![kép](https://github.com/Nanobiosensorics/microscope-napari/assets/65455148/82d300b9-c523-4b0a-bf44-0f3bfdadae07)

For further information make sure to check out ![cellpose](https://github.com/MouseLand/cellpose) and ![cellpose-napari](https://github.com/MouseLand/cellpose-napari) plugin.

## Cell counting

Cells can be counted in images with custom cellpose models. Multiple samples can be provided as input, the results can be exported as csv.
Thresholds can be used to fine-tune cellpose dynamics and get better results.

![kép](https://github.com/Nanobiosensorics/microscope-napari/assets/65455148/d4803e93-127a-413b-b96f-0ccf5cdd8408)
