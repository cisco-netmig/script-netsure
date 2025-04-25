import logging
import os
import json
from PyQt5 import QtWidgets, QtGui, QtCore
from .workers import RunEvent, TemplateLoaderThread


class Ui_Form:
    """
    A PyQt5 UI form class for configuring and executing network diagnostics.

    """

    def setup_ui(self, form):
        """
        Set up the layout and UI elements of the diagnostics form.

        Args:
            form (QWidget): The parent widget to apply the layout and components to.
        """
        self.form = form
        self.main_layout = QtWidgets.QHBoxLayout(self.form)

        self.devices_group_box = QtWidgets.QGroupBox(self.form)
        self.devices_group_box.setTitle('Devices')
        self.devices_layout = QtWidgets.QVBoxLayout(self.devices_group_box)
        self.devices_text_edit = QtWidgets.QTextEdit(self.devices_group_box)
        self.devices_layout.addWidget(self.devices_text_edit)
        self.main_layout.addWidget(self.devices_group_box)

        self.right_panel_layout = QtWidgets.QVBoxLayout()
        self.main_layout.addLayout(self.right_panel_layout)

        self._setup_checks_ui()
        self._setup_actions_ui()
        self._setup_outputs_ui()

    def _setup_checks_ui(self):
        """Sets up the checks group box and its contents."""
        self.checks_group_box = QtWidgets.QGroupBox(self.form)
        self.checks_group_box.setTitle('Checks')
        self.right_panel_layout.addWidget(self.checks_group_box)

        self.checks_layout = QtWidgets.QVBoxLayout(self.checks_group_box)
        self.checks_header_layout = QtWidgets.QHBoxLayout()
        self.checks_layout.addLayout(self.checks_header_layout)

        self.filter_line_edit = QtWidgets.QLineEdit(self.checks_group_box)
        self.filter_line_edit.setPlaceholderText("Filter...")
        self.filter_line_edit.textChanged.connect(self.filter_tree)
        self.checks_header_layout.addWidget(self.filter_line_edit)

        self.checks_manager_button = QtWidgets.QPushButton()
        self.checks_manager_button.setToolTip('Checks Manager')
        self.checks_manager_button.setIcon(self._get_icon('briefcase-settings'))
        self.checks_manager_button.setIconSize(QtCore.QSize(20, 20))
        self.checks_manager_button.clicked.connect(lambda: ChecksManagerDialog(self.form))
        self.checks_header_layout.addWidget(self.checks_manager_button)

        self.checks_tree = QtWidgets.QTreeWidget(self.checks_group_box)
        self.checks_tree.header().setVisible(False)
        self.checks_tree.setStyleSheet("QTreeWidget::item { padding: 3px; border: none; }")
        self.checks_tree.itemChanged.connect(self.on_item_changed)
        self.checks_layout.addWidget(self.checks_tree)

    def _setup_actions_ui(self):
        """Sets up the actions group box and its contents."""
        self.actions_group_box = QtWidgets.QGroupBox(self.form)
        self.actions_group_box.setTitle('Actions')
        self.right_panel_layout.addWidget(self.actions_group_box)

        self.actions_layout = QtWidgets.QHBoxLayout(self.actions_group_box)
        self.run_button = QtWidgets.QPushButton()
        self.run_button.setText('Run')
        self.run_button.setIcon(self._get_icon('run-command'))
        self.run_button.setIconSize(QtCore.QSize(20, 20))
        self.run_button.setFixedSize(150, 30)
        self.actions_layout.addWidget(self.run_button)

        self.actions_layout.addItem(QtWidgets.QSpacerItem(
            0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))

    def _setup_outputs_ui(self):
        """Sets up the outputs group box and its contents."""
        self.outputs_group_box = QtWidgets.QGroupBox(self.form)
        self.outputs_group_box.setTitle('Output')
        self.right_panel_layout.addWidget(self.outputs_group_box)

        self.output_layout = QtWidgets.QHBoxLayout(self.outputs_group_box)

        self.last_report_button = QtWidgets.QPushButton()
        self.last_report_button.setText('Last Report')
        self.last_report_button.setIcon(self._get_icon('xls'))
        self.last_report_button.setIconSize(QtCore.QSize(20, 20))
        self.last_report_button.setFixedSize(150, 30)
        self.output_layout.addWidget(self.last_report_button)

        self.folder_button = QtWidgets.QPushButton()
        self.folder_button.setText('Folder')
        self.folder_button.setIcon(self._get_icon('opened-folder'))
        self.folder_button.setIconSize(QtCore.QSize(20, 20))
        self.folder_button.setFixedSize(150, 30)
        self.output_layout.addWidget(self.folder_button)

        self.output_layout.addItem(QtWidgets.QSpacerItem(
            0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum))

    def on_item_changed(self, item):
        """
        Handles cascading check state changes for a top-level tree item.

        Args:
            item (QTreeWidgetItem): The changed item.
        """
        if item.parent() is None:
            state = item.checkState(0)
            for i in range(item.childCount()):
                item.child(i).setCheckState(0, state)

    def filter_tree(self):
        """
        Filters the tree view items based on the text input in the filter line edit.
        """
        filter_text = self.filter_line_edit.text().strip().lower()

        for i in range(self.checks_tree.topLevelItemCount()):
            parent = self.checks_tree.topLevelItem(i)
            parent_match = filter_text in parent.text(0).lower()
            child_match = False

            for j in range(parent.childCount()):
                child = parent.child(j)
                if filter_text in child.text(0).lower():
                    child.setHidden(False)
                    child_match = True
                else:
                    child.setHidden(True)

            parent.setHidden(not (parent_match or child_match))

    def populate_checks_tree(self):
        """
        Populates the checks tree widget with checklist data from the form.
        """
        self.checks_tree.clear()

        for checklist, check_data in self.form.checks_data.items():
            checklist_item = QtWidgets.QTreeWidgetItem(self.checks_tree)
            checklist_item.setText(0, checklist)
            checklist_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable)
            checklist_item.setCheckState(0, QtCore.Qt.Unchecked)
            checklist_item.setIcon(0, self._get_icon('checklist'))

            for check, props in check_data.items():
                check_item = QtWidgets.QTreeWidgetItem(checklist_item)
                check_item.setText(0, check)
                check_item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable)
                check_item.setCheckState(0, QtCore.Qt.Unchecked)
                check_item.setIcon(0, self._get_icon('check'))

        self.checks_tree.expandAll()

    def _get_icon(self, filename: str) -> QtGui.QIcon:
        """
        Load an icon from the assets directory.

        Args:
            filename (str): Name of the icon file (without extension).

        Returns:
            QtGui.QIcon: The QIcon object.
        """
        icon_path = os.path.join(os.path.dirname(__file__), "assets", f"{filename}.ico")
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(icon_path), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.Off)
        return icon


class CustomComboBox(QtWidgets.QComboBox):
    """
    A customizable QComboBox with filtering and auto-completion.
    """

    def __init__(self, parent=None):
        """
        Initializes the custom combo box with an editable line and auto-complete features.

        Args:
            parent (QWidget, optional): The parent widget.
        """
        super().__init__(parent)
        self.setEditable(True)

        self.completer = QtWidgets.QCompleter(self)
        self.completer.setCompletionMode(QtWidgets.QCompleter.UnfilteredPopupCompletion)

        self.filter_model = QtCore.QSortFilterProxyModel(self)
        self.filter_model.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self.completer.setModel(self.filter_model)
        self.setCompleter(self.completer)

        self.lineEdit().textEdited.connect(self.filter_model.setFilterFixedString)
        self.completer.activated.connect(self.setTextIfCompleterIsClicked)

    def setModel(self, model):
        """
        Sets the data model for the combo box and its completer.

        Args:
            model (QAbstractItemModel): The model to assign.
        """
        super().setModel(model)
        self.filter_model.setSourceModel(model)
        self.completer.setModel(self.filter_model)

    def setModelColumn(self, column):
        """
        Sets the column of the model used for completion and filtering.

        Args:
            column (int): The model column index to use.
        """
        self.completer.setCompletionColumn(column)
        self.filter_model.setFilterKeyColumn(column)
        super().setModelColumn(column)

    def setTextIfCompleterIsClicked(self, text):
        """
        Sets the current index if a completer item is selected.

        Args:
            text (str): The selected text from the completer.
        """
        index = self.findText(text, QtCore.Qt.MatchFixedString)
        if index >= 0:
            self.setCurrentIndex(index)

    def addItems(self, texts):
        """
        Adds a list of strings as items to the combo box.

        Args:
            texts (list[str]): The items to add.
        """
        model = QtGui.QStandardItemModel(self)
        for i, word in enumerate(texts):
            item = QtGui.QStandardItem(word)
            item.setFont(self.font())
            model.setItem(i, 0, item)
        self.setModel(model)
        self.setModelColumn(0)


class ChecksManagerDialog(QtWidgets.QDialog):
    """Dialog for managing checklists and checks in a tree-based UI."""

    def __init__(self, form):
        super().__init__(form)
        self.form = form
        self.setObjectName('SessionsDialog')
        self.setWindowFlags(self.windowFlags() ^ QtCore.Qt.WindowType.WindowContextHelpButtonHint)
        self.load_templates()
        self._setup_ui()
        self._populate_nav_tree()
        self._populate_checklist_template_fields()
        self._set_page_mode()
        self.show()
        self.active = {'widget': '', 'key': '', 'edit': False}
        self._page_setup()

    def load_templates(self):
        """
        Load NTC templates.
        """
        self.template_loader_thread = TemplateLoaderThread(self)
        self.template_loader_thread.templates_loaded.connect(self.on_templates_loaded)
        self.template_loader_thread.start()

    def on_templates_loaded(self, templates):
        """
        Slot that is triggered when templates are loaded.
        """
        logging.info("Received loaded templates.")
        self.form.templates_data = templates

    def _setup_ui(self):
        """Sets up the UI layout and widgets."""
        self.setMinimumSize(800, 600)
        self.setWindowIcon(self.form._get_icon('briefcase-settings'))
        self.setWindowTitle('Checks Manager')

        # Main layout
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)

        # Navigation tree panel
        self._setup_nav_tree()

        # Main content panel
        self._setup_main_content()

    def _setup_nav_tree(self):
        """Initializes the navigation tree UI."""
        self.nav_tree_widget = QtWidgets.QWidget(self)
        self.nav_tree_widget.setObjectName('SessionsDialogSessionList')
        self.nav_tree_widget.setFixedWidth(250)

        self.nav_tree_layout = QtWidgets.QVBoxLayout(self.nav_tree_widget)
        self.nav_tree_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_tree_layout.setSpacing(5)

        self.filter_line_edit = QtWidgets.QLineEdit(self.nav_tree_widget)
        self.filter_line_edit.setPlaceholderText('Filter..')
        self.filter_line_edit.setMinimumSize(QtCore.QSize(200, 0))
        self.filter_line_edit.textChanged.connect(self._filter_tree)
        self.nav_tree_layout.addWidget(self.filter_line_edit)

        self.nav_tree = QtWidgets.QTreeWidget(self.nav_tree_widget)
        self.nav_tree.itemClicked.connect(self._on_item_clicked)
        self.nav_tree.header().setVisible(False)
        self.nav_tree.setStyleSheet("QTreeWidget::item { padding: 3px; border: none; }")
        self.nav_tree_layout.addWidget(self.nav_tree)

        self.layout.addWidget(self.nav_tree_widget)

    def _setup_main_content(self):
        """Initializes the main content area including forms and buttons."""
        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(2)
        self.layout.addLayout(self.main_layout)

        self._setup_action_buttons()
        self._setup_check_form()
        self._setup_checklist_form()
        self._setup_form_buttons()

        self.main_layout.addItem(QtWidgets.QSpacerItem(0, 0,
                                                       QtWidgets.QSizePolicy.Policy.Minimum,
                                                       QtWidgets.QSizePolicy.Policy.Expanding))

    def _setup_action_buttons(self):
        """Creates action buttons for adding checklists and checks."""
        self.actions_layout = QtWidgets.QHBoxLayout()
        self.actions_layout.setContentsMargins(0, 0, 0, 0)
        self.actions_layout.setSpacing(5)
        self.main_layout.addLayout(self.actions_layout)

        self.new_checklist_button = QtWidgets.QPushButton()
        self.new_checklist_button.setToolTip('New Checklist')
        self.new_checklist_button.setIcon(self.form._get_icon('checklist'))
        self.new_checklist_button.setIconSize(QtCore.QSize(20, 20))
        self.new_checklist_button.clicked.connect(self.create_new_checklist)
        self.actions_layout.addWidget(self.new_checklist_button)

        self.new_check_button = QtWidgets.QPushButton()
        self.new_check_button.setToolTip('New Check')
        self.new_check_button.setIcon(self.form._get_icon('check'))
        self.new_check_button.setIconSize(QtCore.QSize(20, 20))
        self.new_check_button.clicked.connect(self.create_new_check)
        self.actions_layout.addWidget(self.new_check_button)

        self.raw_button = QtWidgets.QPushButton()
        self.raw_button.setToolTip('Open Raw')
        self.raw_button.setIcon(self.form._get_icon('raw'))
        self.raw_button.setIconSize(QtCore.QSize(20, 20))
        self.raw_button.clicked.connect(lambda: self.form.openPathEvent(self.form.PATH_CHECKS_DATA))
        self.actions_layout.addWidget(self.raw_button)

        self.actions_layout.addItem(QtWidgets.QSpacerItem(0, 0,
                                                          QtWidgets.QSizePolicy.Policy.Expanding,
                                                          QtWidgets.QSizePolicy.Policy.Minimum))

    def _setup_check_form(self):
        """
        Sets up the form for creating or editing individual checks.
        Includes input fields for name, checklist, template, search key, regex, and primary key.
        """
        self.checks_form_widget = QtWidgets.QWidget(self)
        self.checks_form_widget.setStyleSheet('QComboBox {font-weight: 300;}')
        self.main_layout.addWidget(self.checks_form_widget)
        self.checks_form_widget.hide()

        self.checks_form_layout = QtWidgets.QVBoxLayout(self.checks_form_widget)
        self.checks_form_input_layout = QtWidgets.QGridLayout()
        self.checks_form_layout.addLayout(self.checks_form_input_layout)
        self.checks_form_input_layout.setContentsMargins(5, 8, 5, 5)
        self.checks_form_input_layout.setSpacing(10)

        self.checks_name_label = QtWidgets.QLabel('Name')
        self.checks_name_field = QtWidgets.QLineEdit()
        self.checks_name_field.setPlaceholderText('Name: Mandatory')

        self.checks_checklist_label = QtWidgets.QLabel('Checklist')
        self.checks_checklist_field = CustomComboBox(self.checks_form_widget)
        self.checks_checklist_field.lineEdit().setPlaceholderText('Checklist: Mandatory')

        self.checks_template_label = QtWidgets.QLabel('Template')
        self.checks_template_field = CustomComboBox(self.checks_form_widget)
        self.checks_template_field.lineEdit().setPlaceholderText('Template: Mandatory')

        self.checks_search_key_label = QtWidgets.QLabel('Search Key')
        self.checks_search_key_field = CustomComboBox(self.checks_form_widget)
        self.checks_search_key_field.lineEdit().setPlaceholderText('Search Key: Optional')

        self.checks_regex_label = QtWidgets.QLabel('Regex')
        self.checks_regex_field = QtWidgets.QLineEdit()
        self.checks_regex_field.setPlaceholderText('Regex: Mandatory')

        self.checks_primary_key_label = QtWidgets.QLabel('Primary Key')
        self.checks_primary_key_field = CustomComboBox(self.checks_form_widget)
        self.checks_primary_key_field.lineEdit().setPlaceholderText('Primary Key: Optional')

        self.checks_form_input_layout.addWidget(self.checks_name_label, 0, 0)
        self.checks_form_input_layout.addWidget(self.checks_name_field, 0, 1)
        self.checks_form_input_layout.addWidget(self.checks_checklist_label, 1, 0)
        self.checks_form_input_layout.addWidget(self.checks_checklist_field, 1, 1)
        self.checks_form_input_layout.addWidget(self.checks_template_label, 2, 0)
        self.checks_form_input_layout.addWidget(self.checks_template_field, 2, 1)
        self.checks_form_input_layout.addWidget(self.checks_search_key_label, 3, 0)
        self.checks_form_input_layout.addWidget(self.checks_search_key_field, 3, 1)
        self.checks_form_input_layout.addWidget(self.checks_regex_label, 4, 0)
        self.checks_form_input_layout.addWidget(self.checks_regex_field, 4, 1)
        self.checks_form_input_layout.addWidget(self.checks_primary_key_label, 5, 0)
        self.checks_form_input_layout.addWidget(self.checks_primary_key_field, 5, 1)

    def _setup_checklist_form(self):
        """
        Sets up the form for creating or editing checklists.
        Includes input field for checklist name.
        """
        self.checklist_form_widget = QtWidgets.QWidget(self)
        self.main_layout.addWidget(self.checklist_form_widget)
        self.checklist_form_widget.hide()

        self.checklist_form_layout = QtWidgets.QVBoxLayout(self.checklist_form_widget)
        self.checklist_form_input_layout = QtWidgets.QGridLayout()
        self.checklist_form_layout.addLayout(self.checklist_form_input_layout)
        self.checklist_form_input_layout.setContentsMargins(5, 8, 5, 5)
        self.checklist_form_input_layout.setSpacing(10)

        self.checklist_name_label = QtWidgets.QLabel('Name')
        self.checklist_name_field = QtWidgets.QLineEdit()

        self.checklist_form_input_layout.addWidget(self.checklist_name_label, 0, 0)
        self.checklist_form_input_layout.addWidget(self.checklist_name_field, 0, 1)

    def _setup_form_buttons(self):
        """
        Sets up the action buttons for the form: Edit, Delete, Save, and Cancel.
        """
        self.form_action_widget = QtWidgets.QWidget()
        self.main_layout.addWidget(self.form_action_widget)
        self.form_action_layout = QtWidgets.QHBoxLayout(self.form_action_widget)
        self.form_action_layout.setContentsMargins(10, 10, 10, 10)
        self.form_action_layout.setSpacing(20)

        self.form_edit_button = QtWidgets.QPushButton(self)
        self.form_edit_button.setText('Edit')
        self.form_edit_button.setMinimumSize(QtCore.QSize(100, 16777215))
        self.form_edit_button.setIcon(self.form._get_icon('edit'))
        self.form_edit_button.setIconSize(QtCore.QSize(20, 20))
        self.form_edit_button.clicked.connect(self.edit_form_action)

        self.form_delete_button = QtWidgets.QPushButton(self)
        self.form_delete_button.setText('Delete')
        self.form_delete_button.setMinimumSize(QtCore.QSize(100, 16777215))
        self.form_delete_button.setIcon(self.form._get_icon('delete2'))
        self.form_delete_button.setIconSize(QtCore.QSize(20, 20))
        self.form_delete_button.clicked.connect(self.delete_form_action)

        self.form_save_button = QtWidgets.QPushButton(self)
        self.form_save_button.setText('Save')
        self.form_save_button.setMinimumSize(QtCore.QSize(100, 16777215))
        self.form_save_button.setIcon(self.form._get_icon('save'))
        self.form_save_button.setIconSize(QtCore.QSize(20, 20))
        self.form_save_button.clicked.connect(self.save_form_action)

        self.form_cancel_button = QtWidgets.QPushButton(self)
        self.form_cancel_button.setText('Cancel')
        self.form_cancel_button.setMinimumSize(QtCore.QSize(100, 16777215))
        self.form_cancel_button.setIcon(self.form._get_icon('cancel'))
        self.form_cancel_button.setIconSize(QtCore.QSize(20, 20))
        self.form_cancel_button.clicked.connect(self.cancel_form_action)

        self.form_action_layout.addWidget(self.form_edit_button)
        self.form_action_layout.addWidget(self.form_delete_button)
        self.form_action_layout.addWidget(self.form_save_button)
        self.form_action_layout.addWidget(self.form_cancel_button)
        self.form_action_layout.addItem(QtWidgets.QSpacerItem(
            0, 0, QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Minimum))

    def _populate_checklist_template_fields(self):
        """Populates the dropdowns for checklists and templates."""
        self.checks_checklist_field.clear()
        self.checks_template_field.clear()
        self.checks_search_key_field.clear()
        self.checks_primary_key_field.clear()

        self.checks_checklist_field.addItems(list(self.form.checks_data.keys()))
        self.checks_template_field.addItems(list(self.form.templates_data.keys()))
        self.checks_template_field.currentTextChanged.connect(self._populate_key_fields)
        self._populate_key_fields()

    def _populate_key_fields(self):
        """Populates the key fields based on the selected template."""
        template = self.checks_template_field.currentText()
        if template and self.form.templates_data.get(template):
            headers = self.form.templates_data[template]['headers']
            self.checks_search_key_field.clear()
            self.checks_primary_key_field.clear()
            self.checks_search_key_field.addItems([''] + headers)
            self.checks_primary_key_field.addItems([''] + headers)

    def _filter_tree(self):
        """Filters the tree based on text input."""
        filter_text = self.filter_line_edit.text().strip().lower()
        for i in range(self.nav_tree.topLevelItemCount()):
            parent = self.nav_tree.topLevelItem(i)
            parent_match = filter_text in parent.text(0).lower()
            child_match = False
            for j in range(parent.childCount()):
                child = parent.child(j)
                child_visible = filter_text in child.text(0).lower()
                child.setHidden(not child_visible)
                child_match |= child_visible
            parent.setHidden(not (parent_match or child_match))

    def _populate_nav_tree(self):
        """Populates the navigation tree with checklists and checks."""
        self.nav_tree.clear()
        for checklist, check_data in self.form.checks_data.items():
            checklist_item = QtWidgets.QTreeWidgetItem(self.nav_tree)
            checklist_item.setText(0, checklist)
            checklist_item.setFlags(QtCore.Qt.ItemIsEnabled)
            checklist_item.setIcon(0, self.form._get_icon('checklist'))
            for check, props in check_data.items():
                check_item = QtWidgets.QTreeWidgetItem(checklist_item)
                check_item.setText(0, check)
                check_item.setFlags(QtCore.Qt.ItemIsEnabled)
                check_item.setIcon(0, self.form._get_icon('check'))
        self.nav_tree.expandAll()

    def _on_item_clicked(self, widget, column):
        """Handles item click in the navigation tree."""
        self.active['key'] = widget.text(column)
        self.active['widget'] = 'checklist' if widget in [
            self.nav_tree.topLevelItem(i) for i in range(self.nav_tree.topLevelItemCount())] else 'checks'
        self._page_setup()

    def _page_setup(self, mode='r'):
        """Sets up the page UI based on active item and mode."""
        self.active['edit'] = False
        if self.active['key']:
            self._set_page_mode(mode)
            key = self.active['key']
            if self.active['widget'] == 'checklist':
                self.checklist_name_field.setText(key)
            elif self.active['widget'] == 'checks':
                for checklist, check_data in self.form.checks_data.items():
                    if check_data.get(key):
                        check = check_data[key]
                        self.checks_name_field.setText(key)
                        self.checks_checklist_field.setCurrentText(checklist)
                        self.checks_template_field.setCurrentText(check['template'])
                        self.checks_search_key_field.setCurrentText(check['search_key'])
                        self.checks_primary_key_field.setCurrentText(check['primary_key'])
                        self.checks_regex_field.setText(check['regex'])
                        break
        else:
            self._set_page_mode()

    def _set_page_mode(self, mode=''):
        """Controls visibility of form modes (read/write)."""
        self.form_edit_button.hide()
        self.form_delete_button.hide()
        self.form_save_button.hide()
        self.form_cancel_button.hide()
        self.checks_form_widget.hide()
        self.checklist_form_widget.hide()

        if mode == 'r':
            self.form_edit_button.show()
            self.form_delete_button.show()
            if self.active['widget'] == 'checklist':
                self.checklist_form_widget.show()
                self.checklist_form_widget.setDisabled(True)
            else:
                self.checks_form_widget.show()
                self.checks_form_widget.setDisabled(True)
        elif mode == 'w':
            self.form_save_button.show()
            self.form_cancel_button.show()
            if self.active['widget'] == 'checklist':
                self.checklist_form_widget.show()
                self.checklist_form_widget.setDisabled(False)
            else:
                self.checks_form_widget.show()
                self.checks_form_widget.setDisabled(False)

    def create_new_checklist(self):
        """Initialize a new checklist form for creation."""
        self.active['widget'] = 'checklist'
        self.active['key'] = ''
        self._set_page_mode('w')
        self.checklist_name_field.setText('')

    def create_new_check(self):
        """Initialize a new check form for creation."""
        self.active['widget'] = 'check'
        self.active['key'] = ''
        self._set_page_mode('w')
        self.checks_name_field.setText('')
        self.checks_regex_field.setText('')

    def edit_form_action(self):
        """Enable editing mode for the current form."""
        self._set_page_mode('w')
        self.active['edit'] = True

    def save_form_action(self):
        """Save the current form based on widget type (checklist or check)."""
        if self.active['widget'] == 'checklist':
            name = self.checklist_name_field.text()

            if self.active.get('edit'):
                self.form.checks_data[name] = self.form.checks_data.pop(self.active['key'])
            elif name in self.form.checks_data:
                QtWidgets.QMessageBox.warning(
                    self, 'Checks Manager', 'Name Exists!',
                    QtWidgets.QMessageBox.StandardButton.Ok
                )
                return
            else:
                self.form.checks_data[name] = {}

            self.form.update_checks_data()
            self._populate_nav_tree()
            self.active['key'] = name
            self._page_setup()

        else:
            name = self.checks_name_field.text()
            checklist = self.checks_checklist_field.currentText()
            template = self.checks_template_field.currentText()
            search_key = self.checks_search_key_field.currentText()
            primary_key = self.checks_primary_key_field.currentText()
            regex = self.checks_regex_field.text()

            if self.active.get('edit'):
                old_checklist = next(
                    (cl for cl, data in self.form.checks_data.items() if self.active['key'] in data),
                    ''
                )
                self.form.checks_data[checklist][name] = self.form.checks_data[old_checklist].pop(self.active['key'])

            elif name in self.form.checks_data[checklist]:
                QtWidgets.QMessageBox.warning(
                    self, 'Checks Manager', 'Name Exists!',
                    QtWidgets.QMessageBox.StandardButton.Ok
                )
                return

            self.form.checks_data[checklist][name] = {
                'template': template,
                'search_key': search_key,
                'primary_key': primary_key,
                'regex': regex
            }

            self.form.update_checks_data()
            self._populate_nav_tree()
            self.active['key'] = name
            self._page_setup()

        self._populate_checklist_template_fields()

    def delete_form_action(self):
        """Delete the current checklist or check from data and update the UI."""
        if self.active['widget'] == 'checklist':
            self.form.checks_data.pop(self.active['key'], None)
            self.active['key'] = next(iter(self.form.checks_data), '')
        else:
            for checklist, checks in self.form.checks_data.items():
                if self.active['key'] in checks:
                    checks.pop(self.active['key'], None)
                    self.active['key'] = checklist
                    self.active['widget'] = 'checklist'
                    break

        self.form.update_checks_data()
        self._populate_nav_tree()
        self._page_setup()

    def cancel_form_action(self):
        """Cancel current edit or create action and revert to view mode."""
        self._page_setup()

    def closeEvent(self, event):
        """Handle window close event by refreshing the checks tree."""
        self.form.populate_checks_tree()


class Form(QtWidgets.QWidget, Ui_Form):
    """
    UI Form class.

    """

    def __init__(self, parent=None, **kwargs):
        """
        Initialize the UI form.

        Args:
            parent (QWidget): Parent widget.
            **kwargs: Additional arguments for customization or metadata.
        """
        super().__init__(parent)
        self.kwargs = kwargs
        self.session = kwargs.get("session")

        self.setup_ui(self)

        self.output_dir = os.path.join(self.kwargs.get("output_dir"),
                                       os.path.basename(os.path.dirname(__file__).upper()))
        self.output_report = ""
        self.checks_data = {}
        self.templates_data = {}
        self.path_checks_data = os.path.join(os.path.expanduser('~'), '.netmig', 'checklist.json')

        self.create_checks_path()
        self.load_checks_data()

        self.run_button.clicked.connect(self.run_start_event)
        self.last_report_button.clicked.connect(lambda: self.open_path(self.output_report))
        self.folder_button.clicked.connect(lambda: self.open_path(self.output_dir))

    def create_checks_path(self):
        """
        Ensures the checklist data path exists; if not, initializes it.
        """
        if not os.path.exists(self.path_checks_data):
            logging.info("Checklist path not found, creating new checklist data file.")
            self.update_checks_data()

    def update_checks_data(self):
        """
        Writes the current checks data to the JSON file.
        """
        with open(self.path_checks_data, 'w') as f:
            json.dump(self.checks_data, f, indent=4)
        logging.debug("Checklist data updated.")

    def load_checks_data(self):
        """
        Loads checks data from the saved JSON file.
        """
        with open(self.path_checks_data, 'r') as f:
            self.checks_data = json.load(f)
        self.populate_checks_tree()
        logging.debug("Checklist data loaded and tree populated.")

    def run_start_event(self):
        """
        Starts the task runner when 'Run' is clicked.
        """
        self.run_button.setEnabled(False)
        self.run_worker = RunEvent(self)
        self.run_worker.start()
        self.run_worker.finished.connect(self.run_finish_event)
        logging.debug("Run worker started.")

    def run_finish_event(self):
        """
        Re-enables the Run button and notifies the user upon completion.
        """
        self.run_button.setEnabled(True)
        QtWidgets.QMessageBox.information(self, 'Info', 'Task completed!!')
        logging.info("Run worker finished successfully.")

    def open_path(self, path: str):
        """
        Open a file or directory using the system's default handler.

        Args:
            path (str): File or directory path to open.
        """
        try:
            if path and os.path.exists(path):
                logging.info(f"Opening path: {path}")
                QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(path))
            else:
                logging.error(f"Invalid or non-existent path: {path}")
        except Exception as e:
            logging.exception(f"Failed to open path: {e}")
