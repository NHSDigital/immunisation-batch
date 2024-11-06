import logging
import json
import time
from datetime import datetime
from functools import wraps
from log_firehose import Forwarder_FirehoseLogger
from utils_for_record_forwarder import extract_vaccine_type_from_file_key


logging.basicConfig()
logger = logging.getLogger()
logger.setLevel("INFO")

firehose_logger = Forwarder_FirehoseLogger()


def forwarder_function_info(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        event = args[0] if args else {}

        log_data = {
            "function_name": func.__name__,
            "date_time": str(datetime.now()),
            "supplier": event.get("supplier"),
            "file_key": event.get("file_key"),
            "action_flag": event.get("operation_requested"),
            "vaccine_type": extract_vaccine_type_from_file_key(event.get("file_key")),
            "message_id": event.get("row_id"),
        }

        def send_logs(start_time, log_data, is_success):
            end_time = time.time()
            log_data["time_taken"] = f"{round(end_time - start_time, 5)}s"
            log_data["status"] = "success" if is_success else "Fail"
            logging_function = logger.info if is_success else logger.exception
            logging_function(json.dumps(log_data))
            firehose_logger.forwarder_send_log({"event": log_data})

        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            send_logs(start_time, log_data, is_success=True)
            return result

        except Exception as e:
            log_data["status_code"] = 400
            log_data["error"] = str(e)
            send_logs(start_time, log_data, is_success=False)
            raise

    return wrapper
