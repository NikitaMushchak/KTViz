import json
import sys
import time

import math
from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import QWidget, QApplication, QVBoxLayout, QPushButton, QDoubleSpinBox

from konverter import coords_global

hmi_data = {
    "wind_direction": 189.0,
    "wind_speed": 1.1,
    "tide_direction": 0,
    "tide_speed": 0,
    "swell": 1,
    "visibility": 13.0
}

settings = {
    "maneuver_calculation": {
        "priority": 0,
        "maneuver_way": 2,
        "safe_diverg_dist": 3.0,
        "minimal_speed": 3.0,
        "maximal_speed": 30.0,
        "max_course_delta": 70.0,
        "time_advance": 300,
        "can_leave_route": True,
        "max_route_deviation": 3.3,
        "circulation_radius": 0.4
    },
    "safety_control": {
        "cpa": 2.0,
        "tcpa": 180.0,
        "min_detect_dist": 15.0,
        "last_moment_dist": 2.0,
        "safety_zone": {
            "safety_zone_type": 0,
            "radius": 1.5
        }
    }
}

constraints = {
    "type": "FeatureCollection",
    "features": []
}


class Widget(QWidget):
    rs_signal = QtCore.pyqtSignal(QtCore.QSize)

    def __init__(self):
        super(Widget, self).__init__()
        self.layout = QVBoxLayout()
        # Latitude selection
        self.spinBox1 = QDoubleSpinBox(self)
        # Longitude selection
        self.spinBox2 = QDoubleSpinBox(self)
        # Time horizont selection
        self.spinBox3 = QDoubleSpinBox(self)
        self.keepDraw = False
        self.start = QPoint()
        self.end = QPoint()
        self.resize(600, 600)
        self.move(100, 100)
        self.setWindowTitle("Scenario drawer")
        self.type = 'our'
        self.image = []
        self.index = []
        # Scale: pixels in nm
        self.scale = 10
        # Preferred number of lines in grid
        self.n_line_x = 10
        self.n_line_y = 10
        # Time horizon
        self.time_horizon = 2
        self.initUI()

    def initUI(self):
        imageSize = QtCore.QSize(1366, 768)
        self.image = QtGui.QImage(imageSize, QtGui.QImage.Format_RGB32)
        self.image.fill(QtGui.qRgb(255, 255, 255))

        # Resize signal
        self.rs_signal.connect(self.resize_grid)

        # Clear button
        button = QPushButton('Clear field', self)
        button.move(0, 0)
        button.resize(140, 50)
        button.clicked.connect(self.clear_window)

        # Convert button
        button1 = QPushButton('Convert', self)
        button1.move(140, 0)
        button1.resize(140, 50)
        button1.clicked.connect(self.convert_file)

        # Latitude spinbox
        # lbe = QLabel(self)
        # lbe.setText('Start Latitude')
        # lbe.move(280, 0)
        self.spinBox1.setRange(0, 360)
        self.spinBox1.move(280, 0)
        self.spinBox1.setValue(60)
        self.spinBox1.setSingleStep(0.01)

        # Longitude spinbox
        self.spinBox2.setRange(0, 360)
        self.spinBox2.move(280, 25)
        self.spinBox2.setValue(30)
        self.spinBox2.setSingleStep(0.01)

        # Time horizont
        self.spinBox3.setRange(0, 10)
        self.spinBox3.move(360, 15)
        self.spinBox3.setValue(2)
        self.spinBox3.setSingleStep(0.1)
        self.spinBox3.valueChanged.connect(self.update_values)

        self.draw_grid()
        
    def update_values(self):
        """
        Updating drawing params
        :return:
        """
        self.time_horizon = self.spinBox3.value()
        print(self.time_horizon)

    def resizeEvent(self, event):
        """
        event onResize
        :param event:
        :return:
        """
        self.rs_signal.emit(self.size())

    def resize_grid(self):
        """
        re-draws grid for new size
        :return:
        """
        self.clear_window()
        self.draw_grid()

    def clear_window(self):
        self.image.fill(QtGui.qRgb(255, 255, 255))
        self.type = 'our'
        self.index = []
        self.update()
        self.draw_grid()

    def draw_grid(self):
        """
        This function draws nm grid
        :return:
        """
        painter = QPainter(self.image)
        # Optimal step — 60 pixels
        optimal_step = 60
        self.n_line_x = round(self.width() / optimal_step)
        self.n_line_y = round(self.height() / optimal_step)
        stepw = self.width() / self.n_line_x
        steph = self.height() / self.n_line_y
        pen = QPen(Qt.black, 1, Qt.SolidLine)
        pen.setStyle(Qt.DashDotDotLine)
        painter.setPen(pen)
        for i in range(self.n_line_x+1):
            painter.drawLine(i*stepw, 0, i*stepw, self.height())
            painter.drawText(i*stepw, self.n_line_y*steph - 10,
                             str(round(i*stepw / self.scale, 2)))
        for i in range(self.n_line_y + 1):
            painter.drawLine(0, i * steph, self.width(), i * steph)
            painter.drawText(self.n_line_x * stepw - 40, self.height() - i * steph,
                             str(round(i * steph / self.scale, 2)))

    def convert_file(self):
        """
        Makes JSON scenario files
        :return:
        """
        try:
            ship = [item for item in self.index if item['type'] == 'our'][0]
            targets = [item for item in self.index if item['type'] != 'our']
        except IndexError:
            print("Add ships first!")
            return
        data = []
        for target in targets:
            coords = coords_global(target['end'][0] - ship['end'][0],
                                   target['end'][1] - ship['end'][1],
                                   self.spinBox1.value(),
                                   self.spinBox2.value())
            dist = ((target['start'][1] - target['end'][1]) ** 2 +
                    (target['start'][0] - target['end'][0]) ** 2) ** 0.5 / self.scale
            vel = dist / self.time_horizon
            data.append({'id': 'target',
                         'cat': 0,
                         'lat': coords[0],
                         'lon': coords[1],
                         'SOG': vel,
                         'COG': math.degrees(math.atan2(target['start'][1] - target['end'][1],
                                                        target['start'][0] - target['end'][0])) + 90,
                         "first_detect_dist": 5.0,
                         "cross_dist": 0,
                         "timestamp": time.time()
                         })
        with open("target_data.json", "w") as fp:
            json.dump(data, fp)

        with open("nav_data.json", "w") as fp:
            course = math.degrees(math.atan2(ship['start'][1] - ship['end'][1],
                                                      ship['start'][0] - ship['end'][0])) + 90
            dist = ((ship['start'][1] - ship['end'][1])**2 +
                    (ship['start'][0] - ship['end'][0])**2)**0.5 / self.scale
            vel = dist / self.time_horizon
            route_item = {
                'begin_angle': course,
                'curve': 0,
                'duration': self.time_horizon*3600,
                'lat': self.spinBox1.value(),
                'lon': self.spinBox2.value(),
                'length': dist,
                "port_dev": 2,
                "starboard_dev": 2
            }

            with open("route_data.json", "w") as fr:
                json.dump({"items": [
                    route_item
                ],
                    'start_time': time.time()}, fr)

            json.dump({'cat': 0,
                       'lat': self.spinBox1.value(),
                       'lon': self.spinBox2.value(),
                       'SOG': vel,
                       'STW': vel,
                       'COG': course,
                       'heading': course,
                       "width": 16.0,
                       "length": 100.0,
                       "width_offset": 10.0,
                       "length_offset": 15.0,
                       'timestamp': time.time()}, fp)

        with open("constraints.json", "w") as fp:
            json.dump(constraints, fp)

        with open("hmi_data.json", "w") as fp:
            json.dump(hmi_data, fp)

        with open("settings.json", "w") as fp:
            json.dump(settings, fp)

    def closeEvent(self, event):
        print("Closed")

    def paintEvent(self, event, type='circle'):
        """
        Event handler for painter
        :param event:
        :param type:
        :return:
        """
        painter = QPainter(self)
        cur_size = QRect(0, 0, self.width(), self.height())
        temp = self.image.copy(cur_size)
        painter.drawImage(event.rect(), temp)
        # painter.drawLine(self.start, self.end)
        if self.type == 'our':
            pen = QPen(Qt.red, 2, Qt.SolidLine)
            painter.setPen(pen)
            painter.drawLine(self.start, self.end)
            painter.drawEllipse(self.end, 10, 10)
        elif self.type == 'foreign':
            pen = QPen(Qt.black, 2, Qt.SolidLine)
            painter.setPen(pen)
            painter.drawLine(self.start, self.end)
            painter.drawEllipse(self.end, 10, 10)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.keepDraw = True
            self.start = self.end = event.pos()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and self.keepDraw:
            painter = QPainter(self.image)
            if self.type == 'our':
                pen = QPen(Qt.red, 2, Qt.SolidLine)
                painter.setPen(pen)
                painter.drawLine(self.start, self.end)
                painter.drawEllipse(self.end, 10, 10)
                self.index.append({'type': self.type,
                                   'start': [self.start.x(), self.start.y()],
                                   'end': [self.end.x(), self.end.y()]})
                self.type = 'foreign'
            elif self.type == 'foreign':
                pen = QPen(Qt.black, 2, Qt.SolidLine)
                painter.setPen(pen)
                painter.drawLine(self.start, self.end)
                painter.drawEllipse(self.end, 10, 10)
                self.index.append({'type': self.type,
                                   'start': [self.start.x(), self.start.y()],
                                   'end': [self.end.x(), self.end.y()]})
            self.update()
            self.keepDraw = False
            # Append new obj to array

    def mouseMoveEvent(self, event):
        if (event.buttons() & QtCore.Qt.LeftButton) and self.keepDraw:
            self.end = event.pos()
        self.update()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    form = Widget()
    form.show()
    app.exec_()
