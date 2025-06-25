import json
import random
from datetime import datetime


def handler(event, context):
    try:
        print("Checking job status...")
        print(f"Event received: {json.dumps(event)}")

        job_details = event.get("job_details", {})
        job_id = job_details.get("job_id", "")
        if not job_id:
            return {"statusCode": 400, "error": "Job ID not found in event"}

        print(f"Checking status for job: {job_id}")
        status = job_details.get("status", "")

        if not status:
            return {"statusCode": 400, "error": "Status not found in event"}

        result_data = {}
        if status == "COMPLETED":
            result_data = {
                "output_s3_uri": f"s3://output-bucket/{job_id}/result.json",
                "completed_at": datetime.now().isoformat(),
                "processing_time_seconds": random.randint(30, 300),
            }
        else:
            result_data = {
                "output_s3_uri": None,
                "completed_at": None,
                "processing_time_seconds": None,
            }
            status = "IN_PROGRESS"

        print(f"Current status: {status}")

        return {
            "statusCode": 200,
            "status": status,
            "job_id": job_id,
            "result": result_data,
            "checked_at": datetime.now().isoformat(),
        }

    except Exception as e:
        print(f"Error checking status: {str(e)}")
        return {"statusCode": 500, "error": str(e), "status": "ERROR"}
