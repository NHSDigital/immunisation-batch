import logging
import json
import time
from datetime import datetime
from functools import wraps
from log_firehose import FirehoseLogger
from utils_for_filenameprocessor import extract_file_key_elements

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel("INFO")

firehose_logger = FirehoseLogger()


def function_info(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        log_data = {
            "function_name": func.__name__,
            "date_time": str(datetime.now()),
            "status": "success",
            "supplier": "supplier",
            "file_key": "file_key",
            "vaccine_type": "vaccine_type",
            "message_id": "message_id",
            "time_taken": None,
        }

        start_time = time.time()
        firehose_log = dict()
        try:
            result = func(*args, **kwargs)
            end_time = time.time()  # End the timer
            log_data["time_taken"] = round(end_time - start_time, 5)

            log_data["status"] = result.get("statusCode")
            log_data["message"] = json.loads(result["body"])
            if isinstance(result, dict):
                file_info = result.get("file_info")

                if isinstance(file_info, list) and file_info:
                    first_file_info = file_info[0]
                    file_key = first_file_info.get("filename")
                    log_data["file_key"] = file_key
                    log_data["message_id"] = first_file_info.get("message_id")
                    file_key_elements = extract_file_key_elements(file_key)
                    log_data["supplier"] = file_key_elements["supplier"]
                    log_data["vaccine_type"] = file_key_elements["vaccine_type"]

            logger.info(json.dumps(log_data))
            firehose_log["event"] = log_data
            firehose_logger.send_log(firehose_log)
            return result

        except Exception as e:
            log_data["error"] = str(e)
            end = time.time()
            log_data["time_taken"] = f"{round(end - start_time, 5)}s"
            logger.exception(json.dumps(log_data))
            firehose_log["event"] = log_data
            firehose_logger.send_log(firehose_log)
            raise

    return wrapper
