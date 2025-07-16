import json
import boto3
import os
import requests

def lambda_handler(event, context):
    enrich_bucket = os.environ["ENRICH_BUCKET"]
    omdb_key      = os.environ["OMDB_API_KEY"]
    s3            = boto3.client("s3")

    for record in event.get("Records", []):
        # Normalize record["body"] into a JSON string
        raw_body = record.get("body", "{}")
        if isinstance(raw_body, str):
            body_str = raw_body
        elif isinstance(raw_body, (bytes, bytearray)):
            body_str = raw_body.decode("utf-8")
        else:
            body_str = json.dumps(raw_body)

        # Now parse safely
        movie = json.loads(body_str)

        imdb_id = movie.get("id") or movie.get("imDbId")
        if not imdb_id:
            print(f"WARNING: skipping record with no id: {movie}")
            continue

        # Enrich via OMDB
        resp = requests.get(f"https://www.omdbapi.com/?apikey={omdb_key}&i={imdb_id}")
        resp.raise_for_status()
        movie.update(resp.json())
        rank    = movie.get("rank", 0)
        imdb_id = movie["id"]
        filekey = f"{rank:02d}_{imdb_id}.json"

        # Write to S3
        s3.put_object(
            Bucket=enrich_bucket,
            Key=filekey,
            Body=json.dumps(movie),
            ContentType="application/json"
        )

    return {
        "statusCode": 200,
        "body": f"Processed {len(event.get('Records', []))} movies"
    }
