import json
import boto3
import os
from urllib.request import urlopen

def lambda_handler(event, context):
    # Environment config
    raw_bucket = os.environ.get("RAW_BUCKET")
    raw_key = os.environ.get("RAW_KEY", "Top250Movies.json")
    queue_url = os.environ.get("QUEUE_URL")

    url = f"https://{raw_bucket}.s3.amazonaws.com/{raw_key}"

    # Debug: URL logging
    print(f"DEBUG: Downloading JSON from {url}")

    # Download JSON
    response = urlopen(url)
    data = json.loads(response.read().decode("utf-8"))

    # Filter TOP 10
    items = data.get("items", data)
    top10 = sorted(
        items,
        key=lambda m: float(m.get("imDbRating", 0)),
        reverse=True
    )[:10]

    # Send to SQS
    sqs = boto3.client("sqs")
    for movie in top10:
        sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(movie))

    return {"statusCode": 200, "body": f"Sent {len(top10)} movies to queue"}