import traceback
import gzip
from timeit import default_timer

import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtCore as QtCore
from PyQt5.QtCore import Qt

from PyQt5.QtWidgets import (QWidget, QMainWindow, QFileDialog,
                             QSpacerItem, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QHBoxLayout,
                             QScrollArea, QGridLayout, QMenuBar, QMenu, QAction, QApplication, QStatusBar, QLineEdit)
from PyQt5.QtGui import QMouseEvent, QImage
import PyQt5.QtGui as QtGui
import PyQt5.QtCore as QtCore


from custom_widgets import catch_exception
from configuration import read_config, make_default_config, save_cfg
from lib.texture import TextureArchive

from bw_model_viewer_widgets import RenderWindow, catch_exception, catch_exception_with_dialog, open_error_dialog
#from lib.model_rendering import Waterbox
from lib.bw_archive import BWArchive
PIKMIN2GEN = "Resource Files (*.res)"


class GenEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.res_file = None

        self.setup_ui()
        self.texture_archive = None

        try:
            self.configuration = read_config()
            print("Config file loaded")
        except FileNotFoundError as e:
            print("No config file found, creating default config...")
            self.configuration = make_default_config()

        self.pathsconfig = self.configuration["default paths"]
        self.editorconfig = self.configuration["gen editor"]
        self.current_gen_path = None

        self.current_coordinates = None
        self.editing_windows = {}
        self.add_object_window = None
        self.object_to_be_added = None

        self.history = EditorHistory(20)
        self.edit_spawn_window = None

        self._window_title = ""
        self._user_made_change = False
        self._justupdatingselectedobject = False

        self.addobjectwindow_last_selected = None

        self.lastshow = None

    @catch_exception
    def reset(self):
        self.history.reset()
        self.object_to_be_added = None
        self.model_list.clear()
        self.res_file = None
        #self.pikmin_gen_view.reset(keep_collision=True)

        self.current_coordinates = None

        #for key, val in self.editing_windows.items():
        #    val.destroy()

        self.editing_windows = {}

        #if self.add_object_window is not None:
        #    self.add_object_window.destroy()
        #    self.add_object_window = None

        #if self.edit_spawn_window is not None:
        #    self.edit_spawn_window.destroy()
        #    self.edit_spawn_window = None

        self.current_gen_path = None
        #self.pik_control.reset_info()
        #self.pik_control.button_add_object.setChecked(False)
        #self.pik_control.button_move_object.setChecked(False)
        self._window_title = ""
        self._user_made_change = False

        self.addobjectwindow_last_selected = None

    def set_base_window_title(self, name):
        self._window_title = name
        if name != "":
            self.setWindowTitle("Battalion Wars Model Viewer - "+name)
        else:
            self.setWindowTitle("Battalion Wars Model Viewer")

    def set_has_unsaved_changes(self, hasunsavedchanges):
        if hasunsavedchanges and not self._user_made_change:
            self._user_made_change = True

            if self._window_title != "":
                self.setWindowTitle("Pikmin 2 Generators Editor [Unsaved Changes] - " + self._window_title)
            else:
                self.setWindowTitle("Pikmin 2 Generators Editor [Unsaved Changes] ")
        elif not hasunsavedchanges and self._user_made_change:
            self._user_made_change = False
            if self._window_title != "":
                self.setWindowTitle("Pikmin 2 Generators Editor - " + self._window_title)
            else:
                self.setWindowTitle("Pikmin 2 Generators Editor")

    def setup_ui(self):
        self.resize(1000, 800)
        self.set_base_window_title("")

        self.setup_ui_menubar()
        self.setup_ui_toolbar()

        self.centralwidget = QWidget(self)
        self.centralwidget.setObjectName("centralwidget")
        self.setCentralWidget(self.centralwidget)

        #self.pikmin_gen_view = GenMapViewer(self.centralwidget)
        self.waterbox_renderer = RenderWindow(self.centralwidget)
        self.model_list = QtWidgets.QListWidget(self.centralwidget)
        self.waterbox_renderer.setMinimumWidth(400)
        self.model_list.setMaximumWidth(200)
        self.model_list.setFocusPolicy(Qt.NoFocus)

        self.horizontalLayout = QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.horizontalLayout.addWidget(self.waterbox_renderer)

        spacerItem = QSpacerItem(10, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.horizontalLayout.addItem(spacerItem)
        self.horizontalLayout.addWidget(self.model_list)

        #self.pik_control = PikminSideWidget(self)
        #self.horizontalLayout.addWidget(self.pik_control)

        #QtWidgets.QShortcut(Qt.CTRL + Qt.Key_E, self).activated.connect(self.action_open_editwindow)
        #QtWidgets.QShortcut(Qt.Key_M, self).activated.connect(self.shortcut_move_objects)
        #QtWidgets.QShortcut(Qt.Key_G, self).activated.connect(self.action_ground_objects)
        #QtWidgets.QShortcut(Qt.CTRL + Qt.Key_A, self).activated.connect(self.shortcut_open_add_item_window)
        self.statusbar = QStatusBar(self)
        self.statusbar.setObjectName("statusbar")
        self.setStatusBar(self.statusbar)

        self.connect_actions()

    def setup_ui_menubar(self):
        self.menubar = QMenuBar(self)
        self.file_menu = QMenu(self)
        self.file_menu.setTitle("File")

        #save_file_shortcut = QtWidgets.QShortcut(Qt.CTRL + Qt.Key_S, self.file_menu)
        #save_file_shortcut.activated.connect(self.button_save_level)
        #QtWidgets.QShortcut(Qt.CTRL + Qt.Key_O, self.file_menu).activated.connect(self.button_load_level)
        #QtWidgets.QShortcut(Qt.CTRL + Qt.Key_Alt + Qt.Key_S, self.file_menu).activated.connect(self.button_save_level_as)

        self.file_load_action = QAction("Load", self)
        self.save_file_action = QAction("Save", self)
        self.save_file_as_action = QAction("Save As", self)
        #self.save_file_action.setShortcut("Ctrl+S")
        #self.file_load_action.setShortcut("Ctrl+O")
        #self.save_file_as_action.setShortcut("Ctrl+Alt+S")

        self.file_load_action.triggered.connect(self.button_load_level)
        #self.save_file_action.triggered.connect(self.button_save_level)
        #self.save_file_as_action.triggered.connect(self.button_save_level_as)

        self.file_menu.addAction(self.file_load_action)
        #self.file_menu.addAction(self.save_file_action)
        #self.file_menu.addAction(self.save_file_as_action)


        # ------ Collision Menu
        """self.collision_menu = QMenu(self.menubar)
        self.collision_menu.setTitle("Geometry")
        self.collision_load_action = QAction("Load .OBJ", self)
        self.collision_load_action.triggered.connect(self.button_load_collision)
        self.collision_menu.addAction(self.collision_load_action)
        self.collision_load_grid_action = QAction("Load GRID.BIN", self)
        self.collision_load_grid_action.triggered.connect(self.button_load_collision_grid)
        self.collision_menu.addAction(self.collision_load_grid_action)"""


        # Misc
        self.misc_menu = QMenu(self.menubar)
        self.misc_menu.setTitle("Misc")


        self.menubar.addAction(self.file_menu.menuAction())
        #self.menubar.addAction(self.collision_menu.menuAction())
        #self.menubar.addAction(self.misc_menu.menuAction())
        self.setMenuBar(self.menubar)

    def setup_ui_toolbar(self):
        # self.toolbar = QtWidgets.QToolBar("Test", self)
        # self.toolbar.addAction(QAction("TestToolbar", self))
        # self.toolbar.addAction(QAction("TestToolbar2", self))
        # self.toolbar.addAction(QAction("TestToolbar3", self))

        # self.toolbar2 = QtWidgets.QToolBar("Second Toolbar", self)
        # self.toolbar2.addAction(QAction("I like cake", self))

        # self.addToolBar(self.toolbar)
        # self.addToolBarBreak()
        # self.addToolBar(self.toolbar2)
        pass

    def connect_actions(self):
        #self.model_list.itemClicked.connect(self.select_model)
        self.model_list.itemSelectionChanged.connect(self.select_model)
        self.waterbox_renderer.camera_moved.connect(self.update_cam_pos)

        return
        #self.pikmin_gen_view.select_update.connect(self.action_update_info)
        self.pik_control.lineedit_coordinatex.textChanged.connect(self.create_field_edit_action("coordinatex"))
        self.pik_control.lineedit_coordinatey.textChanged.connect(self.create_field_edit_action("coordinatey"))
        self.pik_control.lineedit_coordinatez.textChanged.connect(self.create_field_edit_action("coordinatez"))

        self.pik_control.lineedit_rotationx.textChanged.connect(self.create_field_edit_action("rotationx"))
        self.pik_control.lineedit_rotationy.textChanged.connect(self.create_field_edit_action("rotationy"))
        self.pik_control.lineedit_rotationz.textChanged.connect(self.create_field_edit_action("rotationz"))

        #self.pikmin_gen_view.position_update.connect(self.action_update_position)

        #self.pikmin_gen_view.customContextMenuRequested.connect(self.mapview_showcontextmenu)
        self.pik_control.button_edit_object.pressed.connect(self.action_open_editwindow)

        self.pik_control.button_add_object.pressed.connect(self.button_open_add_item_window)
        self.pik_control.button_move_object.pressed.connect(self.button_move_objects)
        #self.pikmin_gen_view.move_points.connect(self.action_move_objects)
        #self.pikmin_gen_view.create_waypoint.connect(self.action_add_object)
        self.pik_control.button_ground_object.pressed.connect(self.action_ground_objects)
        self.pik_control.button_remove_object.pressed.connect(self.action_delete_objects)

        """delete_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(Qt.Key_Delete), self)
        delete_shortcut.activated.connect(self.action_delete_objects)

        undo_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(Qt.CTRL + Qt.Key_Z), self)
        undo_shortcut.activated.connect(self.action_undo)

        redo_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(Qt.CTRL + Qt.Key_Y), self)
        redo_shortcut.activated.connect(self.action_redo)"""

        #self.pikmin_gen_view.rotate_current.connect(self.action_rotate_object)

    #@catch_exception
    def button_load_level(self):
        filepath, choosentype = QFileDialog.getOpenFileName(
            self, "Open File",
            self.pathsconfig["gen"],
            "Resource Files (*.res;*.res.gz);;All files (*)")

        if filepath:
            print("Resetting editor")
            self.reset()
            print("Reset done")
            print("Chosen file type:", choosentype)
            if filepath.endswith(".gz"):
                openfunc = gzip.open
            else:
                openfunc = open

            with openfunc(filepath, "rb") as f:
                try:
                    self.res_file = BWArchive(f)
                    self.texture_archive = TextureArchive(self.res_file)

                    for model in self.res_file.models:
                        self.model_list.addItem(str(model.res_name, encoding="ascii"))
                    self.waterbox_renderer.texarchive = self.texture_archive


                    print("File loaded")
                    # self.bw_map_screen.update()
                    # path_parts = path.split(filepath)
                    self.set_base_window_title(filepath)
                    self.pathsconfig["gen"] = filepath
                    save_cfg(self.configuration)
                    self.current_gen_path = filepath

                except Exception as error:
                    print("Error appeared while loading:", error)
                    traceback.print_exc()
                    open_error_dialog(str(error), self)

    @catch_exception
    def select_model(self):
        #print("selected", curr, self.model_list.currentRow())

        row = self.model_list.currentRow()

        self.waterbox_renderer.create_drawlist(self.res_file.models[row])

    def keyPressEvent(self, event: QtGui.QKeyEvent):

        if event.key() == Qt.Key_Shift:
            self.waterbox_renderer.shift_is_pressed = True
        #elif event.key() == Qt.Key_R:
        #    self.pikmin_gen_view.rotation_is_pressed = True

        if event.key() == Qt.Key_W:
            self.waterbox_renderer.MOVE_FORWARD = 1
        elif event.key() == Qt.Key_S:
            self.waterbox_renderer.MOVE_BACKWARD = 1
        elif event.key() == Qt.Key_A:
            self.waterbox_renderer.MOVE_LEFT = 1
        elif event.key() == Qt.Key_D:
            self.waterbox_renderer.MOVE_RIGHT = 1
        elif event.key() == Qt.Key_Q:
            self.waterbox_renderer.MOVE_UP = 1
        elif event.key() == Qt.Key_E:
            self.waterbox_renderer.MOVE_DOWN = 1

        #if event.key() == Qt.Key_Plus:
        #    self.pikmin_gen_view.zoom_in()
        #elif event.key() == Qt.Key_Minus:
        #    self.pikmin_gen_view.zoom_out()

    def keyReleaseEvent(self, event: QtGui.QKeyEvent):
        if event.key() == Qt.Key_Shift:
            self.waterbox_renderer.shift_is_pressed = False
        #elif event.key() == Qt.Key_R:
        #    self.pikmin_gen_view.rotation_is_pressed = False

        if event.key() == Qt.Key_W:
            self.waterbox_renderer.MOVE_FORWARD = 0
        elif event.key() == Qt.Key_S:
            self.waterbox_renderer.MOVE_BACKWARD = 0
        elif event.key() == Qt.Key_A:
            self.waterbox_renderer.MOVE_LEFT = 0
        elif event.key() == Qt.Key_D:
            self.waterbox_renderer.MOVE_RIGHT = 0
        elif event.key() == Qt.Key_Q:
            self.waterbox_renderer.MOVE_UP = 0
        elif event.key() == Qt.Key_E:
            self.waterbox_renderer.MOVE_DOWN = 0


    @catch_exception
    def mapview_showcontextmenu(self, position):
        context_menu = QMenu(self)
        action = QAction("Copy Coordinates", self)
        action.triggered.connect(self.action_copy_coords_to_clipboard)
        context_menu.addAction(action)
        context_menu.exec(self.mapToGlobal(position))
        context_menu.destroy()

    def action_copy_coords_to_clipboard(self):
        if self.current_coordinates is not None:
            QApplication.clipboard().setText(", ".join(str(x) for x in self.current_coordinates))

    def action_update_position(self, event, pos):
        self.current_coordinates = pos
        self.statusbar.showMessage(str(pos))

    def update_cam_pos(self, x, y, z):
        if self.lastshow is None or default_timer() - self.lastshow > 1/5.0:
            self.statusbar.showMessage(str((x,y,z)))
            self.lastshow = default_timer()


class EditorHistory(object):
    def __init__(self, historysize):
        self.history = []
        self.step = 0
        self.historysize = historysize

    def reset(self):
        del self.history
        self.history = []
        self.step = 0

    def _add_history(self, entry):
        if self.step == len(self.history):
            self.history.append(entry)
            self.step += 1
        else:
            for i in range(len(self.history) - self.step):
                self.history.pop()
            self.history.append(entry)
            self.step += 1
            assert len(self.history) == self.step

        if len(self.history) > self.historysize:
            for i in range(len(self.history) - self.historysize):
                self.history.pop(0)
                self.step -= 1

    def add_history_addobject(self, pikobject):
        self._add_history(("AddObject", pikobject))

    def add_history_removeobjects(self, objects):
        self._add_history(("RemoveObjects", objects))

    def history_undo(self):
        if self.step == 0:
            return None

        self.step -= 1
        return self.history[self.step]

    def history_redo(self):
        if self.step == len(self.history):
            return None

        item = self.history[self.step]
        self.step += 1
        return item


if __name__ == "__main__":
    import sys
    import platform

    app = QApplication(sys.argv)
    if platform.system() == "Windows":
        import ctypes
        myappid = 'P2GeneratorsEditor'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    with open("log.txt", "w") as f:
        #sys.stdout = f
        #sys.stderr = f
        print("Python version: ", sys.version)
        pikmin_gui = GenEditor()
        pikmin_gui.setWindowIcon(QtGui.QIcon('resources/icon.ico'))
        pikmin_gui.show()
        err_code = app.exec()

    sys.exit(err_code)