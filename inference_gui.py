#!/usr/bin/python3
# -*- coding: utf-8 -*-
from __future__ import division, print_function, unicode_literals
from PyQt5.QtCore import Qt, QRect, pyqtSignal, QSize
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QSizePolicy
from PyQt5.QtWidgets import QPushButton, QLabel, QFileDialog, QSplitter, QScrollArea
from PyQt5.QtWidgets import QListView, QRadioButton, QSlider
from PyQt5.QtGui import QPainter, QColor
from skimage.io import imread
from extended_qt_delegate import ImageableStyledItemDelegate
from inferencing_list import InferencingList
from classified_image_datatype import ClassifiedImageBundle
import sys
import os
import re


class ImageWidget(QWidget):
    def __init__(self, img):
        super().__init__()
        self.img = img
        self.rect = QRect(0, 0, 128, 128)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum))
        self.set_img(img)

    def set_img(self, img):
        self.img = img
        if self.img:
            self.setMaximumSize(self.img.size())
            self.setFixedSize(self.img.size())
            self.rect = QRect(0, 0, self.img.width(), self.img.height())
        else:
            self.rect = QRect(0, 0, 128, 128)
            self.setFixedSize(QSize(128, 128))
        self.updateGeometry()
        self.update()

    def minimumSizeHint(self):
        if self.img:
            return QSize(self.img.width(), self.img.height())
        else:
            return QSize(20, 20)

    def sizeHint(self):
        return self.minimumSizeHint()

    def paintEvent(self, e):
        qp = QPainter()
        qp.begin(self)
        self.draw(qp)
        qp.end()

    def draw(self, qp):
        if self.img:
            qp.drawImage(0, 0, self.img)


class ThumbnailList(QWidget):
    img_selected = pyqtSignal(ClassifiedImageBundle)

    def __init__(self):
        super().__init__()
        self.images_list = InferencingList()
        self.selected = 0
        self.thumb_width = 128
        size_policy = QSizePolicy()
        size_policy.setVerticalPolicy(QSizePolicy.MinimumExpanding)
        self.setSizePolicy(size_policy)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(4, 4, 4, 0)
        size_row = QHBoxLayout()
        slider_label = QLabel()
        slider_label.setText("Thumbnailgröße:")
        slider_label.setMinimumHeight(12)
        size_row.addWidget(slider_label, alignment=Qt.AlignLeading)
        slider = QSlider()
        slider.setOrientation(Qt.Horizontal)
        slider.setMinimum(64)
        slider.setMaximum(512)
        size_row.addWidget(slider, alignment=Qt.AlignLeading)
        self.thumb_size_label = QLabel()
        size_row.addWidget(self.thumb_size_label, alignment=Qt.AlignLeading)
        slider.valueChanged.connect(self.slider_changed)
        slider.setValue(self.thumb_width)
        self.layout.addLayout(size_row)
        self.t_list = QListView()
        self.t_list.setMinimumWidth(self.thumb_width)
        self.t_list.setSizePolicy(QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Expanding))
        self.t_list.setMouseTracking(True)
        self.t_list.setItemDelegate(ImageableStyledItemDelegate(parent=self.t_list))
        self.t_list.setSpacing(1)
        self.t_list.setModel(self.images_list)
        self.layout.addWidget(self.t_list, stretch=1)
        self.setLayout(self.layout)

    def load_images(self, path):
        self.images_list.clear()
        filename_regex = re.compile(r".*\.(jpg|JPG|jpeg|JPEG|png|PNG|bmp|BMP)$")
        for filename in os.listdir(path):
            if filename_regex.match(filename):
                np_img = imread(os.path.join(path, filename))
                if len(np_img.shape) < 2:
                    continue
                img_bundle = ClassifiedImageBundle()
                img_bundle.set_np_image(np_img, self.thumb_width)
                img_bundle.selected.connect(self.select_image)
                self.images_list.append(img_bundle)
        self.t_list.setMinimumWidth(self.thumb_width)
        self.t_list.updateGeometry()
        if not self.images_list.is_empty():
            self.img_selected.emit(self.images_list.data_by_int_index(0))

    def select_image(self, image_bundle):
        self.img_selected.emit(image_bundle)

    def stop_worker_thread(self):
        self.images_list.stop_worker_thread()

    def slider_changed(self, value):
        self.thumb_size_label.setText(str(value))


class PreviewArea(QWidget):
    def __init__(self):
        super().__init__()
        size_policy = QSizePolicy()
        size_policy.setHorizontalPolicy(QSizePolicy.Expanding)
        size_policy.setVerticalPolicy(QSizePolicy.Expanding)
        self.setSizePolicy(size_policy)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 4, 0, 0)
        this_row = QHBoxLayout()
        this_row.addSpacing(4)
        selection_label = QLabel()
        selection_label.setText("Dieses Bild: ")
        this_row.addWidget(selection_label)
        keep_button = QRadioButton()
        keep_button.setText("behalten")
        keep_button.setMaximumHeight(14)
        this_row.addWidget(keep_button)
        discard_button = QRadioButton()
        discard_button.setText("löschen")
        discard_button.setMaximumHeight(14)
        this_row.addWidget(discard_button)
        this_row.addStretch(1)
        layout.addLayout(this_row)
        img_scroll_area = QScrollArea()
        img_scroll_area.setSizePolicy(QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding))
        self.img_widget = ImageWidget(None)
        img_scroll_area.setWidget(self.img_widget)
        layout.addWidget(img_scroll_area, stretch=1)
        layout.addStretch()
        self.setLayout(layout)

    def set_image(self, img_d):
        self.img_widget.set_img(img_d.get_image())
        self.update()


class InferenceInterface(QWidget):
    def __init__(self):
        super().__init__(flags=Qt.WindowTitleHint | Qt.WindowCloseButtonHint |
                               Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint)
        self.path = None
        self.setGeometry(200, 100, 1280, 720)
        self.setWindowTitle("Unsharp Detector")
        main_layout = QVBoxLayout()
        path_row = QHBoxLayout()
        open_button = QPushButton()
        open_button.setText("Pfad auswählen")
        open_button.clicked.connect(self.open_path_select_dialog)
        path_row.addWidget(open_button, alignment=Qt.AlignLeading)
        self.path_label = QLabel()
        path_row.addWidget(self.path_label, alignment=Qt.AlignLeading)
        path_row.addStretch()
        delete_button = QPushButton()
        delete_button.setText("Bilder aufräumen")
        delete_button.setStyleSheet("background-color: #BB0000; color: #FFFFFF; font-weight: bold;")
        path_row.addWidget(delete_button, alignment=Qt.AlignTrailing)
        main_layout.addLayout(path_row, stretch=0)
        image_splitter = QSplitter()
        image_splitter.setOrientation(Qt.Horizontal)
        self.thumbnail_list = ThumbnailList()
        self.thumbnail_list.img_selected.connect(self.img_selected)
        image_splitter.addWidget(self.thumbnail_list)
        self.preview_area = PreviewArea()
        image_splitter.addWidget(self.preview_area)
        image_splitter.setSizes([176, self.width()-176])
        image_splitter.setSizePolicy(QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding))
        main_layout.addWidget(image_splitter)
        self.setLayout(main_layout)
        self.show()

    def open_path_select_dialog(self):
        dialog = QFileDialog()
        dialog.setWindowTitle("Pfad der Bilder auswählen")
        dialog.setModal(False)
        dialog.setFileMode(QFileDialog.Directory)
        if dialog.exec():
            self.path = dialog.selectedFiles()[0]
            self.thumbnail_list.load_images(self.path)
            self.path_label.setText("Path: " + self.path)
        else:
            self.path = None
            self.path_label.setText("Kein Pfad ausgewählt.")

    def img_selected(self, img_d):
        self.preview_area.set_image(img_d)

    def closeEvent(self, close_event):
        self.thumbnail_list.stop_worker_thread()
        super().closeEvent(close_event)


if __name__ == "__main__":
    app_object = QApplication(sys.argv)
    window = InferenceInterface()
    status = app_object.exec_()
