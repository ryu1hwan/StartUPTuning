import os
import traceback
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QTextEdit, QTableWidget, QMessageBox, QComboBox, QTableWidgetItem, QDialog, QDesktopWidget
import pymysql
import json
import encryption_module as em
from main import SQLExecutorApp  # MainWindow를 import
from PyQt5.QtGui import QFont, QFontDatabase, QIcon,QPixmap
from PyQt5.QtCore import Qt

class ConnectionDialog(QDialog):
    def __init__(self, login_data, parent):
        super(ConnectionDialog, self).__init__(parent)

        # 아이콘 설정
        self.setWindowIcon(QIcon("./resource/sut_icon.ico"))

        # Window 플래그 설정
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint & ~Qt.WindowCloseButtonHint)

        self.login_data = login_data
        self.setWindowTitle("Connection History")
        self.setGeometry(300, 300, 600, 400)  # (x, y, width, height)

        font_database = QFontDatabase()
        font_id = font_database.addApplicationFont("./resource/NanumGothicCoding.ttf")

        # 폰트 추가가 성공적이면 해당 폰트의 패밀리 이름을 가져와서 설정
        if font_id != -1:
            font_families = font_database.applicationFontFamilies(font_id)
            if font_families:
                font_name = font_families[0]
                font = QFont(font_name, 10)
        else:
            print("Failed to load the font.")
            font = QFont("Arial", 10)  # 실패시 기본 폰트로 설정


        # Layout and Widgets
        layout = QVBoxLayout()

        self.table_conn = QTableWidget()
        self.table_conn.setEditTriggers(QTableWidget.NoEditTriggers)  # 셀 수정 불가능하게 설정
        self.table_conn.cellDoubleClicked.connect(self.on_cell_double_clicked)  # 셀 더블 클릭 이벤트 연결

        self.load_data_to_table(login_data)

        btn_layout = QHBoxLayout()

        connect_btn = QPushButton("연결")
        connect_btn.clicked.connect(self.on_connect)

        delete_btn = QPushButton("삭제")
        delete_btn.clicked.connect(self.on_delete)

        close_btn = QPushButton("닫기")
        close_btn.clicked.connect(self.close)

        btn_layout.addWidget(connect_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addWidget(close_btn)

        layout.addWidget(self.table_conn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.set_font_for_all_widgets(font)
        self.table_conn.resizeColumnsToContents()

    def set_font_for_all_widgets(self, font, widget=None):
        if widget is None:
            widget = self
        try:
            widget.setFont(font)

            # 자식 위젯들에 대해서도 동일한 작업 수행
            for child in widget.children():
                self.set_font_for_all_widgets(font, child)
        except Exception as e:
            pass
            #print(f"Failed to set font for widget {widget}: {e}")

    def load_data_to_table(self, data):
        self.table_conn.setRowCount(len(data))
        self.table_conn.setColumnCount(len(data[0]) if data else 0)
        for row, item in enumerate(data):
            for col, (key, value) in enumerate(item.items()):
                table_item = QTableWidgetItem()
                if key == "password":
                    table_item.setText("**")  # 화면에 표시할 값을 설정
                else:
                    table_item.setText(str(value))
                self.table_conn.setItem(row, col, table_item)
        if data:
            self.table_conn.setHorizontalHeaderLabels(data[0].keys())



    def on_connect(self):
        # 연결 로직 구현
        current_row = self.table_conn.currentRow()
        print(current_row,'current_row')
        if current_row == -1:
            QMessageBox.warning(self, "Warning", "선택된 행이 없습니다.")
        else:
            # 선택한 로우의 key(헤더)와 value를 dic에 담기
            try:
                headers = [self.table_conn.horizontalHeaderItem(col).text() for col in range(self.table_conn.columnCount())]
                selected_data = {}

                # 선택된 alias 값 가져오기
                alias_column_index = headers.index('alias')
                selected_alias = self.table_conn.item(current_row, alias_column_index).text()

                # self.login_data에서 해당 alias에 해당하는 데이터 검색
                for data in self.login_data:
                    if data.get('alias') == selected_alias:
                        for header in headers:
                            # data 딕셔너리에 header 이름에 해당하는 값이 있으면 가져와서 selected_data에 저장
                            if header in data:
                                selected_data[header] = data[header]
                        break

                # 여기서 dic을 부모 윈도우로 넘기는 부분을 구현
                # 예를 들어, 부모 윈도우의 `receive_data`라는 메소드로 넘긴다고 가정하면:
                self.parent().receive_conn(selected_data)

                self.close()
            except Exception as e:
                print(traceback.format_exc())

    def on_delete(self):
        # 삭제 로직 구현
        current_row = self.table_conn.currentRow()
        if current_row == -1:
            QMessageBox.warning(self, "Warning", "선택된 행이 없습니다.")
            return


        selected_alias = self.table_conn.item(current_row, 0).text()  # 여기서 0은 alias의 열 인덱스입니다. 필요한 경우 변경하세요.
        self.parent().delete_hist_encrypted_login_info(selected_alias)
        self.table_conn.removeRow(current_row)

    def on_cell_double_clicked(self, row, column):
        # 셀 더블 클릭 시 연결 로직 구현
        # 예를 들어 선택된 행의 데이터를 가져오려면:
        self.on_connect()






class LoginWindow(QWidget):

    def __init__(self):
        super().__init__()

        # 아이콘 설정
        self.setWindowIcon(QIcon("./resource/sut_icon.ico"))
        # GUI 구성
        self.init_ui()

    def init_ui(self):
        # 위젯 생성
        # 폰트 추가
        font_database = QFontDatabase()
        font_id = font_database.addApplicationFont("./resource/NanumGothicCoding.ttf")

        # 폰트 추가가 성공적이면 해당 폰트의 패밀리 이름을 가져와서 설정
        if font_id != -1:
            font_families = font_database.applicationFontFamilies(font_id)
            if font_families:
                font_name = font_families[0]
                font = QFont(font_name, 10)
        else:
            print("Failed to load the font.")
            font = QFont("Arial", 10)  # 실패시 기본 폰트로 설정

        self.label_alias = QLabel('별칭*:', self)
        self.input_alias = QLineEdit(self)

        self.label_dbms = QLabel('DBSM:',self)
        self.combo_dbms = QComboBox()
        self.combo_dbms.addItem("MySQL")
        self.combo_dbms.addItem("MariaDB")

        self.label_host = QLabel('Host:', self)
        self.input_host = QLineEdit(self)

        self.label_port = QLabel('Port:', self)
        self.input_port = QLineEdit(self)
        self.input_port.setText('')  # MariaDB의 기본 포트

        self.label_user = QLabel('User:', self)
        self.input_user = QLineEdit(self)

        self.label_password = QLabel('Password:', self)
        self.input_password = QLineEdit(self)
        self.input_password.setEchoMode(QLineEdit.Password)  # 비밀번호 마스킹

        self.label_database = QLabel('Database:', self)
        self.input_database = QLineEdit(self)

        self.label_color = QLabel('Color:', self)
        self.combo_color = QComboBox(self)
        colors = {
            "LightGray": (211, 211, 211),
            "Red": (255, 0, 0),
            "Yellow": (255, 255, 0),
            "Blue": (0, 0, 255),
            "Orange": (255, 165, 0),
            "Pink": (255, 192, 203),
            "Green": (0, 128, 0)
        }

        for name, rgb in colors.items():
            self.combo_color.addItem(name)
            index = self.combo_color.count() - 1
            self.combo_color.setItemData(index, rgb)

        self.combo_color.currentIndexChanged.connect(self.updateColorLabel)

        # 콤보박스 초기 선택 값을 'Gray'로 설정
        self.combo_color.setCurrentIndex(self.combo_color.findText("LightGray"))
        self.updateColorLabel(0)

        self.button_login = QPushButton('Login', self)
        self.button_login.clicked.connect(self.handle_login)
        self.button_show_connection = QPushButton('Show Connection', self)
        self.button_show_connection.clicked.connect(self.show_connection)



        # 오른쪽 레이아웃에 들어갈 위젯
        self.label_about = QLabel('StatUp Tuning(SUT)', self)
        self.text_about = QTextEdit(self)
        about_str = "MySQL, MariaDB의 SQL 튜닝을 위한 툴입니다.\n"
        about_str = about_str + " - Release: Ver.0.1.5 - 2023.10.23\n"
        about_str = about_str + " - Copyright: 유일환(스윗보스)\n"
        about_str = about_str + " - 툴 정보: https://sweetquant.tistory.com/457\n"
        about_str = about_str + " - 확인된 지원 DBMS Version MySQL 8, MariaDB 10.0.5\n"
        about_str = about_str + "   : MySQL 8\n"
        about_str = about_str + "   : MariaDB 10.0.5\n"
        about_str = about_str + " - MySQL을 활용한 튜닝 입문 교육 정보\n"
        about_str = about_str + "   : https://cafe.naver.com/dbian/6958\n"
        self.text_about.setText(about_str)
        self.text_about.setReadOnly(True)  # 읽기 전용으로 설정

        image_path = "./resource/sut_logo.png"  # 이미지 파일 경로를 지정하세요.
        image_label = QLabel(self)
        pixmap = QPixmap(image_path)

        new_width = int(pixmap.width() * 0.15)
        new_height = int(pixmap.height() * 0.15)
        scaled_pixmap = pixmap.scaled(new_width, new_height, Qt.KeepAspectRatio)

        image_label.setPixmap(scaled_pixmap)

        # 오른쪽 레이아웃 설정
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.label_about)
        right_layout.addWidget(self.text_about)
        right_layout.addWidget(image_label)

        # 메인 레이아웃 설정
        main_layout = QHBoxLayout()

        # 왼쪽 레이아웃 설정
        left_layout = QVBoxLayout()

        left_layout.addWidget(self.button_show_connection)
        left_layout.addWidget(self.label_alias)
        left_layout.addWidget(self.input_alias)
        left_layout.addWidget(self.label_dbms)
        left_layout.addWidget(self.combo_dbms)
        left_layout.addWidget(self.label_host)
        left_layout.addWidget(self.input_host)
        left_layout.addWidget(self.label_port)
        left_layout.addWidget(self.input_port)
        left_layout.addWidget(self.label_user)
        left_layout.addWidget(self.input_user)
        left_layout.addWidget(self.label_password)
        left_layout.addWidget(self.input_password)
        left_layout.addWidget(self.label_database)
        left_layout.addWidget(self.input_database)
        left_layout.addWidget(self.label_color)
        left_layout.addWidget(self.combo_color)
        left_layout.addWidget(self.button_login)

        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)
        self.setLayout(main_layout)


        # 창을 화면 중앙에 위치시키는 코드
        screen_geometry = QDesktopWidget().screenGeometry()  # 현재 화면의 해상도 가져오기
        window_geometry = self.geometry()  # 현재 창의 geometry 가져오기
        x = (screen_geometry.width() - window_geometry.width()) / 2
        y = (screen_geometry.height() - window_geometry.height()) / 2
        self.move(x, y)  # 창 위치 조정

        # 창 설정
        self.setWindowTitle('Login to MariaDB')
        self.resize(700, 250)  # 창 크기 조정
        # last_login.sut 파일이 있으면 연결 정보를 가져와서 채우기
        if os.path.exists('last_login.sut'):
            self.load_last_login()

        self.set_font_for_all_widgets(font)
        self.setWindowTitle('SUT - StartUP Tuning')  # 윈도우 제목 설정
        self.show()

    def updateColorLabel(self, index):
        try:
            color_rgb = self.combo_color.itemData(index)
            color_style = "QLabel { background-color: rgb(%d, %d, %d); }" % color_rgb
            self.label_color.setStyleSheet(color_style)
        except Exception as e:
            print(traceback.format_exc())

    def set_font_for_all_widgets(self, font, widget=None):
        if widget is None:
            widget = self
        try:
            widget.setFont(font)

            # 자식 위젯들에 대해서도 동일한 작업 수행
            for child in widget.children():
                self.set_font_for_all_widgets(font, child)
        except Exception as e:
            pass
            #print(f"Failed to set font for widget {widget}: {e}")

    def show_connection(self):
        dialog = ConnectionDialog(self.load_encrypted_login_hist(),self)
        dialog.exec_()

    def receive_conn(self,login_dic):
        self.fill_login_info(login_dic)

    def handle_login(self):
        alias = self.input_alias.text().strip()
        if alias == "":
            error_msg = QMessageBox(self)
            error_msg.setIcon(QMessageBox.Critical)
            error_msg.setWindowTitle("Connection Error")
            error_msg.setText(f"별칭을 입력해주세요.")
            error_msg.setStandardButtons(QMessageBox.Ok)
            error_msg.exec_()
            return

        # 입력된 정보를 db_dic에 저장
        db_dic = {
            'host': self.input_host.text().strip(),
            'port': int(self.input_port.text().strip()),
            'user': self.input_user.text().strip(),
            'password': self.input_password.text().strip(),
            'db': self.input_database.text().strip()
        }

        # pymysql을 사용하여 DB 연결 시도
        try:
            connection = pymysql.connect(**db_dic)
            # 연결 성공 시
            if connection:
                connection.close()

                # db_dic의 모든 정보와 현재 선택된 DBMS와 alias 정보를 포함하는 새로운 딕셔너리 db_full_dic를 생성
                db_full_dic = {
                    'alias': self.input_alias.text(),
                    'dbms': self.combo_dbms.currentText(),
                }
                # db_dic의 내용을 db_full_dic에 추가
                db_full_dic.update(db_dic)
                # color를 추가
                db_full_dic['color'] = self.combo_color.currentText()

                self.save_encrypted_login_info(db_full_dic)

                # 로그인에 성공하면 MainWindow를 연다
                self.main_window = SQLExecutorApp(db_full_dic)
                self.main_window.show()  # MainWindow 보이게 하기
                self.main_window.showMaximized()
                self.close()  # LoginWindow 닫기

        except Exception as e:
            # 에러 메시지를 QMessageBox로 보여주기
            error_msg = QMessageBox(self)
            error_msg.setIcon(QMessageBox.Critical)
            error_msg.setWindowTitle("Connection Error")
            error_msg.setText(f"Error: {e}")
            error_msg.setStandardButtons(QMessageBox.Ok)
            error_msg.exec_()

    def save_encrypted_login_info(self, db_full_dic):
        key = em.generate_key()
        encrypted_info = em.encrypt_message(json.dumps(db_full_dic), key)

        with open('last_login.sut', 'wb') as file:
            file.write(key + b'\n' + encrypted_info)
        self.save_hist_encrypted_login_info(db_full_dic)

    # 로그인 히스토리 정보 저장(미자믹 db_full_dic을 추가해서 처리)
    def save_hist_encrypted_login_info(self, db_full_dic):
        # 이전 로그인 정보 불러오기
        previous_logins = self.load_encrypted_login_hist()

        # 같은 alias가 있는 이전 로그인 정보 제거
        previous_logins = [login for login in previous_logins if login.get('alias') != db_full_dic.get('alias')]
        #print("previous_logins----!!!")
        #print(previous_logins)
        # 새 로그인 정보 추가
        previous_logins.append(db_full_dic)

        # 업데이트된 리스트 암호화
        key = em.generate_key()
        encrypted_info = em.encrypt_message(json.dumps(previous_logins), key)

        # 암호화된 리스트 저장
        with open('hist_login.sut', 'wb') as file:
            file.write(key + b'\n' + encrypted_info)



    def load_encrypted_login_hist(self):
        try:
            with open('hist_login.sut', 'rb') as file:
                key = file.readline().strip()
                encrypted_info = file.readline().strip()
                decrypted_info_str = em.decrypt_message(encrypted_info, key)
                return json.loads(decrypted_info_str)
        except:
            return []

    def load_last_login(self):
        with open('last_login.sut', 'rb') as file:
            key = file.readline().strip()  # 첫 번째 줄은 키
            encrypted_info = file.readline().strip()  # 두 번째 줄은 암호화된 연결 정보

        # 복호화
        decrypted_info_str = em.decrypt_message(encrypted_info, key)
        #print('decrypted_info_str',decrypted_info_str)
        db_full_dic = json.loads(decrypted_info_str)
        self.fill_login_info(db_full_dic)

    def fill_login_info(self,db_full_dic):

        # 연결 정보 채우기
        try:
            self.input_alias.setText(str(db_full_dic['alias']))
            self.combo_dbms.setCurrentText(str(db_full_dic['dbms']))
            self.input_host.setText(str(db_full_dic['host']))
            self.input_port.setText(str(db_full_dic['port']))
            self.input_user.setText(str(db_full_dic['user']))
            self.input_password.setText(str(db_full_dic['password']))
            self.input_database.setText(str(db_full_dic['db']))
            self.combo_color.setCurrentText(str(db_full_dic['color']))

        except Exception as e:
            print(str(e))

    def delete_hist_encrypted_login_info(self, delete_alias):
        # 이전 로그인 정보 불러오기
        previous_logins = self.load_encrypted_login_hist()

        # 주어진 alias와 일치하는 로그인 정보 제거
        updated_logins = [login for login in previous_logins if login.get('alias') != delete_alias]

        # 업데이트된 리스트 암호화
        key = em.generate_key()
        encrypted_info = em.encrypt_message(json.dumps(updated_logins), key)

        # 암호화된 리스트 저장
        with open('hist_login.sut', 'wb') as file:
            file.write(key + b'\n' + encrypted_info)

