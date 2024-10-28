import logging
import json
import time
from datetime import datetime
from functools import wraps
from log_firehose import FirehoseLogger


logging.basicConfig()
logger = logging.getLogger()
logger.setLevel("INFO")

firehose_logger = FirehoseLogger()


def forwarder_function_info(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        event = args[0] if args else {}
        print(f"EVENTTTT: {event}")

        supplier = event.get("supplier")
        fhir_json = event.get("fhir_json")
        operation_requested = event.get("operation_requested")
        message_id = event.get("row_id")
        vaccine_type = event.get("vaccine_type")
        file_key = event.get("file_key")
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

        log_data["message"] = kwargs.get("OPERATION_OUTCOME")
        log_data["message_id"] = kwargs.get("row_id")
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            log_data["time_taken"] = round(end_time - start_time, 5)
            print(f"LOGGGYG: {log_data}")
            logger.info(json.dumps(log_data))
            firehose_log["event"] = log_data
            firehose_logger.send_log(firehose_log)
            print(f"RESULTTY: {result}")
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
