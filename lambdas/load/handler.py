import boto3, os, uuid, json

DB_SECRET_ARN = os.environ["DB_SECRET_ARN"]
CLUSTER_ARN   = os.environ["CLUSTER_ARN"]

rds_data = boto3.client("rds-data")

def handler(event, _ctx):
    vectors = event["embedded"]["Payload"]["embeddings"]
    bucket  = event["bucket"]
    key     = event["key"]

    sql = "INSERT INTO rag_embeddings (id, source_s3, chunk_no, embedding) VALUES "
    rows = []
    params = {}
    for i, vec in enumerate(vectors):
        rid = str(uuid.uuid4())
        rows.append(f"(:id{i}, :src{i}, :n{i}, :emb{i})")
        params[f"id{i}"]  = {"stringValue": rid}
        params[f"src{i}"] = {"stringValue": f"s3://{bucket}/{key}"}
        params[f"n{i}"]   = {"longValue": i}
        params[f"emb{i}"] = {"vectorValue": vec}

    sql += ", ".join(rows) + ";"

    rds_data.execute_statement(
        secretArn=DB_SECRET_ARN,
        resourceArn=CLUSTER_ARN,
        database="ragdemo",
        sql=sql,
        parameters=[{"name": k, **v} for k, v in params.items()]
    )
    return {"inserted": len(vectors)}
