import pymysql

def execute_query(sql, fetch_size, dic_conn):
    """
    주어진 SQL을 실행하고 결과를 반환합니다.

    :param sql: 실행할 SQL문
    :param fetch_size: 가져올 레코드 수
    :param dic_conn: DB 연결 정보를 담은 딕셔너리
    :return: (headers, result)
    """
    # DB 연결
    connection = pymysql.connect(**dic_conn)
    cursor = connection.cursor()

    try:
        # SQL 실행
        print(sql)
        cursor.execute(sql)
        # 결과 가져오기
        if fetch_size:
            result = cursor.fetchmany(fetch_size)
        else:
            result = cursor.fetchall()
        # 헤더 가져오기

        if result is None or not result:
            headers = ['Message']
            result = (('Completed',),)
        else:
            headers = [desc[0] for desc in cursor.description]

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
        connection.commit()
        cursor.close()
        connection.close()
