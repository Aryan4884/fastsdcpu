from time import time
from PyQt5.QtWidgets import (
    QWidget,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QSlider,
    QTabWidget,
    QSpacerItem,
    QSizePolicy,
    QComboBox,
    QCheckBox,
    QTextEdit,
    QToolButton,
    QFileDialog,
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import (
    QSize,
    QThreadPool,
    Qt,
)

from PIL.ImageQt import ImageQt
import os
from uuid import uuid4
from backend.lcm_text_to_image import LCMTextToImage
from backend.models.lcmdiffusion_setting import LCMDiffusionSetting
from pprint import pprint
from constants import (
    LCM_DEFAULT_MODEL,
    LCM_DEFAULT_MODEL_OPENVINO,
    APP_NAME,
    APP_VERSION,
)
from frontend.gui.image_generator_worker import ImageGeneratorWorker
from app_settings import AppSettings
from paths import FastStableDiffusionPaths


class MainWindow(QMainWindow):
    def __init__(self, config: AppSettings):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setFixedSize(QSize(530, 600))
        self.init_ui()
        self.pipeline = None
        self.threadpool = QThreadPool()
        self.config = config
        self.device = "cpu"
        self.previous_width = 0
        self.previous_height = 0
        self.previous_model = ""
        self.lcm_text_to_image = LCMTextToImage()
        self.init_ui_values()
        print(f"Output path : {  self.config.settings.results_path}")

    def init_ui_values(self):
        self.lcm_model.setEnabled(
            not self.config.settings.lcm_diffusion_setting.use_openvino
        )
        self.guidance.setValue(
            int(self.config.settings.lcm_diffusion_setting.guidance_scale * 10)
        )
        self.seed_value.setEnabled(self.config.settings.lcm_diffusion_setting.use_seed)
        self.safety_checker.setChecked(
            self.config.settings.lcm_diffusion_setting.use_safety_checker
        )
        self.use_openvino_check.setChecked(
            self.config.settings.lcm_diffusion_setting.use_openvino
        )
        self.width.setCurrentText(
            str(self.config.settings.lcm_diffusion_setting.image_width)
        )
        self.height.setCurrentText(
            str(self.config.settings.lcm_diffusion_setting.image_height)
        )
        self.inference_steps.setValue(
            int(self.config.settings.lcm_diffusion_setting.inference_steps)
        )
        self.seed_check.setChecked(self.config.settings.lcm_diffusion_setting.use_seed)
        self.seed_value.setText(str(self.config.settings.lcm_diffusion_setting.seed))
        self.use_local_model_folder.setChecked(
            self.config.settings.lcm_diffusion_setting.use_offline_model
        )
        self.results_path.setText(self.config.settings.results_path)

    def init_ui(self):
        self.create_main_tab()
        self.create_settings_tab()
        self.create_about_tab()
        self.show()

    def create_main_tab(self):
        self.img = QLabel("<<Image>>")
        self.img.setAlignment(Qt.AlignCenter)
        self.img.setFixedSize(QSize(512, 512))

        self.prompt = QTextEdit()
        self.prompt.setPlaceholderText("A fantasy landscape")
        self.generate = QPushButton("Generate")
        self.generate.clicked.connect(self.text_to_image)
        self.prompt.setFixedHeight(35)

        hlayout = QHBoxLayout()
        hlayout.addWidget(self.prompt)
        hlayout.addWidget(self.generate)

        vlayout = QVBoxLayout()
        vlayout.addWidget(self.img)
        vlayout.addLayout(hlayout)

        self.tab_widget = QTabWidget(self)
        self.tab_main = QWidget()
        self.tab_settings = QWidget()
        self.tab_about = QWidget()
        self.tab_main.setLayout(vlayout)

        self.tab_widget.addTab(self.tab_main, "Text to Image")
        self.tab_widget.addTab(self.tab_settings, "Settings")
        self.tab_widget.addTab(self.tab_about, "About")

        self.setCentralWidget(self.tab_widget)
        self.use_seed = False

    def create_settings_tab(self):
        model_hlayout = QHBoxLayout()
        self.lcm_model_label = QLabel("Latent Consistency Model:")
        self.lcm_model = QLineEdit(LCM_DEFAULT_MODEL)
        model_hlayout.addWidget(self.lcm_model_label)
        model_hlayout.addWidget(self.lcm_model)

        self.inference_steps_value = QLabel("Number of inference steps: 4")
        self.inference_steps = QSlider(orientation=Qt.Orientation.Horizontal)
        self.inference_steps.setMaximum(25)
        self.inference_steps.setMinimum(1)
        self.inference_steps.setValue(4)
        self.inference_steps.valueChanged.connect(self.update_steps_label)

        self.guidance_value = QLabel("Guidance scale: 8")
        self.guidance = QSlider(orientation=Qt.Orientation.Horizontal)
        self.guidance.setMaximum(200)
        self.guidance.setMinimum(10)
        self.guidance.setValue(80)
        self.guidance.valueChanged.connect(self.update_guidance_label)

        self.width_value = QLabel("Width :")
        self.width = QComboBox(self)
        self.width.addItem("256")
        self.width.addItem("512")
        self.width.addItem("768")
        self.width.setCurrentText("512")
        self.width.currentIndexChanged.connect(self.on_width_changed)

        self.height_value = QLabel("Height :")
        self.height = QComboBox(self)
        self.height.addItem("256")
        self.height.addItem("512")
        self.height.addItem("768")
        self.height.setCurrentText("512")
        self.height.currentIndexChanged.connect(self.on_height_changed)

        self.seed_check = QCheckBox("Use seed")
        self.seed_value = QLineEdit()
        self.seed_value.setInputMask("9999999999")
        self.seed_value.setText("123123")
        self.seed_check.stateChanged.connect(self.seed_changed)

        self.safety_checker = QCheckBox("Use safety checker")
        self.safety_checker.setChecked(True)
        self.safety_checker.stateChanged.connect(self.use_safety_checker_changed)

        self.use_openvino_check = QCheckBox("Use OpenVINO")
        self.use_openvino_check.setChecked(False)
        self.use_local_model_folder = QCheckBox(
            "Use locally cached model or downloaded model folder(offline)"
        )
        self.use_local_model_folder.setChecked(False)
        self.use_local_model_folder.stateChanged.connect(self.use_offline_model_changed)
        self.use_openvino_check.stateChanged.connect(self.use_openvino_changed)

        hlayout = QHBoxLayout()
        hlayout.addWidget(self.seed_check)
        hlayout.addWidget(self.seed_value)
        hspacer = QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum)
        slider_hspacer = QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.results_path_label = QLabel("Output path:")
        self.results_path = QLineEdit()
        self.results_path.textChanged.connect(self.on_path_changed)
        self.browse_folder_btn = QToolButton()
        self.browse_folder_btn.setText("...")
        self.browse_folder_btn.clicked.connect(self.on_browse_folder)

        self.reset = QPushButton("Reset All")
        self.reset.clicked.connect(self.reset_all_settings)

        vlayout = QVBoxLayout()
        vspacer = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        vlayout.addItem(hspacer)
        vlayout.addLayout(model_hlayout)
        vlayout.addWidget(self.use_local_model_folder)
        vlayout.addItem(slider_hspacer)
        vlayout.addWidget(self.inference_steps_value)
        vlayout.addWidget(self.inference_steps)
        vlayout.addWidget(self.width_value)
        vlayout.addWidget(self.width)
        vlayout.addWidget(self.height_value)
        vlayout.addWidget(self.height)
        vlayout.addWidget(self.guidance_value)
        vlayout.addWidget(self.guidance)
        vlayout.addLayout(hlayout)
        vlayout.addWidget(self.safety_checker)
        vlayout.addWidget(self.use_openvino_check)
        vlayout.addWidget(self.results_path_label)
        hlayout_path = QHBoxLayout()
        hlayout_path.addWidget(self.results_path)
        hlayout_path.addWidget(self.browse_folder_btn)
        vlayout.addLayout(hlayout_path)
        self.tab_settings.setLayout(vlayout)
        hlayout_reset = QHBoxLayout()
        hspacer = QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        hlayout_reset.addItem(hspacer)
        hlayout_reset.addWidget(self.reset)
        vlayout.addLayout(hlayout_reset)
        vlayout.addItem(vspacer)

    def create_about_tab(self):
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setText(
            f"""<h1>FastSD CPU {APP_VERSION}</h1> 
               <h3>(c)2023 - Rupesh Sreeraman</h3>
                <h3>Faster stable diffusion on CPU</h3>
                 <h3>Based on Latent Consistency Models</h3>
                <h3>GitHub : https://github.com/rupeshs/fastsdcpu/</h3>"""
        )

        vlayout = QVBoxLayout()
        vlayout.addWidget(self.label)
        self.tab_about.setLayout(vlayout)

    def on_path_changed(self, text):
        self.config.settings.results_path = text

    def on_browse_folder(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ShowDirsOnly

        folder_path = QFileDialog.getExistingDirectory(
            self, "Select a Folder", "", options=options
        )

        if folder_path:
            self.config.settings.results_path = folder_path
            self.results_path.setText(folder_path)

    def on_width_changed(self, index):
        width_txt = self.width.itemText(index)
        self.config.settings.lcm_diffusion_setting.image_width = int(width_txt)

    def on_height_changed(self, index):
        height_txt = self.height.itemText(index)
        self.config.settings.lcm_diffusion_setting.image_height = int(height_txt)

    def use_openvino_changed(self, state):
        if state == 2:
            self.lcm_model.setEnabled(False)
            self.config.settings.lcm_diffusion_setting.use_openvino = True
        else:
            self.config.settings.lcm_diffusion_setting.use_openvino = False

    def use_offline_model_changed(self, state):
        if state == 2:
            self.config.settings.lcm_diffusion_setting.use_offline_model = True
        else:
            self.config.settings.lcm_diffusion_setting.use_offline_model = False

    def use_safety_checker_changed(self, state):
        if state == 2:
            self.config.settings.lcm_diffusion_setting.use_safety_checker = True
        else:
            self.config.settings.lcm_diffusion_setting.use_safety_checker = False

    def update_steps_label(self, value):
        self.inference_steps_value.setText(f"Number of inference steps: {value}")
        self.config.settings.lcm_diffusion_setting.inference_steps = value

    def update_guidance_label(self, value):
        val = round(int(value) / 10, 1)
        self.guidance_value.setText(f"Guidance scale: {val}")
        self.config.settings.lcm_diffusion_setting.guidance_scale = val

    def seed_changed(self, state):
        if state == 2:
            self.seed_value.setEnabled(True)
            self.config.settings.lcm_diffusion_setting.use_seed = True
        else:
            self.seed_value.setEnabled(False)
            self.config.settings.lcm_diffusion_setting.use_seed = False

    def get_seed_value(self) -> int:
        use_seed = self.config.settings.lcm_diffusion_setting.use_seed
        seed_value = int(self.seed_value.text()) if use_seed else -1
        return seed_value

    def generate_image(self):
        self.config.settings.lcm_diffusion_setting.seed = self.get_seed_value()
        self.config.settings.lcm_diffusion_setting.prompt = self.prompt.toPlainText()

        if self.config.settings.lcm_diffusion_setting.use_openvino:
            model_id = LCM_DEFAULT_MODEL_OPENVINO
        else:
            model_id = self.lcm_model.text()

        if self.pipeline is None or self.previous_model != model_id:
            print(f"Using LCM model {model_id}")
            self.lcm_text_to_image.init(
                model_id=model_id,
                use_openvino=self.config.settings.lcm_diffusion_setting.use_openvino,
                use_local_model=self.config.settings.lcm_diffusion_setting.use_offline_model,
            )

        pprint(dict(self.config.settings.lcm_diffusion_setting))
        tick = time()
        reshape_required = False
        if self.config.settings.lcm_diffusion_setting.use_openvino:
            # Detect dimension change
            if (
                self.previous_width
                != self.config.settings.lcm_diffusion_setting.image_width
                or self.previous_height
                != self.config.settings.lcm_diffusion_setting.image_height
                or self.previous_model != model_id
            ):
                pprint("Reshape and compile")
                reshape_required = True

        images = self.lcm_text_to_image.generate(
            self.config.settings.lcm_diffusion_setting,
            reshape_required,
        )
        elapsed = time() - tick
        print(f"Elapsed time : {elapsed:.2f} sec")
        image_id = uuid4()
        if not os.path.exists(self.config.settings.results_path):
            os.mkdir(self.config.settings.results_path)

        images[0].save(
            os.path.join(self.config.settings.results_path, f"{image_id}.png")
        )
        print(f"Image {image_id}.png saved")
        im = ImageQt(images[0]).copy()
        pixmap = QPixmap.fromImage(im)
        self.img.setPixmap(pixmap)

        self.previous_width = self.config.settings.lcm_diffusion_setting.image_width
        self.previous_height = self.config.settings.lcm_diffusion_setting.image_height
        self.previous_model = model_id

    def text_to_image(self):
        self.img.setText("Please wait...")
        worker = ImageGeneratorWorker(self.generate_image)
        self.threadpool.start(worker)

    def closeEvent(self, event):
        self.config.settings.lcm_diffusion_setting.seed = self.get_seed_value()
        print(self.config.settings.lcm_diffusion_setting)
        print("Saving settings")
        self.config.save()

    def reset_all_settings(self):
        self.use_local_model_folder.setChecked(False)
        self.width.setCurrentText("512")
        self.height.setCurrentText("512")
        self.inference_steps.setValue(4)
        self.guidance.setValue(80)
        self.use_openvino_check.setChecked(False)
        self.seed_check.setChecked(False)
        self.safety_checker.setChecked(True)
        self.results_path.setText(FastStableDiffusionPaths().get_results_path())
