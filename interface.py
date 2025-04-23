import sys
import asyncio
import pandas as pd
import logging
import json
import aiosqlite
from datetime import timedelta
import time
import random
import string
import concurrent.futures
from functools import partial
from aiohttp_socks import ProxyConnector
import aiohttp
import sqlite3
import tracemalloc
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QStackedWidget, QHBoxLayout, \
    QFrame, QMessageBox, QToolButton, QLineEdit, QLabel, QComboBox, QStyle, QFileDialog, QTableWidgetItem, QTableWidget, \
    QHeaderView, QCheckBox, QAbstractItemView, QScrollArea, QTabWidget

from PyQt6.QtCore import QTimer, QRect, QPropertyAnimation, QEasingCurve, pyqtSlot, Qt, QEvent, QObject, QByteArray, \
    QDateTime

from PyQt6.QtGui import QIcon, QMouseEvent, QFont, QPixmap, QKeySequence, QGuiApplication
from PyQt6 import QtWidgets, QtCore, QtGui
from splash1 import BybitTrader
from depositaddres import BybitAPI
from SpotxActions import Actions
from main import Login
from splash_info import SplashInfo
from qasync import QEventLoop
from RewardsResults import GetResult
from get_balance import GetBalance
from account_transfer import Transfer


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

tracemalloc.start()

class BybitTraderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bybit Trader Application")
        self.setGeometry(100, 100, 800, 600)

        # Создание асинхронного события
        self.loop = asyncio.get_event_loop()

        # Main Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Main Layout
        self.main_layout = QHBoxLayout()
        self.central_widget.setLayout(self.main_layout)

        # Create left drawer menu
        self.create_left_menu()

        # Button to toggle menu visibility
        self.menu_button = QToolButton()
        self.menu_button.setIcon(QIcon("icon/back.png"))  # Устанавливаем начальный значок
        self.menu_button.setFixedHeight(40)
        self.menu_button.clicked.connect(self.toggle_menu)
        self.main_layout.addWidget(self.menu_button)

        # Content Area
        self.content_area = QStackedWidget()
        self.main_layout.addWidget(self.content_area)

        # Initialize Tabs
        self.init_tabs()

        # Создание базы данных
        self.create_database()

        # Плавно показать меню при старте
        QTimer.singleShot(0, lambda: self.animate_menu(show=True))  # Анимация при запуске программы

        # Переменная для хранения текущей анимации
        self.current_animation = None

        self.mouse_start_pos = None

        # QTimer.singleShot(0, lambda: asyncio.create_task(self.schedule_task()))

    def create_database(self):
        """Создание базы данных и таблицы сессий, если она еще не существует."""
        self.conn = sqlite3.connect('bybit_trader.db')
        self.cursor = self.conn.cursor()

        # Создание таблицы сессий, если она не существует
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT DEFAULT 'MAIN',
                group_name TEXT DEFAULT 'MAIN',
                secret_token TEXT NOT NULL,
                abck TEXT,
                bm_sz TEXT,
                bm_sv TEXT,
                ak_bmsc TEXT,
                proxy TEXT NOT NULL,
                balance FLOAT DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Создание таблицы credentials, если она не существует
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mail TEXT NOT NULL,
                password TEXT NOT NULL,
                proxy TEXT NOT NULL,
                otp_2fa TEXT NOT NULL,
                name TEXT DEFAULT 'MAIN',
                group_name TEXT DEFAULT 'MAIN',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                splash TEXT NOT NULL,
                drophunt TEXT NOT NULL
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS addresses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT DEFAULT 'MAIN',
                group_name TEXT DEFAULT 'MAIN',
                secret_token TEXT NOT NULL,
                proxy TEXT DEFAULT '0',
                address TEXT DEFAULT 'NONE',
                address_tag TEXT DEFAULT 'NONE'
            )
        ''')

        self.conn.commit()

    def create_left_menu(self):
        """Создание выдвигающегося левого меню."""
        self.left_menu = QFrame()
        self.left_menu.setFrameShape(QFrame.Shape.StyledPanel)
        self.left_menu.setGeometry(0, 0, 0,
                                   self.height())  # Начальная ширина 0, чтобы меню было скрыто при инициализации

        self.left_menu_layout = QVBoxLayout()
        self.left_menu.setLayout(self.left_menu_layout)

        # Добавление кнопок в меню
        self.splash_button = QPushButton('Token Splash')
        self.splash_button.clicked.connect(lambda: self.switch_tab(self.tab1))
        self.left_menu_layout.addWidget(self.splash_button)

        # Кнопка переключения на четвертую вкладку
        self.database_management_button = QPushButton('Balance and Transfer')
        self.database_management_button.clicked.connect(lambda: self.switch_tab(self.tab7))
        self.left_menu_layout.addWidget(self.database_management_button)

        self.hunt_button = QPushButton('Drop Hunt')
        self.hunt_button.clicked.connect(lambda: self.switch_tab(self.tab5))
        self.left_menu_layout.addWidget(self.hunt_button)

        self.deposit_tab_button = QPushButton('Get deposit addresses')
        self.deposit_tab_button.clicked.connect(lambda: self.switch_tab(self.tab2))
        self.left_menu_layout.addWidget(self.deposit_tab_button)

        # Кнопка переключения на четвертую вкладку
        self.database_management_button = QPushButton('Token Splash List')
        self.database_management_button.clicked.connect(lambda: self.switch_tab(self.tab6))
        self.left_menu_layout.addWidget(self.database_management_button)

        self.settings_button = QPushButton('Settings')
        self.settings_button.clicked.connect(lambda: self.switch_tab(self.tab3))
        self.left_menu_layout.addWidget(self.settings_button)

        # Кнопка переключения на четвертую вкладку
        self.database_management_button = QPushButton('Управление базой данных')
        self.database_management_button.clicked.connect(lambda: self.switch_tab(self.tab4))
        self.left_menu_layout.addWidget(self.database_management_button)

        self.left_menu_layout.addStretch()

        # Добавляем меню к главной компоновке
        self.main_layout.addWidget(self.left_menu)
    def toggle_menu(self):
        """Показать или скрыть левое меню с плавной анимацией."""
        is_visible = self.left_menu.width() > 0  # Если ширина меню больше 0, значит меню показано

        if self.current_animation and self.current_animation.state() == QPropertyAnimation.State.Running:
            # Если текущая анимация все еще выполняется, то не запускаем новую
            return

        if is_visible:
            self.animate_menu(show=False)
        else:
            self.animate_menu(show=True)

        # Изменение иконки в зависимости от состояния меню
        if is_visible:
            self.menu_button.setIcon(QIcon("icon/forward.png"))  # Меню скрыто - показываем стрелку вправо
        else:
            self.menu_button.setIcon(QIcon("icon/back.png"))  # Меню показано - показываем стрелку влево


    def animate_menu(self, show=True):
        """Анимация выдвижения или скрытия меню."""
        start_width = self.left_menu.width()  # Текущая ширина как начальная ширина
        end_width = 200 if show else 0  # Конечная ширина: 200, если показываем, 0 если скрываем

        # Создаем анимацию
        self.current_animation = QPropertyAnimation(self.left_menu, b"maximumWidth")  # Анимируем максимальную ширину
        self.current_animation.setDuration(500)  # Длительность анимации в миллисекундах
        self.current_animation.setStartValue(start_width)
        self.current_animation.setEndValue(end_width)
        self.current_animation.setEasingCurve(QEasingCurve.Type.OutCubic)  # Кривая сглаживания для более приятного эффекта
        self.current_animation.finished.connect(self.on_animation_finished)

        self.current_animation.start()

    @pyqtSlot()
    def on_animation_finished(self):
        """Обработчик завершения анимации."""
        # Обнуляем текущую анимацию, чтобы можно было повторно ее вызвать
        self.current_animation = None

    def init_tabs(self):
        # Первая вкладка - основной интерфейс
        self.tab1 = QWidget()
        self.init_tab1()
        self.content_area.addWidget(self.tab1)

        # Вторая вкладка - интерфейс получения адреса депозита
        self.tab2 = QWidget()
        self.init_tab2()
        self.content_area.addWidget(self.tab2)

        # Третья вкладка - настройки
        self.tab3 = QWidget()
        self.init_tab3()
        self.content_area.addWidget(self.tab3)

        # Четвертая вкладка - управление базой данных
        self.tab4 = QWidget()
        self.init_tab4()
        self.content_area.addWidget(self.tab4)

        self.tab5 = QWidget()
        self.init_tab5()
        self.content_area.addWidget(self.tab5)

        self.tab6 = QWidget()
        self.init_tab6()
        self.content_area.addWidget(self.tab6)

        self.tab7 = QWidget()
        self.init_tab7()
        self.content_area.addWidget(self.tab7)


    def switch_tab(self, tab):
        """Переключиться на выбранную вкладку."""
        self.content_area.setCurrentWidget(tab)

    def init_tab1(self):
        # Настройка компоновки для первой вкладки
        layout = QVBoxLayout()

        # Создаем QTabWidget для под-вкладок
        tab_widget = QTabWidget()


        # Вкладка 1: текущая содержимое
        sub_tab1 = QWidget()
        sub_layout1 = QVBoxLayout()

        table_layout = QHBoxLayout()

        # Создаем таблицу splash_table
        self.splash_table = QTableWidget()
        self.splash_table.setColumnCount(8)
        self.splash_table.setHorizontalHeaderLabels(
            ['Выбрать', 'ID', 'Name', 'Group', 'Secret Token', 'Proxy', 'Account Balance', 'Created At'])
        header = self.splash_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        table_layout.addWidget(self.splash_table)

        # Создаем таблицу для отображения текущего прогресса торговли по аккаунтам
        self.progress_table = QTableWidget()
        self.progress_table.setColumnCount(6)
        self.progress_table.setHorizontalHeaderLabels(['ID', 'Name', 'Start Balance', 'Current Trade Progress', 'Finish Balance', 'Difference'])
        header = self.progress_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        table_layout.addWidget(self.progress_table)

        sub_layout1.addLayout(table_layout)
        sub_tab1.setLayout(sub_layout1)

        # Создаем макет для поля "Сумма для работы" и добавляем чекбокс для "Использовать весь доступный баланс"
        usdt_input_layout = QHBoxLayout()
        self.usdt_amount_label = QLabel('Сумма для работы:')
        self.usdt_amount_input = QLineEdit()

        # Чекбокс "Использовать весь доступный баланс"
        self.use_full_balance_checkbox = QCheckBox('Использовать весь доступный баланс')

        # Подключаем функцию для блокировки ввода
        self.use_full_balance_checkbox.stateChanged.connect(self.toggle_usdt_input)

        # Добавляем виджеты в макет
        usdt_input_layout.addWidget(self.usdt_amount_label)
        usdt_input_layout.addWidget(self.usdt_amount_input)
        usdt_input_layout.addWidget(self.use_full_balance_checkbox)

        # Добавляем макет в основной макет
        sub_layout1.addLayout(usdt_input_layout)

        # Остальные элементы интерфейса
        trade_amount_layout = QHBoxLayout()
        self.trade_amount_label = QLabel('Итоговый оборот:')
        self.trade_amount_input = QLineEdit()
        trade_amount_layout.addWidget(self.trade_amount_label)
        trade_amount_layout.addWidget(self.trade_amount_input)
        sub_layout1.addLayout(trade_amount_layout)

        token_name_layout = QHBoxLayout()
        self.token_name_label = QLabel('Название монеты:')
        self.dropdown_splash = QComboBox()
        self.get_promotions_button = QPushButton("Обновить действующие акции")
        self.get_promotions_button.clicked.connect(lambda: asyncio.create_task(self.on_get_drop_clicked('splash', self.dropdown_splash)))
        token_name_layout.addWidget(self.token_name_label)
        token_name_layout.addWidget(self.dropdown_splash)
        token_name_layout.addWidget(self.get_promotions_button)

        sub_layout1.addLayout(token_name_layout)

        self.start_button = QPushButton('Старт')
        self.start_button.clicked.connect(self.start_processing)
        sub_layout1.addWidget(self.start_button)

        # Вкладка 2: пустая
        sub_tab2 = QWidget()
        sub_layout2 = QVBoxLayout()
        sub_tab2.setLayout(sub_layout2)

        # Таблица
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(4)
        self.result_table.setHorizontalHeaderLabels(["ID", "Name", "Secure Token", "Total Rewards"])
        header = self.result_table.horizontalHeader()
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        sub_layout2.addWidget(self.result_table)
        # Кнопка
        self.check_rewards_button = QPushButton("Проверить награды")
        self.check_rewards_button.clicked.connect(lambda: asyncio.create_task(self.check_rewards_for_all_rows()))
        sub_layout2.addWidget(self.check_rewards_button)

        # Добавляем обе под-вкладки в QTabWidget
        tab_widget.addTab(sub_tab1, "Token Splash")
        tab_widget.addTab(sub_tab2, "Results")

        # Добавляем QTabWidget в основную вкладку
        layout.addWidget(tab_widget)
        self.tab1.setLayout(layout)

        self.last_checked_row = None

        # Установка фильтра событий
        QTimer.singleShot(0, lambda: asyncio.create_task(self.update_dropdown(self.dropdown_splash)))
        QTimer.singleShot(0, lambda: self.splash_table.viewport().installEventFilter(self))
        QTimer.singleShot(0, lambda: asyncio.create_task(self.load_data_from_db(self.splash_table)))
        QTimer.singleShot(0, lambda: asyncio.create_task(self.populate_table_from_database()))
        # QTimer.singleShot(0, self.start_schedule)
        # QTimer.singleShot(0, lambda: asyncio.create_task(self.populate_table()))
    async def populate_table(self):
        """
        Заполняет таблицу в соответствии с указанными требованиями.
        """
        try:

            self.result_table.setRowCount(100)  # Устанавливаем 100 строк
            self.result_table.insertColumn(3)  # Добавляем колонку NS на позицию 3
            self.result_table.setHorizontalHeaderItem(3, QTableWidgetItem("NS"))  # Название колонки NS

            filled_rows = random.sample(range(100), 80)  # Выбираем 80 случайных строк для заполнения "300 NS"

            for row in range(100):
                # Заполнение первой колонки: значения от 1 до 100
                self.result_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))

                # Заполнение второй колонки: bybit1 до bybit100
                self.result_table.setItem(row, 1, QTableWidgetItem(f"bybit{row + 1}"))

                # Заполнение третьей колонки: случайная строка с началом "eyJhbGciOiJFU" и длиной >= 40 символов
                random_string = "eyJhbGciOiJFU" + ''.join(random.choices(string.ascii_letters + string.digits, k=150))
                self.result_table.setItem(row, 2, QTableWidgetItem(random_string))

                # Заполнение четвертой колонки: "300 NS" или "0"
                if row in filled_rows:
                    self.result_table.setItem(row, 3, QTableWidgetItem("300 NS"))
                    # Заполнение пятой колонки: "14.29$" для строк с "300 NS"
                    self.result_table.setItem(row, 4, QTableWidgetItem("144.83$"))
                else:
                    self.result_table.setItem(row, 3, QTableWidgetItem("0"))
                    # Заполнение пятой колонки: пустое значение для остальных строк
                    self.result_table.setItem(row, 4, QTableWidgetItem(""))
        except Exception as e:
            print(e)

    async def check_rewards_for_all_rows(self):
        """
        Проверяет награды для каждой строки таблицы.
        """
        async with aiosqlite.connect('bybit_trader.db') as db:
            async with db.execute("SELECT id, secret_token, proxy FROM sessions") as cursor:
                rows = await cursor.fetchall()

                # Обрабатываем каждую строку
                tasks = [self.process_row(row) for row in rows]
                await asyncio.gather(*tasks)

    async def process_row(self, row):
        """
        Обрабатывает одну строку таблицы.
        """
        row_id, secret_token, proxy = row

        # Создаем сессию
        session = await self.create_session(secret_token, proxy)
        if isinstance(session, aiohttp.client.ClientSession):
            # Получаем данные через модуль GetResult
            result = GetResult(session=session)
            response = await result.get_result()
            print(response)
            # Обновляем таблицу
            await self.save_session(session, row_id)
            await self.update_table(row_id, response)
        else:
            print(f'error session {session}')
            await self.update_table(row_id, session)
    async def populate_table_from_database(self):
        """
        Заполняет таблицу начальными данными из базы данных.
        """
        async with aiosqlite.connect('bybit_trader.db') as db:
            async with db.execute("SELECT id, name, secret_token FROM sessions") as cursor:
                rows = await cursor.fetchall()

                # Заполняем таблицу
                for row in rows:
                    row_position = self.result_table.rowCount()
                    self.result_table.insertRow(row_position)
                    self.result_table.setItem(row_position, 0, QTableWidgetItem(str(row[0])))  # ID
                    self.result_table.setItem(row_position, 1, QTableWidgetItem(row[1]))  # Name
                    self.result_table.setItem(row_position, 2, QTableWidgetItem(row[2]))  # secure_token

    async def update_table(self, row_id, result):
        """
        Обновляет строку таблицы по ID на основе полученных данных.
        """
        # Ищем строку в таблице по ID
        for row_index in range(self.result_table.rowCount()):
            if self.result_table.item(row_index, 0).text() == str(row_id):
                # Если результат содержит два значения (словарь и строка)
                if isinstance(result, tuple) and len(result) == 2:
                    data_dict, last_column_value = result

                    # Проверка типов значений
                    if not isinstance(data_dict, dict) or not isinstance(last_column_value, str):
                        print(f"Некорректные типы данных в результате: {result}")
                        last_column_index = self.result_table.columnCount() - 1
                        print(f"Запись одиночного значения: '{result}' в последнюю колонку (индекс: {last_column_index})")
                        self.result_table.setItem(row_index, last_column_index, QTableWidgetItem(str(result)))
                        return

                    # Обработка словаря
                    for key, value in data_dict.items():
                        # Проверяем, существует ли колонка с именем key
                        column_names = [self.result_table.horizontalHeaderItem(i).text() for i in
                                        range(self.result_table.columnCount())]
                        if key not in column_names:
                            # Добавляем новую колонку на индекс 3, если её нет
                            self.result_table.insertColumn(3)
                            self.result_table.setHorizontalHeaderItem(3, QTableWidgetItem(key))
                            column_names.insert(3, key)

                        # Получаем индекс добавленной или существующей колонки
                        column_index = column_names.index(key)

                        # Обновляем значение в строке
                        print(f"Запись значения: '{value}' в колонку '{key}' (индекс: {column_index})")
                        self.result_table.setItem(row_index, column_index, QTableWidgetItem(str(value)))

                    # Добавляем значение в последнюю колонку
                    last_column_index = self.result_table.columnCount() - 1
                    print(f"Запись значения в последнюю колонку: '{last_column_value}' (индекс: {last_column_index})")
                    self.result_table.setItem(row_index, last_column_index, QTableWidgetItem(last_column_value))

                # Если результат содержит одно значение
                elif isinstance(result, (str, int, float)):
                    last_column_index = self.result_table.columnCount() - 1
                    print(f"Запись одиночного значения: '{result}' в последнюю колонку (индекс: {last_column_index})")
                    self.result_table.setItem(row_index, last_column_index, QTableWidgetItem(str(result)))

                else:
                    print(f"Некорректный формат результата: {result}")

                break

    def toggle_usdt_input(self, state):
        """Блокировка или разблокировка поля ввода суммы в зависимости от состояния чекбокса."""
        try:
            # Проверяем состояние чекбокса и блокируем или разблокируем поле ввода
            if state == 2:
                self.usdt_amount_input.setDisabled(True)
            else:
                self.usdt_amount_input.setDisabled(False)
        except Exception as e:
            print(f"Ошибка при переключении доступности поля ввода: {e}")

    async def load_splash_from_db(self):
        try:
            async with aiosqlite.connect('bybit_trader.db') as db:
                async with db.execute('SELECT * FROM sessions') as cursor:
                    rows = await cursor.fetchall()

                    # Обновляем интерфейс
                    self.splash_table.setRowCount(len(rows))
                    for row_idx, row_data in enumerate(rows):
                        for col_idx, data in enumerate(row_data):
                            self.splash_table.setItem(row_idx, col_idx, QTableWidgetItem(str(data)))
        except Exception as e:
            print(f"Ошибка при загрузке данных из базы данных: {e}")

    def init_tab2(self):
        # Настройка компоновки для второй вкладки
        layout = QVBoxLayout()

        # Выпадающий список для выбора цепочки
        input_layout = QHBoxLayout()
        self.chain_label = QLabel('Выберите цепочку:')
        self.chain_dropdown = QComboBox()
        self.chain_dropdown.addItems(
            ["ERC20", "TRC20", "Arbitrum One", "SOL", "BSC (BEP20)", "Polygon PoS", "OP Mainnet", "AVAXC",
             "Mantle Network", "KAVAEVM", "CELO", "TON"])
        input_layout.addWidget(self.chain_label)
        input_layout.addWidget(self.chain_dropdown)
        layout.addLayout(input_layout)

        # Кнопка для запуска получения адреса депозита
        self.start_deposit_button = QPushButton('Получить адрес депозита')
        self.start_deposit_button.clicked.connect(lambda: asyncio.create_task(self.on_get_deposit_address_clicked()))
        layout.addWidget(self.start_deposit_button)

        # Таблица для отображения данных из таблицы addresses
        self.addresses_table = QTableWidget()
        self.addresses_table.setColumnCount(7)
        self.addresses_table.setHorizontalHeaderLabels(['ID', 'Name', 'Group', 'Secret Token', 'Proxy', 'Address', 'Tag'])
        self.addresses_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        self.addresses_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        # Разрешить пользователю изменять размеры колонок по ширине
        header = self.addresses_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)  # Растягивает все колонки по ширине всей таблицы
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)

        # Добавляем таблицу в основной макет
        layout.addWidget(self.addresses_table)

        # Устанавливаем компоновку для второй вкладки
        self.tab2.setLayout(layout)

        # Загрузить данные из базы данных при открытии вкладки
        QTimer.singleShot(0, lambda: asyncio.create_task(self.load_addresses_from_db(self.addresses_table)))

    def keyPressEvent(self, event):
        # Переопределение Ctrl+C для копирования выделенных ячеек
        if event.matches(QKeySequence.StandardKey.Copy):
            self.copy_selection()
        else:
            super().keyPressEvent(event)

    def copy_selection(self):
        selected_ranges = self.addresses_table.selectedRanges()
        if not selected_ranges:
            return

        copied_text = []

        for selected_range in selected_ranges:
            for row in range(selected_range.topRow(), selected_range.bottomRow() + 1):
                row_data = []
                for col in range(selected_range.leftColumn(), selected_range.rightColumn() + 1):
                    item = self.addresses_table.item(row, col)
                    row_data.append(item.text() if item else "")
                copied_text.append("\t".join(row_data))

        copied_text_str = "\n".join(copied_text)

        # Копирование текста в буфер обмена
        QGuiApplication.clipboard().setText(copied_text_str)

    async def load_addresses_from_db(self, table_widget):
        try:
            async with aiosqlite.connect('bybit_trader.db') as db:
                async with db.execute('SELECT * FROM addresses') as cursor:
                    rows = await cursor.fetchall()
                    print(f"Найдено строк: {len(rows)} в таблице addresses")
                    # Обновляем интерфейс
                    table_widget.setRowCount(len(rows))
                    for row_idx, row_data in enumerate(rows):
                        for col_idx, data in enumerate(row_data):
                            table_widget.setItem(row_idx, col_idx, QTableWidgetItem(str(data)))
        except Exception as e:
            print(f"Ошибка при загрузке данных из базы данных: {e}")

    def fetch_addresses_from_db(self):
        """Выполняет запрос к базе данных для получения всех адресов."""
        self.cursor.execute('SELECT * FROM addresses')
        return self.cursor.fetchall()
    async def on_get_deposit_address_clicked(self):
        """Обработчик события для кнопки 'Получить адрес депозита'."""
        try:
            await self.start_deposit_address()  # Ждем завершения задачи
            await self.load_addresses_from_db(self.addresses_table)  # Обновляем таблицу после завершения задачи
        except Exception as e:
            print(f"Ошибка при получении адреса депозита: {e}")

    def init_tab3(self):
        # Настройка компоновки для вкладки настроек
        layout = QVBoxLayout()

        # Кнопка загрузки Excel файла с готовыми secure токенами
        self.load_button = QPushButton('Загрузить Excel файл с готовыми secure токенами')
        self.load_button.clicked.connect(self.load_excel_file)
        layout.addWidget(self.load_button)

        # Контейнер для кнопок load_button_2fa и secure_tokens_button
        buttons_layout = QVBoxLayout()

        # Кнопка загрузки Excel файла с данными от аккаунта с 2fa
        self.load_button_2fa = QPushButton('Загрузить Excel файл с данными от аккаунтов с 2fa')
        self.load_button_2fa.clicked.connect(self.load_2fa_file)
        buttons_layout.addWidget(self.load_button_2fa)

        # Кнопка сделать secure_tokens
        self.secure_tokens_button = QPushButton('Сделать secure_tokens')
        self.secure_tokens_button.clicked.connect(self.handle_login)
        buttons_layout.addWidget(self.secure_tokens_button)

        layout.addLayout(buttons_layout)

        # Устанавливаем компоновку для вкладки настроек
        self.tab3.setLayout(layout)

    def init_tab7(self):
        try:
            layout = QVBoxLayout()
            tab_widget = QTabWidget()

            sub_tab1 = QWidget()
            sub_layout1 = QVBoxLayout()

            # Выпадающий список для выбора типа аккаунта
            self.account_type_combo_box = QComboBox()
            self.account_type_combo_box.addItems(["FUNDING ACCOUNT", "UNIFIED ACCOUNT"])

            # Кнопка "Получить баланс"
            self.get_balance_button = QPushButton("Получить баланс")
            self.get_balance_button.clicked.connect(lambda: asyncio.create_task(self.update_all_balances()))

            top_layout = QHBoxLayout()
            top_layout.addWidget(self.get_balance_button)
            top_layout.addWidget(self.account_type_combo_box)
            sub_layout1.addLayout(top_layout)

            # Выпадающий список с монетами
            self.coin_combo_box = QComboBox()
            self.coin_combo_box.currentTextChanged.connect(
                lambda: asyncio.create_task(self.update_table_for_selected_coin()))


            # Таблица
            self.table_trans = QTableWidget()
            self.table_trans.setColumnCount(4)
            self.table_trans.setHorizontalHeaderLabels(["ID", "Name", "Group", "Balance"])

            # Добавление виджетов в макет
            sub_layout1.addWidget(self.get_balance_button)

            # Горизонтальный макет для выпадающего списка
            h_layout = QHBoxLayout()
            h_layout.addWidget(self.coin_combo_box)
            sub_layout1.addLayout(h_layout)

            sub_layout1.addWidget(self.table_trans)
            sub_tab1.setLayout(sub_layout1)

            # Вкладка 2: Transfer
            sub_tab2 = QWidget()
            sub_layout2 = QVBoxLayout()

            # Выпадающий список из монет, синхронизированный с первой вкладкой
            self.transfer_coin_combo_box = QComboBox()
            self.transfer_coin_combo_box.currentTextChanged.connect(
                lambda: asyncio.create_task(self.update_table_for_selected_coin()))

            # Два выпадающих списка и текст "на"
            self.from_account_combo_box = QComboBox()
            self.from_account_combo_box.addItems(["FUNDING ACCOUNT", "UNIFIED ACCOUNT"])

            self.to_account_combo_box = QComboBox()
            self.to_account_combo_box.addItems(["FUNDING ACCOUNT", "UNIFIED ACCOUNT"])

            account_layout = QHBoxLayout()
            account_layout.addWidget(self.from_account_combo_box)

            # Поле ввода суммы для перевода
            amount_layout = QHBoxLayout()
            self.amount_label = QLabel("Сумма для перевода:")
            self.amount_input = QLineEdit()
            amount_layout.addWidget(self.amount_label)
            amount_layout.addWidget(self.amount_input)

            # Кнопка "Перевести"
            self.transfer_button = QPushButton("Перевести")
            self.transfer_button.clicked.connect(lambda: asyncio.create_task(self.execute_transfers()))

            # Таблица для Transfer
            self.transfer_table = QTableWidget()
            self.transfer_table.setColumnCount(4)
            self.transfer_table.setHorizontalHeaderLabels(["ID", "Name", "Group", "Balance"])

            # Добавление виджетов в макет Transfer
            sub_layout2.addWidget(self.transfer_coin_combo_box)
            sub_layout2.addLayout(account_layout)
            sub_layout2.addLayout(amount_layout)
            sub_layout2.addWidget(self.transfer_button)
            sub_layout2.addWidget(self.transfer_table)
            sub_tab2.setLayout(sub_layout2)

            tab_widget.addTab(sub_tab1, "Balance")
            tab_widget.addTab(sub_tab2, "Transfer")
            layout.addWidget(tab_widget)
            self.tab7.setLayout(layout)
            # Загрузка аккаунтов из базы данных
            QTimer.singleShot(0, lambda: self.loop.create_task(self.load_accounts()))
        except Exception as e:
            print(e)



    async def load_accounts(self):
        try:
            """Загрузка аккаунтов из базы данных."""
            connection = sqlite3.connect("bybit_trader.db")
            cursor = connection.cursor()
            cursor.execute("SELECT id, name, group_name, secret_token, proxy FROM sessions")
            accounts = cursor.fetchall()
            connection.close()

            self.table_trans.setRowCount(len(accounts))
            for row_idx, (account_id, name, group_name, secret_token, proxy) in enumerate(accounts):
                self.table_trans.setItem(row_idx, 0, QTableWidgetItem(str(account_id)))
                self.table_trans.setItem(row_idx, 1, QTableWidgetItem(name))
                self.table_trans.setItem(row_idx, 2, QTableWidgetItem(group_name))

            self.transfer_table.setRowCount(len(accounts))
            for row_idx, (account_id, name, group_name, secret_token, proxy) in enumerate(accounts):
                self.transfer_table.setItem(row_idx, 0, QTableWidgetItem(str(account_id)))
                self.transfer_table.setItem(row_idx, 1, QTableWidgetItem(name))
                self.transfer_table.setItem(row_idx, 2, QTableWidgetItem(group_name))

            self.accounts = accounts  # Сохраняем аккаунты для последующего использования
            print(accounts)
        except Exception as e:
            print(e)

    async def update_balance_for_account(self, row_idx, secret_token, proxy):
        try:
            """Асинхронное обновление баланса для конкретного аккаунта."""
            account_type = 'fund' if self.account_type_combo_box.currentText() == "FUNDING ACCOUNT" else 'unif'
            balances = await self.get_coin_balances_for_account(secret_token, account_type, proxy)
            selected_coin = self.coin_combo_box.currentText()
            selected_coin2 = self.transfer_coin_combo_box.currentText()
            balance = balances.get(selected_coin, "0")
            self.table_trans.setItem(row_idx, 3, QTableWidgetItem(balance))

            balance2 = balances.get(selected_coin2, "0")
            self.transfer_table.setItem(row_idx, 3, QTableWidgetItem(balance2))

            # Обновляем выпадающий список монет
            existing_coins = [self.coin_combo_box.itemText(i) for i in range(self.coin_combo_box.count())]
            for coin in balances.keys():
                if coin not in existing_coins:
                    self.coin_combo_box.addItem(coin)

            existing_coins = [self.transfer_coin_combo_box.itemText(i) for i in range(self.transfer_coin_combo_box.count())]
            for coin in balances.keys():
                if coin not in existing_coins:
                    self.transfer_coin_combo_box.addItem(coin)
        except Exception as e:
            print(e)

    async def update_all_balances(self):
        try:
            """Обновление баланса для всех аккаунтов."""
            tasks = []
            for row_idx, (_, _, _, secret_token, proxy) in enumerate(self.accounts):
                tasks.append(self.update_balance_for_account(row_idx, secret_token, proxy))

            await asyncio.gather(*tasks)
        except Exception as e:
            print(e)

    async def update_table_for_selected_coin(self):
        try:
            """Обновление таблицы для выбранной монеты."""
            tasks = []
            for row_idx, (_, _, _, secret_token, proxy) in enumerate(self.accounts):
                tasks.append(self.update_balance_for_account(row_idx, secret_token, proxy))

            await asyncio.gather(*tasks)
        except Exception as e:
            print(e)

    async def get_coin_balances_for_account(self, secure_token, account_type, proxy):
        session = await self.create_session(secure_token, proxy)
        transfer = GetBalance(account_type, session)
        return await transfer.send_request()

    async def execute_transfers(self):
        try:
            """Асинхронный перевод для всех аккаунтов."""
            coin = self.transfer_coin_combo_box.currentText()
            from_account = self.from_account_combo_box.currentText()
            to_account = self.to_account_combo_box.currentText()
            direction = "fund_to_unified" if from_account == "UNIFIED ACCOUNT" else "unified_to_fund"
            sum_to_transfer = self.amount_input.text()

            tasks = []
            for row_idx, (_, _, _, secure_token, proxy) in enumerate(self.accounts):
                async def transfer_for_account(secure_token, proxy):
                    session = await self.create_session(secure_token, proxy)
                    transfer = Transfer(direction, sum_to_transfer, session, coin)
                    await transfer.send_request()

                tasks.append(transfer_for_account(secure_token, proxy))

            await asyncio.gather(*tasks)
        except Exception as e:
            print(f"Ошибка в execute_transfers: {e}")
    def init_tab4(self):
        try:
            # Настройка компоновки для вкладки управления базой данных
            layout = QVBoxLayout()

            # Таблица для отображения данных из базы данных
            self.db_table = QTableWidget()
            self.db_table.setColumnCount(8)  # Добавляем дополнительную колонку для галочек
            self.db_table.setHorizontalHeaderLabels(
                ['Выбрать', 'ID', 'Name', 'Group', 'Secret Token', 'Proxy', 'Account Balance', 'Created At'])
            self.db_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            self.db_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            layout.addWidget(self.db_table)

            # Кнопки для управления таблицей
            self.load_data_button = QPushButton('Загрузить данные')
            self.load_data_button.clicked.connect(lambda: asyncio.create_task(self.load_data_from_db(self.db_table)))
            layout.addWidget(self.load_data_button)

            self.save_changes_button = QPushButton('Сохранить изменения')
            self.save_changes_button.clicked.connect(self.save_changes_to_db)
            layout.addWidget(self.save_changes_button)

            self.delete_row_button = QPushButton('Удалить выбранные строки')
            self.delete_row_button.clicked.connect(self.delete_selected_row)
            layout.addWidget(self.delete_row_button)

            # Устанавливаем компоновку для вкладки управления базой данных
            self.tab4.setLayout(layout)

            # Инициализация переменной для отслеживания
            self.last_checked_row = None

            # Теперь можно установить фильтр событий
            self.db_table.viewport().installEventFilter(self)
        except Exception as e:
            print(e)

    def init_tab5(self):
        # Основной макет
        layout = QVBoxLayout()

        # Выпадающий список и кнопка "Получить акции"
        dropdown_layout = QHBoxLayout()
        self.dropdown = QComboBox()
        dropdown_layout.addWidget(self.dropdown)
        self.get_promotions_button = QPushButton("Обновить действующие акции")
        self.get_promotions_button.clicked.connect(lambda: asyncio.create_task(self.on_get_drop_clicked('splash', self.dropdown)))

        dropdown_layout.addWidget(self.get_promotions_button)

        # Список заданий с галочками
        self.task_checkboxes = {
            "Регистрация": QCheckBox("Регистрация"),
            "Задание 1": QCheckBox("Задание 1"),
            "Задание 2": QCheckBox("Задание 2"),
            "Задание 3": QCheckBox("Задание 3"),
            "Задание 5": QCheckBox("Задание 5"),
            "Задание 6": QCheckBox("Задание 6"),
        }
        tasks_layout = QVBoxLayout()
        for task, checkbox in self.task_checkboxes.items():
            tasks_layout.addWidget(checkbox)
            # Подключение события для Задания 6
            if task == "Задание 6":
                checkbox.stateChanged.connect(self.toggle_import_button)

        # Кнопка для импорта Excel
        self.import_button = QPushButton("Импортировать Excel")
        self.import_button.setEnabled(False)
        self.import_button.clicked.connect(self.import_excel)

        # Добавление виджетов в основной макет
        layout.addLayout(dropdown_layout)
        layout.addLayout(tasks_layout)
        layout.addWidget(self.import_button)

        self.tab5.setLayout(layout)

        # Используем QTimer.singleShot, чтобы запустить update_dropdown после запуска цикла событий
        QTimer.singleShot(0, lambda: asyncio.create_task(self.update_dropdown(self.dropdown)))

    def init_tab6(self):
        layout = QVBoxLayout()

        # Create scroll area to add cards for each token
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        # Получить данные о токенах асинхронно и добавить карточки
        # asyncio.create_task(self.add_token_cards(scroll_layout))

        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        self.tab6.setLayout(layout)

        QTimer.singleShot(0, lambda: asyncio.create_task(self.add_token_cards(scroll_layout)))



    async def add_token_cards(self, layout):
        # Создаем асинхронную сессию и получаем данные
        session = await self.create_session()
        splash_info = SplashInfo(session)
        tokens_data = await splash_info.get_info()

        for token in tokens_data:
            card = self.create_card(token)
            layout.addWidget(card)

    def create_card(self, token_info):
        # Создаем виджет карточки
        card = QFrame()  # Используем QFrame для возможности установки границ
        card_layout = QVBoxLayout(card)

        # Настройки стилей для карточки
        card.setStyleSheet("""
            QFrame {
                border: 1px solid #C0C0C0;  /* Серая рамка */
                border-radius: 10px;
                
                padding: 15px;
                margin: 10px;
            }
        """)

        # Название токена
        name_label = QLabel(f"Название токена: {token_info['name']}")
        name_label.setStyleSheet("font-weight: bold; font-size: 16px; ")
        card_layout.addWidget(name_label)

        # Ссылка на токен
        link_label = QLabel(f'<a href="{token_info["link"]}">Подробнее о токене</a>')
        link_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction | Qt.TextInteractionFlag.LinksAccessibleByMouse)
        link_label.setOpenExternalLinks(True)
        link_label.setStyleSheet("font-size: 14px; color: #1E90FF;")
        card_layout.addWidget(link_label)

        # Общий призовой пул
        prize_pool_label = QLabel(f"Общий призовой пул: {token_info['total_prize_pool']}")
        prize_pool_label.setStyleSheet("font-size: 14px; ")
        card_layout.addWidget(prize_pool_label)

        # Количество участников
        participants_label = QLabel(f"Участников: {token_info['participants']}")
        participants_label.setStyleSheet("font-size: 14px; ")
        card_layout.addWidget(participants_label)

        # Флаг для старых пользователей
        old_users_label = QLabel(
            "Доступно для всех" if token_info['for_old_users'] else "Только для новых пользователей")
        old_users_label.setStyleSheet(
            "font-size: 14px; color: #006400;" if token_info['for_old_users'] else "font-size: 14px; color: #8B0000;")
        card_layout.addWidget(old_users_label)

        # Время действия
        action_time_label = QLabel(f"Время активности: {token_info['action_time']}")
        action_time_label.setStyleSheet("font-size: 14px; ")
        card_layout.addWidget(action_time_label)

        # Время депозита
        deposit_time_label = QLabel(f"Время депозита: {token_info['deposit_time']}")
        deposit_time_label.setStyleSheet("font-size: 14px; ")
        card_layout.addWidget(deposit_time_label)

        # Добавляем иконку токена
        icon_label = QLabel()
        pixmap = QPixmap()
        icon_label.setPixmap(pixmap)
        icon_label.setFixedSize(90, 90)
        icon_label.setScaledContents(True)
        card_layout.addWidget(icon_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Загрузка иконки асинхронно и её установка
        async def load_icon():
            try:
                session = await self.create_session()
                async with session.get(token_info['icon_link']) as response:
                    data = await response.read()
                    pixmap.loadFromData(data)
                    # Проверка на то, что виджет еще существует
                    if not icon_label.isHidden():
                        icon_label.setPixmap(pixmap)
                await session.close()
            except Exception as e:
                print(f"Ошибка при загрузке иконки: {e}")

        asyncio.create_task(load_icon())

        # Добавляем таймер обратного отсчета
        countdown_label = QLabel()
        countdown_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #FF4500;")
        card_layout.addWidget(countdown_label)

        end_time = QDateTime.fromString(token_info['deposit_time'].split(' - ')[1], 'yyyy-MM-dd HH:mm:ss')
        timer = QTimer(card)

        def update_countdown():
            remaining_time = QDateTime.currentDateTime().secsTo(end_time)
            if remaining_time > 0:
                countdown_text = str(timedelta(seconds=remaining_time))
                countdown_label.setText(f"До окончания: {countdown_text}")
            else:
                countdown_label.setText("Акция завершена")
                timer.stop()

        timer.timeout.connect(update_countdown)
        timer.start(1000)
        update_countdown()

        # Добавляем кнопку для участия
        participate_button = QPushButton("Принять участие")
        participate_button.setStyleSheet("""
            QPushButton {
                background-color: #F0F0F0;
                color: #333;
                font-size: 14px;
                padding: 8px;
                border-radius: 5px;
                border: 1px solid #C0C0C0;
            }
            QPushButton:hover {
                background-color: #E0E0E0;
            }
        """)
        participate_button.clicked.connect(lambda: self.switch_tab(self.tab1))
        card_layout.addWidget(participate_button, alignment=Qt.AlignmentFlag.AlignCenter)

        return card

    def toggle_import_button(self):
        """Активировать или деактивировать кнопку импорта в зависимости от Задания 6"""
        is_checked = self.task_checkboxes["Задание 6"].isChecked()
        self.import_button.setEnabled(is_checked)

    def import_excel(self):
        """Открыть диалоговое окно для выбора Excel-файла"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Выбрать Excel-файл", "", "Excel Files (*.xlsx *.xls)")
        if file_path:
            print(f"Выбран файл: {file_path}")

    async def on_get_drop_clicked(self, type, element):
        """Обработка нажатия кнопки 'Обновить действующие акции'"""
        # Сначала ждем завершения обновления данных в базе данных
        await self.get_spotx(type)
        # После этого обновляем выпадающий список
        await self.update_dropdown(element)

    async def update_dropdown(self, element):
        """Обновить выпадающий список данными из колонки базы данных."""
        try:
            # Очищаем выпадающий список перед обновлением
            element.clear()

            # Выбираем данные из колонки 'splash' в таблице 'events'
            self.cursor.execute('SELECT splash FROM events')
            rows = self.cursor.fetchall()
            print(f"Полученные строки из базы данных для dropdown: {rows}")

            # Добавляем данные в выпадающий список
            for row in rows:
                if row[0] is not None:
                    # Преобразуем строку JSON обратно в список
                    splash_values = json.loads(row[0])
                    if isinstance(splash_values, list):
                        for value in splash_values:
                            element.addItem(value)
                    else:
                        # Если вдруг это не список, добавляем как есть
                        element.addItem(splash_values)

            print("Выпадающий список обновлен данными из колонки базы данных.")
        except sqlite3.Error as e:
            print(f"Ошибка при обновлении выпадающего списка: {e}")

    async def get_spotx(self, type):
        try:

            session = await self.create_session()
            bybit_api = Actions(session, type)
            response = await bybit_api.main()

            # Закрываем сессию
            await session.close()

            try:
                # Преобразуем список в строку JSON перед сохранением
                response_json = json.dumps(response)
                print(f"JSON для сохранения в базу данных: {response_json}")

                # Проверяем наличие строки с id = 1 в таблице events
                self.cursor.execute('SELECT * FROM events WHERE id = 1')
                row = self.cursor.fetchone()

                if not row:
                    # Если строки с id = 1 нет, добавляем новую строку
                    self.cursor.execute('''
                        INSERT INTO events (id, splash, drophunt)
                        VALUES (?, ?, ?)
                    ''', (1, response_json if type == 'splash' else "0",
                          response_json if type == 'drophunt' else "0"))
                    print(f"Добавлена новая строка в таблицу events с id = 1 и значением '{type}'.")
                else:
                    # Если строка существует, обновляем соответствующую колонку
                    self.cursor.execute(f'''
                        UPDATE events
                        SET {type} = ?
                        WHERE id = ?
                    ''', (response_json, 1))
                    print(f"Успешно обновлена колонка '{type}'.")

                # Сохранение изменений
                self.conn.commit()

                # Проверяем результат обновления
                self.cursor.execute('SELECT * FROM events')
                rows = self.cursor.fetchall()
                print(f"Текущее состояние таблицы events после обновления: {rows}")

            except sqlite3.Error as e:
                print(f"Ошибка при обновлении данных: {e}")

        except Exception as e:
            print(f"Ошибка: {e}")

    async def load_data_from_db(self, table_widget):
        """Асинхронная загрузка данных из таблицы sessions в указанный виджет таблицы."""
        try:
            # Список запрещённых столбцов
            forbidden_columns = {"abck", "bm_sz", "bm_sv", "ak_bmsc"}

            async with aiosqlite.connect('bybit_trader.db') as db:
                # Получаем названия столбцов таблицы
                async with db.execute("PRAGMA table_info(sessions)") as cursor:
                    columns_info = await cursor.fetchall()
                    column_names = [col[1] for col in columns_info]

                # Определяем индексы разрешённых столбцов
                allowed_indices = [
                    idx for idx, col_name in enumerate(column_names)
                    if col_name not in forbidden_columns
                ]
                allowed_column_names = [
                    col_name for col_name in column_names
                    if col_name not in forbidden_columns
                ]

                # Если нет разрешённых данных, завершаем функцию
                if not allowed_indices:
                    print("Нет разрешённых данных для отображения.")
                    return

                # Загружаем строки только с разрешёнными данными
                async with db.execute("SELECT * FROM sessions") as cursor:
                    rows = await cursor.fetchall()

                    # Проверяем, нужно ли добавить колонку для чекбоксов
                    table_widget.setColumnCount(len(allowed_indices) + 1)
                    header_labels = ['Выбрать'] + allowed_column_names
                    table_widget.setHorizontalHeaderLabels(header_labels)

                    # Очистить таблицу перед загрузкой данных
                    table_widget.setRowCount(0)

                    # Заполнить таблицу данными
                    table_widget.setRowCount(len(rows))
                    for row_idx, row_data in enumerate(rows):
                        # Создаем чекбокс для каждой строки
                        checkbox = QCheckBox()
                        checkbox.setChecked(False)  # Изначально галочка не установлена
                        checkbox.stateChanged.connect(
                            partial(self.on_checkbox_state_changed, table_widget)
                        )  # Подключаем сигнал изменения состояния
                        table_widget.setCellWidget(row_idx, 0, checkbox)  # Добавляем галочку в первую колонку

                        # Заполняем разрешённые колонки данными из базы данных
                        for col_idx, allowed_col_idx in enumerate(allowed_indices):
                            table_widget.setItem(
                                row_idx, col_idx + 1,
                                QTableWidgetItem(str(row_data[allowed_col_idx]))
                            )

                    # Дополнительно обновляем прогресс
                    self.update_progress_table(rows)

        except Exception as e:
            print(f"Ошибка при загрузке данных из базы данных: {e}")

    def on_checkbox_state_changed(self, table_widget):
        """Обработка изменения состояния чекбокса для множественного выделения."""
        sender = self.sender()
        if isinstance(sender, QCheckBox) and sender.isChecked():
            row_idx = table_widget.indexAt(sender.pos()).row()
            self.last_checked_row = row_idx

    def save_changes_to_db(self):
        """Сохранение изменений в базу данных."""
        for row_idx in range(self.db_table.rowCount()):
            id_item = self.db_table.item(row_idx, 1)
            name = self.db_table.item(row_idx, 2)
            group_name = self.db_table.item(row_idx, 3)
            secret_token_item = self.db_table.item(row_idx, 4)
            proxy_item = self.db_table.item(row_idx, 5)
            created_at_item = self.db_table.item(row_idx, 7)
            if id_item and secret_token_item and proxy_item and created_at_item:
                session_id = int(id_item.text())
                secret_token = secret_token_item.text()
                proxy = proxy_item.text()
                created_at = created_at_item.text()
                if name:
                    name = name.text()
                if group_name:
                    group_name = group_name.text()
                # Обновляем данные в базе данных
                self.cursor.execute('''
                    UPDATE sessions
                    SET secret_token = ?, proxy = ?, created_at = ?, name = ?, group_name = ?
                    WHERE id = ?
                ''', (secret_token, proxy, created_at, name, group_name, session_id))
                self.cursor.execute('''
                    UPDATE addresses
                    SET secret_token = ?, proxy = ?, name = ?, group_name = ?
                    WHERE id = ?
                ''', (secret_token, proxy, name, group_name, session_id))
        asyncio.create_task(self.load_data_from_db(self.splash_table))
        asyncio.create_task(self.load_addresses_from_db(self.addresses_table))
        self.conn.commit()
        QMessageBox.information(self, "Успешно", "Изменения сохранены в базу данных")

    def eventFilter(self, source, event):
        """Фильтр событий для захвата нажатия мыши и реализации множественного выбора с Shift и Ctrl."""
        if source in [self.db_table, self.splash_table, self.db_table.viewport(), self.splash_table.viewport()]:
            # Проверяем тип события для обработки только нужных
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                # Запоминаем начальную позицию мыши при нажатии кнопки
                self.mouse_start_pos = event.pos()
                index = source.indexAt(event.pos()) if isinstance(source, QTableWidget) else source.parent().indexAt(
                    event.pos())

                if index.isValid():
                    current_row = index.row()
                    current_column = index.column()

                    # Проверяем, что клик произошел именно на колонку с чекбоксами (колонка 0)
                    if current_column == 0:
                        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier and self.last_checked_row is not None:
                            # Множественное выделение с помощью Shift
                            start_row = min(self.last_checked_row, current_row)
                            end_row = max(self.last_checked_row, current_row)
                            for row in range(start_row, end_row + 1):
                                checkbox = source.cellWidget(row, 0) if isinstance(source,
                                                                                   QTableWidget) else source.parent().cellWidget(
                                    row, 0)
                                if isinstance(checkbox, QCheckBox):
                                    checkbox.setChecked(
                                        not checkbox.isChecked() if event.modifiers() & Qt.KeyboardModifier.ControlModifier else True)
                        elif event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                            # Выбор с помощью Ctrl (переключение состояния чекбокса)
                            checkbox = source.cellWidget(current_row, 0) if isinstance(source,
                                                                                       QTableWidget) else source.parent().cellWidget(
                                current_row, 0)
                            if isinstance(checkbox, QCheckBox):
                                checkbox.setChecked(not checkbox.isChecked())
                        else:
                            # Обычный клик по строке
                            checkbox = source.cellWidget(current_row, 0) if isinstance(source,
                                                                                       QTableWidget) else source.parent().cellWidget(
                                current_row, 0)
                            if isinstance(checkbox, QCheckBox):
                                checkbox.setChecked(not checkbox.isChecked())
                            # Запоминаем последнюю выбранную строку для работы с Shift
                            self.last_checked_row = current_row

            elif event.type() == QEvent.Type.MouseMove and event.buttons() & Qt.MouseButton.LeftButton:
                # Проверяем, прошло ли достаточное расстояние для начала выделения
                if self.mouse_start_pos:
                    distance = (event.pos() - self.mouse_start_pos).manhattanLength()
                    min_distance = 10  # Минимальное расстояние для начала выделения (в пикселях)

                    if distance >= min_distance:
                        # Если расстояние достаточное, начинаем выделение
                        index = source.indexAt(event.pos()) if isinstance(source,
                                                                          QTableWidget) else source.parent().indexAt(
                            event.pos())
                        if index.isValid():
                            current_row = index.row()
                            current_column = index.column()

                            # Проверяем, что выделение происходит в колонке с чекбоксами (колонка 0)
                            if current_column == 0:
                                checkbox = source.cellWidget(current_row, 0) if isinstance(source,
                                                                                           QTableWidget) else source.parent().cellWidget(
                                    current_row, 0)
                                if isinstance(checkbox, QCheckBox):
                                    checkbox.setChecked(True)

            elif event.type() == QEvent.Type.MouseButtonRelease:
                # Сбрасываем начальную позицию при отпускании кнопки мыши
                self.mouse_start_pos = None

        # Возвращаем вызов родительскому классу для обработки всех остальных событий
        return super().eventFilter(source, event)

    def delete_selected_row(self):
        """Удаление выбранных строк из таблицы и базы данных."""
        rows_to_delete = []
        for row_idx in range(self.db_table.rowCount()):
            checkbox = self.db_table.cellWidget(row_idx, 0)
            if checkbox and checkbox.isChecked():
                id_item = self.db_table.item(row_idx, 1)  # ID теперь находится во второй колонке
                if id_item:
                    session_id = int(id_item.text())
                    rows_to_delete.append((session_id, row_idx))

        if rows_to_delete:
            for session_id, row_idx in sorted(rows_to_delete, key=lambda x: x[1], reverse=True):
                # Удаляем запись из базы данных
                self.cursor.execute('DELETE FROM sessions WHERE id = ?', (session_id,))
                self.cursor.execute('DELETE FROM addresses WHERE id = ?', (session_id,))
                self.conn.commit()

                # Удаляем строку из таблицы
                self.db_table.removeRow(row_idx)
            asyncio.create_task(self.load_data_from_db(self.splash_table))
            asyncio.create_task(self.load_addresses_from_db(self.addresses_table))
            QMessageBox.information(self, "Успешно", "Выбранные строки удалены из базы данных")
        else:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, выберите строки для удаления")



    async def create_session(self, secure_token=False, proxy=False):
        """Асинхронное создание сессии aiohttp для secure_token."""
        headers = {
            "Sec-Ch-Ua-Platform": "\"Windows\"",
            "Lang": "en",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Ch-Ua": "\"Not?A_Brand\";v=\"99\", \"Chromium\";v=\"130\"",
            "Sec-Ch-Ua-Mobile": "?0",
            "Usertoken": "",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.70 Safari/537.36",
            "Accept": "application/json",
            "Content-Type": "application/json;charset=UTF-8",
            "Platform": "pc",
            "Origin": "https://www.bybit.com",
            "Sec-Fetch-Site": "same-site",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Referer": "https://www.bybit.com/",
            "Accept-Encoding": "gzip, deflate, br",
            "Priority": "u=4, i",
        }
        if secure_token:
            cookies = {
                "secure-token": secure_token
            }
            # Подключение к базе данных для извлечения дополнительных куков
            async with aiosqlite.connect('bybit_trader.db') as db:
                cursor = await db.execute(
                    """
                    SELECT abck, bm_sz, bm_sv, ak_bmsc
                    FROM sessions 
                    WHERE secret_token = ?
                    """,
                    (secure_token,)
                )
                result = await cursor.fetchone()
                if result:
                    abck, bm_sz, bm_sv, ak_bmsc = result
                    # Если значения из базы данных найдены, добавляем их в куки
                    if abck:
                        cookies["_abck"] = abck
                    if bm_sz:
                        cookies["bm_sz"] = bm_sz
                    if bm_sv:
                        cookies["bm_sv"] = bm_sv
                    if ak_bmsc:
                        cookies["ak_bmsc"] = ak_bmsc
                else:
                    raise ValueError(f"secure_token '{secure_token}' не найден в базе данных.")
            if proxy:
                try:
                    # Создание сессии aiohttp с заголовками и куки
                    connector = ProxyConnector.from_url(proxy)
                    session = aiohttp.ClientSession(headers=headers, cookies=cookies, connector=connector)
                except Exception as e:
                    return str(e)
            else:
                try:
                    session = aiohttp.ClientSession(headers=headers, cookies=cookies)
                except Exception as e:
                    return str(e)
        else:
            # Создание сессии aiohttp с заголовками
            session = aiohttp.ClientSession(headers=headers)
        print('сессия создана:', session)
        return session
    async def save_session(self, session, row_id):
        # Словарь для хранения извлеченных куков
        cookie_values = {"secure-token": None, "_abck": None, "bm_sz": None, "bm_sv": None, "ak_bmsc": None}

        # Извлечение куков из cookie_jar
        for cookie in session.cookie_jar:
            print(cookie)
            if cookie.key in cookie_values:
                cookie_values[cookie.key] = cookie.value

        # Проверка обязательного кука
        if not cookie_values["secure-token"]:
            return "Куки secure-token отсутствуют в сессии"

        # Обновление базы данных
        async with aiosqlite.connect('bybit_trader.db') as db:
            await db.execute(
                """
                UPDATE sessions
                SET secret_token = ?, abck = ?, bm_sz = ?, bm_sv = ?, ak_bmsc = ?
                WHERE id = ?
                """,
                (
                    cookie_values["secure-token"],
                    cookie_values["_abck"],
                    cookie_values["bm_sz"],
                    cookie_values["bm_sv"],
                    cookie_values["ak_bmsc"],
                    row_id,
                ),
            )
            await db.commit()


    def load_2fa_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Загрузить Excel файл", "", "Excel Files (*.xlsx *.xls)")
        if file_name:
            df = pd.read_excel(file_name)
            if 'mail' in df.columns and 'pass' in df.columns and 'proxy' in df.columns and '2fa' in df.columns:
                try:
                    if 'group' in df.columns:
                        self.group = df['group'].tolist()
                    if 'name' in df.columns:
                        self.name = df['name'].tolist()
                    self.mail = df['mail'].tolist()
                    self.passwd = df['pass'].tolist()
                    self.proxy = df['proxy'].tolist()
                    self.otp_2fa = df['2fa'].tolist()

                    for mail, passwd, proxy, otp_2fa in zip(self.mail, self.passwd, self.proxy, self.otp_2fa):
                        print('подключаемся к бд')
                        # Проверяем, есть ли уже запись с таким же proxy
                        self.cursor.execute('SELECT * FROM credentials WHERE mail = ?', (mail,))
                        existing_row = self.cursor.fetchone()

                        if existing_row:
                            print('найдена обновленная запись')
                            # Если запись существует, проверяем mail
                            if existing_row[2] != passwd or existing_row[3] != proxy or existing_row[4] != otp_2fa:
                                # Обновляем данные и дату
                                self.cursor.execute('''
                                            UPDATE credentials
                                            SET password = ?, proxy = ?, otp_2fa = ?, created_at = ?
                                            WHERE mail = ?
                                        ''', (passwd, proxy, otp_2fa, datetime.now(), mail))
                                self.conn.commit()
                        else:
                            print('найдена новая запись')
                            # Если записи не существует, добавляем новую запись
                            try:
                                self.cursor.execute('''
                                            INSERT INTO credentials (mail, password, proxy, otp_2fa, created_at)
                                            VALUES (?, ?, ?, ?, ?)
                                        ''', (mail, passwd, proxy, otp_2fa, datetime.now()))
                                self.conn.commit()
                            except Exception as e:
                                print(e)

                    QMessageBox.information(self, "Успешно",
                                            f"Файл загружен успешно. Загружено аккаунтов: {len(self.mail)}")
                    asyncio.create_task(self.load_data_from_db(self.splash_table))
                    asyncio.create_task(self.load_addresses_from_db(self.addresses_table))
                except Exception as e:
                    print(QMessageBox.warning(self, "Ошибка", f"{e}"))
            else:
                QMessageBox.warning(self, "Ошибка", "Файл должен содержать столбцы 'mail', 'pass', 'proxy' и '2fa'")

    def handle_login(self):
        # Запуск асинхронной функции через событийный цикл PyQt
        asyncio.run(self.fetch_credentials_and_login())

    async def fetch_credentials_and_login(self):
        # Подключение к базе данных
        conn = sqlite3.connect('bybit_trader.db')
        cursor = conn.cursor()

        # Получение всех данных из таблицы credentials
        cursor.execute("SELECT mail, password, proxy, otp_2fa FROM credentials")
        rows = cursor.fetchall()

        tasks = []
        for row in rows:
            username, password, proxy, otp_code = row
            login_instance = Login(username, password, proxy, captcha_api_key='75c51a5218ce18a00f07614b1e1b77ce', otp=True, base32secret3232=otp_code)
            tasks.append(login_instance.start_login())

        # Выполнение всех логинов асинхронно
        results = await asyncio.gather(*tasks)
        for result in results:
            logger.info(f"Received token: {result[0]}\n PROXY: {result[1]}")
            self.cursor.execute('SELECT * FROM sessions WHERE proxy = ?', (result[1],))
            existing_row = self.cursor.fetchone()

            if existing_row:
                # Обновляем secret_token и дату
                self.cursor.execute('''
                    UPDATE sessions
                    SET secret_token = ?, created_at = ?
                    WHERE proxy = ?
                ''', (result[0], datetime.now(), result[1]))
                self.conn.commit()
            else:
                # Если записи не существует, добавляем новую запись
                self.cursor.execute('''
                    INSERT INTO sessions (secret_token, proxy, created_at) 
                    VALUES (?, ?, ?)
                ''', (result[0], result[1], datetime.now()))
                self.conn.commit()
        # Закрытие соединения с базой данных
        conn.close()

    def load_excel_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Загрузить Excel файл", "", "Excel Files (*.xlsx *.xls)")
        if file_name:
            df = pd.read_excel(file_name)
            # Проверяем наличие всех необходимых колонок
            has_group = 'group' in df.columns
            has_name = 'name' in df.columns

            if 'secret_token' in df.columns and 'proxy' in df.columns:
                # Извлекаем данные из столбцов
                self.secret_tokens = df['secret_token'].tolist()
                self.proxies = df['proxy'].tolist()
                self.groups = df['group'].tolist() if has_group else [None] * len(df)
                self.names = df['name'].tolist() if has_name else [None] * len(df)

                for secret_token, proxy, group, name in zip(self.secret_tokens, self.proxies, self.groups, self.names):
                    # Проверяем, есть ли уже запись с таким же proxy
                    self.cursor.execute(
                        'SELECT id, name, group_name, secret_token, proxy FROM sessions WHERE proxy = ?', (proxy,))
                    existing_row = self.cursor.fetchone()

                    if existing_row:
                        # Если запись существует, проверяем, нужно ли обновить secret_token или другие поля
                        if (existing_row[3] != secret_token or
                                (has_group and existing_row[2] != group) or
                                (has_name and existing_row[1] != name)):
                            # Обновляем данные и дату
                            self.cursor.execute('''
                                UPDATE sessions
                                SET secret_token = ?, created_at = ?, group_name = ?, name = ?
                                WHERE proxy = ?
                            ''', (secret_token, datetime.now(), group if group else existing_row[2],
                                  name if name else existing_row[1], proxy))
                            self.conn.commit()
                    else:
                        # Если записи не существует, добавляем новую запись
                        self.cursor.execute('''
                            INSERT INTO sessions (secret_token, proxy, created_at, group_name, name) 
                            VALUES (?, ?, ?, ?, ?)
                        ''', (secret_token, proxy, datetime.now(), group, name))
                        self.conn.commit()

                    # Проверяем, существует ли уже запись с данным proxy
                    self.cursor.execute('SELECT * FROM addresses WHERE proxy = ?', (proxy,))
                    existing_row = self.cursor.fetchone()

                    if existing_row:
                        # Обновляем запись, если она уже существует
                        self.cursor.execute('''
                                                UPDATE addresses
                                                SET secret_token = ?, group_name = ?, name = ?
                                                WHERE proxy = ?
                                            ''', (secret_token, group if group else existing_row[2],
                                  name if name else existing_row[1], proxy))
                        self.conn.commit()
                    else:
                        # Добавляем новую запись, если ее еще нет
                        self.cursor.execute('''
                                                INSERT INTO addresses (secret_token, proxy, group_name, name)
                                                VALUES (?, ?, ?, ?)
                                            ''', (secret_token, proxy, group, name))
                        self.conn.commit()

                QMessageBox.information(self, "Успешно",
                                        f"Файл загружен успешно. Загружено аккаунтов: {len(self.secret_tokens)}")
                asyncio.create_task(self.load_data_from_db(self.splash_table))
                asyncio.create_task(self.load_addresses_from_db(self.addresses_table))
            else:
                QMessageBox.warning(self, "Ошибка", "Файл должен содержать столбцы 'secret_token' и 'proxy'")

    async def fetch_deposit_address_for_account(self, chain, secure_token, proxy, account_id):
        print(secure_token, proxy)
        try:
            session = await self.create_session(secure_token, proxy)
            print(type(session))
            if isinstance(session, aiohttp.client.ClientSession):
                bybit_api = BybitAPI(chain=chain, coin="USDT", session=session)
                response = await bybit_api.get_deposit_address()
                print(response)
                print(type(response))
                address, tag = response
                # for cookie, value in session.cookie_jar:
                #     print(cookie, value)
                await self.save_session(session, account_id)
                print(f"addresses: {secure_token, proxy, address, tag}")
                return secure_token, proxy, address, tag
            else:
                return secure_token, proxy, session, ''
        except Exception as e:
            return f"Ошибка для proxy {proxy}: {str(e)}"

    async def process_deposit_addresses_async(self):
        chain = self.chain_dropdown.currentText()

        # Получение списка всех записей из базы данных
        self.cursor.execute('SELECT secret_token, proxy, id FROM sessions')
        rows = self.cursor.fetchall()

        tasks = [self.fetch_deposit_address_for_account(chain, secure_token, proxy, id) for secure_token, proxy, id in rows]

        results = await asyncio.gather(*tasks)
        print('results: ', results)
        # for result in results:
        for result in results:
            if result:
                print(result)
                # Ожидается, что результат будет в виде кортежа (secret_token, proxy, address)
                secret_token, proxy, address, tag = result

                # Проверяем, существует ли уже запись с данным proxy
                self.cursor.execute('SELECT * FROM addresses WHERE secret_token = ?', (secret_token,))
                existing_row = self.cursor.fetchone()

                if existing_row:
                    # Обновляем запись, если она уже существует
                    self.cursor.execute('''
                            UPDATE addresses
                            SET address = ?, address_tag = ?
                            WHERE secret_token = ?
                        ''', (address, tag, secret_token))
                else:
                    # Добавляем новую запись, если ее еще нет
                    self.cursor.execute('''
                            INSERT INTO addresses (secret_token, proxy, address, address_tag)
                            VALUES (?, ?, ?, ?)
                        ''', (secret_token, proxy, address, tag))

                # Коммитим изменения в базу данных
                self.conn.commit()

    async def start_deposit_address(self):
        try:
            # Проверка, есть ли хотя бы одна запись в базе данных
            self.cursor.execute('SELECT COUNT(*) FROM sessions')
            count = self.cursor.fetchone()[0]

            if count == 0:
                QMessageBox.warning(self, "Ошибка", "Сначала загрузите файл с токенами")
                return

            # Ожидаем завершения процесса получения адресов депозитов
            await self.process_deposit_addresses_async()

            # После завершения процесса обновляем таблицу
            await self.load_addresses_from_db(self.addresses_table)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def update_progress_table(self, rows):
        """Обновление таблицы прогресса с использованием данных из sessions."""
        self.progress_table.setRowCount(len(rows))
        for row_idx, row_data in enumerate(rows):
            id_item = QTableWidgetItem(str(row_data[0]))  # ID аккаунта
            name_item = QTableWidgetItem(str(row_data[1]))  # Имя аккаунта
            start_balance = QTableWidgetItem("0")
            progress_item = QTableWidgetItem("0")  # Начальное значение прогресса торговли
            finish_balance = QTableWidgetItem("0")
            difference = QTableWidgetItem("0")

            self.progress_table.setItem(row_idx, 0, id_item)
            self.progress_table.setItem(row_idx, 1, name_item)
            self.progress_table.setItem(row_idx, 2, start_balance)
            self.progress_table.setItem(row_idx, 3, progress_item)
            self.progress_table.setItem(row_idx, 4, finish_balance)
            self.progress_table.setItem(row_idx, 5, difference)

    def update_variable_async(self, account_id, variable_name, value):
        """Асинхронное обновление значения переменной для конкретного аккаунта."""
        QTimer.singleShot(0, lambda: self.update_variable(account_id, variable_name, value))

    def update_variable(self, account_id, variable_name, value):
        """Обновление значения переменной для конкретного аккаунта."""
        variable_column_map = {
            'start_balance': 2,
            'trade_amount': 3,
            'finish_balance': 4,
            'difference': 5,
        }

        column_idx = variable_column_map.get(variable_name)
        if column_idx is None:
            print(f"Ошибка: переменная {variable_name} не найдена")
            return

        # Обновляем значение в нужной колонке
        for row_idx in range(self.progress_table.rowCount()):
            id_item = self.progress_table.item(row_idx, 0)
            if id_item and id_item.text() == str(account_id):
                self.progress_table.setItem(row_idx, column_idx, QTableWidgetItem(str(value)))
                break

    def start_schedule(self):
        """Запускает планировщик после старта цикла событий."""
        asyncio.create_task(self.schedule_trader())
    async def schedule_trader(self):
        """Запланировать выполнение задачи в 10:00 UTC."""
        # QMessageBox.information(self, "Успешно", "Оборот начнется в 10:00 UTC")
        while True:
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc)

            target_time = now.replace(hour=10, minute=5, second=0, microsecond=0)

            if now >= target_time:
                # Если текущее время уже позже 10:00, запланируем на следующий день
                target_time += timedelta(days=1)

            # Рассчитать, сколько времени осталось до выполнения
            seconds_until_target = (target_time - now).total_seconds()
            print(f"Задача будет выполнена через {seconds_until_target} секунд.")

            # Ожидание до запланированного времени
            await asyncio.sleep(seconds_until_target)

            # Выполнить задачу после пробуждения
            await self.process_tokens_async()
            print("Задача выполнена в 10:00 UTC")

    async def start_trader(self, token, secure_token, usdt_start_count, trade_amount, proxy, is_full, account_id):
        session = await self.create_session(secure_token, proxy)
        print(session)
        trader = BybitTrader(token, usdt_start_count, is_full, trade_amount, session=session)
        usdt_count_start_balance = await trader.get_spot_wallet_balance("USDT")
        self.update_variable_async(account_id, 'start_balance', usdt_count_start_balance)
        # Регистрируем коллбек для обновления прогресса
        trader.register_progress_callback(lambda trade_progress: self.update_variable_async(account_id, 'trade_amount', "{:.8f}".format(trade_progress)))

        try:
            # Создаём и ожидаем завершение задачи, не закрывая сессию до её завершения
            result = await trader.run()
            print(result[0])
            if result[0] == 1:
                print("Задача успешно завершена")
                usdt_count_finish_balance = await trader.get_spot_wallet_balance("USDT")
                self.update_variable_async(account_id, 'finish_balance', usdt_count_finish_balance)
                usdt_count_difference = float(usdt_count_start_balance) - float(usdt_count_finish_balance)
                usdt_count_difference = "{:.8f}".format(usdt_count_difference)
                self.update_variable_async(account_id, 'difference', usdt_count_difference)
            else:
                self.update_variable_async(account_id, 'start_balance', result)
                self.update_variable_async(account_id, 'trade_amount', result)
                self.update_variable_async(account_id, 'finish_balance', result)
                self.update_variable_async(account_id, 'difference', result)
                print(f"Задача завершилась с ошибкой: {result}")
        except Exception as e:
            print(f"Unexpected error: {e}")
        finally:
            # Закрываем сессию только после того, как задача завершена
            print('Сохранение сессии')
            await self.save_session(session, account_id)
            # await session.close()

    async def schedule_task(self, target_hour=13, target_minute=2):
        """Запуск функции process_tokens_async в определённое время UTC."""
        from datetime import datetime, timezone, timedelta

        while True:
            now = datetime.now(timezone.utc)
            target_time = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)

            # Если текущее время уже позже целевого времени, планируем на следующий день
            if now >= target_time:
                target_time += timedelta(days=1)

            seconds_until_target = (target_time - now).total_seconds()
            print(f"Функция будет запущена через {seconds_until_target} секунд (в {target_time}).")

            # Ожидание до целевого времени
            await asyncio.sleep(seconds_until_target)

            # Запуск целевой функции
            print("Запуск функции process_tokens_async в 13:02 UTC")
            await self.process_tokens_async()

    async def process_tokens_async(self):
        try:
            usdt_start_count = float(self.usdt_amount_input.text())
        except ValueError:
            usdt_start_count = 0
            self.usdt_amount_input.setText("0")
        trade_amount = float(self.trade_amount_input.text())
        token_name = self.dropdown_splash.currentText()
        is_full = self.use_full_balance_checkbox.isChecked()

        selected_rows = []

        # Проход по всем строкам в таблице и проверка чекбоксов
        for row_idx in range(self.splash_table.rowCount()):
            checkbox = self.splash_table.cellWidget(row_idx, 0)
            if isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                selected_rows.append(row_idx)

        if not selected_rows:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, выберите хотя бы один аккаунт для обработки")
            return

        tasks = []

        for row_idx in selected_rows:
            secure_token_item = self.splash_table.item(row_idx, 4)
            proxy_item = self.splash_table.item(row_idx, 5)
            id_item = self.splash_table.item(row_idx, 1)
            print(f'id_item: {id_item.text()}')

            if secure_token_item and proxy_item:
                secure_token = secure_token_item.text()
                proxy = proxy_item.text()
                account_id = int(id_item.text())
                print(f'account_id: {account_id}')
                # Добавляем задачу с использованием secure_token и proxy из выбранной строки
                tasks.append(
                    self.start_trader(token_name, secure_token, usdt_start_count, trade_amount, proxy, is_full, account_id))

        # Используем asyncio.gather для параллельного выполнения всех задач
        await asyncio.gather(*tasks, return_exceptions=True)

    def start_processing(self):
        try:
            # Проверка, есть ли хотя бы одна запись в базе данных
            self.cursor.execute('SELECT COUNT(*) FROM sessions')
            count = self.cursor.fetchone()[0]

            if count == 0:
                QMessageBox.warning(self, "Ошибка", "Сначала загрузите файл с токенами")
                return

            asyncio.create_task(self.process_tokens_async())

            QMessageBox.information(self, "Успешно", "Процесс запущен")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

if __name__ == '__main__':
    app = QApplication(sys.argv)

    font = QFont('Regular', 10)
    app.setStyleSheet("""
            QPushButton {
                height: 16px;
            }
            QLineEdit {
                height: 20px;
            }
            QComboBox {
                height: 26px;
            }
        """)
    app.setFont(font)

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = BybitTraderApp()
    window.show()

    with loop:
        loop.run_forever()
