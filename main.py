# 아나콘다 가상환경 들아거사. conda activate venv_StartUpTuning
# E:
# cd E:\PyProjectE\StartUpTuning
# pyinstaller --onefile --noconsole --name=SUT --icon=sut_icon.ico main.py
import openai
import pymysql
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QTableWidget, QTableWidgetItem, QSplitter, QTabWidget, QLineEdit, QLabel, QSpinBox, QComboBox, QMessageBox, QCheckBox, QDialog
import traceback
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QProgressDialog
from PyQt5.QtCore import Qt
import LoginWindow
# from execute_query import execute_query
from PyQt5.QtGui import QFont, QFontDatabase, QTextCursor, QIcon
import re

from PyQt5.QtGui import QClipboard

ignored_starts = ["explain", "analyze", "show" , "create","drop","alter","set"]

class BindVariableDialog(QDialog):
    # 사용자 정의 시그널을 정의합니다. 이 시그널은 처리된 바인드 변수를 전달합니다.
    bind_variables_processed = pyqtSignal(str,dict)
    past_bind = {}  # 클래스 레벨 변수로 선언

    def __init__(self, sql, parent=None):
        super().__init__(parent)

        # 폰트 추가
        font_database = QFontDatabase()
        font_id = font_database.addApplicationFont("./resource/NanumGothicCoding.ttf")

        # 폰트 추가가 성공적이면 해당 폰트의 패밀리 이름을 가져와서 설정
        if font_id != -1:
            font_families = font_database.applicationFontFamilies(font_id)
            if font_families:
                font_name = font_families[0]
                font = QFont(font_name, 11)
        else:
            print("Failed to load the font.")
            font = QFont("Arial", 11)  # 실패시 기본 폰트로 설정

        self.layout = QVBoxLayout()
        self.label = QLabel("바인드 변수를 입력하세요. (예: @변수명 = 값)")
        self.param_edit = QTextEdit()
        self.ok_button = QPushButton("완료")
        self.cancel_button = QPushButton("취소")

        # 폰트가 제공되면 각 위젯에 폰트를 설정합니다.
        if font is not None:
            self.label.setFont(font)
            self.param_edit.setFont(font)
            self.ok_button.setFont(font)
            self.cancel_button.setFont(font)

        self.layout.addWidget(self.label)
        self.layout.addWidget(self.param_edit)
        self.layout.addWidget(self.ok_button)
        self.layout.addWidget(self.cancel_button)
        self.setLayout(self.layout)

        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.ok_button.clicked.connect(self.process_bind_variables)
        self.run_sql = sql
        self.setBindList()

    def setBindList(self):
        # 정규 표현식을 사용하여 @로 시작하는 단어를 찾습니다.
        bind_vars = re.findall(r'@\w+', self.run_sql)
        # 중복 제거
        bind_vars = list(set(bind_vars))

        # 각 바인드 변수에 대해, line_edit에 "SET @VARNAME = VALUE;" 형식으로 추가합니다.
        bind_var_text_list = []
        for var in bind_vars:
            # past_bind에서 해당 변수의 값을 가져오기
            value = BindVariableDialog.past_bind.get(var[1:])  # var[1:]은 '@' 제거
            if value:
                bind_var_text_list.append(f"SET {var} = '{value}';")
            else:
                bind_var_text_list.append(f"SET {var} = '';")

        bind_var_text = '\n'.join(bind_var_text_list)
        self.param_edit.setText(bind_var_text)

    def process_bind_variables(self):
        try:
            bind_variable_strs = self.param_edit.toPlainText().split('\n')
            bind_variables = {}
            for var_str in bind_variable_strs:
                # "SET @VARNAME = '';" 형식의 문자열에서 변수 이름과 값을 추출합니다.
                parts = var_str.split('=')
                if len(parts) == 2:
                    var_name = parts[0].strip().replace('SET ', '').replace('@', '')
                    var_value = parts[1].strip().replace(';', '').replace("'", "")
                    bind_variables[var_name] = var_value

                    # var_name과 var_value를 past_bind에 저장 (또는 업데이트)
                    BindVariableDialog.past_bind[var_name] = var_value

            # 처리된 바인드 변수를 시그널을 통해 전달합니다.
            self.bind_variables_processed.emit(self.run_sql, bind_variables)
            self.accept()
        except Exception as e:
            print(traceback.format_exc())



def execute_sql(sql, fetch_size, db_conn, param_dic={}):
    # DB 연결
    cursor = db_conn.cursor()
    try:
        # SQL 실행
        print('before----------------')
        print(sql)
        print(param_dic)

        # param_dic에 요소가 있으면, @VARNAME을 %s로 변경하고, 해당 부분에 param_dic의 값이 들어가도록 변경합니다.
        if param_dic:
            sql = sql.replace('%', '%%')
            placeholders = []
            # 정규 표현식을 사용하여 SQL 쿼리에서 @로 시작하는 단어를 찾습니다.
            for match in re.finditer(r'@\w+', sql):
                var_name = match.group()[1:]  # '@' 문자를 제거합니다.
                value = param_dic.get(var_name)
                if value is not None:
                    placeholders.append(value)
                    sql = sql.replace(match.group(), '%s', 1)  # 첫 번째 출현을 %s로 대체합니다.

            #sql = sql.replace('%%', '%')

            print('after-yes_bind---------------')
            print(sql)
            print(placeholders)
            cursor.execute(sql, placeholders)
        else:
            print('after-no_bind----------------')
            print(sql)
            cursor.execute(sql)

        # 결과 가져오기
        if fetch_size:
            result = cursor.fetchmany(fetch_size)
        else:
            result = cursor.fetchall()

        print('result------------------------')
        print(result)
        if result is None or not result:
            if sql.lstrip().lower().startswith("select"):
                headers = ['Result']
                result = (('No-Data',),)
            else:
                headers = ['Message']
                result = (('Completed',),)
        else:
            headers = [desc[0] for desc in cursor.description]

        print(headers)
        print(result)
        return headers, result
    except pymysql.MySQLError as e:
        print(f"Error while sql running: {e}")
        error_message = e.args[1] if len(e.args) > 1 else str(e)
        error_tuple = ((error_message,),)
        return ['Error'], error_tuple

    except Exception as e:
        print(f"Error: {e}")
        error_message = e.args[1] if len(e.args) > 1 else str(e)
        error_tuple = ((error_message,),)
        return ['Error'], error_tuple

    finally:
        db_conn.commit()
        cursor.close()


class SQLEdit(QTextEdit):
    def __init__(self, parent, sql_executor):
        super(SQLEdit, self).__init__(parent)
        # 아이콘 설정
        self.setWindowIcon(QIcon("./resource/sut_icon.ico"))
        self.sql_executor = sql_executor


    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Tab:
            cursor = self.textCursor()
            current_line = cursor.block().text()
            current_position_in_line = cursor.positionInBlock()

            # 4의 배수로 스페이스를 추가
            spaces_needed = 4 - (current_position_in_line % 4)
            for _ in range(spaces_needed):
                cursor.insertText(" ")
            return
        elif event.key() in [Qt.Key_Enter, Qt.Key_Return] and event.modifiers() == Qt.ControlModifier:
            self.extract_text_from_cursor_position()
        else:
            super().keyPressEvent(event)

    def extract_text_from_cursor_position(self):
        try:
            text = self.toPlainText()
            cursor_position = self.textCursor().position()

            # 세미콜론으로 문장들을 나눕니다.
            #split_statements = text.split(";")
            # 주석 및 따옴표 안의 내용을 일치시키는 정규 표현식
            pattern = re.compile(r'--.*?$|".*?"|\'.*?\'|#.*?$', re.MULTILINE | re.DOTALL)

            # 주석 및 따옴표 안의 내용을 임시 문자로 대체
            def replacer(match):
                return match.group(0).replace(';', '\0')

            processed_text = pattern.sub(replacer, text)
            split_statements = [stmt.replace('\0', ';').strip() for stmt in processed_text.split(';') if stmt.strip()]

            # 발견된 ';' 이 없으면, "실행할 SQL이 없습니다. SQL 뒤에 ';'을 반드시 추가하세요." 라고 메세지 보여줘(Logic-1)
            # Logic-1: 발견된 ';' 이 없으면, 메세지를 보여줍니다.
            if not split_statements:
                error_msg = QMessageBox(self)
                error_msg.setIcon(QMessageBox.Critical)
                error_msg.setWindowTitle("SQL 에러")
                error_msg.setText(f"실행할 SQL이 없습니다. SQL 뒤에 ';'을 반드시 추가하세요.")
                error_msg.setStandardButtons(QMessageBox.Ok)
                error_msg.exec_()
                return

            # Logic-2: 발견된 ';' 이 단 하나라면, 해당 한 문장의 SQL을 그냥 실행합니다.
            if len(split_statements) == 1:
                run_sql = split_statements[0]
                #self.sql_executor.run_sql(split_statements[0])
                #return
            else:
                last_index = 0
                for stmt in split_statements:
                    start_index = text.find(stmt, last_index)
                    end_index = start_index + len(stmt)

                    # 현재 커서 위치가 해당 문장 범위 안에 있는지 확인합니다.
                    if start_index <= cursor_position <= end_index:
                        #self.sql_executor.run_sql(stmt)
                        run_sql = stmt
                        break
                    last_index = end_index

            # 필요로직
            # run_sql에 @가 있는지 확인, @가 있으면, 바인드 변수를 입력받는 별도 창 Open(Modal)
            # 바인드 입력창은 별도 클래스로 구성(pyqt5 사용)
            # @바인드변수명 = '' 과 같은 내용으로 값을 입력받으면 됨
            # 여러 변수가 있으면 엔터로 분리
            # 버튼은 완료, 취소 두개만
            # 필요로직

            if '@' in run_sql:
                dialog = BindVariableDialog(parent=self, sql=run_sql)
                # bind_variables_processed 시그널을 슬롯에 연결합니다.
                dialog.bind_variables_processed.connect(self.handle_bind_variables)

                dialog.exec_()
            else:
                self.sql_executor.run_sql(run_sql)

        except Exception as e:
            print(traceback.format_exc())


    # 부모 위젯에서 bind_variables_processed 시그널을 처리하는 메소드:
    def handle_bind_variables(self, run_sql, bind_variables):
        print('connect widget')
        self.sql_executor.run_sql(run_sql, bind_variables)


class QueryThread(QThread):

    queryFinished = pyqtSignal(tuple, tuple, list, list, str, dict)
    queryError = pyqtSignal(str)  # 에러 메시지를 전달하는 시그널 추가

    def __init__(self, query, conn, include_io, fetch_size ,param_dic):
        super().__init__()
        self.conn = conn
        self.query = query
        self.include_io = include_io
        self.fetch_size = fetch_size
        self.param_dic = param_dic

    def run(self):
        try:

            if self.include_io and not any(self.query.lstrip().lower().startswith(s) for s in ignored_starts):
                rows_read_before, buffer_pages_before, disk_reads_before = self.get_innodb_status()
            else:
                rows_read_before = buffer_pages_before = disk_reads_before = 0

            time_before = datetime.now()
            headers, result = execute_sql(self.query, fetch_size=self.fetch_size, db_conn=self.conn, param_dic=self.param_dic)
            time_after = datetime.now()

            if self.include_io and not any(self.query.lstrip().lower().startswith(s) for s in ignored_starts):
                rows_read_after, buffer_pages_after, disk_reads_after = self.get_innodb_status()
            else:
                rows_read_after = buffer_pages_after = disk_reads_after = 0

            self.queryFinished.emit((rows_read_before, buffer_pages_before, disk_reads_before, time_before), (rows_read_after, buffer_pages_after, disk_reads_after, time_after), headers, list(result),self.query,self.param_dic)
        except Exception as e:
            print(str(e))
            print(traceback.format_exc())
            self.queryError.emit(str(e))  # 예외 발생 시 시그널을 emit

    def get_innodb_status(self):
        """Get InnoDB status values."""
        h, r = execute_sql(sql="SHOW STATUS LIKE 'Innodb_rows_read'", fetch_size=None, db_conn=self.conn)
        rows_read = r[0][1]
        h, r = execute_sql(sql="SHOW STATUS LIKE 'Innodb_buffer_pool_read_requests'", fetch_size=None, db_conn=self.conn)
        buffer_pages = r[0][1]
        h, r = execute_sql(sql="SHOW STATUS LIKE 'Innodb_buffer_pool_reads'", fetch_size=None, db_conn=self.conn)
        disk_reads = r[0][1]

        return rows_read, buffer_pages, disk_reads





class SQLExecutorApp(QWidget):

    def __init__(self, dic_conn_full=None):
        super().__init__()

        # 아이콘 설정
        self.setWindowIcon(QIcon("./resource/sut_icon.ico"))
        self.dic_conn_full = dic_conn_full.copy()
        self.dic_conn = {key: dic_conn_full[key] for key in ['host','port','user','password','db'] if key in dic_conn_full}
        self.colors = {
            "LightGray": (211, 211, 211),
            "Red": (255, 0, 0),
            "Yellow": (255, 255, 0),
            "Blue": (0, 0, 255),
            "Orange": (255, 165, 0),
            "Pink": (255, 192, 203),
            "Green": (0, 128, 0)
        }

        self.run_db_conn() # db연결 처리.

        # 폰트 추가
        font_database = QFontDatabase()
        font_id = font_database.addApplicationFont("./resource/NanumGothicCoding.ttf")

        # 폰트 추가가 성공적이면 해당 폰트의 패밀리 이름을 가져와서 설정
        if font_id != -1:
            font_families = font_database.applicationFontFamilies(font_id)
            if font_families:
                font_name = font_families[0]
                self.font = QFont(font_name, 11)
        else:
            print("Failed to load the font.")
            self.font = QFont("Arial", 11)  # 실패시 기본 폰트로 설정

        # Main Layout 설정
        main_layout = QHBoxLayout()

        # Left Layout 설정
        left_layout = QVBoxLayout()

        # SQL 입력을 위한 TextEdit
        self.sql_input = SQLEdit(self,self) #QTextEdit(self)
        self.sql_input.setAcceptRichText(False)
        # 가로 레이아웃 생성
        h_layout_exe_control = QHBoxLayout()
        #lbl_Execute_info = QLabel("SQL에 커서를 위치한 후 Ctrl+Enter 로 실행")
        lbl_fetch_size = QLabel("Fetch Size:")
        #h_layout_exe_control.addWidget(lbl_Execute_info)
        h_layout_exe_control.addWidget(lbl_fetch_size)
        self.fetch_size_sel = 30
        self.combo_fetch_size = QComboBox()
        self.combo_fetch_size.addItem("10")
        self.combo_fetch_size.addItem("30")
        self.combo_fetch_size.addItem("50")
        self.combo_fetch_size.addItem("100")
        self.combo_fetch_size.addItem("ALL")
        self.combo_fetch_size.setCurrentText(str(self.fetch_size_sel))
        self.combo_fetch_size.currentIndexChanged.connect(self.on_combo_fetch_size_changed)

        h_layout_exe_control.addWidget(self.combo_fetch_size)


        # "Time sec:" 라벨 추가
        time_label = QLabel("Time sec:")
        h_layout_exe_control.addWidget(time_label)
        # QLineEdit 위젯 추가 (변경 불가능하게 설정)
        self.time_line_edit = QLineEdit(self)
        self.time_line_edit.setReadOnly(True)
        h_layout_exe_control.addWidget(self.time_line_edit)


        # 위젯 넓이 비율 설정 (execute_button : 7, time_label : 1, time_line_edit : 2)
        # h_layout_exe_control.setStretchFactor(self.execute_button, 7)
        #h_layout_exe_control.setStretchFactor(lbl_fetch_size, 1)
        #h_layout_exe_control.setStretchFactor(self.combo_fetch_size, 1)
        #h_layout_exe_control.setStretchFactor(time_label, 1)
        #h_layout_exe_control.setStretchFactor(self.time_line_edit, 2)
        h_layout_exe_control.addStretch(1)

        # 결과 출력을 위한 TableWidget
        self.table_output = QTableWidget(self)

        # 헤더의 스타일 변경
        header_table_output = self.table_output.horizontalHeader()
        header_table_output.setStyleSheet("QHeaderView::section { background-color: lightgray }")

        # 결과 출력을 위한 TextEdit
        self.text_output = QTextEdit(self)
        self.text_output.setReadOnly(True)


        # tab_result 생성 및 위젯 추가
        self.tab_result = QTabWidget()
        self.tab_result.addTab(self.table_output, "Result-Table")
        self.tab_result.addTab(self.text_output, "Result-Text")

        h_layout_plan_control = QHBoxLayout()
        lbl_plan_control = QLabel("Plan 주요 항목만 보기")
        self.checkbox_plan_prio = QCheckBox()
        h_layout_plan_control.addWidget(lbl_plan_control)
        h_layout_plan_control.addWidget(self.checkbox_plan_prio)
        h_layout_plan_control.addStretch(1)

        # tab_plan 생성
        self.tab_plan = QTabWidget()
        self.plan_table = QTableWidget(self)  # Plan-Table 위젯
        # 헤더의 스타일 변경
        header_plan_table = self.plan_table.horizontalHeader()
        header_plan_table.setStyleSheet("QHeaderView::section { background-color: lightgray }")

        self.plan_text = QTextEdit(self)  # Plan-Text 위젯
        self.plan_tree = QTextEdit(self)  # Plan-tree 위젯

        self.tab_plan.addTab(self.plan_table, "Plan-Table")
        self.tab_plan.addTab(self.plan_text, "Plan-Text")
        self.tab_plan.addTab(self.plan_tree, "Plan-Tree")

        lbl_msg = "SQL에 커서를 위치한 후 Ctrl+Enter 로 실행"
        lbl_msg = lbl_msg + "\n - StartUP Tuning은 문장 단위 Auto commit입니다. CUD 작업에 주의하세요."
        lbl_msg = lbl_msg + "\n - 바인드 변수는 SQL 자체에 '@변수명'과 같이 사용하세요. SQL을 실행하면 바인드값 입력창이 뜹니다."
        label_sql = QLabel(lbl_msg)  # "SQL" 레이블 추가

        splitter = QSplitter(Qt.Vertical)  # 가로 방향의 스플리터 생성

        # 첫 번째 묶음
        widget1 = QWidget()
        layout1 = QVBoxLayout()
        layout1.addWidget(label_sql)
        layout1.addWidget(self.sql_input)
        widget1.setLayout(layout1)

        # 두 번째 묶음
        widget2 = QWidget()
        layout2 = QVBoxLayout()
        layout2.addLayout(h_layout_exe_control)  # 가로 레이아웃을 주 레이아웃에 추가
        layout2.addWidget(self.tab_result)
        widget2.setLayout(layout2)

        # 세 번째 묶음
        widget3 = QWidget()
        layout3 = QVBoxLayout()
        layout3.addLayout(h_layout_plan_control)
        layout3.addWidget(self.tab_plan)
        widget3.setLayout(layout3)

        # 각 위젯을 스플리터에 추가
        splitter.addWidget(widget1)
        splitter.addWidget(widget2)
        splitter.addWidget(widget3)

        left_layout.addWidget(splitter)  # 스플리터를 주 레이아웃에 추가

        # 오른쪽 위젯 설정
        right_layout = QVBoxLayout()
        self.label_conn_info = QLabel()
        # self.dic_conn에서 암호를 제외한 정보를 가져옵니다.
        conn_info = {k: v for k, v in self.dic_conn.items() if k != 'password'}
        # 정보를 세미콜론으로 구분하여 문자열로 변환합니다.
        conn_info_str = '; '.join([f"{k}: {v}" for k, v in conn_info.items()])
        conn_info_str = "[" + self.dic_conn_full.get('alias') + "] " + conn_info_str
        # 변환된 문자열을 QLabel에 설정합니다.
        self.label_conn_info.setText(conn_info_str)

        color_rgb = self.colors.get(self.dic_conn_full.get('color'))
        color_style = "QLabel { background-color: rgb(%d, %d, %d); }" % color_rgb
        self.label_conn_info.setStyleSheet(color_style)

        # Tab 설정
        self.tabs = QTabWidget()

        # Index 탭
        table_info_layout = QVBoxLayout()

        # Search Input and Button in a Horizontal Layout
        table_info_control = QHBoxLayout()
        self.input_index_search = QLineEdit(self)  # 한 줄 입력 위젯
        table_info_control.addWidget(self.input_index_search)

        self.index_search_button = QPushButton("Show Index", self)  # 검색 버튼
        self.index_search_button.clicked.connect(self.index_search)
        table_info_control.addWidget(self.index_search_button)

        self.table_search_button = QPushButton("Show Table", self)  # 검색 버튼
        self.table_search_button.clicked.connect(self.show_table)
        table_info_control.addWidget(self.table_search_button)

        self.show_ddl_button = QPushButton("Show DDL", self)  # 검색 버튼
        self.show_ddl_button.clicked.connect(self.show_ddl)
        table_info_control.addWidget(self.show_ddl_button)


        self.show_tab_info_clear = QPushButton("Clear", self)  # 검색 버튼
        self.show_tab_info_clear.clicked.connect(self.show_tab_info_clear_click)
        table_info_control.addWidget(self.show_tab_info_clear)


        # Add the horizontal layout to the main layout
        table_info_layout.addLayout(table_info_control)

        self.text_index_list = QTextEdit(self)  # 여러 줄을 보여주는 텍스트 박스
        self.text_index_list.setReadOnly(True)  # 읽기 전용으로 설정
        table_info_layout.addWidget(self.text_index_list)

        table_info_widget = QWidget()  # Index 탭의 위젯을 포함하기 위한 임시 위젯
        table_info_widget.setLayout(table_info_layout)
        self.tabs.addTab(table_info_widget, "Table Information")

        ##########################################
        # SQL Hist 탭
        ##########################################
        layout_sql_hist_control = QHBoxLayout()
        # Include Global I/O 라벨 추가
        label_io = QLabel("Include Global I/O:")
        layout_sql_hist_control.addWidget(label_io)
        # 체크박스 추가
        self.checkbox_io = QCheckBox()
        layout_sql_hist_control.addWidget(self.checkbox_io)
        layout_sql_hist_control.addStretch(1)
        self.show_hist_clear = QPushButton("Clear", self)  # 검색 버튼
        self.show_hist_clear.clicked.connect(self.show_hist_clear_click)
        layout_sql_hist_control.addWidget(self.show_hist_clear)
        self.text_sql_hist = QTextEdit(self)
        # QTextEdit을 읽기 전용으로 설정
        self.text_sql_hist.setReadOnly(True)
        # 배경색을 연한 회색으로 설정
        self.text_sql_hist.setStyleSheet("background-color: #f5f5f5;")  # #f5f5f5는 연한 회색 코드입니다.
        # Vertical layout to contain the control layout and the text edit
        layout_sql_hist_main = QVBoxLayout()
        layout_sql_hist_main.addLayout(layout_sql_hist_control)
        layout_sql_hist_main.addWidget(self.text_sql_hist)
        # Wrap the QVBoxLayout inside a QWidget to add it to the tab
        sql_hist_widget = QWidget()
        sql_hist_widget.setLayout(layout_sql_hist_main)
        self.tabs.addTab(sql_hist_widget, "SQL History")

        ##########################################
        # GPT Table
        ##########################################
        layout_gpt_control = QHBoxLayout()
        layout_gpt_main = QVBoxLayout()
        label_io = QLabel("API:")

        self.text_gpt_api_key = QLineEdit(self)
        self.text_gpt_api_key.setEchoMode(QLineEdit.Password)  # 비밀번호 마스킹
        self.text_gpt_api_key.setText('') # !!!!!! 빌드시 제거!!!!

        btn_ask_gpt = QPushButton(" Ask to GPT(Need API Key) ")
        btn_ask_gpt.clicked.connect(self.run_ask_gpt)

        layout_gpt_control.addWidget(label_io)
        layout_gpt_control.addWidget(self.text_gpt_api_key)
        layout_gpt_control.addWidget(btn_ask_gpt)
        layout_gpt_control.addStretch(1)

        self.text_gpt_q = QTextEdit(self)
        self.text_gpt_a = QTextEdit(self)
        self.text_gpt_a.setReadOnly(True)
        self.text_gpt_a.setStyleSheet("background-color: #f5f5f5;")  # #f5f5f5는 연한 회색 코드입니다.

        layout_sql_hist_control.addWidget(label_io)

        layout_gpt_main.addLayout(layout_gpt_control)
        layout_gpt_main.addWidget(self.text_gpt_q)
        layout_gpt_main.addWidget(self.text_gpt_a)
        gpt_main_widget = QWidget()
        gpt_main_widget.setLayout(layout_gpt_main)
        # self.tabs.addTab(gpt_main_widget, "GPT(Beta)")


        ##########################################
        # UI 컨트롤 레이아웃
        ##########################################
        layout_ui_control = QHBoxLayout()
        # Database 라벨 추가
        reconnect_button = QPushButton("재연결")
        reconnect_button.clicked.connect(self.run_db_conn)
        layout_ui_control.addWidget(reconnect_button)

        label_database = QLabel("Database:")
        layout_ui_control.addWidget(label_database)
        # Database 콤보박스 추가
        self.combo_current_db = QComboBox()
        layout_ui_control.addWidget(self.combo_current_db)

        # FontSize 라벨 추가
        label_font_size = QLabel("FontSize:")
        layout_ui_control.addWidget(label_font_size)
        # 스핀박스 추가 (8에서 20까지)
        self.spin_font_size = QSpinBox()
        self.spin_font_size.setRange(8, 20)
        self.spin_font_size.setValue(11)
        self.spin_font_size.valueChanged.connect(self.on_font_size_changed)
        layout_ui_control.addWidget(self.spin_font_size)

        # 오른쪽에 여백 추가
        layout_ui_control.addStretch(1)

        # 이후 필요한 다른 컨트롤들을 여기에 추가할 수 있습니다.

        right_layout.addWidget(self.label_conn_info)
        right_layout.addLayout(layout_ui_control)
        right_layout.addWidget(self.tabs)
        right_widget = QWidget()
        right_widget.setLayout(right_layout)

        # Splitter 설정
        splitter = QSplitter(self)
        left_widget = QWidget()  # left_layout을 위한 임시 위젯
        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        main_layout.addWidget(splitter)

        self.set_database()

        self.set_font_for_all_widgets()
        self.setLayout(main_layout)

        # 메인 윈도우 크기 설정
        self.resize(800, 600)

        # 조건 설정
        self.highlight_conditions = {
            'type': ['ALL', 'index']
        }

        self.setWindowTitle('SUT - StartUP Tuning')  # 윈도우 제목 설정

    def show_hist_clear_click(self):
        self.text_sql_hist.setText('')

    def show_tab_info_clear_click(self):
        self.text_index_list.setText('')

    def run_db_conn(self):
        # db_conn 처리
        try:
            self.conn.close()
        except Exception as e:
            pass

        try:
            self.conn = pymysql.connect(**self.dic_conn,autocommit=True)
        except Exception as e:
            print(f"Error: {e}")


    def set_database(self):
        sql = "SHOW DATABASES"
        _, result = execute_sql(sql, fetch_size=None, db_conn=self.conn, param_dic={})
        # result의 값들을 combo_current_db에 추가
        for item in result:
            self.combo_current_db.addItem(item[0])
        # 무조건 빈값 추가
        self.combo_current_db.addItem("")

        db_value = self.dic_conn.get('db')
        db_value_lower = db_value.lower()

        matching_text = None
        for i in range(self.combo_current_db.count()):
            item_text = self.combo_current_db.itemText(i)
            if db_value_lower == item_text.lower():
                matching_text = item_text
                break

        # 일치하는 값을 찾았으면 그 값을 콤보박스의 현재 선택값으로 설정
        if matching_text:
            self.combo_current_db.setCurrentText(matching_text)
            self.dic_conn['db'] = matching_text
        else:
            self.combo_current_db.setCurrentText("")  # 일치하는 값이 없으면 빈 값을 선택

        self.combo_current_db.currentIndexChanged.connect(self.on_combo_changed)

    def on_combo_fetch_size_changed(self, index):
        # 이 함수는 콤보박스 값이 변경될 때마다 호출됩니다.
        selected_text = self.combo_fetch_size.itemText(index)
        if selected_text == 'ALL':
            self.fetch_size_sel = None
        else:
            self.fetch_size_sel = int(selected_text)


    def on_combo_changed(self, index):
        # 이 함수는 콤보박스 값이 변경될 때마다 호출됩니다.
        selected_text = self.combo_current_db.itemText(index)
        self.dic_conn['db'] = selected_text
        sql = 'USE ' + self.dic_conn['db'] + ';'
        execute_sql(sql,None,self.conn,{}) # change db



    def on_font_size_changed(self ,value):
        # 현재 설정된 폰트의 크기를 스핀박스의 값으로 변경
        self.font.setPointSize(value)
        self.set_font_for_all_widgets()

    def set_font_for_all_widgets(self, widget=None):
        if widget is None:
            widget = self
        try:
            widget.setFont(self.font)

            # 위젯이 QTableWidget인 경우, 헤더에도 폰트 적용
            if isinstance(widget, QTableWidget):
                widget.horizontalHeader().setFont(self.font)
                widget.verticalHeader().setFont(self.font)

            # 자식 위젯들에 대해서도 동일한 작업 수행
            for child in widget.children():
                self.set_font_for_all_widgets(child)
        except Exception as e:
            pass


    def run_ask_gpt(self):

        api_key = self.text_gpt_api_key.text()
        if api_key == "":
            error_msg = QMessageBox(self)
            error_msg.setIcon(QMessageBox.Critical)
            error_msg.setWindowTitle("GPT 에러")
            error_msg.setText("유료 OpenAI API 키가 필요합니다.")
            error_msg.setStandardButtons(QMessageBox.Ok)
            error_msg.exec_()
            return
        else:
            openai.api_key = api_key

        try:
            # ProgressDialog 생성
            progress = QProgressDialog(self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setWindowFlags(progress.windowFlags() & ~Qt.WindowContextHelpButtonHint)  # 컨텍스트 헬프 버튼 제거
            progress.setCancelButton(None)  # 취소 버튼 제거
            progress.setMinimumDuration(0)  # 대화 상자 즉시 표시
            # progress.setRange(0, 100)  # 진행 범위 설정

            # 레이블 텍스트와 창 제목 설정
            # progress.setLabelText("GPT에게 질문중")
            progress.setWindowTitle("GPT에 질문중 - 기다려주세요")
            progress.resize(progress.width() * 2, progress.height())
            progress.show()

            dbms = self.dic_conn_full.get('DBMS')
            sys_msg = f"너는 {dbms} 의 SQL을 성능 측면에서 검토만 하는 사람이야. SQL 성능 전문가에게 문의가 필요한 상황인지 결정해줘야해"
            user_msg = self.text_gpt_q.toPlainText()

            model = "gpt-3.5-turbo"
            # model = "gpt-4"
            response = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": user_msg},
                ]
            )
            # 생성된 텍스트 출력

            res = response.choices[0].message['content']
            res = res.replace(". ", "\n")
            res = res + "\n\n\n===========================================================\n\n\n"

            self.text_gpt_a.append(res)
        except Exception as e:
            print(traceback.format_exc())
            error_msg = QMessageBox(self)
            error_msg.setIcon(QMessageBox.Critical)
            error_msg.setWindowTitle("GPT 에러")
            error_msg.setText("GPT로 처리중 오류입니다. OpenAI 사이트를 사용해주세요.")
            error_msg.setStandardButtons(QMessageBox.Ok)
            error_msg.exec_()
        finally:
            progress.close()


    def chk_sql(self,query):
        # 주석을 제거
        query = re.sub(r'--.*', '', query)  # '-- ' 뒤의 주석 제거
        query = re.sub(r'#.*', '', query)  # '# ' 뒤의 주석 제거
        query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)  # '/* */' 사이의 주석 제거

        # 세미콜론 개수 확인
        if query.count(';') >= 2:
            error_msg = QMessageBox(self)
            error_msg.setIcon(QMessageBox.Critical)
            error_msg.setWindowTitle("SQL 에러")
            error_msg.setText(f"Error: 한 문장의 SQL만 실행 가능합니다.")
            error_msg.setStandardButtons(QMessageBox.Ok)
            error_msg.exec_()
            return False

        return True


    def run_sql(self,query,param_dic={}):
        try:
            # 초기화
            # 쿼리 유효성 체크

            # 쿼리 실행 쓰레드 시작
            # query = self.sql_input.toPlainText()

            if self.chk_sql(query) == False:
                return

            # QTableWidget 초기화
            self.table_output.setRowCount(0)  # 로우를 0으로 설정
            self.table_output.setColumnCount(0)  # 컬럼을 0으로 설정
            self.text_output.setPlainText('')  # 빈 텍스트로 설정
            self.plan_table.setRowCount(0)
            self.plan_table.setColumnCount(0)
            self.plan_text.setPlainText('')  # 빈 텍스트로 설정
            self.plan_tree.setPlainText('')
            self.time_line_edit.setText("")

            # QProgressDialog 생성
            self.progress = QProgressDialog("Executing SQL...", "Cancel", 0, 0, self)
            self.progress.setFont(self.font)
            self.progress.setWindowTitle("Executing")  # 여기서 제목 설정
            self.progress.setWindowModality(Qt.WindowModal)
            self.progress.resize(400, 150)  # 크기 설정: 너비 400px, 높이 150px
            self.progress.setWindowFlags(self.progress.windowFlags() & ~Qt.WindowContextHelpButtonHint & ~Qt.WindowCloseButtonHint)

            # QProgressDialog의 모든 자식 위젯들을 검색하여 중앙 정렬
            for widget in self.progress.findChildren(QWidget):
                try:
                    if widget.parent() == self.progress:
                        widget.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                except Exception as e:
                    pass

            include_io = self.checkbox_io.isChecked()

            if not any(query.lstrip().lower().startswith(s) for s in ignored_starts):
                self.query_thread = QueryThread(query, self.conn, include_io, self.fetch_size_sel,param_dic)
            else:
                self.query_thread = QueryThread(query,self.conn, include_io,None,param_dic)

            self.query_thread.queryFinished.connect(self.handle_query_results)
            self.query_thread.queryError.connect(self.handle_query_error)  # 에러 핸들러 연결
            self.progress.canceled.connect(self.stop_thread)
            self.query_thread.start()
            # Progress Dialog 표시
            self.progress.exec_()
        except Exception as e:
            print(traceback.format_exc())

    def handle_query_error(self, error_message):
        self.progress.close()  # Progress Dialog 닫기
        # 여기에 오류 메시지를 사용자에게 표시하는 코드를 추가, 예를 들어:
        self.text_output.append(f"Error: {error_message}")

    def stop_thread(self):
        # 쓰레드 종료
        try:
            self.query_thread.terminate()
            self.conn.close()
            self.run_db_conn()
        except Exception as e:
            print(traceback.format_exc())

    def handle_query_results(self, before_values, after_values, headers, result, query ,param_dic):
        try:

            # query = self.sql_input.toPlainText()

            rows_read_before, buffer_pages_before, disk_reads_before, time_before = before_values
            rows_read_after, buffer_pages_after, disk_reads_after, time_after = after_values

            # Close the progress dialog
            self.progress.close()
            if not query.lstrip().lower().startswith("explain") and not query.lstrip().lower().startswith("analyze"):
                # explain과 analyze가 아닐 때만, result에 결과 표시.
                self.display_text_result(headers, result)
                self.display_table_result(headers, result)
            else:
                self.print_execution_plan(headers,result) # explain이거나 analyze면 실행계획 부분에 결과를 출력하도록 처리.

            rows_read_diff = int(rows_read_after) - int(rows_read_before)
            buffer_pages_diff = int(buffer_pages_after) - int(buffer_pages_before)
            disk_reads_diff = int(disk_reads_after) - int(disk_reads_before)

            time_difference = time_after - time_before
            time_difference_in_seconds = time_difference.total_seconds()
            tree_plan = ''
            print(result)
            if not any(query.lstrip().lower().startswith(s) for s in ignored_starts):
                execution_plan = self.get_execution_plan(query,param_dic)
                if self.dic_conn_full.get('dbms') == 'MySQL':
                    tree_plan = self.get_execution_plan_tree(query,param_dic)
            else:
                execution_plan = None

            self.add_query_to_history(query, execution_plan, rows_read_diff, buffer_pages_diff, disk_reads_diff, time_difference_in_seconds,tree_plan)
        except Exception as e:
            print(traceback.format_exc())

    def add_query_to_history(self, query, execution_plan=None, rows_read_diff=None, buffer_pages_diff=None, disk_reads_diff=None, time_difference_in_seconds=None,tree_plan=None):
        """Add the given query to the SQL history widget."""
        # current_hist = self.text_sql_hist.toPlainText()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # 날짜 시간, SQL, 실행계획, stats_info 순서대로 정보를 구성
        updated_hist = f"Executed at [{current_time}]\n\n{query}\n\n"
        if execution_plan:
            updated_hist += f"{execution_plan}\n\n"
            if tree_plan is not None:
                updated_hist += f"{tree_plan}\n\n"

        stats_info = f" - Time sec: {time_difference_in_seconds:.6f}\n"
        self.time_line_edit.setText(f"{time_difference_in_seconds:.6f}")
        if self.checkbox_io.isChecked():
            stats_info = stats_info + f"\n - 아래 수치는 글로벌 수치입니다.(여러명이 동시 사용중인 DB에서는 맞지 않습니다.)\n   * Rows read: {rows_read_diff}\n   * Buffer pages: {buffer_pages_diff}\n   * Disk reads: {disk_reads_diff}\n" if rows_read_diff is not None and buffer_pages_diff is not None else ""

        updated_hist += f"{stats_info}\n\n=================================================================================\n\n"

        self.text_sql_hist.append(updated_hist)
        scrollbar = self.text_sql_hist.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())



    def display_text_result(self, headers, result):
        """Display text result in text_output widget."""
        formatted_result = self.format_result_to_string(headers, result)
        self.text_output.clear()
        self.text_output.append(formatted_result)

    def show_ddl(self):
        table_name = self.input_index_search.text().strip()

        # SQL 쿼리 실행
        sql = """
        SHOW CREATE TABLE {0};
        """.format(table_name)

        headers, result = execute_sql(sql=sql, fetch_size=None, db_conn=self.conn)
        ddl = result[0][1]

        # 기존 텍스트를 가져와서 새로운 결과와 함께 설정
        self.text_index_list.append("\n" + ddl + "\n\n")
        scrollbar = self.text_index_list.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def show_table(self):
        try:
            table_name = self.input_index_search.text().strip()
            db_value = self.dic_conn.get('db')
            info_txt = self.get_table_info(table_name,db_value)
            # 기존 텍스트를 가져와서 새로운 결과와 함께 설정
            self.text_index_list.append("\n" + info_txt + "\n\n")
            scrollbar = self.text_index_list.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

        except Exception as e:
            print(traceback.format_exc())


    def get_table_info(self,table_name,table_schema):
        sql_get_table = """
                    SELECT  T1.TABLE_SCHEMA ,T1.TABLE_NAME ,T1.ENGINE
                                ,ROUND((DATA_LENGTH) / 1024 / 1024, 2) AS TAB_MB
                                ,ROUND((INDEX_LENGTH) / 1024 / 1024, 2) AS IX_MB
                                ,T1.TABLE_COMMENT CMT
                        FROM    INFORMATION_SCHEMA.TABLES T1
                        WHERE   UPPER(T1.TABLE_NAME) = UPPER('{0}')
                        AND     UPPER(T1.TABLE_SCHEMA) = UPPER('{1}')
                        ORDER BY T1.TABLE_SCHEMA ,T1.TABLE_NAME;
                    """.format(table_name, table_schema)

        sql_get_columns = """
                    SELECT T1.ORDINAL_POSITION CNO
                          ,T1.COLUMN_NAME
                          ,T1.IS_NULLABLE IS_NULL
                          ,T1.COLUMN_KEY IS_KEY
                          ,T1.COLUMN_TYPE TYPE
                          ,T1.COLUMN_COMMENT CMT
                    FROM    INFORMATION_SCHEMA.COLUMNS T1
                    WHERE   UPPER(T1.TABLE_NAME) = UPPER('{0}')
                    AND     UPPER(T1.TABLE_SCHEMA) = UPPER('{1}')
                    ORDER BY T1.ORDINAL_POSITION;
                    """
        tab_headers, tab_result = execute_sql(sql=sql_get_table, fetch_size=None, db_conn=self.conn)
        info_txt = ""
        for tab_row in tab_result:
            tab_schema = tab_row[0]
            tab_name = tab_row[1]
            tab_row_tup = (tab_row,)
            formatted_table = self.format_result_to_string(tab_headers, tab_row_tup)
            sql_run = sql_get_columns.format(tab_name, tab_schema)
            col_headers, col_result = execute_sql(sql=sql_run, fetch_size=None, db_conn=self.conn)
            formatted_cols = self.format_result_to_string(col_headers, col_result)
            info_txt = info_txt + "\n\n" + formatted_table + "\n\n" + formatted_cols + "\n\n\n"

        return info_txt

    def index_search(self):
        # 입력된 테이블 이름 가져오기
        table_name = self.input_index_search.text().strip()
        db_value = self.dic_conn.get('db')

        formatted_result = self.get_index_info(table_name, db_value)
        # 기존 텍스트를 가져와서 새로운 결과와 함께 설정
        self.text_index_list.append("\n" + formatted_result + "\n\n")
        scrollbar = self.text_index_list.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def get_index_info(self,table_name,table_schema):
        # SQL 쿼리 실행
        sql = """
            SELECT T1.TABLE_SCHEMA, T1.TABLE_NAME, T1.INDEX_NAME, 
                   GROUP_CONCAT(T1.COLUMN_NAME ORDER BY T1.SEQ_IN_INDEX) AS IX_COLS,
                   (
                   SELECT  ROUND(stat_value * @@innodb_page_size / 1024 / 1024, 2)
                   FROM    mysql.innodb_index_stats x
                   WHERE   x.database_name = T1.table_schema
                   AND     x.table_name = T1.table_name
                   AND     x.index_name = T1.index_name
                   AND     x.stat_name = 'size') MB
            FROM information_schema.STATISTICS T1
            WHERE UPPER(T1.TABLE_NAME) = UPPER('{0}')
            AND   UPPER(T1.TABLE_SCHEMA) = UPPER('{1}')
            GROUP BY T1.TABLE_SCHEMA, T1.TABLE_NAME, T1.INDEX_NAME;
            """.format(table_name,table_schema)

        headers, result = execute_sql(sql=sql, fetch_size=None, db_conn=self.conn)
        formatted_result = self.format_result_to_string(headers, result)
        return formatted_result



    def format_result_to_string(self, headers, result):
        """Convert headers and result into formatted string."""
        try:
            # 최대 길이 계산
            max_lengths = []
            for idx, header in enumerate(headers):
                max_len = len(header) + self.count_korean_characters(header)
                for row in result:
                    item = str(row[idx])
                    item_length = len(item) + self.count_korean_characters(item)
                    if item_length > max_len:
                        max_len = item_length
                max_lengths.append(max_len + 2)

            # headers 출력
            header_str = "".join([header.ljust(max_lengths[idx]) for idx, header in enumerate(headers)])

            # 구분선 출력
            separator = "".join(['-' * (length - 2) + "  " for length in max_lengths])

            # 결과 출력
            rows = []
            for row in result:
                row_str = "".join([str(item).ljust(max_lengths[idx]) for idx, item in enumerate(row)])
                rows.append(row_str)

            return f"{header_str}\n{separator}\n" + "\n".join(rows)
        except Exception as e:
            print('format err',str(e))

    def count_korean_characters(self,s):
        return sum([1 for c in s if '가' <= c <= '힣'])


    def print_execution_plan(self,headers,result):

        if self.checkbox_plan_prio.isChecked():
            desired_headers = ["id", "select_type", "table", "type", "key", "ref", "rows","EXPLAIN"]
            # 체크박스가 선택되어 있는 경우
            if self.checkbox_plan_prio.isChecked():
                # 원하는 항목들의 인덱스를 찾는다
                indices = [headers.index(h) for h in desired_headers if h in headers]
                # 헤더와 결과를 필터링한다
                headers = [headers[i] for i in indices]
                result = [[row[i] for i in indices] for row in result]

        plan = self.format_result_to_string(headers, result)
        self.plan_text.setText(f"Execution Plan:\n{plan}")

        # Set the headers and result to plan_table
        self.plan_table.setColumnCount(len(headers))
        self.plan_table.setHorizontalHeaderLabels(headers)
        self.plan_table.setRowCount(len(result))

        for row_idx, row in enumerate(result):
            for col_idx, header in enumerate(headers):
                item = QTableWidgetItem(str(row[col_idx]))  # Use col_idx instead of header
                # 조건에 따라 스타일 변경
                if header in self.highlight_conditions and str(row[col_idx]) in self.highlight_conditions[header]:
                    item.setBackground(Qt.red)

                self.plan_table.setItem(row_idx, col_idx, item)

        # 컬럼 길이 재정리
        self.plan_table.resizeColumnsToContents()

        return f"Execution Plan:\n{plan}"


    def get_execution_plan(self, query,param_dic):
        """Get the execution plan for the given query."""
        headers, result = execute_sql(sql=f"EXPLAIN {query}",fetch_size=None,db_conn=self.conn,param_dic=param_dic)
        # Convert the result to a string format using format_result_to_string
        plan = self.print_execution_plan(headers,result)
        return plan

    def get_execution_plan_tree(self, query,param_dic):
        """Get the execution plan for the given query."""
        _, result = execute_sql(sql=f"EXPLAIN FORMAT = TREE {query}", fetch_size=None, db_conn=self.conn,param_dic=param_dic)
        plan_tree = result[0][0]
        self.plan_tree.setText(plan_tree)
        return plan_tree

    def display_table_result(self, headers, result):
        """Display table result in table_output widget."""
        self.table_output.setRowCount(0)
        self.table_output.setColumnCount(len(headers))
        self.table_output.setHorizontalHeaderLabels(headers)

        for row_data in result:
            row_number = self.table_output.rowCount()
            self.table_output.insertRow(row_number)
            for column_number, data in enumerate(row_data):
                self.table_output.setItem(row_number, column_number, QTableWidgetItem(str(data)))

        # 컬럼 길이 재정리
        self.table_output.resizeColumnsToContents()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = LoginWindow.LoginWindow()
    sys.exit(app.exec_())