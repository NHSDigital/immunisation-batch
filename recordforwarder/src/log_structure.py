import logging
import json
import time
from datetime import datetime
from functools import wraps
from log_firehose import Forwarder_FirehoseLogger
from utils_for_record_forwarder import extract_file_key_elements


logging.basicConfig()
logger = logging.getLogger()
logger.setLevel("INFO")

firehose_logger = Forwarder_FirehoseLogger()


def forwarder_function_info(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        event = args[0] if args else {}
        print(f"EVENTTTT: {event}")

        supplier = event.get("supplier")
        operation_requested = event.get("operation_requested")
        message_id = event.get("row_id")
        file_key = event.get("file_key")
        vaccine_type = extract_file_key_elements(file_key).get("vaccine_type")
        log_data = {
            "function_name": func.__name__,
            "date_time": str(datetime.now()),
            "status": "success",
            "supplier": supplier,
            "file_key": file_key,
            "action_flag": operation_requested,
            "vaccine_type": vaccine_type,
            "message_id": message_id,
            "time_taken": None,
        }
        print(f"{log_data}")
        start_time = time.time()
        firehose_log = dict()

        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            log_data["time_taken"] = round(end_time - start_time, 5)
            print(f"LOGGGYG: {log_data}")
            logger.info(json.dumps(log_data))
            firehose_log["event"] = log_data
            firehose_logger.forwarder_send_log(firehose_log)
            print(f"RESULTTY: {result}")
            return result

        except Exception as e:
            log_data["status_code"] = 400
            log_data["error"] = str(e)
            log_data["status"] = "Fail"
            log_data.pop("message", None)
            end = time.time()
            log_data["time_taken"] = f"{round(end - start_time, 5)}s"
            logger.exception(json.dumps(log_data))
            firehose_log["event"] = log_data
            firehose_logger.forwarder_send_log(firehose_log)
            raise

    return wrapper
