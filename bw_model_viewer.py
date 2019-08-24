import traceback
import gzip
import os
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
from lib.texture import Texture
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
        #self.editorconfig = self.configuration["gen editor"]
        self.current_gen_path = None

        self.current_coordinates = None
        self.editing_windows = {}
        self.add_object_window = None
        self.object_to_be_added = None

        self.edit_spawn_window = None

        self._window_title = ""
        self._user_made_change = False
        self._justupdatingselectedobject = False

        self.addobjectwindow_last_selected = None

        self.lastshow = None
        self.modelindices = {}

    @catch_exception
    def reset(self):
        self.object_to_be_added = None
        self.model_list.clear()
        self.res_file = None
        self.current_coordinates = None

        self.editing_windows = {}

        self.current_gen_path = None
        self._window_title = ""
        self._user_made_change = False

        self.addobjectwindow_last_selected = None
        self.waterbox_renderer.reset()
        if self.texture_archive is not None:
            self.texture_archive.reset()

        if self.res_file is not None:
            del self.res_file
            self.res_file = None

    def set_base_window_title(self, name):
        self._window_title = name
        if name != "":
            self.setWindowTitle("Battalion Wars Model Viewer - "+name)
        else:
            self.setWindowTitle("Battalion Wars Model Viewer")

    def set_has_unsaved_changes(self, hasunsavedchanges):
        return

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

        self.statusbar = QStatusBar(self)
        self.statusbar.setObjectName("statusbar")
        self.setStatusBar(self.statusbar)

        self.connect_actions()

    def setup_ui_menubar(self):
        self.menubar = QMenuBar(self)
        self.file_menu = QMenu(self)
        self.file_menu.setTitle("File")

        self.file_load_action = QAction("Load", self)
        self.save_file_action = QAction("Save", self)
        self.save_file_as_action = QAction("Save As", self)
        #self.save_file_action.setShortcut("Ctrl+S")
        #self.file_load_action.setShortcut("Ctrl+O")
        #self.save_file_as_action.setShortcut("Ctrl+Alt+S")

        self.file_load_action.triggered.connect(self.button_load_level)

        self.file_menu.addAction(self.file_load_action)


        # Misc
        self.model_menu = QMenu(self.menubar)
        self.model_menu.setTitle("Model")
        self.export_model_obj_action = QAction("Export current as OBJ", self)
        self.export_model_obj_action.triggered.connect(self.export_model_obj)
        self.model_menu.addAction(self.export_model_obj_action)

        self.export_model_obj_batch_action = QAction("Export All as OBJ", self)
        self.export_model_obj_batch_action.triggered.connect(self.export_model_obj_batch)
        self.model_menu.addAction(self.export_model_obj_batch_action)


        self.texturemenu = QMenu(self.menubar)
        self.texturemenu.setTitle("Textures")
        self.export_tex_action = QAction("Export All Textures as PNG", self)
        self.export_tex_action.triggered.connect(self.export_all_textures)
        self.texturemenu.addAction(self.export_tex_action)

        self.menubar.addAction(self.file_menu.menuAction())
        self.menubar.addAction(self.model_menu.menuAction())
        self.menubar.addAction(self.texturemenu.menuAction())

        #self.menubar.addAction(self.collision_menu.menuAction())
        #self.menubar.addAction(self.misc_menu.menuAction())
        self.setMenuBar(self.menubar)

    @catch_exception
    def export_model_obj(self, bool):
        filepath = QFileDialog.getExistingDirectory(
            self, "Open Directory",
            self.pathsconfig["exportedModels"])

        if filepath:
            if self.waterbox_renderer.main_model is not None:
                self.waterbox_renderer.main_model.export_obj(filepath, self.waterbox_renderer.texarchive)
                self.pathsconfig["exportedModels"] = filepath
                save_cfg(self.configuration)

    @catch_exception_with_dialog
    def export_model_obj_batch(self, bool):
        filepath = QFileDialog.getExistingDirectory(
            self, "Open Directory",
            self.pathsconfig["exportedModels"])

        if filepath:
            i = 0
            total = len(self.res_file.models)

            for model in self.res_file.models:

                QtCore.QCoreApplication.processEvents()
                i+=1
                name = str(bytes(model.res_name).strip(), encoding="ascii")

                self.waterbox_renderer.create_drawlist(model, isbw1=self.res_file.is_bw())
                #self.waterbox_renderer.do_redraw()

                folderpath = os.path.join(filepath, name)
                os.makedirs(folderpath, exist_ok=True)
                self.statusbar.showMessage("Exporting {0} ({1} out of {2})".format(name, i, total))
                self.waterbox_renderer.main_model.export_obj(folderpath, self.waterbox_renderer.texarchive)
            self.waterbox_renderer.do_redraw()
            self.pathsconfig["exportedModels"] = filepath
            save_cfg(self.configuration)
            self.statusbar.showMessage("Finished", 3000)

    def setup_ui_toolbar(self):
        pass

    def connect_actions(self):
        #self.model_list.itemClicked.connect(self.select_model)
        self.model_list.itemSelectionChanged.connect(self.select_model)
        #self.waterbox_renderer.camera_moved.connect(self.update_cam_pos)

        return

    @catch_exception_with_dialog
    def export_all_textures(self, _):
        if self.res_file is None:
            return

        filepath = QFileDialog.getExistingDirectory(
            self, "Open Directory",
            self.pathsconfig["exportedModels"])
        isbw = self.res_file.is_bw()

        curr = 0
        total_tex = len(self.texture_archive.textures)
        if filepath and self.texture_archive is not None:
            for texname, texentry in self.texture_archive.textures.items():
                curr += 1
                QtCore.QCoreApplication.processEvents()

                tex = Texture(texname)
                if isbw:
                    tex.from_file_bw1(texentry.fileobj)
                else:
                    tex.from_file(texentry.fileobj)
                filename = str(texname.strip(b"\x00"), encoding="ascii")+".png"
                outpath = os.path.join(filepath, filename)

                tex.dump_to_file(outpath)
                self.statusbar.showMessage("Extracted {0} ({1} of {2})".format(
                    filename, curr, total_tex
                ))
            self.statusbar.showMessage("Finished", 5000)
            self.pathsconfig["exportedModels"] = filepath

    #@catch_exception
    def button_load_level(self):
        filepath, choosentype = QFileDialog.getOpenFileName(
            self, "Open File",
            self.pathsconfig["resourceFiles"],
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
                    self.modelindices = {}
                    modellist = []
                    for model in self.res_file.models:
                        name = str(model.res_name, encoding="ascii")
                        modellist.append(name)
                        self.modelindices[name] = len(modellist)-1
                    modellist.sort()
                    for name in modellist:
                        self.model_list.addItem(name)

                    self.waterbox_renderer.texarchive = self.texture_archive


                    print("File loaded")
                    # self.bw_map_screen.update()
                    # path_parts = path.split(filepath)
                    self.set_base_window_title(filepath)
                    self.pathsconfig["resourceFiles"] = filepath
                    save_cfg(self.configuration)
                    self.current_gen_path = filepath

                except Exception as error:
                    self.modelindices = {}
                    print("Error appeared while loading:", error)
                    traceback.print_exc()
                    open_error_dialog(str(error), self)

    @catch_exception_with_dialog
    def select_model(self):
        item = self.model_list.currentItem().text()
        index = self.modelindices[item]

        self.waterbox_renderer.create_drawlist(self.res_file.models[index], isbw1=self.res_file.is_bw())
        self.waterbox_renderer.do_redraw()

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if event.key() == Qt.Key_Shift:
            self.waterbox_renderer.shift_is_pressed = True

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
        elif event.key() == Qt.Key_R:
            self.waterbox_renderer.ROTATE_LEFT = 1
        elif event.key() == Qt.Key_T:
            self.waterbox_renderer.ROTATE_RIGHT = 1

        elif event.key() == Qt.Key_Up:
            row = self.model_list.currentRow()-1
            if row < 0:
                row = 0
            self.model_list.setCurrentRow(row)

        elif event.key() == Qt.Key_Down:
            row = self.model_list.currentRow()+1
            if self.res_file is None:
                row = 0
            elif row >= len(self.res_file.models):
                row = len(self.res_file.models)-1
            self.model_list.setCurrentRow(row)

    def keyReleaseEvent(self, event: QtGui.QKeyEvent):
        if event.key() == Qt.Key_Shift:
            self.waterbox_renderer.shift_is_pressed = False

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
        elif event.key() == Qt.Key_R:
            self.waterbox_renderer.ROTATE_LEFT = 0
        elif event.key() == Qt.Key_T:
            self.waterbox_renderer.ROTATE_RIGHT = 0


if __name__ == "__main__":
    import sys
    import platform

    app = QApplication(sys.argv)
    if platform.system() == "Windows":
        import ctypes
        myappid = 'BW2ModelViewer'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    with open("log.txt", "w") as f:
        f.write("")

    with open("log.txt", "a") as f:
        #sys.stdout = f
        #sys.stderr = f
        print("Python version: ", sys.version)
        pikmin_gui = GenEditor()
        #pikmin_gui.setWindowIcon(QtGui.QIcon('resources/icon.ico'))
        pikmin_gui.show()
        err_code = app.exec()

    sys.exit(err_code)