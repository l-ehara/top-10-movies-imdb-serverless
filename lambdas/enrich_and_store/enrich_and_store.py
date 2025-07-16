import json
import boto3
import os
import requests

def lambda_handler(event, context):
    enrich_bucket = os.environ.get("ENRICH_BUCKET")
    omdb_key = os.environ.get("OMDB_API_KEY")
    s3 = boto3.client("s3")

    for record in event.get("Records", []):
        movie = json.loads(record.get("body", '{}'))
        imdb_id = movie.get("id") or movie.get("imDbId")

        # Request OMDB API
        resp = requests.get(f"https://www.omdbapi.com/?apikey={omdb_key}&i={imdb_id}")
        extra = resp.json()

        # Enrich data
        movie.update(extra)

        # Save on S3
        s3.put_object(
            Bucket=enrich_bucket,
            Key=f"{imdb_id}.json",
            Body=json.dumps(movie),
            ContentType="application/json"
        )

    return {"statusCode": 200, "body": f"Total movies processed: {len(event.get('Records', []))}"}
