#!/usr/bin/env bash
set -e

# Load environment variables
env_file="../.env"
[ -f "$env_file" ] && source "$env_file"

# Set default region if not configured
REGION="${AWS_DEFAULT_REGION:-sa-east-1}"

echo "Using ACCOUNT_ID = $ACCOUNT_ID"
echo "Using region    = $REGION"

# 1) Generate infra/policy.json
cat > infra/policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject","s3:PutObject"],
      "Resource": [
        "arn:aws:s3:::${RAW_BUCKET}/*",
        "arn:aws:s3:::${ENRICH_BUCKET}/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["sqs:SendMessage","sqs:ReceiveMessage","sqs:DeleteMessage","sqs:GetQueueAttributes"],
      "Resource": "arn:aws:sqs:${REGION}:${ACCOUNT_ID}:EnrichMoviesQueue"
    }
  ]
}
EOF

# 2) Apply policy to the Role
echo "Applying policy to MoviesPipelineRole..."
aws iam put-role-policy \
  --role-name MoviesPipelineRole \
  --policy-name MoviesPipelinePolicy \
  --policy-document file://infra/policy.json \
  --region "$REGION"

# 3) Get the Role ARN
ROLE_ARN=$(aws iam get-role --role-name MoviesPipelineRole --query 'Role.Arn' --output text --region "$REGION")
echo "ROLE_ARN = $ROLE_ARN"

# 4) Package Lambdas
# 4.1 GetTop10Movies
echo "-- Packaging GetTop10Movies --"
rm -f get_top10.zip
cd lambdas/get_top10
zip -j ../../infra/get_top10.zip get_top10.py
cd ../../infra

# 4.2 EnrichAndStoreMovie
echo "-- Packaging EnrichAndStoreMovie --"
rm -f enrich_and_store.zip
cd ../lambdas/enrich_and_store
pip install --target . -r requirements.txt
zip -qr ../../infra/enrich_and_store.zip .
cd ../../infra

# 5) Deploy Lambda functions
# 5.1 GetTop10Movies
echo "-- Deploy/Update GetTop10Movies --"
if aws lambda get-function --function-name GetTop10Movies --region "$REGION" > /dev/null 2>&1; then
  aws lambda update-function-code \
    --function-name GetTop10Movies \
    --zip-file fileb://get_top10.zip \
    --region "$REGION"
else
  aws lambda create-function \
    --function-name GetTop10Movies \
    --runtime python3.9 \
    --handler get_top10.lambda_handler \
    --role "$ROLE_ARN" \
    --zip-file fileb://get_top10.zip \
    --timeout 30 \
    --memory-size 256 \
    --environment Variables="{RAW_BUCKET=${RAW_BUCKET},RAW_KEY=Top250Movies.json,QUEUE_URL=${QUEUE_URL}}" \
    --region "$REGION"
fi

# 5.2 EnrichAndStoreMovie
echo "-- Deploy/Update EnrichAndStoreMovie --"
if aws lambda get-function --function-name EnrichAndStoreMovie --region "$REGION" > /dev/null 2>&1; then
  aws lambda update-function-code \
    --function-name EnrichAndStoreMovie \
    --zip-file fileb://enrich_and_store.zip \
    --region "$REGION"
else
  aws lambda create-function \
    --function-name EnrichAndStoreMovie \
    --runtime python3.9 \
    --handler enrich_and_store.lambda_handler \
    --role "$ROLE_ARN" \
    --zip-file fileb://enrich_and_store.zip \
    --timeout 30 \
    --memory-size 256 \
    --environment Variables="{ENRICH_BUCKET=${ENRICH_BUCKET},OMDB_API_KEY=${OMDB_API_KEY}}" \
    --region "$REGION"
fi

# 6) Configure SQS trigger for EnrichAndStoreMovie
echo "-- Configuring SQS trigger --"
aws lambda create-event-source-mapping \
  --function-name EnrichAndStoreMovie \
  --batch-size 5 \
  --event-source-arn arn:aws:sqs:${REGION}:${ACCOUNT_ID}:EnrichMoviesQueue \
  --region "$REGION" || echo "Trigger already exists or benign error"

echo "Deploy completed successfully."
