
# 🎬 Top-10-Movies Serverless Pipeline

Fetch the **IMDb Top 250**, pick the **10 highest‑rated** titles, enrich each one with
extra metadata from **OMDb**, and drop the results—cleanly versioned JSON
objects—into an S3 bucket.  
All of that happens **serverlessly** on AWS Free Tier, driven by two small
Lambda functions and an SQS queue.

<p align="center">
  <img src="https://img.shields.io/badge/AWS-Free%20Tier-brightgreen?logo=amazonaws">
  <img src="https://img.shields.io/badge/Lambda-Python%203.9-blue?logo=python">
</p>

---

## ✨ Why you’ll love it

* **One‑click deploy.** A single `./infra/deploy.sh` provisions IAM, SQS, both
  Lambdas and their triggers.
* **Zero‑maintenance.** EventBridge runs the pipeline daily; SQS scales the
  concurrency; IAM keeps the blast‑radius minimal.
* **Readable costs.** Everything fits the AWS Free Tier (< 1 M requests/mo, tiny
  storage).
* **Drop‑in JSONs.** Each object is named `01_tt0111161.json`, `02_…`—sorted and
  ready for downstream analytics or dashboards.

---

## 🗺️ Architecture (one‑glance)

```mermaid
graph TD
  A(EventBridge cron daily)
  B(GetTop10Movies Lambda)
  C(EnrichMoviesQueue SQS)
  D(EnrichAndStoreMovie Lambda)
  E(S3 Bucket top-movies-enriched-\$ACCOUNT_ID)

  A -->|Invoke| B
  B -->|10 messages| C
  C -->|batch of 5| D
  D -->|JSON Put| E
```

*GetTop10Movies* never touches S3 permissions—downloads the public
Top 250 JSON directly.

---

## 📁 Repo layout

```text
.
├── lambdas
│   ├── get_top10
│   │   ├── get_top10.py
│   │   └── requirements.txt      # requests
│   └── enrich_and_store
│       ├── enrich_and_store.py
│       └── requirements.txt      # requests
├── infra
│   ├── deploy.sh                 # full IaC‑lite bash deploy
│   └── policy.json               # generated at runtime
└── .env.sample                   # copy → .env with your IDs
```

---

## 🚀 Quick start

> Tested on **WSL Ubuntu 22.04** + **AWS CLI v2**.

```bash
# 0. Clone & enter
git clone https://github.com/yourname/top-10-movies-interview-sap.git
cd top-10-movies-interview-sap

# 1. Fill in .env
cp .env.exmaple .env                # edit ACCOUNT_ID, OMDB_API_KEY …
source .env

# 2. Deploy (≈ 1 min)
cd infra && ./deploy.sh            # creates/upgrades everything

# 3. Trigger once manually
aws lambda invoke   --function-name GetTop10Movies   --payload '{}' /dev/stdout   --region "$AWS_DEFAULT_REGION"

# 4. Watch objects appear
aws s3 ls s3://$ENRICH_BUCKET/ --region "$AWS_DEFAULT_REGION"
```

Daily cron is already scheduled; each run costs < 1¢.

---

## 🔧 Environment variables

| Variable            | Description                                 | Example                                 |
|---------------------|---------------------------------------------|-----------------------------------------|
| `ACCOUNT_ID`        | Your AWS account number                     | `12345678910`                          |
| `AWS_DEFAULT_REGION`| Region for all resources                    | `sa-east-1` (São Paulo)                 |
| `QUEUE_URL`         | Full SQS URL                                | `https://sqs.sa-east-1.amazonaws.com/…` |
| `ENRICH_BUCKET`     | Private bucket for enriched movies          | `top-movies-enriched-$ACCOUNT_ID`       |
| `OMDB_API_KEY`      | Free key from <https://omdbapi.com>         | `abcd1234`                              |

---

## 🛠️ Local development tips


* **Tail logs quickly**

  ```bash
  aws logs tail /aws/lambda/EnrichAndStoreMovie --follow --region $AWS_DEFAULT_REGION
  ```

* **Empty buckets**

  ```bash
  aws s3 rm s3://$ENRICH_BUCKET/ --recursive --region $AWS_DEFAULT_REGION
  ```

---

## 💸 Cost control (Free‑Tier‑friendly)

| Service      | Free Tier | Typical per run |
|--------------|-----------|-----------------|
| Lambda       | 1 M req / mo | < 0.0002 USD |
| SQS          | 1 M req / mo | negligible |
| S3           | 5 GB / mo    | < 50 kB total |
| EventBridge  | 100 k events / mo | ~30 events |
