import json
import boto3
import requests
import os

# Since the data is public no need to hide it
RAW_URL  = "https://top-movies.s3.eu-central-1.amazonaws.com/Top250Movies.json"
QUEUE_URL = os.environ["QUEUE_URL"]

sqs = boto3.client("sqs")

def lambda_handler(event, context):
    print(f"DEBUG: fetching {RAW_URL}")
    resp = requests.get(RAW_URL)
    resp.raise_for_status()
    json_data = resp.json()

    # extract the array of movies – Top250Movies.json uses the "items" field
    if isinstance(json_data, dict) and "items" in json_data:
        movies_list = json_data["items"]
    elif isinstance(json_data, list):
        movies_list = json_data
    else:
        raise ValueError(f"Unexpected JSON structure: {type(json_data)}")

    # Sort and rank top 10
    movies = sorted(
        movies_list,
        key=lambda m: float(m["imDbRating"]),
        reverse=True
    )[:10]
    print(f"DEBUG: found {len(movies)} movies with rating")
    
    for idx, movie in enumerate(movies, start=1):
        movie_with_rank = {**movie, "rank": idx}
        resp = sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(movie_with_rank)
        )
        print(f"DEBUG: sent rank={idx} id={movie['id']} msgId={resp['MessageId']}")

    return {
        "statusCode": 200,
        "body": f"Sent {len(movies)} movies to the SQS queue"
    }