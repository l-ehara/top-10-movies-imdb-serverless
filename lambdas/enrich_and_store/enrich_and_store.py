import json
import boto3
import os
import requests

def lambda_handler(event, context):
    # Environment configuration
    enrich_bucket = os.environ.get("ENRICH_BUCKET")
    omdb_key = os.environ.get("OMDB_API_KEY")
    s3 = boto3.client("s3")

    # Process each record from the SQS event
    for record in event.get("Records", []):
        movie = json.loads(record.get("body", "{}"))
        imdb_id = movie.get("id") or movie.get("imDbId")

        # Call the OMDB API to get additional data
        resp = requests.get(f"https://www.omdbapi.com/?apikey={omdb_key}&i={imdb_id}")
        extra = resp.json()

        # Enrich the movie record with extra data
        movie.update(extra)

        # Save the enriched movie record to S3
        s3.put_object(
            Bucket=enrich_bucket,
            Key=f"{imdb_id}.json",
            Body=json.dumps(movie),
            ContentType="application/json"
        )

    # Return success message
    return {
        "statusCode": 200,
        "body": f"Processed {len(event.get('Records', []))} movies"
    }